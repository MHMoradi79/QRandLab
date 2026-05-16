# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Slicer core.

- Uses shared InputFileMeta for loose coupling
- Unified event `on_slice` emitting OperationStatus with payloads
- Async slicing on background thread
- Returns sliced data via event payloads (no internal saving)
- Uses pathlib for all filesystem operations
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread, Event as ThreadEvent
from typing import Optional, Tuple, Dict, Any, List
import random

from .observer import Event
from .types import InputFileMeta, OperationStatus, FileItem


class Slicer:
    """Slice byte ranges from the input file referenced by InputFileMeta.
    
    Events:
    - on_multi_slice(OperationStatus): Emitted after multi-file slicing completes.
    - on_slice_progress(OperationStatus): Emitted for each file during multi-file slicing.
    """

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_multi_slice = Event()  # For multi-file slicing
        self.on_slice_progress = Event()  # Progress for each file

        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self._multi_results: List[Dict[str, Any]] = []
    
    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    # --------------------- Multi-File Slicing ---------------------
    def slice_files_equal_parts_async(self, file_items: List[FileItem], parts: int) -> None:
        """Slice multiple files into equal parts."""
        if not file_items:
            self.on_multi_slice.notify(status=OperationStatus(ok=False, message="No files to slice"))
            return
        if self._thread and self._thread.is_alive():
            self.on_multi_slice.notify(status=OperationStatus(ok=False, message="Slicing already in progress"))
            return
        self._stop_event.clear()
        self._multi_results = []
        self._thread = Thread(target=self._slice_files_equal_worker, args=(file_items, parts), daemon=True)
        self._thread.start()

    def slice_files_single_async(self, file_items: List[FileItem], start: int, length: int) -> None:
        """Slice a portion from multiple files."""
        if not file_items:
            self.on_multi_slice.notify(status=OperationStatus(ok=False, message="No files to slice"))
            return
        if self._thread and self._thread.is_alive():
            self.on_multi_slice.notify(status=OperationStatus(ok=False, message="Slicing already in progress"))
            return
        self._stop_event.clear()
        self._multi_results = []
        self._thread = Thread(target=self._slice_files_single_worker, args=(file_items, start, length), daemon=True)
        self._thread.start()

    def slice_files_random_async(self, file_items: List[FileItem], count: int, size: int, seed: Optional[int] = None) -> None:
        """Create random samples from multiple files."""
        if not file_items:
            self.on_multi_slice.notify(status=OperationStatus(ok=False, message="No files to slice"))
            return
        if self._thread and self._thread.is_alive():
            self.on_multi_slice.notify(status=OperationStatus(ok=False, message="Slicing already in progress"))
            return
        self._stop_event.clear()
        self._multi_results = []
        self._thread = Thread(target=self._slice_files_random_worker, args=(file_items, count, size, seed), daemon=True)
        self._thread.start()

    def _slice_files_equal_worker(self, file_items: List[FileItem], parts: int) -> None:
        """Worker for equal parts slicing of multiple files."""
        results = []
        success_count = 0
        fail_count = 0
        total_files = len(file_items)
        
        for idx, file_item in enumerate(file_items):
            if self._stop_event.is_set():
                return
            try:
                p = Path(file_item.file_path)
                if not p.is_file():
                    results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'File not found'})
                    fail_count += 1
                    self.on_slice_progress.notify(status=OperationStatus(
                        ok=True, message=f"Processing {idx + 1}/{total_files}",
                        payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                    ))
                    continue
                
                file_size = p.stat().st_size
                if file_size < parts:
                    results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': f'File too small for {parts} parts'})
                    fail_count += 1
                    self.on_slice_progress.notify(status=OperationStatus(
                        ok=True, message=f"Processing {idx + 1}/{total_files}",
                        payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                    ))
                    continue
                
                base_size = file_size // parts
                remainder = file_size % parts
                part_results = []
                
                with open(p, "rb") as f:
                    offset = 0
                    for i in range(parts):
                        extra = 1 if i < remainder else 0
                        seg_len = base_size + extra
                        f.seek(offset)
                        data = f.read(seg_len)
                        ext = file_item.file_ext.value if file_item.file_ext else ".bin"
                        suggested = f"{file_item.file_name}_part{i+1}of{parts}{ext}"
                        part_results.append({'data': data, 'suggested_name': suggested, 'start': offset, 'length': seg_len})
                        offset += seg_len
                
                results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': True, 'parts': part_results})
                success_count += 1
            except Exception as e:
                results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': str(e)})
                fail_count += 1
            
            # Emit progress after each file
            self.on_slice_progress.notify(status=OperationStatus(
                ok=True, message=f"Processing {idx + 1}/{total_files}",
                payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
            ))
        
        self._multi_results = results
        self.on_multi_slice.notify(status=OperationStatus(
            ok=success_count > 0,
            message=f"Sliced {success_count} file(s) into {parts} parts each, {fail_count} failed",
            payload={'method': 'equal_parts', 'parts_count': parts, 'results': results, 'success_count': success_count, 'fail_count': fail_count}
        ))

    def _slice_files_single_worker(self, file_items: List[FileItem], start: int, length: int) -> None:
        """Worker for single slice from multiple files."""
        results = []
        success_count = 0
        fail_count = 0
        total_files = len(file_items)
        
        for idx, file_item in enumerate(file_items):
            if self._stop_event.is_set():
                return
            try:
                p = Path(file_item.file_path)
                if not p.is_file():
                    results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'File not found'})
                    fail_count += 1
                    self.on_slice_progress.notify(status=OperationStatus(
                        ok=True, message=f"Processing {idx + 1}/{total_files}",
                        payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                    ))
                    continue
                
                file_size = p.stat().st_size
                if start >= file_size:
                    results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': f'Start position ({start}) exceeds file size ({file_size})'})
                    fail_count += 1
                    self.on_slice_progress.notify(status=OperationStatus(
                        ok=True, message=f"Processing {idx + 1}/{total_files}",
                        payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                    ))
                    continue
                
                actual_length = min(length, file_size - start)
                
                with open(p, "rb") as f:
                    f.seek(start)
                    data = f.read(actual_length)
                
                ext = file_item.file_ext.value if file_item.file_ext else ".bin"
                suggested = f"{file_item.file_name}_slice_s{start}_l{actual_length}{ext}"
                results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': True, 'data': data, 'suggested_name': suggested, 'start': start, 'length': actual_length})
                success_count += 1
            except Exception as e:
                results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': str(e)})
                fail_count += 1
            
            # Emit progress after each file
            self.on_slice_progress.notify(status=OperationStatus(
                ok=True, message=f"Processing {idx + 1}/{total_files}",
                payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
            ))
        
        self._multi_results = results
        self.on_multi_slice.notify(status=OperationStatus(
            ok=success_count > 0,
            message=f"Sliced {success_count} file(s), {fail_count} failed",
            payload={'method': 'single', 'results': results, 'success_count': success_count, 'fail_count': fail_count}
        ))

    def _slice_files_random_worker(self, file_items: List[FileItem], count: int, size: int, seed: Optional[int]) -> None:
        """Worker for random sampling from multiple files."""
        results = []
        success_count = 0
        fail_count = 0
        rng = random.Random(seed)
        total_files = len(file_items)
        
        for idx, file_item in enumerate(file_items):
            if self._stop_event.is_set():
                return
            try:
                p = Path(file_item.file_path)
                if not p.is_file():
                    results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': 'File not found'})
                    fail_count += 1
                    self.on_slice_progress.notify(status=OperationStatus(
                        ok=True, message=f"Processing {idx + 1}/{total_files}",
                        payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                    ))
                    continue
                
                file_size = p.stat().st_size
                if size > file_size:
                    results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': f'Sample size ({size}) exceeds file size ({file_size})'})
                    fail_count += 1
                    self.on_slice_progress.notify(status=OperationStatus(
                        ok=True, message=f"Processing {idx + 1}/{total_files}",
                        payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
                    ))
                    continue
                
                max_start = file_size - size
                starts = [rng.randint(0, max_start) for _ in range(count)]
                samples = []
                
                with open(p, "rb") as f:
                    for i, s in enumerate(starts):
                        f.seek(s)
                        data = f.read(size)
                        ext = file_item.file_ext.value if file_item.file_ext else ".bin"
                        suggested = f"{file_item.file_name}_sample{i+1}{ext}"
                        samples.append({'data': data, 'suggested_name': suggested, 'start': s, 'length': len(data)})
                
                results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': True, 'samples': samples})
                success_count += 1
            except Exception as e:
                results.append({'file_id': file_item.id, 'file_name': file_item.file_name, 'ok': False, 'message': str(e)})
                fail_count += 1
            
            # Emit progress after each file
            self.on_slice_progress.notify(status=OperationStatus(
                ok=True, message=f"Processing {idx + 1}/{total_files}",
                payload={'current': idx + 1, 'total': total_files, 'file_name': file_item.file_name}
            ))
        
        self._multi_results = results
        self.on_multi_slice.notify(status=OperationStatus(
            ok=success_count > 0,
            message=f"Created {count} samples from {success_count} file(s), {fail_count} failed",
            payload={'method': 'random_samples', 'sample_count': count, 'sample_size': size, 'results': results, 'success_count': success_count, 'fail_count': fail_count}
        ))
