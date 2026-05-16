# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Core Manager - Coordinates all core modules and manages shared state.

Manages:
- InputFileMeta shared state
- Core module initialization and coordination
- Event routing between cores and upper layers
- Operation orchestration
"""

from __future__ import annotations

from typing import Optional, Dict, Any, List
from pathlib import Path

from ..core.observer import Event
from ..core.types import OperationStatus, InputFileMeta
from ..core.qrng import QRNG
from ..core.tests import Tests
from ..core.preprocessing import PreProcessing
from ..core.slicer import Slicer
from ..core.fileconverter import FileConverter
from ..core.inputfile import InputFile


class CoreManager:
    """Central manager for all core modules with shared InputFileMeta state."""

    def __init__(self) -> None:
        # Shared state
        self.input_meta = InputFileMeta()
        
        # Last used directory for file dialogs - defaults to app running directory
        self._last_directory: Optional[str] = str(Path.cwd())
        
        # Core modules
        self.qrng = QRNG()
        self.tests = Tests(self.input_meta)
        self.preprocessing = PreProcessing(self.input_meta)
        self.slicer = Slicer(self.input_meta)
        self.fileconverter = FileConverter(self.input_meta)
        self.inputfile = InputFile(self.input_meta)
        
        # Manager-level events for GUI integration
        self.on_operation_started = Event()
        self.on_operation_progress = Event()
        self.on_operation_completed = Event()
        self.on_operation_failed = Event()
        self.on_file_loaded = Event()
        self.on_file_converted = Event()
        self.on_files_converted = Event()  # For multi-file conversion
        self.on_files_sliced = Event()  # For multi-file slicing
        self.on_files_preprocessed = Event()  # For multi-file preprocessing
        self.on_files_tested = Event()  # For multi-file testing
        self.on_file_validated = Event()  # For file validation result
        self.on_file_metadata_updated = Event()  # For file type changes, etc.
        self.on_file_cleared = Event()  # For file/state reset
        self.on_sample_read = Event()  # For sample data display
        
        # Multi-file events
        self.on_files_added = Event()          # When files are added
        self.on_files_removed = Event()        # When files are removed
        self.on_file_type_changed = Event()    # When a file's type is changed
        self.on_file_item_validated = Event()  # When a single file item is validated
        self.on_all_files_validated = Event()  # When all files validation completes
        self.on_files_cleared = Event()        # When all files are cleared
        
        # Progress events for GUI progress bars
        self.on_validation_progress = Event()  # Validation progress
        self.on_convert_progress = Event()     # Conversion progress
        self.on_preprocess_progress = Event()  # Preprocessing progress
        self.on_slice_progress = Event()       # Slicing progress
        
        # Setup event routing
        self._setup_event_routing()

    def _setup_event_routing(self) -> None:
        """Setup event forwarding from cores to manager-level events."""
        
        # QRNG events
        self.qrng.on_qrng_completed.subscribe(self._handle_qrng_completed)
        self.qrng.on_qrng_failed.subscribe(self._handle_qrng_failed)
        
        # Test events
        self.tests.on_test.subscribe(self._handle_test_completed)
        self.tests.on_progress.subscribe(self._handle_test_progress)
        self.tests.on_multi_test.subscribe(self._handle_multi_test_completed)
        
        # Preprocessing events
        self.preprocessing.on_multi_preprocess.subscribe(self._handle_multi_preprocess_completed)
        
        # Slicer events
        self.slicer.on_multi_slice.subscribe(self._handle_multi_slice_completed)
        
        # File converter events
        self.fileconverter.on_multi_convert.subscribe(self._handle_multi_convert_completed)
        
        # Input file events (single file)
        self.inputfile.on_import_file.subscribe(self._handle_file_loaded)
        self.inputfile.on_set_file_type.subscribe(self._handle_file_type_set)
        self.inputfile.on_check_file.subscribe(self._handle_file_checked)
        self.inputfile.on_read_sample.subscribe(self._handle_sample_read)
        
        # Multi-file events
        self.inputfile.on_files_added.subscribe(self._handle_files_added)
        self.inputfile.on_files_removed.subscribe(self._handle_files_removed)
        self.inputfile.on_file_type_changed.subscribe(self._handle_file_type_changed)
        self.inputfile.on_file_validated.subscribe(self._handle_file_item_validated)
        self.inputfile.on_all_files_validated.subscribe(self._handle_all_files_validated)
        self.inputfile.on_files_cleared.subscribe(self._handle_files_cleared)
        
        # Progress events for GUI progress bars
        self.inputfile.on_validation_progress.subscribe(self._forward_validation_progress)
        self.fileconverter.on_convert_progress.subscribe(self._forward_convert_progress)
        self.preprocessing.on_preprocess_progress.subscribe(self._forward_preprocess_progress)
        self.slicer.on_slice_progress.subscribe(self._forward_slice_progress)

    # ==================== Input File Management ====================
    
    def load_file(self, file_path: str) -> OperationStatus:
        """Load input file and update shared InputFileMeta."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True, 
                message="Loading input file",
                payload={"operation": "load_file", "file_path": file_path}
            ))
            
            return self.inputfile.import_file(file_path)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"File load error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def set_file_type(self, file_type: str) -> OperationStatus:
        """Set file type for loaded file."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Setting file type to {file_type}",
                payload={"operation": "set_file_type", "file_type": file_type}
            ))
            
            return self.inputfile.set_file_type(file_type)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Set file type error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def check_file(self) -> OperationStatus:
        """Validate loaded file asynchronously."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message="Validating file",
                payload={"operation": "check_file"}
            ))
            
            # Use async version to avoid blocking UI
            return self.inputfile.check_file_async()
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"File check error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def read_sample(self, n_bytes: int = 256) -> OperationStatus:
        """Read sample from loaded file."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Reading {n_bytes} byte sample",
                payload={"operation": "read_sample", "n_bytes": n_bytes}
            ))
            
            return self.inputfile.read_sample(n_bytes)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Read sample error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def _handle_file_loaded(self, status: OperationStatus) -> None:
        """Handle successful file import."""
        # The InputFile core updates the shared meta directly
        # We just need to forward the event
        if status.ok:
            self.on_file_loaded.notify(status=status)
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message="File loaded successfully",
                payload={
                    "operation": "load_file",
                    "meta": {
                        "file_path": self.input_meta.file_path,
                        "file_name": self.input_meta.file_name,
                        "file_size": self.input_meta.file_size,
                        "file_type": self.input_meta.file_type.value if self.input_meta.file_type else None
                    }
                }
            ))
        else:
            self._handle_file_failed(status)

    def _handle_file_failed(self, status: OperationStatus) -> None:
        """Handle file loading failure."""
        self.on_operation_failed.notify(status=OperationStatus(
            ok=False,
            message=f"File load failed: {status.message}",
            payload={"operation": "load_file", "error": status.message}
        ))
    
    def _handle_file_type_set(self, status: OperationStatus) -> None:
        """Handle file type setting."""
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message="File type set successfully",
                payload={"operation": "set_file_type", "file_type": status.payload}
            ))
            # Notify all tabs about metadata update
            self.on_file_metadata_updated.notify(status=OperationStatus(
                ok=True,
                message="File metadata updated",
                payload=self.input_meta
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Set file type failed: {status.message}",
                payload={"operation": "set_file_type", "error": status.message}
            ))
    
    def _handle_file_checked(self, status: OperationStatus) -> None:
        """Handle file validation."""
        # Always emit the dedicated validation event so GUI can update
        self.on_file_validated.notify(status=status)
        
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message="File validation completed",
                payload={"operation": "check_file", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"File validation failed: {status.message}",
                payload={"operation": "check_file", "error": status.message}
            ))
    
    def _handle_sample_read(self, status: OperationStatus) -> None:
        """Handle sample reading."""
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message="Sample read completed",
                payload={"operation": "read_sample", "result": status.payload}
            ))
            # Emit dedicated sample read event for report/display
            self.on_sample_read.notify(status=status)
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Sample read failed: {status.message}",
                payload={"operation": "read_sample", "error": status.message}
            ))

    # ==================== Multi-File Management ====================
    
    def add_files(self, file_paths: List[str]) -> OperationStatus:
        """Add multiple files to the collection."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Adding {len(file_paths)} file(s)",
                payload={"operation": "add_files", "count": len(file_paths)}
            ))
            return self.inputfile.add_files(file_paths)
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Add files error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def remove_files(self, file_ids: List[str]) -> OperationStatus:
        """Remove files from the collection by their IDs."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Removing {len(file_ids)} file(s)",
                payload={"operation": "remove_files", "count": len(file_ids)}
            ))
            return self.inputfile.remove_files(file_ids)
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Remove files error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def set_file_type_for_item(self, file_id: str, file_type: str) -> OperationStatus:
        """Set file type for a specific file item."""
        try:
            return self.inputfile.set_file_type_for_item(file_id, file_type)
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Set file type error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def validate_all_files(self) -> OperationStatus:
        """Validate all files that have a type set."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message="Validating all files",
                payload={"operation": "validate_all_files"}
            ))
            return self.inputfile.validate_all_files_async()
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Validate all files error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def read_sample_from_item(self, file_id: str, n_bytes: int = 256) -> OperationStatus:
        """Read sample from a specific file item."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Reading sample from file",
                payload={"operation": "read_sample_item", "file_id": file_id, "n_bytes": n_bytes}
            ))
            return self.inputfile.read_sample_from_item(file_id, n_bytes)
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Read sample error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def clear_all_files(self) -> OperationStatus:
        """Clear all files from the collection."""
        try:
            return self.inputfile.clear_all_files()
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Clear files error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def get_all_files(self) -> List:
        """Get all file items in the collection."""
        return self.inputfile.get_all_files()
    
    def get_file_count(self) -> int:
        """Get the number of files in the collection."""
        return self.inputfile.get_file_count()
    
    def get_file_by_id(self, file_id: str):
        """Get a file item by its ID."""
        return self.input_meta.get_file_by_id(file_id)
    
    def _handle_files_added(self, status: OperationStatus) -> None:
        """Handle files added event."""
        self.on_files_added.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "add_files", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Add files failed: {status.message}",
                payload={"operation": "add_files", "error": status.message}
            ))
    
    def _handle_files_removed(self, status: OperationStatus) -> None:
        """Handle files removed event."""
        self.on_files_removed.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "remove_files", "result": status.payload}
            ))
    
    def _handle_file_type_changed(self, status: OperationStatus) -> None:
        """Handle file type changed event."""
        self.on_file_type_changed.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "set_file_type_item", "result": status.payload}
            ))
    
    def _handle_file_item_validated(self, status: OperationStatus) -> None:
        """Handle single file item validation event."""
        self.on_file_item_validated.notify(status=status)
    
    def _handle_all_files_validated(self, status: OperationStatus) -> None:
        """Handle all files validation completion event."""
        self.on_all_files_validated.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "validate_all_files", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=status.message,
                payload={"operation": "validate_all_files", "error": status.message}
            ))
    
    def _handle_files_cleared(self, status: OperationStatus) -> None:
        """Handle files cleared event."""
        self.on_files_cleared.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "clear_files", "result": status.payload}
            ))

    # ==================== File Conversion ====================
    
    def convert_files(self, file_items: List, target_format: str, tag: str = "") -> OperationStatus:
        """Convert multiple files to target format."""
        if not file_items:
            status = OperationStatus(ok=False, message="No files to convert")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Converting {len(file_items)} file(s) to {target_format}",
                payload={"operation": "convert_files", "count": len(file_items), "target_format": target_format}
            ))
            
            self.fileconverter.convert_files_async(file_items, target_format, tag)
            return OperationStatus(ok=True, message="Multi-file conversion started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Multi-file conversion error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def _handle_multi_convert_completed(self, status: OperationStatus) -> None:
        """Handle multi-file conversion completion."""
        self.on_files_converted.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "convert_files", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Multi-file conversion failed: {status.message}",
                payload={"operation": "convert_files", "error": status.message}
            ))

    # ==================== QRNG Operations ====================
    
    def start_eyl_offline(self, base_filename: str, num_files: int, file_size_bits: int, **kwargs) -> OperationStatus:
        """Start EYL offline generation."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Starting EYL offline generation: {num_files} files",
                payload={"operation": "eyl_offline", "base_filename": base_filename, "num_files": num_files}
            ))
            
            return self.qrng.start_eyl_offline(base_filename, num_files, file_size_bits, **kwargs)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"EYL offline start error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def start_eyl_display(self, **kwargs) -> OperationStatus:
        """Start EYL display mode - continuous data stream for GUI display."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message="Starting EYL display mode",
                payload={"operation": "eyl_display"}
            ))
            
            return self.qrng.start_eyl_display(**kwargs)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"EYL display start error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def start_eyl_stream(self, host: str = "127.0.0.1", port: int = 4000, **kwargs) -> OperationStatus:
        """Start EYL stream mode."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Starting EYL stream mode on {host}:{port}",
                payload={"operation": "eyl_stream", "host": host, "port": port}
            ))
            
            return self.qrng.start_eyl_stream(host, port, **kwargs)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"EYL stream start error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def stop_eyl_generation(self) -> OperationStatus:
        """Stop EYL generation."""
        try:
            result = self.qrng.stop_eyl_generation()
            if result.ok:
                self.on_operation_completed.notify(status=OperationStatus(
                    ok=True,
                    message="EYL generation stopped",
                    payload={"operation": "eyl_stop"}
                ))
            return result
        except Exception as e:
            status = OperationStatus(ok=False, message=f"EYL stop error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def is_eyl_running(self) -> bool:
        """Check if EYL is running."""
        return self.qrng.is_eyl_running()

    def check_eyl_dll(self) -> OperationStatus:
        """Check if EYL DLL is available and can be loaded."""
        return self.qrng.eyl.check_dll()

    def test_eyl_connection(self) -> OperationStatus:
        """Test connection to EYL device."""
        return self.qrng.eyl.test_connection()

    def disconnect_eyl(self) -> None:
        """Disconnect from EYL device."""
        self.qrng.eyl.disconnect()

    def stop_api_fetch(self) -> OperationStatus:
        """Stop current API fetch operation."""
        return self.qrng.stop_api_fetch()

    def generate_prng(self, generator_id: int, seed: int, save_path: str, num_files: int, 
                      size_per_file: int, include_header: bool = True,
                      include_gen_id: bool = True, include_seed: bool = True,
                      base_name: str = "prng", output_format: str = "uint32") -> OperationStatus:
        """Generate PRNG data and save directly to files."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Starting PRNG generation: generator {generator_id}, {num_files} files",
                payload={"operation": "prng_generate", "generator_id": generator_id, "num_files": num_files}
            ))
            
            return self.qrng.generate_prng(
                generator_id, seed, save_path, num_files, size_per_file, 
                include_header, include_gen_id, include_seed, base_name, output_format
            )
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"PRNG generation error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def stop_prng_generation(self) -> OperationStatus:
        """Stop PRNG generation."""
        try:
            result = self.qrng.stop_prng_generation()
            if result.ok:
                self.on_operation_completed.notify(status=OperationStatus(
                    ok=True,
                    message="PRNG generation stopped",
                    payload={"operation": "prng_stop"}
                ))
            return result
        except Exception as e:
            status = OperationStatus(ok=False, message=f"PRNG stop error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def get_available_generators(self) -> List[Dict[str, Any]]:
        """Get available PRNG generators."""
        return self.qrng.get_available_generators()

    def is_prng_running(self) -> bool:
        """Check if PRNG is running."""
        return self.qrng.is_prng_running()

    def fetch_api_data(self, provider: str, length: int, **kwargs) -> OperationStatus:
        """Fetch data from API provider."""
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Fetching data from {provider}: {length} values",
                payload={"operation": "api_fetch", "provider": provider, "length": length}
            ))
            
            return self.qrng.fetch_api_data(provider, length, **kwargs)
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"API fetch error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def get_available_api_providers(self) -> List[Dict[str, Any]]:
        """Get available API providers."""
        return self.qrng.get_available_api_providers()

    def is_api_running(self) -> bool:
        """Check if API is running."""
        return self.qrng.is_api_running()

    def configure_eyl(self, **kwargs) -> OperationStatus:
        """Configure EYL parameters."""
        return self.qrng.configure_eyl(**kwargs)

    def configure_prng(self, **kwargs) -> OperationStatus:
        """Configure PRNG parameters."""
        return self.qrng.configure_prng(**kwargs)

    def configure_api(self, **kwargs) -> OperationStatus:
        """Configure API parameters."""
        return self.qrng.configure_api(**kwargs)

    def add_api_provider(self, name: str, provider) -> OperationStatus:
        """Add custom API provider."""
        return self.qrng.add_api_provider(name, provider)

    def remove_api_provider(self, name: str) -> OperationStatus:
        """Remove API provider."""
        return self.qrng.remove_api_provider(name)

    def _handle_qrng_completed(self, status: OperationStatus) -> None:
        """Handle QRNG operation completion."""
        self.on_operation_completed.notify(status=OperationStatus(
            ok=True,
            message="QRNG operation completed",
            payload={
                "operation": "qrng",
                "result": status.payload
            }
        ))

    def _handle_qrng_failed(self, status: OperationStatus) -> None:
        """Handle QRNG operation failure."""
        self.on_operation_failed.notify(status=OperationStatus(
            ok=False,
            message=f"QRNG operation failed: {status.message}",
            payload={"operation": "qrng", "error": status.message}
        ))

    # ==================== Test Operations ====================
    
    def run_test(self, test_name: str, **kwargs) -> OperationStatus:
        """Run a specific test on loaded file."""
        if not self.input_meta.file_path:
            status = OperationStatus(ok=False, message="No file loaded for testing")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Running {test_name} test",
                payload={"operation": "test", "test_name": test_name}
            ))
            
            self.tests.run_test_async(test_name, **kwargs)
            return OperationStatus(ok=True, message=f"{test_name} test started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Test error: {e}")
            self.on_operation_failed.notify(status=status)
            return status

    def configure_ent_test(self, binary: bool = False, chi_square: bool = False, fold: bool = False, terse: bool = False) -> OperationStatus:
        """Configure ENT test options."""
        try:
            self.tests.configure_ent(binary, chi_square, fold, terse)
            return OperationStatus(ok=True, message="ENT test configured")
        except Exception as e:
            return OperationStatus(ok=False, message=f"ENT configuration error: {e}")

    def configure_dieharder_test(self, settings: Dict[str, Any]) -> OperationStatus:
        """Configure DieHarder test settings."""
        try:
            self.tests.configure_dieharder(settings)
            return OperationStatus(ok=True, message="DieHarder test configured")
        except Exception as e:
            return OperationStatus(ok=False, message=f"DieHarder configuration error: {e}")

    def configure_nist_test(self, enabled_tests: List[bool], sequence_length: int = 1000000, verbose: bool = False, p_value_threshold: float = 0.01) -> OperationStatus:
        """Configure NIST test suite."""
        try:
            self.tests.configure_nist(enabled_tests, sequence_length, verbose, p_value_threshold)
            return OperationStatus(ok=True, message="NIST test configured")
        except Exception as e:
            return OperationStatus(ok=False, message=f"NIST configuration error: {e}")

    def configure_borel_test(self, min_pattern_length: int = 2, max_pattern_length: int = 10, auto_mode: bool = False) -> OperationStatus:
        """Configure Borel test parameters."""
        try:
            self.tests.configure_borel(min_pattern_length, max_pattern_length, auto_mode)
            return OperationStatus(ok=True, message="Borel test configured")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Borel configuration error: {e}")

    def configure_autocorrelation_test(self, max_lag: int = 100, use_whole_data: bool = False) -> OperationStatus:
        """Configure autocorrelation test parameters."""
        try:
            self.tests.configure_autocorrelation(nlags=max_lag, use_whole_data=use_whole_data)
            return OperationStatus(ok=True, message="Autocorrelation test configured")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Autocorrelation configuration error: {e}")

    def get_available_tests(self) -> List[str]:
        """Get list of available test names."""
        return self.tests.get_available_tests()

    def _handle_test_completed(self, status: OperationStatus) -> None:
        """Handle test completion (success or failure)."""
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message="Test completed",
                payload={
                    "operation": "test",
                    "result": status.payload
                }
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Test failed: {status.message}",
                payload={"operation": "test", "error": status.message}
            ))
    
    def _handle_test_progress(self, status: OperationStatus) -> None:
        """Handle test progress updates (e.g., dieharder individual test completion)."""
        self.on_operation_progress.notify(status=status)

    # ==================== Multi-File Testing ====================
    
    def run_test_on_files(self, file_items: List, test_name: str, auto_convert: bool = False,
                          test_config: dict = None) -> OperationStatus:
        """Run a test on multiple files."""
        if not file_items:
            status = OperationStatus(ok=False, message="No files to test")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Running {test_name} test on {len(file_items)} file(s)",
                payload={"operation": "test_files", "count": len(file_items), "test_name": test_name}
            ))
            
            self.tests.run_multi_test_async(file_items, test_name, auto_convert, test_config)
            return OperationStatus(ok=True, message="Multi-file test started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Multi-file test error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def _handle_multi_test_completed(self, status: OperationStatus) -> None:
        """Handle multi-file test completion."""
        self.on_files_tested.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "test_files", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Multi-file test failed: {status.message}",
                payload={"operation": "test_files", "error": status.message}
            ))

    # ==================== Multi-File Preprocessing ====================
    
    def preprocess_files(self, file_items: List, algorithm: str, auto_convert: bool = False,
                         convert_back: bool = False, tz_settings: dict = None, output_tag: str = "") -> OperationStatus:
        """Run preprocessing algorithm on multiple files."""
        if not file_items:
            status = OperationStatus(ok=False, message="No files to preprocess")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Preprocessing {len(file_items)} file(s) with {algorithm}",
                payload={"operation": "preprocess_files", "count": len(file_items), "algorithm": algorithm}
            ))
            
            self.preprocessing.run_multi_algorithm_async(file_items, algorithm, auto_convert, convert_back, tz_settings, output_tag)
            return OperationStatus(ok=True, message="Multi-file preprocessing started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Multi-file preprocessing error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def _handle_multi_preprocess_completed(self, status: OperationStatus) -> None:
        """Handle multi-file preprocessing completion."""
        self.on_files_preprocessed.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "preprocess_files", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Multi-file preprocessing failed: {status.message}",
                payload={"operation": "preprocess_files", "error": status.message}
            ))

    # ==================== Multi-File Slicing ====================
    
    def slice_files_equal_parts(self, file_items: List, parts: int) -> OperationStatus:
        """Slice multiple files into equal parts."""
        if not file_items:
            status = OperationStatus(ok=False, message="No files to slice")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Slicing {len(file_items)} file(s) into {parts} parts",
                payload={"operation": "slice_files", "count": len(file_items), "parts": parts}
            ))
            
            self.slicer.slice_files_equal_parts_async(file_items, parts)
            return OperationStatus(ok=True, message="Multi-file slicing started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Multi-file slice error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def slice_files_single(self, file_items: List, start: int, length: int) -> OperationStatus:
        """Slice a portion from multiple files."""
        if not file_items:
            status = OperationStatus(ok=False, message="No files to slice")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Slicing {len(file_items)} file(s): start={start}, length={length}",
                payload={"operation": "slice_files", "count": len(file_items), "start": start, "length": length}
            ))
            
            self.slicer.slice_files_single_async(file_items, start, length)
            return OperationStatus(ok=True, message="Multi-file slicing started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Multi-file slice error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def slice_files_random(self, file_items: List, count: int, size: int, seed: int = None) -> OperationStatus:
        """Create random samples from multiple files."""
        if not file_items:
            status = OperationStatus(ok=False, message="No files to slice")
            self.on_operation_failed.notify(status=status)
            return status
        
        try:
            self.on_operation_started.notify(status=OperationStatus(
                ok=True,
                message=f"Creating {count} random samples from {len(file_items)} file(s)",
                payload={"operation": "slice_files", "count": len(file_items), "samples": count, "size": size}
            ))
            
            self.slicer.slice_files_random_async(file_items, count, size, seed)
            return OperationStatus(ok=True, message="Multi-file random sampling started")
            
        except Exception as e:
            status = OperationStatus(ok=False, message=f"Multi-file slice error: {e}")
            self.on_operation_failed.notify(status=status)
            return status
    
    def _handle_multi_slice_completed(self, status: OperationStatus) -> None:
        """Handle multi-file slice completion."""
        self.on_files_sliced.notify(status=status)
        if status.ok:
            self.on_operation_completed.notify(status=OperationStatus(
                ok=True,
                message=status.message,
                payload={"operation": "slice_files", "result": status.payload}
            ))
        else:
            self.on_operation_failed.notify(status=OperationStatus(
                ok=False,
                message=f"Multi-file slicing failed: {status.message}",
                payload={"operation": "slice_files", "error": status.message}
            ))

    # ==================== Status and Control ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all cores and shared state."""
        return {
            "input_meta": {
                "file_path": self.input_meta.file_path,
                "file_name": self.input_meta.file_name,
                "file_size": self.input_meta.file_size,
                "file_type": self.input_meta.file_type.value if self.input_meta.file_type else None,
                "file_ext": self.input_meta.file_ext.value if self.input_meta.file_ext else None
            },
            "qrng_status": self.qrng.get_status(),
            "operations_running": {
                "eyl": self.qrng.is_eyl_running(),
                "prng": self.qrng.is_prng_running(),
                "api": self.qrng.is_api_running(),
                "qrng_any": self.qrng.is_eyl_running() or self.qrng.is_prng_running() or self.qrng.is_api_running(),
                "preprocessing": self.preprocessing._thread and self.preprocessing._thread.is_alive(),
                "slicer": self.slicer._thread and self.slicer._thread.is_alive(),
                "converter": self.fileconverter._thread and self.fileconverter._thread.is_alive()
            },
            "available_resources": {
                "prng_generators": len(self.qrng.get_available_generators()),
                "api_providers": len(self.qrng.get_available_api_providers()),
                "tests": self.tests.get_available_tests()
            }
        }

    def has_running_operations(self) -> bool:
        """Check if any operations are currently running."""
        try:
            # Check preprocessing thread
            if hasattr(self.preprocessing, '_thread') and self.preprocessing._thread:
                if self.preprocessing._thread.is_alive():
                    return True
            
            # Check tests threads
            if hasattr(self.tests, '_thread') and self.tests._thread:
                if self.tests._thread.is_alive():
                    return True
            
            # Check slicer thread
            if hasattr(self.slicer, '_thread') and self.slicer._thread:
                if self.slicer._thread.is_alive():
                    return True
            
            # Check converter thread
            if hasattr(self.fileconverter, '_thread') and self.fileconverter._thread:
                if self.fileconverter._thread.is_alive():
                    return True
            
            # Check QRNG threads
            if hasattr(self.qrng, '_threads'):
                for thread in self.qrng._threads.values():
                    if thread and thread.is_alive():
                        return True
            
            return False
        except Exception:
            return False

    def stop_all_operations(self) -> Dict[str, OperationStatus]:
        """Stop all running operations."""
        results = {}
        
        # Stop QRNG operations
        results.update(self.qrng.stop_all())
        
        # Stop input file operations
        if hasattr(self.inputfile, 'stop'):
            self.inputfile.stop()
            results['inputfile'] = OperationStatus(ok=True, message="InputFile stopped")
        
        # Stop file converter operations
        if hasattr(self.fileconverter, 'stop'):
            self.fileconverter.stop()
            results['fileconverter'] = OperationStatus(ok=True, message="FileConverter stopped")
        
        # Stop preprocessing operations
        if hasattr(self.preprocessing, 'stop'):
            self.preprocessing.stop()
            results['preprocessing'] = OperationStatus(ok=True, message="Preprocessing stopped")
        
        # Stop slicer operations
        if hasattr(self.slicer, 'stop'):
            self.slicer.stop()
            results['slicer'] = OperationStatus(ok=True, message="Slicer stopped")
        
        # Stop test operations
        if hasattr(self.tests, 'stop'):
            self.tests.stop()
            results['tests'] = OperationStatus(ok=True, message="Tests stopped")
        
        return results

    def reset_state(self) -> OperationStatus:
        """Reset shared state and stop all operations.
        
        Resets input_meta in place to preserve core module references and event subscriptions.
        """
        try:
            # Stop all operations
            self.stop_all_operations()
            
            # Reset shared meta in place (don't create new instance)
            # This preserves all core module references and event subscriptions
            self.input_meta.file_path = None
            self.input_meta.file_dir = None
            self.input_meta.file_name = None
            self.input_meta.file_ext = None
            self.input_meta.file_size = None
            self.input_meta.file_type = None
            
            # Clear multi-file collection
            self.input_meta.clear_file_items()
            
            # Notify all tabs that file was cleared
            self.on_file_cleared.notify(status=OperationStatus(
                ok=True,
                message="File cleared",
                payload=None
            ))
            
            # Notify files cleared for multi-file UI
            self.on_files_cleared.notify(status=OperationStatus(
                ok=True,
                message="All files cleared",
                payload={'cleared_count': 0}
            ))
            
            return OperationStatus(ok=True, message="Core manager state reset")
            
        except Exception as e:
            return OperationStatus(ok=False, message=f"Reset failed: {e}")

    # ==================== Directory Management ====================
    
    def get_last_directory(self) -> str:
        """Get last used directory for file dialogs."""
        return self._last_directory or str(Path.cwd())
    
    def set_last_directory(self, directory: str) -> None:
        """Set last used directory from a file path or directory path."""
        try:
            path = Path(directory)
            if path.is_file():
                self._last_directory = str(path.parent)
            elif path.is_dir():
                self._last_directory = str(path)
            else:
                # If path doesn't exist, try to get parent
                self._last_directory = str(path.parent)
        except Exception:
            pass  # Keep existing value on error

    # ==================== Progress Event Forwarding ====================
    
    def _forward_validation_progress(self, status: OperationStatus) -> None:
        """Forward validation progress events to GUI."""
        self.on_validation_progress.notify(status=status)
    
    def _forward_convert_progress(self, status: OperationStatus) -> None:
        """Forward conversion progress events to GUI."""
        self.on_convert_progress.notify(status=status)
    
    def _forward_preprocess_progress(self, status: OperationStatus) -> None:
        """Forward preprocessing progress events to GUI."""
        self.on_preprocess_progress.notify(status=status)
    
    def _forward_slice_progress(self, status: OperationStatus) -> None:
        """Forward slicing progress events to GUI."""
        self.on_slice_progress.notify(status=status)
