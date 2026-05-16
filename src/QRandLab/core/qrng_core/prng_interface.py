# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""PRNG Interface for software-based random number generators."""

from __future__ import annotations
import sys

import re
import threading
import subprocess as sp
import tempfile
from typing import Optional, Dict, Any, List
from pathlib import Path

from ..observer import Event
from ..types import OperationStatus


class PRNGInterface:
    """Interface for Pseudo-Random Number Generator operations."""

    def __init__(self) -> None:
        self.on_prng_data = Event()  # Final data/completion notification
        self.on_prng_error = Event()  # Error occurred
        self.on_prng_progress = Event()  # Progress updates for each file
        
        self._stop_event = threading.Event()
        self._prng_thread: Optional[threading.Thread] = None
        self._files_saved = 0

    def generate_dieharder(self, generator_id: int, seed: int, save_path: str, 
                          num_files: int, size_per_file: int, 
                          include_header: bool = True,
                          include_gen_id: bool = True,
                          include_seed: bool = True,
                          base_name: str = "prng",
                          output_format: str = "uint32") -> OperationStatus:
        """Generate random numbers using DieHarder PRNG and save directly to files.
        
        Runs DieHarder executable in a separate thread for each file. Uses temporary
        files to capture output, then converts to requested format and saves to final
        location. Emits progress events for each completed file.
        
        Args:
            generator_id: DieHarder generator ID (0-61, plus special IDs)
            seed: Random seed (incremented for each file)
            save_path: Folder path to save generated files
            num_files: Number of files to generate
            size_per_file: Number of random values per file
            include_header: If True, include DieHarder header; if False, only raw values
            include_gen_id: If True, include generator ID in filename
            include_seed: If True, include seed in filename
            base_name: Base name for generated files (default: "prng")
            output_format: Output format (uint32, binary, string01, hex, uint8, uint16, uint64)
            
        Returns:
            OperationStatus indicating success/failure
            
        Emits:
            on_prng_progress: Progress updates for each file saved
            on_prng_data: Final completion notification with summary
            on_prng_error: On fatal errors
        """
        if self._prng_thread and self._prng_thread.is_alive():
            return OperationStatus(ok=False, message="PRNG generation already in progress")

        # Validate parameters
        validation_result = self._validate_params(generator_id, seed, save_path, num_files, size_per_file)
        if not validation_result.ok:
            return validation_result
        
        # Validate save path
        save_dir = Path(save_path)
        if not save_dir.exists():
            return OperationStatus(ok=False, message=f"Save path does not exist: {save_path}")

        def worker():
            try:
                # Find DieHarder executable using pathlib
                if hasattr(sys, '_MEIPASS'):
                    project_root = Path(sys._MEIPASS)
                else:
                    project_root = Path(__file__).resolve().parent.parent.parent
                exe_path = project_root / "third_party" / "bin" / "dieharder.exe"
                if not exe_path.exists():
                    self._emit_error(f"DieHarder executable not found at {exe_path}")
                    return

                # Clear stop event
                self._stop_event.clear()
                self._files_saved = 0

                # Determine file extension based on output format
                ext_map = {
                    "uint32": ".txt", "binary": ".bin", "string01": ".txt", "hex": ".txt",
                    "uint8": ".txt", "uint16": ".txt", "uint64": ".txt"
                }
                file_ext = ext_map.get(output_format, ".txt")
                
                for file_index in range(num_files):
                    if self._stop_event.is_set():
                        break
                    
                    # Build filename based on options
                    parts = [base_name]
                    if include_gen_id:
                        parts.append(str(generator_id))
                    if include_seed:
                        parts.append(str(seed + file_index))
                    parts.append(str(file_index + 1))
                    output_filename = "_".join(parts) + file_ext
                    output_path = save_dir / output_filename
                    
                    # Create temporary file for DieHarder output
                    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as temp_file:
                        temp_path = Path(temp_file.name)
                    
                    try:
                        # Run DieHarder
                        command = [
                            str(exe_path),
                            "-o",
                            "-f", str(temp_path),
                            "-g", str(generator_id),
                            "-t", str(size_per_file),
                            "-S", str(seed + file_index)  # Different seed for each file
                        ]
                        
                        result = sp.run(command, capture_output=True, text=True, timeout=300)
                        
                        if result.returncode != 0:
                            self._emit_error(f"DieHarder failed for file {file_index + 1}: {result.stderr}")
                            temp_path.unlink(missing_ok=True)
                            return
                        
                        # Read generated data
                        if temp_path.exists():
                            raw_data = temp_path.read_text(encoding='utf-8')
                            
                            # Extract uint32 values (always needed for conversion)
                            uint32_values = self._extract_uint32_list(raw_data)
                            
                            # Convert to output format and save
                            self._save_with_format(
                                output_path, uint32_values, output_format,
                                include_header=include_header,
                                seed=seed + file_index,
                                generator_id=generator_id,
                                count=size_per_file
                            )
                            self._files_saved += 1
                            
                            # Notify progress for each file saved
                            self.on_prng_progress.notify(status=OperationStatus(
                                ok=True,
                                message=f"Saved file {file_index + 1}/{num_files}",
                                payload={
                                    "file_index": file_index + 1,
                                    "total_files": num_files,
                                    "filename": output_filename,
                                    "saved_path": str(output_path),
                                    "files_saved": self._files_saved
                                }
                            ))
                        else:
                            self._emit_error(f"Output file not created for file {file_index + 1}")
                            return
                            
                    finally:
                        # Cleanup temporary file
                        temp_path.unlink(missing_ok=True)

                # Notify completion
                self.on_prng_data.notify(status=OperationStatus(
                    ok=True,
                    message="PRNG generation complete" if not self._stop_event.is_set() else "PRNG generation stopped",
                    payload={
                        "provider": "prng",
                        "save_path": str(save_dir),
                        "total_files": num_files,
                        "files_saved": self._files_saved,
                        "complete": not self._stop_event.is_set(),
                        "stopped": self._stop_event.is_set()
                    }
                ))

            except sp.TimeoutExpired:
                self._emit_error("DieHarder generation timed out")
            except Exception as e:
                self._emit_error(f"PRNG generation error: {e}")

        self._prng_thread = threading.Thread(target=worker, daemon=True)
        self._prng_thread.start()
        return OperationStatus(ok=True, message="DieHarder PRNG generation started")
    
    def _extract_uint32_values(self, raw_data: str) -> str:
        """Extract only uint32 values from DieHarder output, removing header."""
        return '\n'.join(str(v) for v in self._extract_uint32_list(raw_data))
    
    def _extract_uint32_list(self, raw_data: str) -> List[int]:
        """Extract uint32 values from DieHarder output.
        
        Parses DieHarder's text output, extracting only valid integer values.
        Handles both header comments and data lines.
        
        Args:
            raw_data: Raw text output from DieHarder executable
            
        Returns:
            List of uint32 integer values extracted from the output
        """
        # Find all uint32 values (0 to 4294967295) that are on their own line
        # DieHarder outputs values after the header, each on its own line
        uint32_pattern = re.compile(r'^\s*(\d{1,10})\s*$', re.MULTILINE)
        matches = uint32_pattern.findall(raw_data)
        
        # Filter to valid uint32 range (0 to 4294967295)
        valid_values = []
        for match in matches:
            try:
                value = int(match)
                if 0 <= value <= 4294967295:
                    valid_values.append(value)
            except ValueError:
                continue
        
        return valid_values
    
    def _generate_header(self, generator_id: int, seed: int, count: int, numbit: int) -> str:
        """Generate DieHarder-style header with updated parameters.
        
        Creates a standard DieHarder header format with generator info,
        seed, count, and bit width. Maps generator IDs to names for readability.
        
        Args:
            generator_id: Generator ID used (mapped to name if known)
            seed: Seed value used
            count: Number of values in the file
            numbit: Bits per value (depends on output format)
            
        Returns:
            Multi-line header string in DieHarder format
        """
        # Get generator name (simplified mapping)
        gen_names = {0: "mt19937", 8: "cmrg", 10: "taus", 13: "ran0"}
        gen_name = gen_names.get(generator_id, f"generator_{generator_id}")
        
        header = f"#==================================================================\n"
        header += f"# generator {gen_name}  seed = {seed}\n"
        header += f"#==================================================================\n"
        header += f"type: d\n"
        header += f"count: {count}\n"
        header += f"numbit: {numbit}\n"
        return header
    
    def _save_with_format(self, output_path: Path, uint32_values: List[int], 
                         output_format: str, include_header: bool = False,
                         seed: int = 0, generator_id: int = 0, count: int = 0):
        """Save data with the specified output format.
        
        Converts uint32 values to the requested output format and saves to file.
        Supports multiple formats: text (uint32), binary, binary strings (0/1),
        hexadecimal, and different integer sizes (uint8, uint16, uint64).
        
        Args:
            output_path: Path to save the file
            uint32_values: List of uint32 values to convert and save
            output_format: Output format (uint32, binary, string01, hex, uint8, uint16, uint64)
            include_header: Whether to include DieHarder header in output
            seed: Seed value for header (if include_header is True)
            generator_id: Generator ID for header (if include_header is True)
            count: Count value for header (if include_header is True)
        """
        # Determine numbit based on output format
        numbit_map = {
            "uint32": 32, "binary": 32, "string01": 1, "hex": 32,
            "uint8": 8, "uint16": 16, "uint64": 64
        }
        numbit = numbit_map.get(output_format, 32)
        
        if output_format == "uint32":
            # Save as uint32 text (one per line)
            data_str = '\n'.join(str(v) for v in uint32_values)
            if include_header:
                header = self._generate_header(generator_id, seed, count, numbit)
                output_path.write_text(header + data_str, encoding='utf-8')
            else:
                output_path.write_text(data_str, encoding='utf-8')
        
        elif output_format == "binary":
            # Convert uint32 values to raw binary bytes (no header for binary)
            binary_data = b''.join(v.to_bytes(4, byteorder='big') for v in uint32_values)
            output_path.write_bytes(binary_data)
        
        elif output_format == "string01":
            # Convert uint32 values to binary string (32 bits each)
            bits = ''.join(format(v, '032b') for v in uint32_values)
            if include_header:
                header = self._generate_header(generator_id, seed, len(bits), numbit)
                output_path.write_text(header + bits, encoding='utf-8')
            else:
                output_path.write_text(bits, encoding='utf-8')
        
        elif output_format == "hex":
            # Convert uint32 values to hex string
            hex_str = ''.join(format(v, '08x') for v in uint32_values)
            if include_header:
                header = self._generate_header(generator_id, seed, len(hex_str) // 2, numbit)
                output_path.write_text(header + hex_str, encoding='utf-8')
            else:
                output_path.write_text(hex_str, encoding='utf-8')
        
        elif output_format in ("uint8", "uint16", "uint64"):
            # Convert uint32 to other uint formats
            # First convert to bytes, then reinterpret as target format
            binary_data = b''.join(v.to_bytes(4, byteorder='big') for v in uint32_values)
            
            nbytes = {"uint8": 1, "uint16": 2, "uint64": 8}[output_format]
            uint_list = []
            for i in range(0, len(binary_data), nbytes):
                chunk = binary_data[i:i+nbytes]
                if len(chunk) < nbytes:
                    chunk = chunk.ljust(nbytes, b'\0')
                uint_value = int.from_bytes(chunk, byteorder='big')
                uint_list.append(str(uint_value))
            
            data_str = '\n'.join(uint_list)
            if include_header:
                header = self._generate_header(generator_id, seed, len(uint_list), numbit)
                output_path.write_text(header + data_str, encoding='utf-8')
            else:
                output_path.write_text(data_str, encoding='utf-8')
        
        else:
            # Default: save as uint32 text
            data_str = '\n'.join(str(v) for v in uint32_values)
            if include_header:
                header = self._generate_header(generator_id, seed, count, 32)
                output_path.write_text(header + data_str, encoding='utf-8')
            else:
                output_path.write_text(data_str, encoding='utf-8')

    def _validate_params(self, generator_id: int, seed: int, save_path: str, 
                        num_files: int, size_per_file: int) -> OperationStatus:
        """Validate DieHarder parameters.
        
        Checks that all parameters are valid types and within acceptable ranges.
        Validates generator IDs against known DieHarder generators.
        
        Args:
            generator_id: DieHarder generator ID to validate
            seed: Random seed value
            save_path: Directory path where files will be saved
            num_files: Number of files to generate
            size_per_file: Size parameter (number of values) per file
            
        Returns:
            OperationStatus with validation result
        """
        try:
            if not save_path or not isinstance(save_path, str):
                return OperationStatus(ok=False, message="Save path cannot be empty")
            
            if not isinstance(num_files, int) or num_files <= 0:
                return OperationStatus(ok=False, message="Number of files must be a positive integer")
            
            if not isinstance(size_per_file, int) or size_per_file <= 0:
                return OperationStatus(ok=False, message="Size per file must be a positive integer")
            
            if not isinstance(generator_id, int):
                return OperationStatus(ok=False, message="Generator ID must be an integer")

            # Valid DieHarder generator IDs (simplified list)
            valid_ids = list(range(0, 62)) + [203, 204, 205, 206, 400, 401, 402, 403, 404, 405, 500, 501]
            
            if generator_id not in valid_ids:
                return OperationStatus(ok=False, message=f"Invalid generator ID: {generator_id}")

            return OperationStatus(ok=True, message="Parameters valid")

        except Exception as e:
            return OperationStatus(ok=False, message=f"Parameter validation error: {e}")

    def _emit_error(self, message: str) -> None:
        """Emit error event."""
        self.on_prng_error.notify(status=OperationStatus(ok=False, message=message))
    
    def get_files_saved(self) -> int:
        """Get number of files saved so far."""
        return self._files_saved

    def get_available_generators(self) -> List[Dict[str, Any]]:
        """Get list of available DieHarder generators.
        
        Returns a comprehensive list of all DieHarder generators with their
        IDs, names, and descriptions. Includes standard generators (0-61),
        file input generators (203-206), cryptographic generators (400-405),
        and system generators (500-501).
        
        Returns:
            List of dictionaries with keys: id, name, description
        """
        # Common DieHarder generators with descriptions
        generators = [
            {"id": 0, "name": "mt19937", "description": "Mersenne Twister"},
            {"id": 1, "name": "ranlxs0", "description": "RANLUX level 0"},
            {"id": 2, "name": "ranlxs1", "description": "RANLUX level 1"},
            {"id": 3, "name": "ranlxs2", "description": "RANLUX level 2"},
            {"id": 4, "name": "ranlxd1", "description": "RANLUX double level 1"},
            {"id": 5, "name": "ranlxd2", "description": "RANLUX double level 2"},
            {"id": 6, "name": "ranlux", "description": "RANLUX"},
            {"id": 7, "name": "ranlux389", "description": "RANLUX 389"},
            {"id": 8, "name": "cmrg", "description": "Combined multiple recursive generator"},
            {"id": 9, "name": "mrg", "description": "Multiple recursive generator"},
            {"id": 10, "name": "taus", "description": "Tausworthe generator"},
            {"id": 11, "name": "taus2", "description": "Tausworthe generator 2"},
            {"id": 12, "name": "gfsr4", "description": "Generalized feedback shift register"},
            {"id": 13, "name": "ran0", "description": "Numerical Recipes ran0"},
            {"id": 14, "name": "ran1", "description": "Numerical Recipes ran1"},
            {"id": 15, "name": "ran2", "description": "Numerical Recipes ran2"},
            {"id": 16, "name": "ran3", "description": "Numerical Recipes ran3"},
            {"id": 17, "name": "rand", "description": "BSD rand()"},
            {"id": 18, "name": "rand48", "description": "Unix rand48()"},
            {"id": 19, "name": "random", "description": "BSD random()"},
            {"id": 20, "name": "randu", "description": "RANDU (known bad generator)"},
            {"id": 21, "name": "ranf", "description": "RANF"},
            {"id": 22, "name": "ranmar", "description": "RANMAR"},
            {"id": 23, "name": "r250", "description": "R250 shift register"},
            {"id": 24, "name": "tt800", "description": "TT800"},
            {"id": 25, "name": "vax", "description": "VAX generator"},
            {"id": 26, "name": "transputer", "description": "Transputer generator"},
            {"id": 27, "name": "rng4", "description": "RNG4"},
            {"id": 28, "name": "rng5", "description": "RNG5"},
            {"id": 29, "name": "uvag", "description": "UVAG"},
            {"id": 30, "name": "minstd", "description": "Minimal standard"},
            {"id": 31, "name": "uni", "description": "UNI"},
            {"id": 32, "name": "uni32", "description": "UNI32"},
            {"id": 33, "name": "slatec", "description": "SLATEC"},
            {"id": 34, "name": "zuf", "description": "ZUF"},
            {"id": 35, "name": "borosh13", "description": "Borosh-Niederreiter 13"},
            {"id": 36, "name": "coveyou", "description": "Coveyou"},
            {"id": 37, "name": "fishman18", "description": "Fishman 18"},
            {"id": 38, "name": "fishman20", "description": "Fishman 20"},
            {"id": 39, "name": "lecuyer21", "description": "L'Ecuyer 21"},
            {"id": 40, "name": "waterman14", "description": "Waterman 14"},
            {"id": 41, "name": "fishman2x", "description": "Fishman 2x"},
            {"id": 42, "name": "knuthran2", "description": "Knuth RAN2"},
            {"id": 43, "name": "knuthran", "description": "Knuth RAN"},
            {"id": 44, "name": "ran_array", "description": "RAN array"},
            {"id": 45, "name": "ranf_array", "description": "RANF array"},
            {"id": 46, "name": "mt19937_1999", "description": "Mersenne Twister 1999"},
            {"id": 47, "name": "mt19937_1998", "description": "Mersenne Twister 1998"},
            {"id": 48, "name": "r250_521", "description": "R250/521"},
            {"id": 49, "name": "waterman", "description": "Waterman"},
            {"id": 50, "name": "kiss", "description": "KISS"},
            {"id": 51, "name": "superkiss", "description": "Super KISS"},
            {"id": 52, "name": "ca", "description": "Cellular automaton"},
            {"id": 53, "name": "borosh", "description": "Borosh"},
            {"id": 54, "name": "fishman", "description": "Fishman"},
            {"id": 55, "name": "lecuyer", "description": "L'Ecuyer"},
            {"id": 56, "name": "weyl", "description": "Weyl"},
            {"id": 57, "name": "drand48", "description": "drand48()"},
            {"id": 58, "name": "random_bsd", "description": "BSD random"},
            {"id": 59, "name": "random_libc5", "description": "libc5 random"},
            {"id": 60, "name": "random_glibc2", "description": "glibc2 random"},
            {"id": 61, "name": "stdin_input_raw", "description": "stdin input raw"},
            # Special generators
            {"id": 203, "name": "file_input", "description": "File input"},
            {"id": 204, "name": "file_input_raw", "description": "File input raw"},
            {"id": 205, "name": "ca_1", "description": "Cellular automaton 1"},
            {"id": 206, "name": "ca_2", "description": "Cellular automaton 2"},
            {"id": 400, "name": "threefish", "description": "Threefish"},
            {"id": 401, "name": "aes", "description": "AES"},
            {"id": 402, "name": "chacha", "description": "ChaCha"},
            {"id": 403, "name": "hc128", "description": "HC-128"},
            {"id": 404, "name": "rabbit", "description": "Rabbit"},
            {"id": 405, "name": "salsa20", "description": "Salsa20"},
            {"id": 500, "name": "dev_random", "description": "/dev/random"},
            {"id": 501, "name": "dev_urandom", "description": "/dev/urandom"}
        ]
        
        return generators

    def stop_generation(self) -> OperationStatus:
        """Stop PRNG generation."""
        if not self._prng_thread or not self._prng_thread.is_alive():
            return OperationStatus(ok=False, message="No PRNG generation is active")
        
        try:
            self._stop_event.set()
            self._prng_thread.join(timeout=2.0)
            return OperationStatus(ok=True, message="PRNG generation stopped")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Error stopping PRNG: {e}")

    def is_running(self) -> bool:
        """Check if PRNG generation is currently running."""
        return self._prng_thread is not None and self._prng_thread.is_alive()
