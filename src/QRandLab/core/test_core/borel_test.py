# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Borel Normality Test core.

Tests for Borel normality in binary sequences.
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread, Event as ThreadEvent
from typing import Optional, Dict, Any
import numpy as np
from math import log, sqrt

from ..observer import Event
from ..types import InputFileMeta, OperationStatus, FileType


class BorelTest:
    """Borel normality test for randomness analysis."""

    def __init__(self, meta: InputFileMeta, min_pattern_length: int = 2, max_pattern_length: int = 10, auto_max: bool = False) -> None:
        """Initialize Borel test with pattern length range.
        
        Args:
            min_pattern_length: Minimum pattern length to test
            max_pattern_length: Maximum pattern length to test (or -1 for auto)
            auto_max: If True, calculate max length as int(log2(log2(L)))
        """
        self.meta = meta
        self.on_test = Event()
        self.on_progress = Event()  # Progress event for pattern updates
        
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self.min_pattern_length = max(1, min_pattern_length)
        self.max_pattern_length = max(self.min_pattern_length, max_pattern_length)
        self.auto_max = auto_max
        self.options = {
            'min_pattern_length': min_pattern_length,
            'max_pattern_length': max_pattern_length,
            'auto_max': auto_max
        }
    
    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def force_stop(self) -> None:
        """Force stop - alias for stop() since Borel has no subprocess."""
        self.stop()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    def set_parameters(self, min_pattern_length: int = 1, max_pattern_length: int = 10, auto_mode: bool = False) -> None:
        """Set Borel test parameters."""
        self.min_pattern_length = max(1, min_pattern_length)  # Force minimum to be 1
        self.max_pattern_length = max(self.min_pattern_length, max_pattern_length)
        self.auto_max = auto_mode

    def run_async(self) -> None:
        """Run Borel test asynchronously. Emits on_test with OperationStatus."""
        if self._thread and self._thread.is_alive():
            self.on_test.notify(status=OperationStatus(ok=False, message="Borel test already in progress"))
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
            self.on_test.notify(status=OperationStatus(ok=False, message="Borel test requires STRING01 file type"))
            return

        # Read data
        try:
            with open(self.meta.file_path, "r") as f:
                binary_data = f.read().strip()
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"Failed to read file: {e}"))
            return

        try:
            n = len(binary_data)
            
            # Calculate max pattern length if auto mode (formula: log2(L))
            if self.auto_max:
                actual_max = int(np.log2(n))
            else:
                actual_max = self.max_pattern_length
            
            if n < 2 ** actual_max:
                self.on_test.notify(status=OperationStatus(ok=False, message="Insufficient data for requested pattern lengths"))
                return

            # Test normality for different pattern lengths
            results = []
            overall_passed = True

            total_patterns = actual_max - self.min_pattern_length + 1
            for idx, pattern_len in enumerate(range(self.min_pattern_length, actual_max + 1)):
                # Check stop event between pattern lengths
                if self._stop_event.is_set():
                    self.on_test.notify(status=OperationStatus(ok=False, message="Borel test cancelled"))
                    return
                
                # Emit progress update
                progress_payload = {
                    "test_type": "Borel",
                    "completed": idx + 1,
                    "total": total_patterns,
                    "current_pattern": pattern_len,
                    "message": f"{pattern_len}-bit pattern"
                }
                self.on_progress.notify(status=OperationStatus(ok=True, payload=progress_payload))
                
                result = self._test_pattern_length(binary_data, pattern_len, n)
                results.append(result)
                if not result["passed"]:
                    overall_passed = False

            # Compute overall assessment
            assessment = "PASS" if overall_passed else "FAIL"
            
            payload = {
                "test_type": "Borel",
                "results": results,
                "data_length": n,
                "pattern_length_range": [self.min_pattern_length, actual_max],
                "overall_assessment": assessment
            }
            
            self.on_test.notify(status=OperationStatus(ok=True, message="Borel test completed", payload=payload))
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"Borel test error: {e}"))

    def _test_pattern_length(self, binary_data: str, pattern_length: int, n: int) -> Dict[str, Any]:
        """Test Borel normality for a specific pattern length using chi-square test.
        
        Args:
            binary_data: Binary string (01)
            pattern_length: Length of patterns to test
            n: Total length of data (L)
        
        Returns:
            Dict with chi-square, mean frequency, and pass/fail for this pattern length
        """
        num_patterns = 2 ** pattern_length
        total_overlapping_patterns = n - pattern_length + 1
        expected_freq = total_overlapping_patterns / num_patterns
        
        # Count pattern frequencies
        pattern_counts = {}
        for i in range(total_overlapping_patterns):
            pattern = binary_data[i:i + pattern_length]
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        # Ensure all possible patterns are represented
        for i in range(num_patterns):
            pattern = format(i, f'0{pattern_length}b')
            if pattern not in pattern_counts:
                pattern_counts[pattern] = 0
        
        # Compute chi-square statistic
        chi_square = 0
        observed_counts = []
        for pattern in sorted(pattern_counts.keys()):
            observed = pattern_counts[pattern]
            observed_counts.append(observed)
            chi_square += (observed - expected_freq) ** 2 / expected_freq
        
        # Calculate mean observed frequency
        mean_observed_freq = sum(observed_counts) / len(observed_counts)
        
        # Calculate max deviation from expected (more informative than mean fraction)
        max_deviation = max(abs(obs - expected_freq) for obs in observed_counts)
        max_deviation_ratio = max_deviation / expected_freq if expected_freq > 0 else 0
        
        # Ideal fraction for this pattern length
        ideal_fraction = 1.0 / num_patterns
        
        # Degrees of freedom
        df = num_patterns - 1
        
        # Critical value for 95% confidence
        critical_value = self._chi_square_critical(df, 0.05)
        passed = chi_square <= critical_value
        
        # Compute actual division values for display
        chi_critical_ratio = chi_square / critical_value if critical_value > 0 else 0
        # Use max deviation ratio as fraction_ratio (shows how much worst pattern deviates from expected)
        fraction_ratio = max_deviation_ratio
        
        # Calculate mean fraction
        mean_fraction = mean_observed_freq / total_overlapping_patterns if total_overlapping_patterns > 0 else 0
        
        return {
            "pattern_length": pattern_length,
            "chi_square": float(chi_square),
            "degrees_of_freedom": df,
            "critical_value": float(critical_value),
            "mean_fraction": float(mean_fraction),
            "ideal_fraction": float(ideal_fraction),
            "chi_critical_ratio": float(chi_critical_ratio),
            "fraction_ratio": float(fraction_ratio),
            "max_deviation_ratio": float(max_deviation_ratio),
            "mean_observed_frequency": float(mean_observed_freq),
            "expected_frequency": float(expected_freq),
            "total_possible_patterns": num_patterns,
            "passed": passed
        }
    
    def _chi_square_critical(self, df: int, alpha: float) -> float:
        """Approximate chi-square critical value."""
        # Simple approximation for chi-square critical values
        if df == 1:
            return 3.841 if alpha == 0.05 else 6.635
        elif df <= 30:
            # Wilson-Hilferty approximation
            h = 2.0 / (9.0 * df)
            z_alpha = 1.96 if alpha == 0.05 else 2.576
            return df * (1 - h + z_alpha * sqrt(h)) ** 3
        else:
            # Large df approximation
            z_alpha = 1.96 if alpha == 0.05 else 2.576
            return df + z_alpha * sqrt(2 * df)
