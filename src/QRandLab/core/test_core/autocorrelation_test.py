# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Autocorrelation Test core.

Computes autocorrelation function for randomness analysis.
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread, Event as ThreadEvent
from typing import Optional, List, Dict, Any
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from io import BytesIO
import base64

from ..observer import Event
from ..types import InputFileMeta, OperationStatus, FileType


class AutocorrelationTest:
    """Autocorrelation analysis for randomness testing."""

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_test = Event()
        
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self.nlags = 100
        self.generate_plot = True
        self.use_whole_data = False
    
    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def force_stop(self) -> None:
        """Force stop - alias for stop() since Autocorrelation has no subprocess."""
        self.stop()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    def set_parameters(self, nlags: int = 100, generate_plot: bool = True, use_whole_data: bool = False) -> None:
        """Set autocorrelation parameters."""
        self.nlags = nlags
        self.generate_plot = generate_plot
        self.use_whole_data = use_whole_data

    def run_async(self) -> None:
        """Run autocorrelation test asynchronously. Emits on_test with OperationStatus."""
        if self._thread and self._thread.is_alive():
            self.on_test.notify(status=OperationStatus(ok=False, message="Autocorrelation test already in progress"))
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
        if self.meta.file_type != FileType.STRING01:
            self.on_test.notify(status=OperationStatus(ok=False, message="Autocorrelation requires STRING01 file type"))
            return

        # Read data
        try:
            with open(self.meta.file_path, "r") as f:
                binary_data = f.read().strip()
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"Failed to read file: {e}"))
            return

        try:
            # Convert to numeric array
            data = np.array([int(bit) for bit in binary_data])
            n = len(data)
            
            # If use_whole_data, use all data for nlags
            if self.use_whole_data:
                nlags = n - 1  # Use all lags up to data length
            else:
                nlags = self.nlags
                if n < nlags:
                    self.on_test.notify(status=OperationStatus(ok=False, message="Data length insufficient for requested lags"))
                    return

            # Compute autocorrelation
            autocorr = self._compute_autocorrelation(data, nlags, self.use_whole_data)
            
            # Generate plot if requested
            plot_base64 = None
            if self.generate_plot:
                plot_base64 = self._generate_plot(autocorr)

            # Analyze results
            analysis = self._analyze_autocorrelation(autocorr)

            payload = {
                "test_type": "Autocorrelation",
                "autocorrelation": autocorr.tolist(),
                "nlags": self.nlags,
                "data_length": n,
                "analysis": analysis,
                "plot_base64": plot_base64
            }
            
            self.on_test.notify(status=OperationStatus(ok=True, message="Autocorrelation test completed", payload=payload))
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"Autocorrelation computation error: {e}"))

    def _compute_autocorrelation(self, data: np.ndarray, nlags: int, use_whole_data: bool = False) -> np.ndarray:
        """Compute circular/periodic autocorrelation function using FFT.
        
        Uses circular correlation to avoid edge effects where data is lost at 
        higher lags. This treats the data as periodic, so lag k correlates
        the full dataset with a circular shift of k positions.
        """
        n = len(data)
        
        # Only downsample if not using whole data
        if not use_whole_data:
            max_samples = 100000
            if n > max_samples:
                # Downsample for performance
                step = n // max_samples
                data = data[::step]
                n = len(data)
        
        # Center the data
        data_centered = data - np.mean(data)
        
        # Compute circular autocorrelation via FFT
        # FFT of data, multiply by conjugate, inverse FFT gives circular autocorrelation
        fft_data = np.fft.fft(data_centered)
        autocorr = np.fft.ifft(fft_data * np.conj(fft_data)).real
        
        # Normalize by the zero-lag value (variance * n)
        if autocorr[0] != 0:
            autocorr = autocorr / autocorr[0]
        
        # Return requested number of lags (limit to data length)
        # For circular autocorrelation, all lags use full data
        return autocorr[:min(nlags + 1, n)]

    def _analyze_autocorrelation(self, autocorr: np.ndarray) -> Dict[str, Any]:
        """Analyze autocorrelation results."""
        # Confidence bounds (95% confidence interval)
        n_effective = len(autocorr)
        confidence_bound = 1.96 / np.sqrt(n_effective)
        
        # Count significant correlations (excluding lag 0)
        significant_lags = np.where(np.abs(autocorr[1:]) > confidence_bound)[0] + 1
        
        # Maximum absolute correlation (excluding lag 0)
        max_corr = np.max(np.abs(autocorr[1:]))
        max_corr_lag = np.argmax(np.abs(autocorr[1:])) + 1
        
        # Ljung-Box test statistic (simplified)
        ljung_box = len(autocorr) * (len(autocorr) + 2) * np.sum(autocorr[1:]**2 / np.arange(len(autocorr)-1, 0, -1))
        
        return {
            "confidence_bound": confidence_bound,
            "significant_lags": significant_lags.tolist(),
            "num_significant": len(significant_lags),
            "max_correlation": float(max_corr),
            "max_correlation_lag": int(max_corr_lag),
            "ljung_box_statistic": float(ljung_box),
            "assessment": "PASS" if len(significant_lags) < len(autocorr) * 0.05 else "FAIL"
        }

    def _generate_plot(self, autocorr: np.ndarray) -> Optional[str]:
        """Generate autocorrelation plot and return as base64 string."""
        try:
            matplotlib.use('Agg')  # Use non-interactive backend for thread safety
            plt.figure(figsize=(10, 6))
            
            # Ignore first value (lag 0, which is always 1)
            autocorr_plot = autocorr[1:]
            lags = np.arange(1, len(autocorr))
            
            # Plot autocorrelation
            plt.plot(lags, autocorr_plot, 'b-', linewidth=2, label='Autocorrelation')
            plt.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            
            # Add confidence bounds
            confidence_bound = 1.96 / np.sqrt(len(autocorr))
            plt.axhline(y=confidence_bound, color='r', linestyle='--', alpha=0.7, label='95% Confidence')
            plt.axhline(y=-confidence_bound, color='r', linestyle='--', alpha=0.7)
            
            plt.xlabel('Lag')
            plt.ylabel('Autocorrelation')
            plt.title('Autocorrelation Function')
            plt.grid(True, alpha=0.3)
            plt.legend(loc='upper right')
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
            buffer.seek(0)
            plot_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return plot_base64
        except Exception:
            return None
