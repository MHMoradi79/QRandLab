# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""ENT Test core.

Runs ENT entropy analysis on binary files using external ENT.exe tool.
"""

from __future__ import annotations
import sys

from pathlib import Path
from threading import Thread, Event as ThreadEvent, Lock
from typing import Optional, Dict, Any
import subprocess as sp
import re

from ..observer import Event
from ..types import InputFileMeta, OperationStatus, FileType


class EntTest:
    """ENT entropy analysis test using external ENT.exe."""

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_test = Event()
        
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self._process: Optional[sp.Popen] = None
        self._process_lock = Lock()  # Lock for thread-safe process access
        self.options = {
            "binary": False,    # -b: treat input as binary
            "chi_square": False,  # -c: chi-square test
            "fold": False,      # -f: fold upper/lower case
            "terse": False      # -t: terse output
        }
    
    def stop(self) -> None:
        """Signal the running thread to stop and terminate subprocess if running."""
        self._stop_event.set()
        # Terminate subprocess if running (thread-safe)
        with self._process_lock:
            if self._process is not None:
                try:
                    self._process.terminate()
                except Exception:
                    pass
                try:
                    self._process.kill()  # Force kill
                except Exception:
                    pass
    
    def force_stop(self) -> None:
        """Force stop - alias for stop() since it already kills the process."""
        self.stop()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    def set_options(self, binary: bool = False, chi_square: bool = False, fold: bool = False, terse: bool = False) -> None:
        """Configure ENT test options."""
        self.options = {
            "binary": binary,
            "chi_square": chi_square,
            "fold": fold,
            "terse": terse
        }

    def run_async(self) -> None:
        """Run ENT test asynchronously. Emits on_test with OperationStatus."""
        if self._thread and self._thread.is_alive():
            self.on_test.notify(status=OperationStatus(ok=False, message="ENT test already in progress"))
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        # Check stop before starting
        if self._stop_event.is_set():
            return
        # Validate input
        if not self.meta.file_path:
            self.on_test.notify(status=OperationStatus(ok=False, message="No file loaded"))
            return
        if self.meta.file_type != FileType.BINARY:
            self.on_test.notify(status=OperationStatus(ok=False, message="ENT requires BINARY file type"))
            return

        # Find ENT executable
        ent_path = self._resolve_ent_path()
        if not ent_path:
            self.on_test.notify(status=OperationStatus(ok=False, message="ENT.exe not found. Check third_party/bin/"))
            return

        # Build command
        options_str = ""
        if self.options["binary"]:
            options_str += "-b "
        if self.options["chi_square"]:
            options_str += "-c "
        if self.options["fold"]:
            options_str += "-f "
        if self.options["terse"]:
            options_str += "-t "

        cmd = f'"{ent_path}" {options_str}"{self.meta.file_path}"'

        try:
            # Use Popen to allow termination
            with self._process_lock:
                if self._stop_event.is_set():
                    return
                self._process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=True, text=True)
                process = self._process
            
            try:
                stdout, stderr = process.communicate()
                returncode = process.returncode
            except Exception:
                # Process was likely killed
                self.on_test.notify(status=OperationStatus(ok=False, message="ENT test cancelled"))
                return
            finally:
                with self._process_lock:
                    self._process = None
            
            # Check if stopped during execution
            if self._stop_event.is_set():
                self.on_test.notify(status=OperationStatus(ok=False, message="ENT test cancelled"))
                return
            
            # Parse the output to extract structured data
            parsed = self._parse_output(
                stdout, 
                self.options["terse"], 
                self.options["binary"],
                self.options["chi_square"]
            )
            
            payload = {
                "test_type": "ENT",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode,
                "options": self.options.copy(),
                "parsed": parsed
            }
            
            if returncode == 0:
                self.on_test.notify(status=OperationStatus(ok=True, message="ENT test completed", payload=payload))
            else:
                self.on_test.notify(status=OperationStatus(ok=False, message="ENT test failed", payload=payload))
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"ENT execution error: {e}"))

    def _resolve_ent_path(self) -> Optional[str]:
        if hasattr(sys, '_MEIPASS'):
            project_root = Path(sys._MEIPASS)
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
        clean_path = project_root / "third_party" / "bin" / "ent.exe"
        if clean_path.is_file():
            return str(clean_path)
        return None

    def _parse_output(self, stdout: str, is_terse: bool, is_bit_mode: bool, has_occurrence: bool) -> Dict[str, Any]:
        """Parse ENT output and extract structured data.
        
        Args:
            stdout: Raw ENT output
            is_terse: True if -t (terse/CSV) option was used
            is_bit_mode: True if -b (bit stream) option was used
            has_occurrence: True if -c (occurrence count) option was used
        
        Returns:
            Dict with parsed values
        """
        parsed = {
            "file_size": None,
            "file_unit": "bits" if is_bit_mode else "bytes",
            "entropy": None,
            "entropy_unit": "bits per bit" if is_bit_mode else "bits per byte",
            "compression_reduction": None,
            "chi_square": None,
            "chi_square_exceed_percent": None,
            "mean": None,
            "mean_ideal": 0.5 if is_bit_mode else 127.5,
            "monte_carlo_pi": None,
            "monte_carlo_error_percent": None,
            "serial_correlation": None,
            "occurrence_count": []  # List of (value, occurrences, fraction)
        }
        
        if not stdout:
            return parsed
        
        try:
            if is_terse:
                # Parse CSV format
                # Format: 0,File-bytes,Entropy,Chi-square,Mean,Monte-Carlo-Pi,Serial-Correlation
                #         1,50000000,7.998531,101424.947200,127.355064,3.144859,0.004139
                # With -c: 2,Value,Occurrences,Fraction
                #          3,0,135,0.004316
                lines = stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('1,'):
                        parts = line.split(',')
                        if len(parts) >= 7:
                            parsed["file_size"] = int(parts[1]) if parts[1] else None
                            parsed["entropy"] = float(parts[2]) if parts[2] else None
                            parsed["chi_square"] = float(parts[3]) if parts[3] else None
                            parsed["mean"] = float(parts[4]) if parts[4] else None
                            parsed["monte_carlo_pi"] = float(parts[5]) if parts[5] else None
                            parsed["serial_correlation"] = float(parts[6]) if parts[6] else None
                    # Parse occurrence count in terse mode
                    elif line.startswith('3,') and has_occurrence:
                        parts = line.split(',')
                        if len(parts) >= 4:
                            try:
                                value = int(parts[1])
                                occurrences = int(parts[2])
                                fraction = float(parts[3])
                                parsed["occurrence_count"].append((value, occurrences, fraction))
                            except (ValueError, IndexError):
                                pass
            else:
                # Parse verbose format using regex
                
                # Entropy: "Entropy = 7.998531 bits per byte."
                entropy_match = re.search(r'Entropy\s*=\s*([\d.]+)\s*bits per', stdout)
                if entropy_match:
                    parsed["entropy"] = float(entropy_match.group(1))
                
                # File size: "this 50000000 byte file" or "this 400000000 bit file"
                file_size_match = re.search(r'this\s+([\d]+)\s+(byte|bit)\s+file', stdout)
                if file_size_match:
                    parsed["file_size"] = int(file_size_match.group(1))
                
                # Compression: "reduce the size ... by 0 percent"
                compression_match = re.search(r'reduce the size.*?by\s+([\d.]+)\s*percent', stdout, re.DOTALL)
                if compression_match:
                    parsed["compression_reduction"] = float(compression_match.group(1))
                
                # Chi-square: "Chi square distribution for X samples is Y, and randomly would exceed this value less than Z percent"
                chi_match = re.search(r'Chi square distribution for [\d]+ samples is ([\d.]+),.*?less than ([\d.]+) percent', stdout, re.DOTALL)
                if chi_match:
                    parsed["chi_square"] = float(chi_match.group(1))
                    parsed["chi_square_exceed_percent"] = float(chi_match.group(2))
                
                # Mean: "Arithmetic mean value of data bytes is 127.3551" or "...data bits is 0.5005"
                mean_match = re.search(r'Arithmetic mean value of data (?:bytes|bits) is ([\d.]+)', stdout)
                if mean_match:
                    parsed["mean"] = float(mean_match.group(1))
                
                # Monte Carlo Pi: "Monte Carlo value for Pi is 3.144859326 (error 0.10 percent)"
                pi_match = re.search(r'Monte Carlo value for Pi is ([\d.]+).*?error ([\d.]+) percent', stdout)
                if pi_match:
                    parsed["monte_carlo_pi"] = float(pi_match.group(1))
                    parsed["monte_carlo_error_percent"] = float(pi_match.group(2))
                
                # Serial correlation: "Serial correlation coefficient is 0.004139"
                serial_match = re.search(r'Serial correlation coefficient is ([\d.\-]+)', stdout)
                if serial_match:
                    parsed["serial_correlation"] = float(serial_match.group(1))
                
                # Parse occurrence count in verbose mode
                # Format: "  0              135   0.004316" or "  0           125401   0.501139"
                if has_occurrence:
                    # Find lines with occurrence data (value, occurrences, fraction)
                    occ_pattern = re.compile(r'^\s*(\d+)\s+\S*\s+(\d+)\s+([\d.]+)\s*$', re.MULTILINE)
                    for match in occ_pattern.finditer(stdout):
                        try:
                            value = int(match.group(1))
                            occurrences = int(match.group(2))
                            fraction = float(match.group(3))
                            parsed["occurrence_count"].append((value, occurrences, fraction))
                        except (ValueError, IndexError):
                            pass
        except Exception:
            # If parsing fails, return partially filled dict
            pass
        
        return parsed
