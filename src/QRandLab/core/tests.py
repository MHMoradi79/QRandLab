# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Tests core - unified testing interface.

Manages all randomness tests through a single interface using shared InputFileMeta.
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List

from threading import Thread, Event as ThreadEvent
from pathlib import Path
import tempfile

from .observer import Event
from .types import InputFileMeta, OperationStatus, FileItem, FileType
from .test_core.ent_test import EntTest
from .test_core.dieharder_test import DieHarderTest
from .test_core.nist_test import NistTest
from .test_core.autocorrelation_test import AutocorrelationTest
from .test_core.borel_test import BorelTest


class Tests:
    """Unified testing interface for all randomness tests."""

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_test = Event()  # Unified test result event
        self.on_progress = Event()  # Progress event for tests with incremental updates
        self.on_multi_test = Event()  # Multi-file test result event
        
        # Initialize individual test classes
        self.ent = EntTest(meta)
        self.dieharder = DieHarderTest(meta)
        self.nist = NistTest(meta)
        self.autocorrelation = AutocorrelationTest(meta)
        self.borel = BorelTest(meta)
        
        # Multi-file state
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self._multi_results: List[Dict] = []
        
        # Subscribe to all test events and relay through unified event
        self._setup_event_forwarding()

    def _setup_event_forwarding(self) -> None:
        """Forward all individual test events through the unified on_test event."""
        self.ent.on_test.subscribe(self._forward_event)
        self.dieharder.on_test.subscribe(self._forward_event)
        self.nist.on_test.subscribe(self._forward_event)
        self.autocorrelation.on_test.subscribe(self._forward_event)
        self.borel.on_test.subscribe(self._forward_event)
        
        # Forward progress events
        self.dieharder.on_progress.subscribe(self._forward_progress)
        self.borel.on_progress.subscribe(self._forward_progress)
        self.nist.on_progress.subscribe(self._forward_progress)

    def _forward_event(self, status: OperationStatus) -> None:
        """Forward individual test results through unified event."""
        self.on_test.notify(status=status)
    
    def _forward_progress(self, status: OperationStatus) -> None:
        """Forward progress events through unified progress event."""
        self.on_progress.notify(status=status)
    
    def stop(self) -> None:
        """Stop all running tests gracefully."""
        self._stop_event.set()
        self.ent.stop()
        self.dieharder.stop()
        self.nist.stop()
        self.autocorrelation.stop()
        self.borel.stop()
    
    def force_stop(self) -> None:
        """Force stop all running tests immediately by killing processes."""
        self._stop_event.set()
        self.ent.force_stop()
        self.dieharder.force_stop()
        self.nist.force_stop()
        self.autocorrelation.force_stop()
        self.borel.force_stop()

    # ENT Test Interface
    def configure_ent(self, binary: bool = False, chi_square: bool = False, fold: bool = False, terse: bool = False) -> None:
        """Configure ENT test options."""
        self.ent.set_options(binary=binary, chi_square=chi_square, fold=fold, terse=terse)

    def run_ent_async(self) -> None:
        """Run ENT test asynchronously."""
        self.ent.run_async()

    # DieHarder Test Interface
    def configure_dieharder(self, settings: Dict[str, Any]) -> None:
        """Configure DieHarder test settings."""
        self.dieharder.set_settings(settings)

    def run_dieharder_async(self) -> None:
        """Run DieHarder test asynchronously."""
        self.dieharder.run_async()

    # NIST Test Interface
    def configure_nist(self, enabled_tests: List[bool], sequence_length: int = 1000000, verbose: int = 1, p_value_threshold: float = 0.01, use_whole_data: bool = False) -> None:
        """Configure NIST test parameters."""
        self.nist.set_enabled_tests(enabled_tests)
        self.nist.set_parameters(sequence_length=sequence_length, verbose=verbose, p_value_threshold=p_value_threshold, use_whole_data=use_whole_data)

    def run_nist_async(self) -> None:
        """Run NIST tests asynchronously."""
        self.nist.run_async()

    # Autocorrelation Test Interface
    def configure_autocorrelation(self, nlags: int = 100, generate_plot: bool = True, use_whole_data: bool = False) -> None:
        """Configure autocorrelation test parameters."""
        self.autocorrelation.set_parameters(nlags=nlags, generate_plot=generate_plot, use_whole_data=use_whole_data)

    def run_autocorrelation_async(self) -> None:
        """Run autocorrelation test asynchronously."""
        self.autocorrelation.run_async()

    # Borel Test Interface
    def configure_borel(self, min_pattern_length: int = 1, max_pattern_length: int = 10, auto_mode: bool = False) -> None:
        """Configure Borel test parameters."""
        self.borel.set_parameters(min_pattern_length=min_pattern_length, max_pattern_length=max_pattern_length, auto_mode=auto_mode)

    def run_borel_async(self) -> None:
        """Run Borel test asynchronously."""
        self.borel.run_async()

    # Unified Test Interface
    def run_test_async(self, test_name: str, **kwargs) -> None:
        """Run a specific test by name with optional configuration."""
        test_name = test_name.lower()
        
        if test_name == "ent":
            if kwargs:
                self.configure_ent(**kwargs)
            self.run_ent_async()
        elif test_name == "dieharder":
            if "test_args" in kwargs:
                self.configure_dieharder(kwargs["test_args"])
            self.run_dieharder_async()
        elif test_name == "nist":
            if kwargs:
                self.configure_nist(**kwargs)
            self.run_nist_async()
        elif test_name == "autocorrelation":
            if kwargs:
                self.configure_autocorrelation(**kwargs)
            self.run_autocorrelation_async()
        elif test_name == "borel":
            if kwargs:
                self.configure_borel(**kwargs)
            self.run_borel_async()
        else:
            # Emit error for unknown test
            status = OperationStatus(ok=False, message=f"Unknown test: {test_name}")
            self.on_test.notify(status=status)

    def get_available_tests(self) -> List[str]:
        """Get list of available test names."""
        return ["ent", "dieharder", "nist", "autocorrelation", "borel"]

    def get_test_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available tests."""
        return {
            "ent": {
                "name": "ENT Entropy Analysis",
                "description": "Entropy analysis using external ENT tool",
                "required_file_type": "BINARY",
                "external_tool": True
            },
            "dieharder": {
                "name": "DieHarder Test Suite",
                "description": "Comprehensive randomness test battery",
                "required_file_type": "BINARY",
                "external_tool": True
            },
            "nist": {
                "name": "NIST Statistical Test Suite",
                "description": "NIST SP 800-22 statistical tests",
                "required_file_type": "STRING01",
                "external_tool": False
            },
            "autocorrelation": {
                "name": "Autocorrelation Analysis",
                "description": "Autocorrelation function analysis",
                "required_file_type": "STRING01",
                "external_tool": False
            },
            "borel": {
                "name": "Borel Normality Test",
                "description": "Tests for Borel normality in sequences",
                "required_file_type": "STRING01",
                "external_tool": False
            }
        }

    # ==================== Multi-File Test Support ====================
    
    def run_multi_test_async(self, file_items: List[FileItem], test_name: str, 
                              auto_convert: bool = False, test_config: Dict[str, Any] = None) -> None:
        """Run a test on multiple files."""
        if not file_items:
            self.on_multi_test.notify(status=OperationStatus(ok=False, message="No files to test"))
            return
        if self._thread and self._thread.is_alive():
            self.on_multi_test.notify(status=OperationStatus(ok=False, message="Test already in progress"))
            return
        self._stop_event.clear()
        self._multi_results = []
        self._thread = Thread(
            target=self._multi_test_worker,
            args=(file_items, test_name, auto_convert, test_config or {}),
            daemon=True
        )
        self._thread.start()

    def _multi_test_worker(self, file_items: List[FileItem], test_name: str, 
                           auto_convert: bool, test_config: Dict[str, Any]) -> None:
        """Worker for multi-file testing."""
        results = []
        success_count = 0
        fail_count = 0
        
        test_info = self.get_test_info().get(test_name.lower(), {})
        required_type_str = test_info.get("required_file_type", "BINARY")
        required_type = FileType.BINARY if required_type_str == "BINARY" else FileType.STRING01
        
        for file_item in file_items:
            if self._stop_event.is_set():
                return
            
            try:
                result = self._run_single_file_test(file_item, test_name, required_type, auto_convert, test_config)
                results.append(result)
                if result.get('ok'):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                results.append({
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'test_name': test_name,
                    'ok': False,
                    'message': str(e)
                })
                fail_count += 1
        
        self._multi_results = results
        self.on_multi_test.notify(status=OperationStatus(
            ok=success_count > 0,
            message=f"Tested {success_count} file(s), {fail_count} failed",
            payload={
                'test_name': test_name,
                'results': results,
                'success_count': success_count,
                'fail_count': fail_count
            }
        ))

    def _run_single_file_test(self, file_item: FileItem, test_name: str, 
                               required_type: FileType, auto_convert: bool, 
                               test_config: Dict[str, Any]) -> Dict:
        """Run a test on a single file."""
        p = Path(file_item.file_path)
        if not p.is_file():
            return {'file_id': file_item.id, 'file_name': file_item.file_name, 
                    'test_name': test_name, 'ok': False, 'message': 'File not found'}
        
        file_type = file_item.file_type
        test_file_path = file_item.file_path
        temp_file = None
        
        # Check type compatibility
        if file_type != required_type:
            if not auto_convert:
                return {
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'test_name': test_name,
                    'ok': False,
                    'message': f'File type {file_type.value if file_type else "unknown"} incompatible. Required: {required_type.value}. Enable auto-convert.'
                }
            # Convert data to temp file
            temp_file = self._convert_for_test(p, file_type, required_type, file_item.file_name)
            if temp_file is None:
                return {
                    'file_id': file_item.id,
                    'file_name': file_item.file_name,
                    'test_name': test_name,
                    'ok': False,
                    'message': 'Failed to convert file for testing'
                }
            test_file_path = temp_file
        
        # Temporarily set meta to this file for the test
        original_path = self.meta.file_path
        original_name = self.meta.file_name
        original_type = self.meta.file_type
        original_ext = self.meta.file_ext
        
        try:
            # Set meta to current file
            self.meta.file_path = test_file_path
            self.meta.file_name = file_item.file_name
            self.meta.file_type = required_type
            self.meta.file_ext = file_item.file_ext
            
            # Run the test synchronously and capture result
            test_result = self._run_test_sync(test_name.lower(), test_config)
            
            return {
                'file_id': file_item.id,
                'file_name': file_item.file_name,
                'test_name': test_name,
                'ok': test_result.get('ok', False),
                'result': test_result.get('result'),
                'message': test_result.get('message', '')
            }
        finally:
            # Restore original meta
            self.meta.file_path = original_path
            self.meta.file_name = original_name
            self.meta.file_type = original_type
            self.meta.file_ext = original_ext
            
            # Clean up temp file
            if temp_file:
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except Exception:
                    pass

    def _run_test_sync(self, test_name: str, test_config: Dict[str, Any]) -> Dict:
        """Run a test synchronously and return result."""
        import time
        result_holder = {'result': None, 'received': False}
        
        def capture_result(status: OperationStatus):
            result_holder['result'] = {
                'ok': status.ok,
                'message': status.message,
                'result': status.payload
            }
            result_holder['received'] = True
        
        # Subscribe temporarily
        self.on_test.subscribe(capture_result)
        
        try:
            # Configure and run
            if test_name == "ent":
                self.configure_ent(**test_config) if test_config else None
                self.ent.run_async()
            elif test_name == "dieharder":
                if test_config:
                    self.configure_dieharder(test_config)
                self.dieharder.run_async()
            elif test_name == "nist":
                self.configure_nist(**test_config) if test_config else None
                self.nist.run_async()
            elif test_name == "autocorrelation":
                self.configure_autocorrelation(**test_config) if test_config else None
                self.autocorrelation.run_async()
            elif test_name == "borel":
                self.configure_borel(**test_config) if test_config else None
                self.borel.run_async()
            else:
                return {'ok': False, 'message': f'Unknown test: {test_name}'}
            
            # Wait for result with timeout
            timeout = 600  # 10 minutes max
            start = time.time()
            while not result_holder['received'] and (time.time() - start) < timeout:
                if self._stop_event.is_set():
                    return {'ok': False, 'message': 'Test stopped by user'}
                time.sleep(0.1)
            
            if not result_holder['received']:
                return {'ok': False, 'message': 'Test timed out'}
            
            return result_holder['result']
        finally:
            # Unsubscribe
            self.on_test.unsubscribe(capture_result)

    def _convert_for_test(self, file_path: Path, from_type: Optional[FileType], 
                          to_type: FileType, file_name: str) -> Optional[str]:
        """Convert file data to required format for testing, save to temp file."""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            temp_dir = Path(tempfile.gettempdir())
            
            if to_type == FileType.STRING01:
                # Convert to STRING01
                if from_type == FileType.BINARY:
                    converted = ''.join(format(b, '08b') for b in raw_data)
                elif from_type == FileType.HEX:
                    text = raw_data.decode('utf-8', errors='ignore').strip()
                    bytes_data = bytes.fromhex(text)
                    converted = ''.join(format(b, '08b') for b in bytes_data)
                elif from_type in (FileType.UINT8, FileType.UINT16, FileType.UINT32, FileType.UINT64):
                    converted = ''.join(format(b, '08b') for b in raw_data)
                else:
                    return None
                
                temp_file = temp_dir / f"test_temp_{file_name}.txt"
                with open(temp_file, 'w') as f:
                    f.write(converted)
                return str(temp_file)
            
            elif to_type == FileType.BINARY:
                # Convert to BINARY
                if from_type == FileType.STRING01:
                    text = raw_data.decode('utf-8', errors='ignore')
                    bits = ''.join(c for c in text if c in '01')
                    while len(bits) % 8:
                        bits += '0'
                    converted = bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))
                elif from_type == FileType.HEX:
                    text = raw_data.decode('utf-8', errors='ignore').strip()
                    converted = bytes.fromhex(text)
                else:
                    converted = raw_data
                
                temp_file = temp_dir / f"test_temp_{file_name}.bin"
                with open(temp_file, 'wb') as f:
                    f.write(converted)
                return str(temp_file)
            
            return None
        except Exception:
            return None
