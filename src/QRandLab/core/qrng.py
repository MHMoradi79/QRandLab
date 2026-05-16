# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Unified QRNG interface managing all quantum random number generation sources."""

from __future__ import annotations

from typing import Optional, Dict, Any, List

from .observer import Event
from .types import OperationStatus
from .qrng_core import EYLInterface, PRNGInterface, APIInterface


class QRNG:
    """Unified interface for all QRNG sources (EYL hardware, PRNG, APIs)."""

    def __init__(self) -> None:
        # Initialize core interfaces
        self.eyl = EYLInterface()
        self.prng = PRNGInterface()
        self.api = APIInterface()
        
        # Unified events for manager integration  
        self.on_qrng_completed = Event()  # Data ready from any source
        self.on_qrng_failed = Event()     # Error from any source
        self.on_prng_progress = Event()   # PRNG progress updates
        
        # Setup event forwarding from core interfaces
        self._setup_event_forwarding()

    def _setup_event_forwarding(self) -> None:
        """Forward events from core interfaces through unified events."""
        # EYL events  
        self.eyl.on_eyl_data.subscribe(self._forward_completed_event)  # Data ready = completed
        self.eyl.on_eyl_error.subscribe(self._forward_failed_event)
        
        # PRNG events  
        self.prng.on_prng_data.subscribe(self._forward_completed_event)  # Data ready = completed
        self.prng.on_prng_error.subscribe(self._forward_failed_event)
        self.prng.on_prng_progress.subscribe(self._forward_prng_progress)
        
        # API events  
        self.api.on_api_data.subscribe(self._forward_completed_event)  # Data ready = completed
        self.api.on_api_error.subscribe(self._forward_failed_event)

    def _forward_completed_event(self, status: OperationStatus) -> None:
        """Forward completed events through unified interface."""
        self.on_qrng_completed.notify(status=status)

    def _forward_failed_event(self, status: OperationStatus) -> None:
        """Forward failed events through unified interface."""
        self.on_qrng_failed.notify(status=status)

    def _forward_prng_progress(self, status: OperationStatus) -> None:
        """Forward PRNG progress events."""
        self.on_prng_progress.notify(status=status)

    # EYL Hardware Interface
    def start_eyl_offline(self, base_filename: str, num_files: int, 
                         file_size_bits: int, **kwargs) -> OperationStatus:
        """Start EYL offline generation - data sent via events for upper layer to save.
        
        Args:
            base_filename: Base name for files (e.g., "random_data")
            num_files: Number of files to generate
            file_size_bits: Size of each file in bits
            **kwargs: Additional parameters (buffer_size, etc.)
            
        Returns:
            OperationStatus indicating success/failure
        """
        return self.eyl.start_generation(
            mode="offline",
            base_filename=base_filename,
            num_files=num_files,
            file_size_bits=file_size_bits,
            **kwargs
        )

    def start_eyl_display(self, **kwargs) -> OperationStatus:
        """Start EYL display mode - continuous data stream for GUI display.
        
        Args:
            **kwargs: Optional parameters (buffer_size, etc.)
            
        Returns:
            OperationStatus indicating success/failure
        """
        return self.eyl.start_generation(mode="display", **kwargs)

    def start_eyl_stream(self, host: str = "127.0.0.1", port: int = 4000, 
                        **kwargs) -> OperationStatus:
        """Start EYL stream mode - TCP streaming to network clients.
        
        Args:
            host: Host address to bind to
            port: Port number to bind to
            **kwargs: Optional parameters (buffer_size, etc.)
            
        Returns:
            OperationStatus indicating success/failure
        """
        return self.eyl.start_generation(
            mode="stream",
            host=host,
            port=port,
            **kwargs
        )

    def stop_eyl_generation(self) -> OperationStatus:
        """Stop EYL hardware generation."""
        return self.eyl.stop_generation()

    def is_eyl_running(self) -> bool:
        """Check if EYL generation is running."""
        return self.eyl.is_running()

    # PRNG Interface
    def generate_prng(self, generator_id: int, seed: int, save_path: str, 
                     num_files: int, size_per_file: int, include_header: bool = True,
                     include_gen_id: bool = True, include_seed: bool = True,
                     base_name: str = "prng", output_format: str = "uint32") -> OperationStatus:
        """Generate random numbers using DieHarder PRNG and save directly to files.
        
        Args:
            generator_id: DieHarder generator ID
            seed: Random seed
            save_path: Folder path to save generated files
            num_files: Number of files to generate
            size_per_file: Size parameter for each file
            include_header: If True, include DieHarder header; if False, only raw uint32 values
            include_gen_id: If True, include generator ID in filename
            include_seed: If True, include seed in filename
            base_name: Base name for generated files (default: "prng")
            output_format: Output format (uint32, binary, string01, hex, uint8, uint16, uint64)
            
        Returns:
            OperationStatus indicating success/failure
        """
        return self.prng.generate_dieharder(
            generator_id=generator_id,
            seed=seed,
            save_path=save_path,
            num_files=num_files,
            size_per_file=size_per_file,
            include_header=include_header,
            include_gen_id=include_gen_id,
            include_seed=include_seed,
            base_name=base_name,
            output_format=output_format
        )

    def stop_prng_generation(self) -> OperationStatus:
        """Stop PRNG generation."""
        return self.prng.stop_generation()

    def get_available_generators(self) -> List[Dict[str, Any]]:
        """Get list of available PRNG generators."""
        return self.prng.get_available_generators()

    def is_prng_running(self) -> bool:
        """Check if PRNG generation is running."""
        return self.prng.is_running()

    # API Interface
    def fetch_api_data(self, provider: str, length: int, **kwargs) -> OperationStatus:
        """Fetch random data from API provider.
        
        Args:
            provider: Provider name ("anu", "random_org", "hotbits")
            length: Number of random values to fetch
            **kwargs: Provider-specific parameters (e.g., api_key, data_type)
            
        Returns:
            OperationStatus with fetched data
        """
        return self.api.fetch_data(provider=provider, length=length, **kwargs)

    def get_available_api_providers(self) -> List[Dict[str, Any]]:
        """Get list of available API providers."""
        return self.api.get_available_providers()

    def is_api_running(self) -> bool:
        """Check if API fetch is running."""
        return self.api.is_running()

    def stop_api_fetch(self) -> OperationStatus:
        """Stop current API fetch operation."""
        return self.api.stop_fetch()

    # Unified Status Methods
    def get_status(self) -> Dict[str, Any]:
        """Get overall QRNG system status.
        
        Returns:
            Dictionary with status of all components
        """
        return {
            "eyl_running": self.is_eyl_running(),
            "prng_running": self.is_prng_running(),
            "api_running": self.is_api_running(),
            "any_running": self.is_eyl_running() or self.is_prng_running() or self.is_api_running()
        }

    def stop_all(self) -> Dict[str, OperationStatus]:
        """Stop all running QRNG operations.
        
        Returns:
            Dictionary with stop results for each component
        """
        results = {}
        
        if self.is_eyl_running():
            results["eyl"] = self.stop_eyl_generation()
        else:
            results["eyl"] = OperationStatus(ok=True, message="EYL not running")
            
        if self.is_prng_running():
            results["prng"] = self.stop_prng_generation()
        else:
            results["prng"] = OperationStatus(ok=True, message="PRNG not running")
            
        # API doesn't have explicit stop method (short-lived operations)
        results["api"] = OperationStatus(
            ok=True,
            message="API not running" if not self.is_api_running() else "API running (will complete soon)"
        )
        
        return results

    # Helper Methods for Configuration
    def configure_eyl(self, **kwargs) -> OperationStatus:
        """Configure EYL parameters (placeholder for future settings)."""
        return OperationStatus(ok=True, message="EYL configuration updated")

    def configure_prng(self, **kwargs) -> OperationStatus:
        """Configure PRNG parameters (placeholder for future settings)."""
        return OperationStatus(ok=True, message="PRNG configuration updated")

    def configure_api(self, **kwargs) -> OperationStatus:
        """Configure API parameters (placeholder for future settings)."""
        return OperationStatus(ok=True, message="API configuration updated")

    # Extensibility Methods
    def add_api_provider(self, name: str, provider) -> OperationStatus:
        """Add a custom API provider.
        
        Args:
            name: Provider name/key
            provider: Provider instance implementing BaseAPIProvider
            
        Returns:
            OperationStatus indicating success/failure
        """
        return self.api.add_provider(name, provider)
        
    def remove_api_provider(self, name: str) -> OperationStatus:
        """Remove an API provider.
        
        Args:
            name: Provider name/key to remove
            
        Returns:
            OperationStatus indicating success/failure
        """
        return self.api.remove_provider(name)