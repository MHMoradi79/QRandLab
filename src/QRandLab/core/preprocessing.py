# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""PreProcessing core.

- Uses shared InputFileMeta for loose coupling
- Provides common preprocessing algorithms (VN, XOR1, XOR2, TZ Extractor)
- Runs each algorithm on a background thread and emits unified OperationStatus via events with result payloads
"""

from __future__ import annotations
import sys

from threading import Thread, Event as ThreadEvent
from typing import Optional, Callable, Dict, List
import subprocess as sp
from pathlib import Path
import tempfile

from .observer import Event
from .types import InputFileMeta, OperationStatus, FileType, FileItem


class PreProcessing:
    """Preprocessing algorithms operating on shared InputFileMeta.

    Events:
    - on_preprocess_progress(OperationStatus): Emitted for each file during multi-file preprocessing.
    """

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_multi_preprocess = Event()  # For multi-file preprocessing
        self.on_preprocess_progress = Event()  # Progress for each file

        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self._multi_results: List[Dict] = []
    
    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    def _resolve_tz_path(self) -> Optional[str]:
        if hasattr(sys, '_MEIPASS'):
            project_root = Path(sys._MEIPASS)
        else:
            project_root = Path(__file__).resolve().parent.parent
        clean_path = project_root / "third_party" / "bin" / "TZ.exe"
        if clean_path.is_file():
            return str(clean_path)
        return None

    # --------------------- Algorithms ---------------------
    @staticmethod
    def _algo_vn(s: str) -> str:
        # Von Neumann extractor: read pairs, keep first of differing pairs
        out = []
        for i in range(0, len(s) - 1, 2):
            if s[i] != s[i + 1]:
                out.append(s[i])
        return "".join(out)

    @staticmethod
    def _algo_xor1(s: str) -> str:
        # XOR consecutive pairs
        out = []
        for i in range(0, len(s) - 1, 2):
            out.append("0" if s[i] == s[i + 1] else "1")
        return "".join(out)

    @staticmethod
    def _algo_xor2(s: str) -> str:
        # XOR first half vs second half
        N = len(s)
        half = N // 2
        a = s[:half]
        b = s[half:half + half]
        out = []
        for i in range(min(len(a), len(b))):
            out.append("0" if a[i] == b[i] else "1")
        return "".join(out)

    # --------------------- Multi-File Preprocessing ---------------------
    def run_multi_algorithm_async(self, file_items: List[FileItem], algorithm: str, 
                                   auto_convert: bool = False, convert_back: bool = False,
                                   tz_settings: Optional[Dict] = None, output_tag: str = "") -> None:
        """Run preprocessing algorithm on multiple files."""
        if not file_items:
            self.on_multi_preprocess.notify(status=OperationStatus(ok=False, message="No files to preprocess"))
            return
        if self._thread and self._thread.is_alive():
            self.on_multi_preprocess.notify(status=OperationStatus(ok=False, message="Preprocessing already in progress"))
            return
        self._stop_event.clear()
        self._multi_results = []
        self._thread = Thread(
            target=self._multi_worker,
            args=(file_items, algorithm, auto_convert, convert_back, tz_settings, output_tag),
            daemon=True
        )
        self._thread.start()

    def _multi_worker(self, file_items: List[FileItem], algorithm: str, 
                      auto_convert: bool, convert_back: bool, tz_settings: Optional[Dict], output_tag: str) -> None:
        """Worker for multi-file preprocessing."""
        results = []
        success_count = 0
        fail_count = 0
        total_files = len(file_items)
        
        for idx, file_item in enumerate(file_items):
            if self._stop_event.is_set():
                return
            
            try:
                result = self._process_single_file(file_item, algorithm, auto_convert, convert_back, tz_settings, output_tag)
                results.append(result)
                if result.get('ok'):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                results.append({
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'ok': False,
                    'message': str(e)
                })
                fail_count += 1
            
            # Emit progress after each file
            self.on_preprocess_progress.notify(status=OperationStatus(
                ok=True, message=f"Processing {idx + 1}/{total_files}",
                payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
            ))
        
        self._multi_results = results
        self.on_multi_preprocess.notify(status=OperationStatus(
            ok=success_count > 0,
            message=f"Preprocessed {success_count} file(s), {fail_count} failed",
            payload={
                'algorithm': algorithm,
                'results': results,
                'success_count': success_count,
                'fail_count': fail_count
            }
        ))

    def _process_single_file(self, file_item: FileItem, algorithm: str, 
                             auto_convert: bool, convert_back: bool, tz_settings: Optional[Dict], output_tag: str) -> Dict:
        """Process a single file with the specified algorithm."""
        p = Path(file_item.file_path)
        if not p.is_file():
            return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'File not found'}
        
        file_type = file_item.file_type
        original_type = file_type
        was_converted = False
        
        # Check type compatibility
        if algorithm == "TZ Extractor":
            required_type = FileType.BINARY
        else:
            required_type = FileType.STRING01
        
        # Handle auto-convert
        input_data = None
        if file_type != required_type:
            if not auto_convert:
                return {
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'ok': False,
                    'message': f'File type {file_type.value if file_type else "unknown"} incompatible with {algorithm}. Enable auto-convert.'
                }
            # Convert data
            input_data = self._convert_for_preprocessing(p, file_type, required_type)
            if input_data is None:
                return {
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'ok': False,
                    'message': 'Failed to convert file for preprocessing'
                }
            was_converted = True
        
        # Process based on algorithm
        if algorithm == "TZ Extractor":
            result = self._process_tz_file(file_item, tz_settings, output_tag)
        else:
            result = self._process_simple_algorithm(file_item, algorithm, output_tag, input_data)
        
        # Convert back to original format if requested
        if result.get('ok') and convert_back and was_converted and original_type:
            result = self._convert_result_back(result, original_type)
        
        return result

    def _process_simple_algorithm(self, file_item: FileItem, algorithm: str, 
                                   output_tag: str, converted_data: Optional[str] = None) -> Dict:
        """Process VN, XOR1, XOR2 on a single file."""
        try:
            p = Path(file_item.file_path)
            
            # Read data
            if converted_data is not None:
                text = converted_data
            else:
                ext = file_item.file_ext.value if file_item.file_ext else ".bin"
                mode = "r" if ext == ".txt" else "rb"
                with open(p, mode) as f:
                    raw = f.read()
                text = raw if isinstance(raw, str) else raw.decode("utf-8", errors="ignore")
            
            # Keep only 0/1
            text = "".join(c for c in text if c in "01")
            
            # Apply algorithm
            if algorithm == "VonNeuman":
                result = self._algo_vn(text)
                suffix = "VN"
            elif algorithm == "XOR1":
                result = self._algo_xor1(text)
                suffix = "XOR1"
            elif algorithm == "XOR2":
                result = self._algo_xor2(text)
                suffix = "XOR2"
            else:
                return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': f'Unknown algorithm: {algorithm}'}
            
            out_name = f"{file_item.file_name}{output_tag}_{suffix}.txt"
            
            return {
                'file_id': file_item.id,
                'file_name': file_item.file_name,
                'ok': True,
                'data': result,
                'suggested_name': out_name,
                'output_type': FileType.STRING01
            }
        except Exception as e:
            return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': str(e)}

    def _process_tz_file(self, file_item: FileItem, tz_settings: Optional[Dict], output_tag: str) -> Dict:
        """Process TZ Extractor on a single file."""
        tz_path = self._resolve_tz_path()
        if not tz_path:
            return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'TZ.exe not found'}
        
        try:
            settings = tz_settings or {'n': '256', 'l': '128', 'save_tzm': False}
            n_val = settings.get('n', '256')
            l_val = settings.get('l', '128')
            save_tzm = settings.get('save_tzm', False)
            
            temp_dir = Path(tempfile.gettempdir())
            temp_output = temp_dir / f"tz_temp_{file_item.file_name}_output.bin"
            temp_tzm = temp_dir / f"tz_temp_{file_item.file_name}_tzm.txt"
            
            cmd = f'"{tz_path}" -n {n_val} -l {l_val} -o "{temp_output}" -R -i "{file_item.file_path}"'
            if save_tzm:
                cmd += f' -v 2> "{temp_tzm}"'
            
            result = sp.run(cmd, capture_output=True, shell=True, text=True, check=False)
            
            if result.returncode != 0:
                return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': f'TZ failed: {result.stderr}'}
            
            # Read output data
            if temp_output.exists():
                with open(temp_output, 'rb') as f:
                    data = f.read()
            else:
                return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'TZ output not found'}
            
            out_name = f"{file_item.file_name}{output_tag}_TZE.bin"
            
            payload = {
                'file_id': file_item.id,
                'file_name': file_item.file_name,
                'ok': True,
                'data': data,
                'suggested_name': out_name,
                'output_type': FileType.BINARY,
                'n': n_val,
                'l': l_val
            }
            
            if save_tzm and temp_tzm.exists():
                with open(temp_tzm, 'r') as f:
                    payload['tzm_data'] = f.read()
                payload['tzm_name'] = f"{file_item.file_name}{output_tag}_TZM.txt"
            
            return payload
            
        except Exception as e:
            return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': str(e)}

    def _convert_result_back(self, result: Dict, original_type: FileType) -> Dict:
        """Convert preprocessing result back to original file type."""
        try:
            data = result.get('data')
            output_type = result.get('output_type')
            
            if data is None or output_type == original_type:
                return result
            
            converted_data = None
            new_ext = ".bin"
            
            # Convert STRING01 back to original
            if output_type == FileType.STRING01 and isinstance(data, str):
                bits = ''.join(c for c in data if c in '01')
                # Pad to multiple of 8
                while len(bits) % 8:
                    bits += '0'
                byte_data = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
                
                if original_type == FileType.BINARY:
                    converted_data = byte_data
                    new_ext = ".bin"
                elif original_type == FileType.HEX:
                    converted_data = byte_data.hex()
                    new_ext = ".txt"
                elif original_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                    converted_data = byte_data
                    new_ext = ".bin"
            
            # Convert BINARY back to original
            elif output_type == FileType.BINARY and isinstance(data, bytes):
                if original_type == FileType.STRING01:
                    converted_data = ''.join(format(b, '08b') for b in data)
                    new_ext = ".txt"
                elif original_type == FileType.HEX:
                    converted_data = data.hex()
                    new_ext = ".txt"
                else:
                    converted_data = data
                    new_ext = ".bin"
            
            if converted_data is not None:
                # Update result with converted data
                new_result = result.copy()
                new_result['data'] = converted_data
                new_result['output_type'] = original_type
                # Update suggested name extension
                suggested_name = result.get('suggested_name', '')
                if suggested_name:
                    base = Path(suggested_name).stem
                    new_result['suggested_name'] = base + new_ext
                return new_result
            
            return result
        except Exception:
            return result

    def _convert_for_preprocessing(self, file_path: Path, from_type: Optional[FileType], 
                                    to_type: FileType) -> Optional[str]:
        """Convert file data to required format for preprocessing."""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            # Convert to STRING01
            if to_type == FileType.STRING01:
                if from_type == FileType.BINARY:
                    return ''.join(format(b, '08b') for b in raw_data)
                elif from_type == FileType.HEX:
                    text = raw_data.decode('utf-8', errors='ignore').strip()
                    bytes_data = bytes.fromhex(text)
                    return ''.join(format(b, '08b') for b in bytes_data)
                elif from_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                    return ''.join(format(b, '08b') for b in raw_data)
            
            # Convert to BINARY (for TZ)
            elif to_type == FileType.BINARY:
                if from_type == FileType.STRING01:
                    text = raw_data.decode('utf-8', errors='ignore')
                    bits = ''.join(c for c in text if c in '01')
                    # Pad to multiple of 8
                    while len(bits) % 8:
                        bits += '0'
                    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
                elif from_type == FileType.HEX:
                    text = raw_data.decode('utf-8', errors='ignore').strip()
                    return bytes.fromhex(text)
                else:
                    return raw_data
            
            return None
        except Exception:
            return None
