# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""DieHarder Test core.

Runs DieHarder battery of randomness tests on binary files using external dieharder.exe tool.
Note: -a (all tests) option is not used - tests are always run individually.
"""

from __future__ import annotations
import sys

from pathlib import Path
from threading import Thread, Event as ThreadEvent, Lock
from typing import Optional, Dict, Any, List
from datetime import datetime
import subprocess as sp
import re

from ..observer import Event
from ..types import InputFileMeta, OperationStatus, FileType


def parse_dieharder_output(stdout: str, stderr: str, test_num: int) -> Dict[str, Any]:
    """Parse dieharder output for a single test into a structured dict.
    
    Returns:
        Dict with structure:
        {
            'test_id': int,
            'test_name': str,
            'version': str,
            'input_file': str,
            'rands_per_second': str,
            'results': [
                {
                    'ntup': int,
                    'tsamples': int,
                    'psamples': int,
                    'p_value': float,
                    'assessment': str  # 'PASSED', 'FAILED', 'WEAK'
                },
                ...
            ],
            'stderr': str,
            'overall_assessment': str  # 'PASSED' only if all results pass
        }
    """
    result = {
        'test_id': test_num,
        'test_name': '',
        'version': '',
        'input_file': '',
        'rands_per_second': '',
        'results': [],
        'stderr': stderr.strip() if stderr else '',
        'overall_assessment': 'PASSED'
    }
    
    if not stdout:
        return result
    
    lines = stdout.strip().split('\n')
    
    # Parse version from header
    version_match = re.search(r'dieharder version (\d+\.\d+\.\d+)', stdout)
    if version_match:
        result['version'] = version_match.group(1)
    
    # Parse input file and rands/second
    file_match = re.search(r'file_input_raw\|([^|]+)\|\s*([^|]+)\|', stdout)
    if file_match:
        result['input_file'] = file_match.group(1).strip()
        result['rands_per_second'] = file_match.group(2).strip()
    
    # Parse test results - look for data lines after the header
    # Format: test_name|ntup|tsamples|psamples|p-value|Assessment
    # The actual data lines don't have the # prefix
    in_results = False
    for line in lines:
        line = line.strip()
        
        # Skip header lines (starting with #)
        if line.startswith('#'):
            continue
        
        # Skip file_input_raw line
        if 'file_input_raw' in line:
            continue
        
        # Skip empty lines
        if not line:
            continue
        
        # Parse result line - format: name|ntup|tsamples|psamples|p-value|assessment
        # Use regex to extract fields (they are pipe-separated with variable whitespace)
        result_match = re.match(r'\s*([^|]+)\|\s*(\d+)\|\s*(\d+)\|\s*(\d+)\|([\d.]+)\|\s*(\w+)', line)
        if result_match:
            test_name = result_match.group(1).strip()
            if not result['test_name']:
                result['test_name'] = test_name
            
            p_value_str = result_match.group(5)
            try:
                p_value = float(p_value_str)
            except ValueError:
                p_value = 0.0
            
            assessment = result_match.group(6).strip()
            
            result['results'].append({
                'ntup': int(result_match.group(2)),
                'tsamples': int(result_match.group(3)),
                'psamples': int(result_match.group(4)),
                'p_value': p_value,
                'assessment': assessment
            })
            
            # Update overall assessment
            if assessment == 'FAILED':
                result['overall_assessment'] = 'FAILED'
            elif assessment == 'WEAK' and result['overall_assessment'] != 'FAILED':
                result['overall_assessment'] = 'WEAK'
    
    # Calculate summary statistics for tests with multiple outputs
    total_results = len(result['results'])
    passed_count = sum(1 for r in result['results'] if r['assessment'] == 'PASSED')
    failed_count = sum(1 for r in result['results'] if r['assessment'] == 'FAILED')
    weak_count = sum(1 for r in result['results'] if r['assessment'] == 'WEAK')
    
    result['statistics'] = {
        'total_results': total_results,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'weak_count': weak_count,
        'pass_rate': f"{passed_count}/{total_results}" if total_results > 0 else "0/0"
    }
    
    # Collect all p-values for statistical analysis
    result['p_values'] = [r['p_value'] for r in result['results']]
    
    return result


# All 32 available dieharder test numbers
ALL_DIEHARDER_TESTS = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17,  # 18 tests
    100, 101, 102,  # 3 tests
    200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210  # 11 tests
    # Total: 32 tests
]


class DieHarderTest:
    """DieHarder randomness test suite using external dieharder.exe."""

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_test = Event()
        self.on_progress = Event()  # Progress event for individual test completion
        
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self._process: Optional[sp.Popen] = None
        self._process_lock = Lock()  # Lock for thread-safe process access
        self.settings: Dict[str, Any] = {
            'test_mode': 'specific',
            'selected_tests': [],
            'psamples': 100,
            'tentities': 10000,
            'multiplier': 1,
            'ntuple': 0,  # 0 = use default for each test
            'ks_mode': 2,
            'weak_threshold': 0.005,
            'fail_threshold': 0.000001,
            'use_overlap': True,
            'test_strategy': 0,
            'reseed_strategy': 0,
            'save_raw_output': False,
            'raw_output_folder': ''
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

    def set_settings(self, settings: Dict[str, Any]) -> None:
        """Set DieHarder test settings."""
        self.settings = settings

    def run_async(self) -> None:
        """Run DieHarder test asynchronously. Emits on_test with OperationStatus."""
        if self._thread and self._thread.is_alive():
            self.on_test.notify(status=OperationStatus(ok=False, message="DieHarder test already in progress"))
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._worker, daemon=True)
        self._thread.start()

    def _run_single_test(self, dh_path: str, test_num: int) -> Optional[Dict[str, Any]]:
        """Run a single dieharder test. Returns result dict or None if cancelled."""
        test_args = self._build_command_args(single_test=test_num)
        cmd = f'"{dh_path}" -g 201 -f "{self.meta.file_path}" {test_args}'
        
        # Use Popen to allow termination
        with self._process_lock:
            if self._stop_event.is_set():
                return None
            self._process = sp.Popen(cmd, stdout=sp.PIPE, stderr=sp.PIPE, shell=True, text=True)
            process = self._process
        
        try:
            stdout, stderr = process.communicate()
            returncode = process.returncode
        except Exception:
            # Process was likely killed
            return None
        finally:
            with self._process_lock:
                self._process = None
        
        # Check if stopped during execution
        if self._stop_event.is_set():
            return None
        
        return {
            "test_num": test_num,
            "args": test_args,
            "stdout": stdout or "",
            "stderr": stderr or "",
            "returncode": returncode
        }

    def _worker(self) -> None:
        # Check stop before starting
        if self._stop_event.is_set():
            return
        # Validate input
        if not self.meta.file_path:
            self.on_test.notify(status=OperationStatus(ok=False, message="No file loaded"))
            return
        if self.meta.file_type != FileType.BINARY:
            self.on_test.notify(status=OperationStatus(ok=False, message="DieHarder requires BINARY file type"))
            return

        # Find DieHarder executable
        dh_path = self._resolve_dieharder_path()
        if not dh_path:
            self.on_test.notify(status=OperationStatus(ok=False, message="dieharder.exe not found. Check third_party/bin/"))
            return

        try:
            # Determine which tests to run
            if self.settings.get('test_mode') == 'all':
                # Run all tests one by one
                tests_to_run = ALL_DIEHARDER_TESTS.copy()
            else:
                # Run selected tests
                tests_to_run = list(self.settings.get('selected_tests', []))
                tests_to_run = [t for t in tests_to_run if t != 211]
            
            if not tests_to_run:
                self.on_test.notify(status=OperationStatus(ok=False, message="No tests selected"))
                return
            
            # Run each test individually and collect results
            test_results: Dict[int, Dict[str, Any]] = {}  # Dict keyed by test number
            parsed_results: Dict[int, Dict[str, Any]] = {}  # Parsed structured results
            combined_stdout = ""
            combined_stderr = ""
            overall_ok = True
            completed_count = 0
            total_tests = len(tests_to_run)
            
            # Setup raw output saving if enabled
            save_raw = self.settings.get('save_raw_output', False)
            raw_folder = self.settings.get('raw_output_folder', '')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Get input file name for output naming
            input_name = self.meta.file_name if self.meta.file_name else "unknown"
            
            for test_num in tests_to_run:
                # Check stop event between tests
                if self._stop_event.is_set():
                    self.on_test.notify(status=OperationStatus(ok=False, message="DieHarder test cancelled"))
                    return
                
                result = self._run_single_test(dh_path, test_num)
                
                if result is None:
                    # Test was cancelled
                    self.on_test.notify(status=OperationStatus(ok=False, message="DieHarder test cancelled"))
                    return
                
                # Store raw result in dict
                test_results[test_num] = result
                
                # Parse the output into structured format
                parsed = parse_dieharder_output(result["stdout"], result["stderr"], test_num)
                parsed_results[test_num] = parsed
                
                # Accumulate outputs with header
                header = f"\n===== dieharder -d {test_num} =====\n"
                combined_stdout += header + result["stdout"]
                combined_stderr += header + result["stderr"]
                
                # Check assessment
                if parsed['overall_assessment'] == 'FAILED':
                    overall_ok = False
                
                completed_count += 1
                
                # Save raw output immediately after each test (if enabled)
                if save_raw and raw_folder:
                    try:
                        folder_path = Path(raw_folder)
                        folder_path.mkdir(parents=True, exist_ok=True)
                        
                        # Append to stdout file (includes input filename)
                        stdout_file = folder_path / f"{input_name}_dieharder_stdout_{timestamp}.txt"
                        with open(stdout_file, 'a', encoding='utf-8') as f:
                            f.write(header + result["stdout"] + "\n")
                        
                        # Append to stderr file (includes input filename)
                        stderr_file = folder_path / f"{input_name}_dieharder_stderr_{timestamp}.txt"
                        with open(stderr_file, 'a', encoding='utf-8') as f:
                            f.write(header + result["stderr"] + "\n")
                    except Exception:
                        pass  # Silently ignore save errors
                
                # Notify progress after each test
                progress_payload = {
                    "test_type": "DieHarder",
                    "progress_type": "test_complete",
                    "test_num": test_num,
                    "test_name": parsed['test_name'],
                    "completed": completed_count,
                    "total": total_tests,
                    "assessment": parsed['overall_assessment'],
                    "parsed_result": parsed
                }
                self.on_progress.notify(status=OperationStatus(
                    ok=True, 
                    message=f"Test {completed_count}/{total_tests}: {parsed['test_name']} - {parsed['overall_assessment']}",
                    payload=progress_payload
                ))
            
            payload = {
                "test_type": "DieHarder",
                "stdout": combined_stdout.strip(),
                "stderr": combined_stderr.strip(),
                "returncode": 0 if overall_ok else 1,
                "test_results": test_results,  # Raw results keyed by test number
                "parsed_results": parsed_results,  # Parsed structured results
                "tests_run": tests_to_run,
                "completed_count": completed_count,
                "settings": self.settings
            }

            if overall_ok:
                self.on_test.notify(status=OperationStatus(ok=True, message="DieHarder tests completed", payload=payload))
            else:
                self.on_test.notify(status=OperationStatus(ok=True, message="DieHarder tests completed (some failures)", payload=payload))
                
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"DieHarder execution error: {e}"))

    def _build_command_args(self, single_test: int) -> str:
        """Build command line arguments for a single test.
        
        Note: -a option is not used - all tests are run individually
        to allow proper cancellation.
        """
        args = []
        
        # Test selection - always use -d for individual test
        args.extend(['-d', str(single_test)])
        
        # Test parameters (only add if non-default)
        if self.settings['psamples'] != 100:
            args.extend(['-p', str(self.settings['psamples'])])
        
        if self.settings['tentities'] != 10000:
            args.extend(['-t', str(self.settings['tentities'])])
        
        if self.settings['multiplier'] != 1:
            args.extend(['-m', str(self.settings['multiplier'])])
        
        # Ntuple for bit tests (0 = use test default)
        if self.settings.get('ntuple', 0) != 0:
            args.extend(['-n', str(self.settings['ntuple'])])
        
        # Statistical options
        if self.settings['ks_mode'] != 0:  # 0 is default
            args.extend(['-k', str(self.settings['ks_mode'])])
        
        if self.settings['weak_threshold'] != 0.005:
            args.extend(['-W', str(self.settings['weak_threshold'])])
        
        if self.settings['fail_threshold'] != 0.000001:
            args.extend(['-X', str(self.settings['fail_threshold'])])
        
        # Advanced options
        overlap_flag = 1 if self.settings['use_overlap'] else 0
        if overlap_flag != 1:  # Only add if non-default
            args.extend(['-L', str(overlap_flag)])
        
        if self.settings['test_strategy'] != 0:
            args.extend(['-Y', str(self.settings['test_strategy'])])
        
        if self.settings['reseed_strategy'] != 0:
            args.extend(['-s', str(self.settings['reseed_strategy'])])
        
        return ' '.join(args)
    
    def _resolve_dieharder_path(self) -> Optional[str]:
        if hasattr(sys, '_MEIPASS'):
            project_root = Path(sys._MEIPASS)
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
        clean_path = project_root / "third_party" / "bin" / "dieharder.exe"
        if clean_path.is_file():
            return str(clean_path)
        return None
