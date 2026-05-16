# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""File conversion core.

- Uses shared InputFileMeta for loose coupling
- Emits a single OperationStatus via on_convert when async conversion finishes
- Returns converted data in the event payload; saving is the caller's responsibility
"""

from __future__ import annotations

import time
from threading import Thread, Event as ThreadEvent
from typing import Optional, Union, List, Dict, Any
from pathlib import Path

from .observer import Event
from .types import InputFileMeta, OperationStatus, FileType, FileItem


class FileConverter:
    """Convert input data to different formats using shared metadata.

    Events:
    - on_multi_convert(OperationStatus): Emitted after multi-file conversion completes.
    - on_convert_progress(OperationStatus): Emitted for each file during multi-file conversion.
    """

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_multi_convert = Event()  # For multi-file conversion
        self.on_convert_progress = Event()  # Progress for each file

        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self.output_format: str = "string01"
        self._multi_results: List[Dict[str, Any]] = []  # Store results for multi-file
    
    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    # --------------------- Multi-File Conversion ---------------------
    def convert_files_async(self, file_items: List[FileItem], output_format: str, tag: str = "") -> None:
        """Convert multiple files to the specified format.
        
        Args:
            file_items: List of FileItem objects to convert
            output_format: Target format ('binary', 'hex', 'string01', etc.)
            tag: Optional tag to append to output filenames (e.g., '_hex')
        """
        if not file_items:
            self.on_multi_convert.notify(status=OperationStatus(
                ok=False,
                message="No files to convert",
                payload=None
            ))
            return
        
        # Avoid overlapping jobs
        if self._thread and self._thread.is_alive():
            self.on_multi_convert.notify(status=OperationStatus(
                ok=False,
                message="Conversion already in progress",
                payload=None
            ))
            return
        
        self._stop_event.clear()
        self._multi_results = []
        self._thread = Thread(
            target=self._convert_files_worker,
            args=(file_items, output_format, tag),
            daemon=True
        )
        self._thread.start()
    
    def _convert_files_worker(self, file_items: List[FileItem], output_format: str, tag: str) -> None:
        """Worker to convert multiple files."""
        CHUNK_SIZE = 256 * 1024
        results = []
        success_count = 0
        fail_count = 0
        
        total_files = len(file_items)
        for idx, file_item in enumerate(file_items):
            if self._stop_event.is_set():
                return
            
            # Skip files without type set
            if not file_item.file_type:
                results.append({
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'ok': False,
                    'message': 'File type not set',
                    'data': None
                })
                fail_count += 1
                # Emit progress
                self.on_convert_progress.notify(status=OperationStatus(
                    ok=True, message=f"Processing {idx + 1}/{total_files}",
                    payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                ))
                continue
            
            # Skip if source type equals target type
            if file_item.file_type.value == output_format:
                results.append({
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'ok': False,
                    'message': f'Already in {output_format} format',
                    'data': None
                })
                fail_count += 1
                # Emit progress
                self.on_convert_progress.notify(status=OperationStatus(
                    ok=True, message=f"Processing {idx + 1}/{total_files}",
                    payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                ))
                continue
            
            try:
                # Convert this file
                result = self._convert_single_file(file_item, output_format, tag, CHUNK_SIZE)
                results.append(result)
                if result['ok']:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                results.append({
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'ok': False,
                    'message': str(e),
                    'data': None
                })
                fail_count += 1
            
            # Emit progress after each file
            self.on_convert_progress.notify(status=OperationStatus(
                ok=True, message=f"Processing {idx + 1}/{total_files}",
                payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
            ))
        
        self._multi_results = results
        
        # Notify completion
        self.on_multi_convert.notify(status=OperationStatus(
            ok=success_count > 0,
            message=f"Converted {success_count} file(s), {fail_count} failed",
            payload={
                'results': results,
                'success_count': success_count,
                'fail_count': fail_count,
                'output_format': output_format,
                'tag': tag
            }
        ))
    
    def _convert_single_file(self, file_item: FileItem, output_format: str, tag: str, chunk_size: int) -> Dict[str, Any]:
        """Convert a single file item. Returns result dict."""
        # Determine read mode
        ext = file_item.file_ext.value
        if ext in (".bin", ".dat"):
            mode = "rb"
        elif ext == ".txt":
            mode = "r"
        else:
            return {
                'file_id': file_item.id,
                'file_name': file_item.file_name,
                'ok': False,
                'message': f'Unsupported extension: {ext}',
                'data': None
            }
        
        # Read and convert
        binary_chunks = []
        leftover = ""
        
        with open(file_item.file_path, mode) as f:
            while True:
                if self._stop_event.is_set():
                    return {'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'Cancelled', 'data': None}
                
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                
                # Convert based on file type
                if file_item.file_type == FileType.BINARY:
                    if isinstance(chunk, bytes):
                        binary_chunks.append(chunk)
                    else:
                        binary_chunks.append(chunk.encode("utf-8"))
                
                elif file_item.file_type == FileType.HEX:
                    text = chunk if isinstance(chunk, str) else chunk.decode("utf-8", errors="replace")
                    clean = "".join(ch for ch in text if ch in "0123456789abcdefABCDEF")
                    leftover += clean
                    complete_len = (len(leftover) // 2) * 2
                    if complete_len > 0:
                        binary_chunks.append(bytes.fromhex(leftover[:complete_len]))
                        leftover = leftover[complete_len:]
                
                elif file_item.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                    bytes_map = {FileType.UINT8: 1, FileType.UINT16: 2, FileType.UINT32: 4, FileType.UINT64: 8}
                    nbytes = bytes_map[file_item.file_type]
                    text = chunk if isinstance(chunk, str) else chunk.decode("utf-8", errors="replace")
                    lines = (leftover + text).split('\n')
                    leftover = lines[-1]
                    for line in lines[:-1]:
                        line = line.strip()
                        if line:
                            number = int(line)
                            binary_chunks.append(number.to_bytes(nbytes, byteorder='big'))
                
                elif file_item.file_type == FileType.STRING01:
                    text = chunk if isinstance(chunk, str) else chunk.decode("utf-8", errors="replace")
                    bits = leftover + "".join(c for c in text if c in "01")
                    complete_len = (len(bits) // 8) * 8
                    if complete_len > 0:
                        chunk_bytes = bytearray()
                        for i in range(0, complete_len, 8):
                            chunk_bytes.append(int(bits[i:i+8], 2))
                        binary_chunks.append(bytes(chunk_bytes))
                        leftover = bits[complete_len:]
                    else:
                        leftover = bits
                
                time.sleep(0)
        
        # Handle leftover
        if leftover:
            if file_item.file_type == FileType.HEX and len(leftover) >= 2:
                binary_chunks.append(bytes.fromhex(leftover))
            elif file_item.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64) and leftover.strip():
                bytes_map = {FileType.UINT8: 1, FileType.UINT16: 2, FileType.UINT32: 4, FileType.UINT64: 8}
                nbytes = bytes_map[file_item.file_type]
                number = int(leftover.strip())
                binary_chunks.append(number.to_bytes(nbytes, byteorder='big'))
            elif file_item.file_type == FileType.STRING01 and leftover:
                if len(leftover) % 8:
                    leftover += "0" * (8 - len(leftover) % 8)
                chunk_bytes = bytearray()
                for i in range(0, len(leftover), 8):
                    chunk_bytes.append(int(leftover[i:i+8], 2))
                binary_chunks.append(bytes(chunk_bytes))
        
        binary_data = b"".join(binary_chunks)
        
        # Prepare output
        base_name = file_item.file_name
        out_tag = tag if tag else f"_{output_format}"
        
        if output_format == "binary":
            out_name = f"{base_name}{out_tag}.bin"
            out_data = bytes(binary_data)
        elif output_format == "hex":
            out_name = f"{base_name}{out_tag}.txt"
            out_data = self.binary_to_hex(binary_data)
        elif output_format == "uint8":
            out_name = f"{base_name}{out_tag}.txt"
            out_data = self.binary_to_uint(binary_data, 1)
        elif output_format == "uint16":
            out_name = f"{base_name}{out_tag}.txt"
            out_data = self.binary_to_uint(binary_data, 2)
        elif output_format == "uint32":
            out_name = f"{base_name}{out_tag}.txt"
            out_data = self.binary_to_uint(binary_data, 4)
        elif output_format == "uint64":
            out_name = f"{base_name}{out_tag}.txt"
            out_data = self.binary_to_uint(binary_data, 8)
        elif output_format == "string01":
            out_name = f"{base_name}{out_tag}.txt"
            out_data = self.binary_to_string01(binary_data)
        else:
            return {
                'file_id': file_item.id,
                'file_name': file_item.file_name,
                'ok': False,
                'message': f'Unknown format: {output_format}',
                'data': None
            }
        
        return {
            'file_id': file_item.id,
            'file_name': file_item.file_name,
            'ok': True,
            'message': 'Converted successfully',
            'data': out_data,
            'suggested_name': out_name,
            'output_format': output_format,
            'source_type': file_item.file_type.value
        }

    # --------------------- Converters ---------------------
    @staticmethod
    def hex_to_binary(text: str) -> bytes:
        clean = "".join(ch for ch in text if ch.strip())
        return bytes.fromhex(clean)

    @staticmethod
    def string01_to_binary(text: str) -> bytes:
        # Keep only 0/1, then pack into bytes
        bits = [c for c in text if c in "01"]
        # pad to multiple of 8
        if len(bits) % 8:
            bits += ["0"] * (8 - (len(bits) % 8))
        out = bytearray()
        for i in range(0, len(bits), 8):
            byte_str = "".join(bits[i:i+8])
            out.append(int(byte_str, 2))
        return bytes(out)

    @staticmethod
    def binary_to_hex(data: bytes) -> str:
        return data.hex().upper()

    @staticmethod
    def binary_to_uint(data: bytes, nbytes: int) -> str:
        """Convert binary data to uintX format (one unsigned integer per line).
        
        Args:
            data: Binary data to convert
            nbytes: Number of bytes per integer (1=uint8, 2=uint16, 4=uint32, 8=uint64)
            
        Returns:
            str: String with one unsigned integer per line
        """
        uint_list = []
        # Process the binary data in chunks of nbytes
        for i in range(0, len(data), nbytes):
            chunk = data[i:i+nbytes]
            # If the chunk is less than nbytes, pad it with zeros
            if len(chunk) < nbytes:
                chunk = chunk.ljust(nbytes, b'\0')
            # Convert the chunk to an unsigned integer
            uint_value = int.from_bytes(chunk, byteorder='big')
            uint_list.append(str(uint_value))
        return '\n'.join(uint_list)
    
    @staticmethod
    def uint_to_binary(uint_text: str, nbytes: int) -> bytes:
        """Convert uintX format (one unsigned integer per line) to binary data.
        
        Args:
            uint_text: String with one unsigned integer per line
            nbytes: Number of bytes per integer (1=uint8, 2=uint16, 4=uint32, 8=uint64)
            
        Returns:
            bytes: Binary data
        """
        binary_data = bytearray()
        for line in uint_text.strip().split('\n'):
            line = line.strip()
            if line:
                number = int(line)
                binary_data.extend(number.to_bytes(nbytes, byteorder='big'))
        return bytes(binary_data)

    @staticmethod
    def binary_to_string01(data: bytes) -> str:
        return "".join(f"{b:08b}" for b in data)
