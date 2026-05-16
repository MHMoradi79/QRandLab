# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Core InputFile module for handling random data files.

This module provides functionality to import, validate, and read samples from input files.
It emits events for each operation with a unified status payload.

No GUI dependencies; works with plain types and dataclasses.
"""

import math
import re
import time
from pathlib import Path
from threading import Thread, Event as ThreadEvent
from typing import Optional, List

from .observer import Event
from .types import InputFileMeta, ReadSampleResult, FileExt, FileType, OperationStatus, FileItem


class InputFile:
    """Core class for input file operations working on a shared metadata container."""

    def __init__(self, meta: InputFileMeta) -> None:
        """Initialize with a shared InputFileMeta container to be updated in place.

        Args:
            meta: Mutable metadata container shared across cores/manager.
        """
        self.meta = meta

        # Unified events for each method (single file - backward compatibility)
        self.on_import_file = Event()
        self.on_set_file_type = Event()
        self.on_check_file = Event()
        self.on_read_sample = Event()
        
        # Multi-file events
        self.on_files_added = Event()       # Fired when files are added
        self.on_files_removed = Event()     # Fired when files are removed
        self.on_file_type_changed = Event() # Fired when a file's type is changed
        self.on_file_validated = Event()    # Fired when a single file is validated
        self.on_all_files_validated = Event()  # Fired when all files validation completes
        self.on_files_cleared = Event()     # Fired when all files are cleared
        self.on_validation_progress = Event()  # Progress for validation
        
        # Thread for async operations
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self._validation_threads: List[Thread] = []  # For multi-file validation
    
    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    def import_file(self, input_file: str) -> OperationStatus:
        """Import a file and populate the shared InputFileMeta in place.

        Args:
            input_file: Path to the file to import.

        Returns:
            OperationStatus with success/failure and metadata if successful.
        """
        if not input_file or not Path(input_file).is_file():
            status = OperationStatus(
                ok=False,
                message="Invalid file path or file does not exist.",
                payload=None
            )
            self.on_import_file.notify(status=status)
            return status

        try:
            file_size = Path(input_file).stat().st_size
        except OSError as e:
            status = OperationStatus(
                ok=False,
                message=f"Could not get file size: {e}",
                payload=None
            )
            self.on_import_file.notify(status=status)
            return status

        p = Path(input_file)
        file_dir = p.parent.as_posix()
        file_name = p.stem
        file_ext_str = p.suffix

        # Validate extension
        if file_ext_str not in [ext.value for ext in FileExt]:
            status = OperationStatus(
                ok=False,
                message=f"Unsupported file extension: {file_ext_str}. Supported: {[ext.value for ext in FileExt]}",
                payload=None
            )
            self.on_import_file.notify(status=status)
            return status

        # Update meta in place - normalize paths to use forward slashes
        self.meta.file_path = p.as_posix()
        self.meta.file_dir = file_dir
        self.meta.file_name = file_name
        self.meta.file_ext = FileExt(file_ext_str)
        self.meta.file_size = file_size
        self.meta.file_type = None  # Reset file type when new file is imported

        status = OperationStatus(
            ok=True,
            message="File imported successfully.",
            payload=self.meta
        )
        self.on_import_file.notify(status=status)
        return status

    def set_file_type(self, file_type: str) -> OperationStatus:
        """Set the file type for interpretation.

        Args:
            file_type: The file type (e.g., 'binary', 'string01').

        Returns:
            OperationStatus indicating success or failure.
        """
        if not self.meta.file_path:
            status = OperationStatus(
                ok=False,
                message="No file imported yet.",
                payload=None
            )
            self.on_set_file_type.notify(status=status)
            return status

        # Validate file_type
        valid_types = [ft.value for ft in FileType]
        if file_type not in valid_types:
            status = OperationStatus(
                ok=False,
                message=f"Invalid file type: {file_type}. Valid types: {valid_types}",
                payload=None
            )
            self.on_set_file_type.notify(status=status)
            return status

        # store as enum
        self.meta.file_type = FileType(file_type)
        status = OperationStatus(
            ok=True,
            message=f"File type set to {file_type}.",
            payload=self.meta.file_type
        )
        self.on_set_file_type.notify(status=status)
        return status

    def check_file_async(self) -> OperationStatus:
        """Start file validation on a background thread. Emits on_check_file when done.
        
        Returns:
            OperationStatus indicating if the validation started successfully.
        """
        if not self.meta.file_path or not self.meta.file_type:
            status = OperationStatus(
                ok=False,
                message="File path or type not set.",
                payload=None
            )
            self.on_check_file.notify(status=status)
            return status
        
        # Avoid overlapping jobs
        if self._thread and self._thread.is_alive():
            status = OperationStatus(
                ok=False,
                message="Validation already in progress",
                payload=None
            )
            self.on_check_file.notify(status=status)
            return status
        
        self._stop_event.clear()
        self._thread = Thread(target=self._check_file_worker, daemon=True)
        self._thread.start()
        return OperationStatus(ok=True, message="Validation started")
    
    def _check_file_worker(self) -> None:
        """Worker that executes validation and emits the result status.
        
        Uses chunked reading and regex for fast validation without blocking GIL.
        """
        # Check stop before starting
        if self._stop_event.is_set():
            return
        
        # Smaller chunk size to yield control more frequently
        CHUNK_SIZE = 256 * 1024  # 256KB chunks
        
        try:
            if self.meta.file_type == FileType.STRING01:
                # Use regex for fast validation - matches any char NOT in allowed set
                invalid_pattern = re.compile(r'[^01\s]')
                with open(self.meta.file_path, "r", encoding="utf-8") as f:
                    while True:
                        if self._stop_event.is_set():
                            return
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        # Fast regex check for invalid chars
                        if invalid_pattern.search(chunk):
                            status = OperationStatus(
                                ok=False,
                                message="File contains characters other than 0 and 1.",
                                payload=None
                            )
                            self.on_check_file.notify(status=status)
                            return
                        # Yield to other threads briefly
                        time.sleep(0)
                status = OperationStatus(
                    ok=True,
                    message="File contains only 0s and 1s.",
                    payload=None
                )
                
            elif self.meta.file_type == FileType.BINARY:
                # For binary files, just check if it's readable
                with open(self.meta.file_path, "rb") as f:
                    f.read(1024)
                status = OperationStatus(
                    ok=True,
                    message="Binary file is valid and readable.",
                    payload=None
                )
                
            elif self.meta.file_type == FileType.HEX:
                invalid_pattern = re.compile(r'[^0-9a-fA-F\s]')
                with open(self.meta.file_path, "r", encoding="utf-8") as f:
                    while True:
                        if self._stop_event.is_set():
                            return
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        if invalid_pattern.search(chunk):
                            status = OperationStatus(
                                ok=False,
                                message="File contains invalid hexadecimal characters.",
                                payload=None
                            )
                            self.on_check_file.notify(status=status)
                            return
                        time.sleep(0)
                status = OperationStatus(
                    ok=True,
                    message="File contains valid hexadecimal data.",
                    payload=None
                )
                
            elif self.meta.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                # Validate that each line contains a valid unsigned integer
                type_info = {
                    FileType.UINT8: ("uint8", 0, 255),
                    FileType.UINT16: ("uint16", 0, 65535),
                    FileType.UINT32: ("uint32", 0, 4294967295),
                    FileType.UINT64: ("uint64", 0, 18446744073709551615),
                }
                type_name, min_val, max_val = type_info[self.meta.file_type]
                
                with open(self.meta.file_path, "r", encoding="utf-8") as f:
                    line_num = 0
                    leftover = ""
                    while True:
                        if self._stop_event.is_set():
                            return
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            # Process any remaining leftover
                            if leftover.strip():
                                line_num += 1
                                try:
                                    val = int(leftover.strip())
                                    if val < min_val or val > max_val:
                                        status = OperationStatus(
                                            ok=False,
                                            message=f"Line {line_num}: Value {val} out of {type_name} range [{min_val}, {max_val}].",
                                            payload=None
                                        )
                                        self.on_check_file.notify(status=status)
                                        return
                                except ValueError:
                                    status = OperationStatus(
                                        ok=False,
                                        message=f"Line {line_num}: Invalid integer value.",
                                        payload=None
                                    )
                                    self.on_check_file.notify(status=status)
                                    return
                            break
                        
                        # Process lines in chunk
                        lines = (leftover + chunk).split('\n')
                        leftover = lines[-1]  # Keep incomplete line
                        for line in lines[:-1]:
                            line_num += 1
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                val = int(line)
                                if val < min_val or val > max_val:
                                    status = OperationStatus(
                                        ok=False,
                                        message=f"Line {line_num}: Value {val} out of {type_name} range [{min_val}, {max_val}].",
                                        payload=None
                                    )
                                    self.on_check_file.notify(status=status)
                                    return
                            except ValueError:
                                status = OperationStatus(
                                    ok=False,
                                    message=f"Line {line_num}: Invalid integer value.",
                                    payload=None
                                )
                                self.on_check_file.notify(status=status)
                                return
                        time.sleep(0)
                status = OperationStatus(
                    ok=True,
                    message=f"File contains valid {type_name} data.",
                    payload=None
                )
            else:
                status = OperationStatus(
                    ok=False,
                    message=f"Validation not implemented for type: {self.meta.file_type}.",
                    payload=None
                )
            self.on_check_file.notify(status=status)
        except Exception as e:
            status = OperationStatus(
                ok=False,
                message=f"File validation failed: {e}",
                payload=None
            )
            self.on_check_file.notify(status=status)
    
    def check_file(self) -> OperationStatus:
        """Validate the file contents based on the set file_type (synchronous).
        
        Note: Prefer check_file_async() for large files to avoid blocking.

        Returns:
            OperationStatus indicating if the file is valid.
        """
        if not self.meta.file_path or not self.meta.file_type:
            status = OperationStatus(
                ok=False,
                message="File path or type not set.",
                payload=None
            )
            self.on_check_file.notify(status=status)
            return status

        # Run worker directly (synchronous)
        self._check_file_worker()
        return OperationStatus(ok=True, message="Validation completed")

    def read_sample(self, n_bytes: int = 256) -> OperationStatus:
        """Read a sample of data from the file.

        Args:
            n_bytes: Number of bytes to read. For Base64 (num64) files, this is converted to number of lines.

        Returns:
            OperationStatus with ReadSampleResult if successful.
        """
        if not self.meta.file_path:
            status = OperationStatus(
                ok=False,
                message="No file imported.",
                payload=None
            )
            self.on_read_sample.notify(status=status)
            return status
        
        # Check if file type is set
        if not self.meta.file_type:
            status = OperationStatus(
                ok=False,
                message="File type is not set. Please set the file type first.",
                payload=None
            )
            self.on_read_sample.notify(status=status)
            return status

        try:
            if self.meta.file_type == FileType.STRING01:
                # STRING01: each character is 1 bit, need 8x characters for n_bytes
                n_chars = n_bytes * 8
                with open(self.meta.file_path, "r", encoding="utf-8") as f:
                    text_data = f.read(n_chars)
                    data = text_data.encode('utf-8')
                
                # Calculate actual information bytes (bits / 8)
                info_bytes = len(text_data) // 8
                result = ReadSampleResult(
                    title=f"Sample: {len(text_data)} chars ({info_bytes} bytes of information, {len(data)} file bytes)",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(text_data)} characters ({info_bytes} bytes of information).",
                    payload=result
                )
            
            elif self.meta.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                # UINTx: each line is 1/2/4/8 bytes of information depending on type
                bytes_per_line = {
                    FileType.UINT8: 1,
                    FileType.UINT16: 2,
                    FileType.UINT32: 4,
                    FileType.UINT64: 8,
                }
                bpl = bytes_per_line[self.meta.file_type]
                n_lines = math.ceil(n_bytes / bpl)
                
                with open(self.meta.file_path, "r", encoding="utf-8") as f:
                    lines = []
                    for _ in range(n_lines):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                    
                    text_data = ''.join(lines)
                    data = text_data.encode('utf-8')
                
                # Each line = bpl bytes of information
                info_bytes = len(lines) * bpl
                result = ReadSampleResult(
                    title=f"Sample: {len(lines)} lines ({info_bytes} bytes of information, {len(data)} file bytes)",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(lines)} lines ({info_bytes} bytes of information).",
                    payload=result
                )
            
            elif self.meta.file_type == FileType.HEX:
                # HEX: each 2 hex characters = 1 byte of information
                n_chars = n_bytes * 2
                with open(self.meta.file_path, "r", encoding="utf-8") as f:
                    text_data = f.read(n_chars)
                    data = text_data.encode('utf-8')
                
                # Calculate actual information bytes (hex chars / 2)
                # Only count valid hex characters
                hex_chars = sum(1 for c in text_data if c in '0123456789ABCDEFabcdef')
                info_bytes = hex_chars // 2
                result = ReadSampleResult(
                    title=f"Sample: {len(text_data)} chars ({info_bytes} bytes of information, {len(data)} file bytes)",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(text_data)} characters ({info_bytes} bytes of information).",
                    payload=result
                )
            
            elif self.meta.file_type == FileType.BINARY:
                # BINARY: 1 byte = 1 byte of information
                with open(self.meta.file_path, "rb") as f:
                    data = f.read(n_bytes)
                
                result = ReadSampleResult(
                    title=f"Sample: {len(data)} bytes",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(data)} bytes.",
                    payload=result
                )
            
            else:
                # Default fallback
                with open(self.meta.file_path, "rb") as f:
                    data = f.read(n_bytes)
                result = ReadSampleResult(title=f"Sample: {len(data)} bytes", data=data)
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(data)} bytes.",
                    payload=result
                )
            
            self.on_read_sample.notify(status=status)
            return status
        except Exception as e:
            status = OperationStatus(
                ok=False,
                message=f"Failed to read sample: {e}",
                payload=None
            )
            self.on_read_sample.notify(status=status)
            return status

    # ==================== Multi-File Operations ====================
    
    def add_files(self, file_paths: List[str]) -> OperationStatus:
        """Add multiple files to the collection.
        
        Args:
            file_paths: List of file paths to add.
            
        Returns:
            OperationStatus with list of added FileItems in payload.
        """
        if not file_paths:
            status = OperationStatus(
                ok=False,
                message="No files provided.",
                payload=None
            )
            self.on_files_added.notify(status=status)
            return status
        
        added_items = []
        failed_files = []
        
        for file_path in file_paths:
            if not file_path or not Path(file_path).is_file():
                failed_files.append(f"{file_path}: File does not exist")
                continue
            
            try:
                p = Path(file_path)
                file_size = p.stat().st_size
                file_ext_str = p.suffix
                
                # Validate extension
                if file_ext_str not in [ext.value for ext in FileExt]:
                    failed_files.append(f"{p.name}: Unsupported extension {file_ext_str}")
                    continue
                
                # Create FileItem
                item = FileItem(
                    file_path=p.as_posix(),
                    file_dir=p.parent.as_posix(),
                    file_name=p.stem,
                    file_ext=FileExt(file_ext_str),
                    file_type=None,  # Default is None (displayed as '--')
                    file_size=file_size
                )
                
                # Add to meta collection
                self.meta.add_file_item(item)
                added_items.append(item)
                
            except OSError as e:
                failed_files.append(f"{file_path}: {e}")
        
        # Build result message
        if added_items and not failed_files:
            message = f"Added {len(added_items)} file(s) successfully."
            ok = True
        elif added_items and failed_files:
            message = f"Added {len(added_items)} file(s). Failed: {len(failed_files)}."
            ok = True
        else:
            message = f"Failed to add files: {'; '.join(failed_files)}"
            ok = False
        
        status = OperationStatus(
            ok=ok,
            message=message,
            payload={
                'added': added_items,
                'failed': failed_files,
                'total_files': self.meta.get_file_count()
            }
        )
        self.on_files_added.notify(status=status)
        return status
    
    def remove_files(self, file_ids: List[str]) -> OperationStatus:
        """Remove files from the collection by their IDs.
        
        Args:
            file_ids: List of file IDs to remove.
            
        Returns:
            OperationStatus with removed count in payload.
        """
        if not file_ids:
            status = OperationStatus(
                ok=False,
                message="No file IDs provided.",
                payload=None
            )
            self.on_files_removed.notify(status=status)
            return status
        
        removed_count = 0
        removed_paths = []
        for file_id in file_ids:
            # Get file path before removal for report update
            file_item = self.meta.get_file_item(file_id)
            if file_item and file_item.file_path:
                removed_paths.append(file_item.file_path)
            if self.meta.remove_file_item(file_id):
                removed_count += 1
        
        status = OperationStatus(
            ok=True,
            message=f"Removed {removed_count} file(s).",
            payload={
                'removed_count': removed_count,
                'removed_paths': removed_paths,
                'total_files': self.meta.get_file_count()
            }
        )
        self.on_files_removed.notify(status=status)
        return status
    
    def set_file_type_for_item(self, file_id: str, file_type: str) -> OperationStatus:
        """Set file type for a specific file item.
        
        Args:
            file_id: ID of the file to update.
            file_type: The file type to set (e.g., 'binary', 'string01').
            
        Returns:
            OperationStatus indicating success or failure.
        """
        item = self.meta.get_file_by_id(file_id)
        if not item:
            status = OperationStatus(
                ok=False,
                message=f"File with ID {file_id} not found.",
                payload=None
            )
            self.on_file_type_changed.notify(status=status)
            return status
        
        # Validate file_type
        valid_types = [ft.value for ft in FileType]
        if file_type not in valid_types:
            status = OperationStatus(
                ok=False,
                message=f"Invalid file type: {file_type}. Valid types: {valid_types}",
                payload=None
            )
            self.on_file_type_changed.notify(status=status)
            return status
        
        # Update file type
        item.file_type = FileType(file_type)
        
        status = OperationStatus(
            ok=True,
            message=f"File type for '{item.file_name}' set to {file_type}.",
            payload={
                'file_id': file_id,
                'file_type': file_type,
                'item': item
            }
        )
        self.on_file_type_changed.notify(status=status)
        return status
    
    def validate_file_item_async(self, file_id: str) -> OperationStatus:
        """Validate a specific file item asynchronously.
        
        Args:
            file_id: ID of the file to validate.
            
        Returns:
            OperationStatus indicating if validation started.
        """
        item = self.meta.get_file_by_id(file_id)
        if not item:
            status = OperationStatus(
                ok=False,
                message=f"File with ID {file_id} not found.",
                payload=None
            )
            self.on_file_validated.notify(status=status)
            return status
        
        if not item.file_type:
            status = OperationStatus(
                ok=False,
                message=f"File type not set for '{item.file_name}'.",
                payload={'file_id': file_id}
            )
            self.on_file_validated.notify(status=status)
            return status
        
        self._stop_event.clear()
        thread = Thread(target=self._validate_file_item_worker, args=(item,), daemon=True)
        thread.start()
        return OperationStatus(ok=True, message=f"Validation started for '{item.file_name}'")
    
    def _validate_file_item_worker(self, item: FileItem) -> None:
        """Worker to validate a single file item."""
        if self._stop_event.is_set():
            return
        
        CHUNK_SIZE = 256 * 1024
        
        try:
            if item.file_type == FileType.STRING01:
                invalid_pattern = re.compile(r'[^01\s]')
                with open(item.file_path, "r", encoding="utf-8") as f:
                    while True:
                        if self._stop_event.is_set():
                            return
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        if invalid_pattern.search(chunk):
                            status = OperationStatus(
                                ok=False,
                                message=f"'{item.file_name}': Contains invalid characters (not 0/1).",
                                payload={'file_id': item.id, 'item': item}
                            )
                            self.on_file_validated.notify(status=status)
                            return
                        time.sleep(0)
                status = OperationStatus(
                    ok=True,
                    message=f"'{item.file_name}': Valid string01 file.",
                    payload={'file_id': item.id, 'item': item}
                )
                
            elif item.file_type == FileType.BINARY:
                with open(item.file_path, "rb") as f:
                    f.read(1024)
                status = OperationStatus(
                    ok=True,
                    message=f"'{item.file_name}': Valid binary file.",
                    payload={'file_id': item.id, 'item': item}
                )
                
            elif item.file_type == FileType.HEX:
                invalid_pattern = re.compile(r'[^0-9a-fA-F\s]')
                with open(item.file_path, "r", encoding="utf-8") as f:
                    while True:
                        if self._stop_event.is_set():
                            return
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        if invalid_pattern.search(chunk):
                            status = OperationStatus(
                                ok=False,
                                message=f"'{item.file_name}': Contains invalid hex characters.",
                                payload={'file_id': item.id, 'item': item}
                            )
                            self.on_file_validated.notify(status=status)
                            return
                        time.sleep(0)
                status = OperationStatus(
                    ok=True,
                    message=f"'{item.file_name}': Valid hex file.",
                    payload={'file_id': item.id, 'item': item}
                )
                
            elif item.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                type_info = {
                    FileType.UINT8: ("uint8", 0, 255),
                    FileType.UINT16: ("uint16", 0, 65535),
                    FileType.UINT32: ("uint32", 0, 4294967295),
                    FileType.UINT64: ("uint64", 0, 18446744073709551615),
                }
                type_name, min_val, max_val = type_info[item.file_type]
                
                with open(item.file_path, "r", encoding="utf-8") as f:
                    line_num = 0
                    leftover = ""
                    while True:
                        if self._stop_event.is_set():
                            return
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            if leftover.strip():
                                line_num += 1
                                try:
                                    val = int(leftover.strip())
                                    if val < min_val or val > max_val:
                                        status = OperationStatus(
                                            ok=False,
                                            message=f"'{item.file_name}' line {line_num}: Value out of range.",
                                            payload={'file_id': item.id, 'item': item}
                                        )
                                        self.on_file_validated.notify(status=status)
                                        return
                                except ValueError:
                                    status = OperationStatus(
                                        ok=False,
                                        message=f"'{item.file_name}' line {line_num}: Invalid integer.",
                                        payload={'file_id': item.id, 'item': item}
                                    )
                                    self.on_file_validated.notify(status=status)
                                    return
                            break
                        
                        lines = (leftover + chunk).split('\n')
                        leftover = lines[-1]
                        for line in lines[:-1]:
                            line_num += 1
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                val = int(line)
                                if val < min_val or val > max_val:
                                    status = OperationStatus(
                                        ok=False,
                                        message=f"'{item.file_name}' line {line_num}: Value out of range.",
                                        payload={'file_id': item.id, 'item': item}
                                    )
                                    self.on_file_validated.notify(status=status)
                                    return
                            except ValueError:
                                status = OperationStatus(
                                    ok=False,
                                    message=f"'{item.file_name}' line {line_num}: Invalid integer.",
                                    payload={'file_id': item.id, 'item': item}
                                )
                                self.on_file_validated.notify(status=status)
                                return
                        time.sleep(0)
                status = OperationStatus(
                    ok=True,
                    message=f"'{item.file_name}': Valid {type_name} file.",
                    payload={'file_id': item.id, 'item': item}
                )
            else:
                status = OperationStatus(
                    ok=False,
                    message=f"'{item.file_name}': Validation not supported for type {item.file_type}.",
                    payload={'file_id': item.id, 'item': item}
                )
            
            self.on_file_validated.notify(status=status)
            
        except Exception as e:
            status = OperationStatus(
                ok=False,
                message=f"'{item.file_name}': Validation error - {e}",
                payload={'file_id': item.id, 'item': item}
            )
            self.on_file_validated.notify(status=status)
    
    def validate_all_files_async(self) -> OperationStatus:
        """Validate all files that have a type set.
        
        Returns:
            OperationStatus indicating if validation started.
        """
        files_to_validate = [item for item in self.meta.file_items if item.file_type]
        
        if not files_to_validate:
            status = OperationStatus(
                ok=False,
                message="No files with type set to validate.",
                payload=None
            )
            self.on_all_files_validated.notify(status=status)
            return status
        
        self._stop_event.clear()
        thread = Thread(target=self._validate_all_files_worker, args=(files_to_validate,), daemon=True)
        thread.start()
        return OperationStatus(ok=True, message=f"Validation started for {len(files_to_validate)} file(s)")
    
    def _validate_all_files_worker(self, items: List[FileItem]) -> None:
        """Worker to validate all files sequentially."""
        results = []
        passed = 0
        failed = 0
        total_files = len(items)
        
        for idx, item in enumerate(items):
            if self._stop_event.is_set():
                return
            
            # Validate each file
            result = self._validate_single_file_sync(item)
            results.append(result)
            if result['ok']:
                passed += 1
            else:
                failed += 1
            
            # Notify per-file validation
            self.on_file_validated.notify(status=OperationStatus(
                ok=result['ok'],
                message=result['message'],
                payload={'file_id': item.id, 'item': item}
            ))
            
            # Emit progress after each file
            self.on_validation_progress.notify(status=OperationStatus(
                ok=True, message=f"Validating {idx + 1}/{total_files}",
                payload={'current': idx + 1, 'total': total_files, 'file_name': item.file_name}
            ))
        
        # Final summary
        status = OperationStatus(
            ok=failed == 0,
            message=f"Validation complete: {passed} passed, {failed} failed.",
            payload={
                'results': results,
                'passed': passed,
                'failed': failed
            }
        )
        self.on_all_files_validated.notify(status=status)
    
    def _validate_single_file_sync(self, item: FileItem) -> dict:
        """Synchronously validate a single file. Returns dict with ok and message."""
        CHUNK_SIZE = 256 * 1024
        
        try:
            if item.file_type == FileType.STRING01:
                invalid_pattern = re.compile(r'[^01\s]')
                with open(item.file_path, "r", encoding="utf-8") as f:
                    while True:
                        if self._stop_event.is_set():
                            return {'ok': False, 'message': 'Cancelled'}
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        if invalid_pattern.search(chunk):
                            return {'ok': False, 'message': f"'{item.file_name}': Invalid characters"}
                        time.sleep(0)
                return {'ok': True, 'message': f"'{item.file_name}': Valid"}
                
            elif item.file_type == FileType.BINARY:
                with open(item.file_path, "rb") as f:
                    f.read(1024)
                return {'ok': True, 'message': f"'{item.file_name}': Valid"}
                
            elif item.file_type == FileType.HEX:
                invalid_pattern = re.compile(r'[^0-9a-fA-F\s]')
                with open(item.file_path, "r", encoding="utf-8") as f:
                    while True:
                        if self._stop_event.is_set():
                            return {'ok': False, 'message': 'Cancelled'}
                        chunk = f.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        if invalid_pattern.search(chunk):
                            return {'ok': False, 'message': f"'{item.file_name}': Invalid hex"}
                        time.sleep(0)
                return {'ok': True, 'message': f"'{item.file_name}': Valid"}
                
            elif item.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                type_info = {
                    FileType.UINT8: (0, 255),
                    FileType.UINT16: (0, 65535),
                    FileType.UINT32: (0, 4294967295),
                    FileType.UINT64: (0, 18446744073709551615),
                }
                min_val, max_val = type_info[item.file_type]
                
                with open(item.file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if self._stop_event.is_set():
                            return {'ok': False, 'message': 'Cancelled'}
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            val = int(line)
                            if val < min_val or val > max_val:
                                return {'ok': False, 'message': f"'{item.file_name}' line {line_num}: Out of range"}
                        except ValueError:
                            return {'ok': False, 'message': f"'{item.file_name}' line {line_num}: Invalid integer"}
                return {'ok': True, 'message': f"'{item.file_name}': Valid"}
            else:
                return {'ok': False, 'message': f"'{item.file_name}': Unknown type"}
                
        except Exception as e:
            return {'ok': False, 'message': f"'{item.file_name}': {e}"}
    
    def read_sample_from_item(self, file_id: str, n_bytes: int = 256) -> OperationStatus:
        """Read a sample from a specific file item.
        
        Args:
            file_id: ID of the file to read from.
            n_bytes: Number of bytes to read.
            
        Returns:
            OperationStatus with ReadSampleResult in payload.
        """
        item = self.meta.get_file_by_id(file_id)
        if not item:
            status = OperationStatus(
                ok=False,
                message=f"File with ID {file_id} not found.",
                payload=None
            )
            self.on_read_sample.notify(status=status)
            return status
        
        if not item.file_type:
            status = OperationStatus(
                ok=False,
                message=f"File type not set for '{item.file_name}'. Please set the file type first.",
                payload=None
            )
            self.on_read_sample.notify(status=status)
            return status
        
        try:
            if item.file_type == FileType.STRING01:
                n_chars = n_bytes * 8
                with open(item.file_path, "r", encoding="utf-8") as f:
                    text_data = f.read(n_chars)
                    data = text_data.encode('utf-8')
                info_bytes = len(text_data) // 8
                result = ReadSampleResult(
                    title=f"Sample from '{item.file_name}': {len(text_data)} chars ({info_bytes} bytes info)",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(text_data)} characters from '{item.file_name}'.",
                    payload={'result': result, 'file_id': file_id, 'file_type': item.file_type.value}
                )
                
            elif item.file_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                bytes_per_line = {
                    FileType.UINT8: 1, FileType.UINT16: 2,
                    FileType.UINT32: 4, FileType.UINT64: 8,
                }
                bpl = bytes_per_line[item.file_type]
                n_lines = math.ceil(n_bytes / bpl)
                
                with open(item.file_path, "r", encoding="utf-8") as f:
                    lines = []
                    for _ in range(n_lines):
                        line = f.readline()
                        if not line:
                            break
                        lines.append(line)
                    text_data = ''.join(lines)
                    data = text_data.encode('utf-8')
                
                info_bytes = len(lines) * bpl
                result = ReadSampleResult(
                    title=f"Sample from '{item.file_name}': {len(lines)} lines ({info_bytes} bytes info)",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(lines)} lines from '{item.file_name}'.",
                    payload={'result': result, 'file_id': file_id, 'file_type': item.file_type.value}
                )
                
            elif item.file_type == FileType.HEX:
                n_chars = n_bytes * 2
                with open(item.file_path, "r", encoding="utf-8") as f:
                    text_data = f.read(n_chars)
                    data = text_data.encode('utf-8')
                hex_chars = sum(1 for c in text_data if c in '0123456789ABCDEFabcdef')
                info_bytes = hex_chars // 2
                result = ReadSampleResult(
                    title=f"Sample from '{item.file_name}': {len(text_data)} chars ({info_bytes} bytes info)",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(text_data)} characters from '{item.file_name}'.",
                    payload={'result': result, 'file_id': file_id, 'file_type': item.file_type.value}
                )
                
            elif item.file_type == FileType.BINARY:
                with open(item.file_path, "rb") as f:
                    data = f.read(n_bytes)
                result = ReadSampleResult(
                    title=f"Sample from '{item.file_name}': {len(data)} bytes",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(data)} bytes from '{item.file_name}'.",
                    payload={'result': result, 'file_id': file_id, 'file_type': item.file_type.value}
                )
            else:
                with open(item.file_path, "rb") as f:
                    data = f.read(n_bytes)
                result = ReadSampleResult(
                    title=f"Sample from '{item.file_name}': {len(data)} bytes",
                    data=data
                )
                status = OperationStatus(
                    ok=True,
                    message=f"Read {len(data)} bytes from '{item.file_name}'.",
                    payload={'result': result, 'file_id': file_id, 'file_type': item.file_type.value}
                )
            
            self.on_read_sample.notify(status=status)
            return status
            
        except Exception as e:
            status = OperationStatus(
                ok=False,
                message=f"Failed to read sample from '{item.file_name}': {e}",
                payload=None
            )
            self.on_read_sample.notify(status=status)
            return status
    
    def clear_all_files(self) -> OperationStatus:
        """Remove all files from the collection.
        
        Returns:
            OperationStatus indicating success.
        """
        count = self.meta.get_file_count()
        self.meta.clear_file_items()
        
        # Also clear single-file legacy fields
        self.meta.file_path = ""
        self.meta.file_dir = ""
        self.meta.file_name = ""
        self.meta.file_ext = None
        self.meta.file_type = None
        self.meta.file_size = None
        
        status = OperationStatus(
            ok=True,
            message=f"Cleared {count} file(s).",
            payload={'cleared_count': count}
        )
        self.on_files_cleared.notify(status=status)
        return status
    
    def get_all_files(self) -> List[FileItem]:
        """Get all file items in the collection.
        
        Returns:
            List of FileItem objects.
        """
        return self.meta.file_items.copy()
    
    def get_file_count(self) -> int:
        """Get the number of files in the collection.
        
        Returns:
            Number of files.
        """
        return self.meta.get_file_count()

