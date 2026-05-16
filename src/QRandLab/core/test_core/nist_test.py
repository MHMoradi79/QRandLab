# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Complete NIST Statistical Test Suite implementation.

Implements all 16 NIST tests with full functionality.
"""

from __future__ import annotations

from pathlib import Path
from threading import Thread, Event as ThreadEvent
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
from math import sqrt, log, exp, erfc, fabs, floor
from scipy.special import gammaincc, hyp1f1
from scipy.stats import norm
from scipy import fftpack as sff
from copy import copy

from ..observer import Event
from ..types import InputFileMeta, OperationStatus, FileType


class NistTest:
    """NIST Statistical Test Suite implementation with all 16 tests."""

    def __init__(self, meta: InputFileMeta) -> None:
        self.meta = meta
        self.on_test = Event()
        self.on_progress = Event()  # Progress event for each test completed
        
        self._thread: Optional[Thread] = None
        self._stop_event = ThreadEvent()
        self.enabled_tests = [False] * 16  # 16 NIST tests
        self.sequence_length = 1000000
        self.verbose = 1
        self.p_value_threshold = 0.01
        self.use_whole_data = False
        
        # Test names mapping
        self.test_names = [
            '01. Frequency Test (Monobit)',
            '02. Frequency Test within a Block', 
            '03. Run Test',
            '04. Longest Run of Ones in a Block',
            '05. Binary Matrix Rank Test',
            '06. Discrete Fourier Transform (Spectral) Test',
            '07. Non-Overlapping Template Matching Test',
            '08. Overlapping Template Matching Test',
            '09. Maurer\'s Universal Statistical test',
            '10. Linear Complexity Test',
            '11. Serial test',
            '12. Approximate Entropy Test',
            '13. Cumulative Sums (Forward) Test',
            '14. Cumulative Sums (Reverse) Test', 
            '15. Random Excursions Test',
            '16. Random Excursions Variant Test'
        ]
        
        # Minimum data requirements for each test (in bits)
        self.min_data_requirements = [
            100,       # Test 1: Monobit
            100,       # Test 2: Block Frequency
            100,       # Test 3: Runs
            128,       # Test 4: Longest Run
            1024,      # Test 5: Binary Matrix Rank (32x32)
            1000,      # Test 6: DFT
            100,       # Test 7: Non-overlapping Template
            1032,      # Test 8: Overlapping Template (m=9)
            387840,    # Test 9: Universal (L=6, Q=640)
            1000000,   # Test 10: Linear Complexity (M=500)
            100,       # Test 11: Serial
            100,       # Test 12: Approximate Entropy
            100,       # Test 13: Cumulative Sums Forward
            100,       # Test 14: Cumulative Sums Reverse
            1000000,   # Test 15: Random Excursions
            1000000    # Test 16: Random Excursions Variant
        ]

    def stop(self) -> None:
        """Signal the running thread to stop."""
        self._stop_event.set()
    
    def force_stop(self) -> None:
        """Force stop - alias for stop() since NIST has no subprocess."""
        self.stop()
    
    def reset_stop(self) -> None:
        """Reset the stop event for new operations."""
        self._stop_event.clear()

    def set_enabled_tests(self, enabled: List[bool]) -> None:
        """Set which NIST tests to run (16 boolean values)."""
        if len(enabled) == 16:
            self.enabled_tests = enabled.copy()

    def set_parameters(self, sequence_length: int = 1000000, verbose: int = 1, p_value_threshold: float = 0.01, use_whole_data: bool = False) -> None:
        """Set test parameters."""
        self.sequence_length = sequence_length
        self.verbose = verbose
        self.p_value_threshold = p_value_threshold
        self.use_whole_data = use_whole_data

    def run_async(self) -> None:
        """Run NIST tests asynchronously. Emits on_test with OperationStatus."""
        if self._thread and self._thread.is_alive():
            self.on_test.notify(status=OperationStatus(ok=False, message="NIST test already in progress"))
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
            self.on_test.notify(status=OperationStatus(ok=False, message="NIST requires STRING01 file type"))
            return

        # Read data
        try:
            with open(self.meta.file_path, "r") as f:
                binary_data = f.read().strip()
        except Exception as e:
            self.on_test.notify(status=OperationStatus(ok=False, message=f"Failed to read file: {e}"))
            return

        # Use whole data or limit to sequence length
        if self.use_whole_data:
            test_data = binary_data  # Use all data
        else:
            test_data = binary_data[:self.sequence_length] if len(binary_data) > self.sequence_length else binary_data
        # Run enabled tests
        test_results = []
        total_enabled = sum(self.enabled_tests)
        completed_count = 0
        
        for i, enabled in enumerate(self.enabled_tests):
            # Check stop event between tests
            if self._stop_event.is_set():
                self.on_test.notify(status=OperationStatus(ok=False, message="NIST test cancelled"))
                return
            if enabled:
                try:
                    result = self._run_single_test(i, test_data)
                    test_results.append({
                        "test_id": i,
                        "test_name": self.test_names[i],
                        "result": result,
                        "error": None
                    })
                except Exception as e:
                    # Log error but continue with other tests
                    test_results.append({
                        "test_id": i,
                        "test_name": self.test_names[i],
                        "result": {"p_value": 0.0, "passed": False},
                        "error": str(e)
                    })
                
                # Emit progress after each test
                completed_count += 1
                progress_payload = {
                    "test_type": "NIST",
                    "completed": completed_count,
                    "total": total_enabled,
                    "test_name": self.test_names[i]
                }
                self.on_progress.notify(status=OperationStatus(ok=True, payload=progress_payload))    
        payload = {
            "test_type": "NIST",
            "results": test_results,
            "sequence_length": len(test_data),
            "enabled_tests": self.enabled_tests.copy(),
            "verbose": self.verbose
        }
        
        self.on_test.notify(status=OperationStatus(ok=True, message="NIST tests completed", payload=payload))

    def _run_single_test(self, test_id: int, binary_data: str) -> Dict[str, Any]:
        """Run a single NIST test by ID."""
        # Check minimum data requirement
        if test_id < len(self.min_data_requirements):
            min_required = self.min_data_requirements[test_id]
            if len(binary_data) < min_required:
                # Raise exception for insufficient data
                raise ValueError(f"Insufficient data: requires at least {min_required} bits, got {len(binary_data)} bits")
        
        test_functions = {
            0: self._monobit_test,
            1: self._block_frequency_test,
            2: self._runs_test,
            3: self._longest_run_test,
            4: self._binary_matrix_rank_test,
            5: self._spectral_test,
            6: self._non_overlapping_test,
            7: self._overlapping_test,
            8: self._universal_test,
            9: self._linear_complexity_test,
            10: self._serial_test,
            11: self._approximate_entropy_test,
            12: lambda data: self._cumulative_sums_test(data, mode=0),
            13: lambda data: self._cumulative_sums_test(data, mode=1),
            14: self._random_excursions_test,
            15: self._random_excursions_variant_test
        }
        
        test_func = test_functions.get(test_id)
        if test_func:
            return test_func(binary_data)
        else:
            return {"p_value": 0.0, "passed": False, "note": "Test not implemented"}

    # Test 1: Frequency (Monobit) Test
    def _monobit_test(self, binary_data: str) -> Dict[str, Any]:
        """Frequency (Monobit) Test."""
        length_of_bit_string = len(binary_data)
        
        # Variable for S(n)
        count = 0
        # Iterate each bit in the string and compute for S(n)
        for bit in binary_data:
            if bit == '0':
                count -= 1
            elif bit == '1':
                count += 1

        # Compute the test statistic
        s_obs = count / sqrt(length_of_bit_string)
        
        # Compute p-Value
        p_value = erfc(fabs(s_obs) / sqrt(2))
        
        return {
            "p_value": p_value, 
            "passed": p_value >= self.p_value_threshold,
            "statistic": s_obs,
            "count": count
        }

    # Test 2: Block Frequency Test
    def _block_frequency_test(self, binary_data: str, block_size: int = 128) -> Dict[str, Any]:
        """Block Frequency Test."""
        length_of_bit_string = len(binary_data)
        if length_of_bit_string < block_size:
            block_size = length_of_bit_string

        # Compute the number of blocks based on the input given. Discard the remainder
        number_of_blocks = int(length_of_bit_string / block_size)

        if number_of_blocks == 1:
            # For block size M=1, this test degenerates to test 1, the Frequency (Monobit) test.
            return self._monobit_test(binary_data[:block_size])

        # Initialized variables
        block_start = 0
        block_end = block_size
        proportion_sum = 0.0
        proportions = []

        # Create a for loop to process each block
        for counter in range(number_of_blocks):
            # Partition the input sequence and get the data for block
            block_data = binary_data[block_start:block_end]

            # Determine the proportion πi of ones in each M-bit
            one_count = block_data.count('1')
            # compute π
            pi = one_count / block_size
            proportions.append(pi)

            # Compute Σ(πi -½)^2.
            proportion_sum += pow(pi - 0.5, 2.0)

            # Next Block
            block_start += block_size
            block_end += block_size

        # Compute 4M Σ(πi -½)^2.
        chi_squared = 4.0 * block_size * proportion_sum

        # Compute P-Value
        p_value = gammaincc(number_of_blocks / 2, chi_squared / 2)

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "chi_squared": chi_squared,
            "number_of_blocks": number_of_blocks,
            "block_size": block_size,
            "proportions": proportions
        }

    # Test 3: Runs Test
    def _runs_test(self, binary_data: str) -> Dict[str, Any]:
        """Runs Test."""
        length_of_binary_data = len(binary_data)
        
        # Predefined tau = 2 / sqrt(n)
        tau = 2 / sqrt(length_of_binary_data)

        # Step 1 - Compute the pre-test proportion π of ones in the input sequence
        one_count = binary_data.count('1')
        pi = one_count / length_of_binary_data

        # Step 2 - If it can be shown that absolute value of (π - 0.5) is greater than or equal to tau
        # then the run test need not be performed.
        if abs(pi - 0.5) >= tau:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Pre-test failed - frequency test prerequisite not met",
                "pi": pi,
                "tau": tau
            }
        else:
            # Step 3 - Compute vObs
            v_obs = 1
            for item in range(1, length_of_binary_data):
                if binary_data[item] != binary_data[item - 1]:
                    v_obs += 1

            # Step 4 - Compute p_value
            expected_runs = 2 * length_of_binary_data * pi * (1 - pi)
            variance = 2 * sqrt(2 * length_of_binary_data) * pi * (1 - pi)
            
            if variance == 0:
                return {
                    "p_value": 0.0,
                    "passed": False,
                    "note": "Variance is zero - cannot compute p-value"
                }
            
            p_value = erfc(abs(v_obs - expected_runs) / variance)

            return {
                "p_value": p_value,
                "passed": p_value >= self.p_value_threshold,
                "runs_observed": v_obs,
                "expected_runs": expected_runs,
                "pi": pi
            }

    # Test 4: Longest Run of Ones Test
    def _longest_run_test(self, binary_data: str) -> Dict[str, Any]:
        """Longest Run of Ones Test."""
        length_of_binary_data = len(binary_data)

        # Initialized k, m, n, pi and v_values
        if length_of_binary_data < 128:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Not enough data to run this test"
            }
        elif length_of_binary_data < 6272:
            k = 3
            m = 8
            v_values = [1, 2, 3, 4]
            pi_values = [0.2148, 0.3672, 0.2305, 0.1875]
        elif length_of_binary_data < 750000:
            k = 5
            m = 128
            v_values = [4, 5, 6, 7, 8, 9]
            pi_values = [0.1174, 0.2430, 0.2493, 0.1752, 0.1027, 0.1124]
        else:
            k = 6
            m = 10000
            v_values = [10, 11, 12, 13, 14, 15, 16]
            pi_values = [0.0882, 0.2092, 0.2483, 0.1933, 0.1208, 0.0675, 0.0727]

        number_of_blocks = int(length_of_binary_data / m)
        
        if number_of_blocks == 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Insufficient data for longest run test"
            }
        
        block_start = 0
        block_end = m
        frequencies = np.zeros(k + 1)

        for count in range(number_of_blocks):
            block_data = binary_data[block_start:block_end]
            max_run_count = 0
            run_count = 0

            # Count the longest run of ones in this block
            for bit in block_data:
                if bit == '1':
                    run_count += 1
                    max_run_count = max(max_run_count, run_count)
                else:
                    max_run_count = max(max_run_count, run_count)
                    run_count = 0

            max_run_count = max(max_run_count, run_count)

            # Categorize the run length
            if max_run_count < v_values[0]:
                frequencies[0] += 1
            elif max_run_count > v_values[k - 1]:
                frequencies[k] += 1
            else:
                for j in range(k):
                    if max_run_count == v_values[j]:
                        frequencies[j] += 1
                        break

            block_start += m
            block_end += m

        # Compute chi-squared statistic
        chi_squared = 0.0
        for count in range(len(frequencies)):
            expected = number_of_blocks * pi_values[count]
            if expected > 0:
                chi_squared += pow(frequencies[count] - expected, 2.0) / expected

        p_value = gammaincc(float(k / 2), float(chi_squared / 2))

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "chi_squared": chi_squared,
            "frequencies": frequencies.tolist(),
            "expected_frequencies": [number_of_blocks * pi for pi in pi_values],
            "number_of_blocks": number_of_blocks,
            "block_size": m,
            "k": k
        }

    # Test 5: Binary Matrix Rank Test
    def _binary_matrix_rank_test(self, binary_data: str, rows_in_matrix: int = 32, columns_in_matrix: int = 32) -> Dict[str, Any]:
        """Binary Matrix Rank Test (robust implementation).

        Uses exact probabilities for ranks over GF(2) and computes p-value via chi-square with df=2.
        """
        n = len(binary_data)
        M = int(rows_in_matrix)
        Q = int(columns_in_matrix)
        block_size = M * Q
        number_of_blocks = n // block_size

        if number_of_blocks == 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Insufficient data for matrix rank test",
                "number_of_blocks": 0
            }

        # Helper: compute binary rank over GF(2)
        def binary_rank(A: np.ndarray) -> int:
            A = A.copy().astype(np.uint8) & 1
            rows, cols = A.shape
            rank = 0
            row = 0
            for col in range(cols):
                piv = np.where(A[row:rows, col] == 1)[0]
                if piv.size == 0:
                    continue
                piv_row = piv[0] + row
                if piv_row != row:
                    A[[row, piv_row], :] = A[[piv_row, row], :]
                for r in range(row + 1, rows):
                    if A[r, col] == 1:
                        A[r, :] ^= A[row, :]
                rank += 1
                row += 1
                if row == rows:
                    break
            return int(rank)

        # Helper: exact probability that random MxQ binary matrix has rank r
        def rank_probability(Mi: int, Qi: int, r: int) -> float:
            if r < 0 or r > min(Mi, Qi):
                return 0.0
            log_num = 0.0
            for i in range(r):
                log_num += log(2**Mi - 2**i)
                log_num += log(2**Qi - 2**i)
            log_den = 0.0
            for i in range(r):
                log_den += log(2**r - 2**i)
            log_total = (Mi * Qi) * log(2.0)
            log_prob = log_num - log_den - log_total
            return float(exp(log_prob))

        # Count ranks across blocks
        counts = [0, 0, 0]  # full rank, rank-1, other
        shape = (M, Q)
        idx = 0
        for _ in range(number_of_blocks):
            block_bits = binary_data[idx: idx + block_size]
            idx += block_size
            arr = np.frombuffer(bytes(block_bits, "ascii"), dtype=np.uint8)
            arr = (arr - ord('0')).astype(np.uint8)
            matrix = arr.reshape(shape)
            rnk = binary_rank(matrix)
            if rnk == min(M, Q):
                counts[0] += 1
            elif rnk == min(M, Q) - 1:
                counts[1] += 1
            else:
                counts[2] += 1

        # Theoretical probabilities
        m = min(M, Q)
        pi0 = rank_probability(M, Q, m)
        pi1 = rank_probability(M, Q, m - 1) if m - 1 >= 0 else 0.0
        pi2 = max(0.0, 1.0 - pi0 - pi1)
        pi = [pi0, pi1, pi2]

        # Chi-square
        chi_squared = 0.0
        for i in range(3):
            expected = pi[i] * number_of_blocks
            if expected > 0:
                chi_squared += (counts[i] - expected) ** 2 / expected
            else:
                return {
                    "p_value": 0.0,
                    "passed": False,
                    "note": f"Expected count is zero for category {i}; cannot compute chi-square",
                    "counts": counts,
                    "theoretical_probabilities": [float(x) for x in pi],
                    "number_of_blocks": number_of_blocks
                }

        df = 2
        p_value = float(gammaincc(df / 2.0, chi_squared / 2.0))


        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "chi_squared": float(chi_squared),
            "rank_frequencies": counts,
            "theoretical_probabilities": [float(x) for x in pi],
            "number_of_blocks": number_of_blocks,
            "matrix_size": f"{M}x{Q}"
        }

    # Test 6: Discrete Fourier Transform (Spectral) Test
    def _spectral_test(self, binary_data: str) -> Dict[str, Any]:
        """Spectral Test using Discrete Fourier Transform."""
        length_of_binary_data = len(binary_data)
        plus_one_minus_one = []

        # Step 1 - Convert 0s and 1s to -1 and +1
        for char in binary_data:
            if char == '0':
                plus_one_minus_one.append(-1)
            elif char == '1':
                plus_one_minus_one.append(1)

        # Step 2 - Apply DFT
        spectral = sff.fft(plus_one_minus_one)

        # Step 3 - Calculate modulus of first n/2 elements
        slice_point = int(np.floor(length_of_binary_data / 2))
        modulus = abs(spectral[0:slice_point])

        # Step 4 - Compute 95% peak height threshold
        tau = sqrt(log(1 / 0.05) * length_of_binary_data)

        # Step 5 - Compute expected theoretical number of peaks below threshold
        n0 = 0.95 * (length_of_binary_data / 2)

        # Step 6 - Compute actual observed number of peaks below threshold
        n1 = len(np.where(modulus < tau)[0])

        # Step 7 - Compute normalized difference
        d = (n1 - n0) / sqrt(length_of_binary_data * (0.95) * (0.05) / 4)

        # Step 8 - Compute p-value
        p_value = erfc(fabs(d) / sqrt(2))

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "d_statistic": d,
            "threshold": tau,
            "expected_peaks": n0,
            "observed_peaks": n1,
            "total_peaks": slice_point
        }

    # Test 7: Non-Overlapping Template Matching Test
    def _non_overlapping_test(self, binary_data: str, template_pattern: str = '000000001', block: int = 8) -> Dict[str, Any]:
        """Non-Overlapping Template Matching Test."""
        length_of_binary = len(binary_data)
        pattern_size = len(template_pattern)
        block_size = int(np.floor(length_of_binary / block))
        pattern_counts = np.zeros(block)

        # For each block in the data
        for count in range(block):
            block_start = count * block_size
            block_end = block_start + block_size
            block_data = binary_data[block_start:block_end]
            
            # Count non-overlapping pattern matches
            inner_count = 0
            while inner_count < block_size:  # use block_size not block_size - pattern_size + 1
                sub_block = block_data[inner_count:inner_count + pattern_size]
                if sub_block == template_pattern:
                    pattern_counts[count] += 1
                    inner_count += pattern_size  # Non-overlapping
                else:
                    inner_count += 1

        # Calculate theoretical mean and variance 
        mean = (block_size - pattern_size + 1) / pow(2, pattern_size)
        variance = block_size * ((1 / pow(2, pattern_size)) - (((2 * pattern_size) - 1) / (pow(2, pattern_size * 2))))

        if variance == 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Variance is zero - cannot compute chi-squared"
            }

        # Calculate chi-squared statistic
        chi_squared = 0
        for count in range(block):
            chi_squared += pow(pattern_counts[count] - mean, 2.0) / variance

        # Calculate p-value
        p_value = gammaincc(block / 2, chi_squared / 2)

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "chi_squared": chi_squared,
            "pattern": template_pattern,
            "pattern_counts": pattern_counts.tolist(),
            "mean": mean,
            "variance": variance,
            "num_blocks": block,
            "block_size": block_size
        }

    # Test 8: Overlapping Template Matching Test
    def _overlapping_test(self, binary_data: str, pattern_size: int = 9, block_size: int = 1032) -> Dict[str, Any]:
        """Overlapping Template Matching Test."""
        length_of_binary_data = len(binary_data)
        
        # Create pattern of all 1s
        pattern = '1' * pattern_size
        number_of_blocks = int(np.floor(length_of_binary_data / block_size))

        if number_of_blocks == 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Insufficient data for overlapping template test"
            }

        # Calculate lambda and eta
        lambda_val = float(block_size - pattern_size + 1) / pow(2, pattern_size)
        eta = lambda_val / 2.0

        # Calculate theoretical probabilities
        pi = [self._get_prob(i, eta) for i in range(5)]
        diff = float(np.array(pi).sum())
        pi.append(1.0 - diff)

        pattern_counts = np.zeros(6)
        
        for i in range(number_of_blocks):
            block_start = i * block_size
            block_end = block_start + block_size
            block_data = binary_data[block_start:block_end]
            
            # Count overlapping pattern matches
            pattern_count = 0
            j = 0
            while j < block_size - pattern_size + 1:
                sub_block = block_data[j:j + pattern_size]
                if sub_block == pattern:
                    pattern_count += 1
                j += 1
            
            # Categorize count
            if pattern_count <= 4:
                pattern_counts[pattern_count] += 1
            else:
                pattern_counts[5] += 1

        # Calculate chi-squared statistic
        chi_squared = 0.0
        for i in range(len(pattern_counts)):
            expected = number_of_blocks * pi[i]
            chi_squared += pow(pattern_counts[i] - expected, 2.0) / expected

        p_value = gammaincc(5.0 / 2.0, chi_squared / 2.0)

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "chi_squared": chi_squared,
            "pattern": pattern,
            "pattern_counts": pattern_counts.tolist(),
            "theoretical_probabilities": pi,
            "lambda": lambda_val,
            "eta": eta,
            "number_of_blocks": number_of_blocks,
            "block_size": block_size
        }

    def _get_prob(self, u: int, x: float) -> float:
        """Helper function for overlapping template test."""
        if u == 0:
            return exp(-x)
        else:
            return x * exp(2 * -x) * (2 ** -u) * hyp1f1(u + 1, 2, x)

    # Test 9: Maurer's Universal Statistical Test
    def _universal_test(self, binary_data: str) -> Dict[str, Any]:
        """Maurer's Universal Statistical Test."""
        length_of_binary_data = len(binary_data)
        
        # Determine pattern size based on data length
        pattern_size = 5
        if length_of_binary_data >= 387840:
            pattern_size = 6
        if length_of_binary_data >= 904960:
            pattern_size = 7
        if length_of_binary_data >= 2068480:
            pattern_size = 8
        if length_of_binary_data >= 4654080:
            pattern_size = 9
        if length_of_binary_data >= 10342400:
            pattern_size = 10
        if length_of_binary_data >= 22753280:
            pattern_size = 11
        if length_of_binary_data >= 49643520:
            pattern_size = 12
        if length_of_binary_data >= 107560960:
            pattern_size = 13
        if length_of_binary_data >= 231669760:
            pattern_size = 14
        if length_of_binary_data >= 496435200:
            pattern_size = 15
        if length_of_binary_data >= 1059061760:
            pattern_size = 16

        if not (5 < pattern_size < 16):
            return {
                "p_value": 0.0,
                "passed": False,
                "note": f"Pattern size {pattern_size} out of valid range (6-15)"
            }

        # Create the biggest binary string of length pattern_size
        ones = "1" * pattern_size
        num_ints = int(ones, 2)
        vobs = np.zeros(num_ints + 1)

        # Keeps track of the blocks
        num_blocks = int(np.floor(length_of_binary_data / pattern_size))
        init_bits = 10 * pow(2, pattern_size)
        test_bits = num_blocks - init_bits

        if test_bits <= 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Insufficient test bits for universal test"
            }

        # Expected values assuming randomness
        c = 0.7 - 0.8 / pattern_size + (4 + 32 / pattern_size) * pow(test_bits, -3 / pattern_size) / 15
        variance = [0, 0, 0, 0, 0, 0, 2.954, 3.125, 3.238, 3.311, 3.356, 3.384, 3.401, 3.410, 3.416, 3.419, 3.421]
        expected = [0, 0, 0, 0, 0, 0, 5.2177052, 6.1962507, 7.1836656, 8.1764248, 9.1723243,
                    10.170032, 11.168765, 12.168070, 13.167693, 14.167488, 15.167379]
        sigma = c * sqrt(variance[pattern_size] / test_bits)

        cumsum = 0.0
        # Process blocks
        for i in range(num_blocks):
            block_start = i * pattern_size
            block_end = block_start + pattern_size
            block_data = binary_data[block_start:block_end]
            int_rep = int(block_data, 2)

            if i < init_bits:
                vobs[int_rep] = i + 1
            else:
                initial = vobs[int_rep]
                vobs[int_rep] = i + 1
                cumsum += log(i - initial + 1, 2)

        # Compute the statistic
        phi = float(cumsum / test_bits)
        stat = abs(phi - expected[pattern_size]) / (float(sqrt(2)) * sigma)
        p_value = erfc(stat)

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "phi": phi,
            "expected_phi": expected[pattern_size],
            "sigma": sigma,
            "pattern_size": pattern_size,
            "test_bits": test_bits,
            "init_bits": init_bits
        }

    # Test 10: Linear Complexity Test
    def _linear_complexity_test(self, binary_data: str, block_size: int = 500) -> Dict[str, Any]:
        """Linear Complexity Test."""
        length_of_binary_data = len(binary_data)
        degree_of_freedom = 6
        pi = [0.01047, 0.03125, 0.125, 0.5, 0.25, 0.0625, 0.020833]

        t2 = (block_size / 3.0 + 2.0 / 9) / 2 ** block_size
        mean = 0.5 * block_size + (1.0 / 36) * (9 + (-1) ** (block_size + 1)) - t2
        number_of_blocks = int(length_of_binary_data / block_size)

        if number_of_blocks <= 1:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Insufficient blocks for linear complexity test"
            }

        # Process blocks
        blocks = []
        for i in range(number_of_blocks):
            block_start = i * block_size
            block_end = block_start + block_size
            blocks.append(binary_data[block_start:block_end])

        # Calculate complexities using Berlekamp-Massey algorithm
        complexities = []
        for block in blocks:
            complexities.append(self._berlekamp_massey_algorithm(block))

        # Calculate test statistic
        t = [(((-1.0) ** block_size) * (chunk - mean) + 2.0 / 9) for chunk in complexities]
        vg = np.histogram(t, bins=[-9999999999, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, 9999999999])[0]
        im = [((vg[ii] - number_of_blocks * pi[ii]) ** 2) / (number_of_blocks * pi[ii]) for ii in range(7)]

        chi_squared = sum(im)
        p_value = gammaincc(degree_of_freedom / 2.0, chi_squared / 2.0)

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "chi_squared": chi_squared,
            "complexities": complexities,
            "mean": mean,
            "number_of_blocks": number_of_blocks,
            "block_size": block_size
        }

    # Test 11: Serial Test
    def _serial_test(self, binary_data: str, pattern_length: int = 16) -> Dict[str, Any]:
        """Serial Test - returns two p-values."""
        length_of_binary_data = len(binary_data)
        binary_data += binary_data[:(pattern_length - 1)]

        # Get max length patterns for m, m-1, m-2
        max_pattern = '1' * (pattern_length + 1)

        # Determine frequencies for different pattern lengths
        vobs_01 = np.zeros(int(max_pattern[0:pattern_length], 2) + 1)
        vobs_02 = np.zeros(int(max_pattern[0:pattern_length - 1], 2) + 1)
        vobs_03 = np.zeros(int(max_pattern[0:pattern_length - 2], 2) + 1)

        for i in range(length_of_binary_data):
            vobs_01[int(binary_data[i:i + pattern_length], 2)] += 1
            vobs_02[int(binary_data[i:i + pattern_length - 1], 2)] += 1
            vobs_03[int(binary_data[i:i + pattern_length - 2], 2)] += 1

        vobs = [vobs_01, vobs_02, vobs_03]

        if length_of_binary_data == 0:
            return {
                "p_value_1": 0.0,
                "p_value_2": 0.0,
                "passed_1": False,
                "passed_2": False,
                "note": "Zero length data"
            }
        
        # Compute ψs
        sums = np.zeros(3)
        for i in range(3):
            for j in range(len(vobs[i])):
                sums[i] += pow(vobs[i][j], 2)
            sums[i] = (sums[i] * pow(2, pattern_length - i) / length_of_binary_data) - length_of_binary_data

        # Compute ∇
        nabla_01 = sums[0] - sums[1]
        nabla_02 = sums[0] - 2.0 * sums[1] + sums[2]

        # Compute P-Values
        p_value_01 = gammaincc(pow(2, pattern_length - 1) / 2, nabla_01 / 2.0)
        p_value_02 = gammaincc(pow(2, pattern_length - 2) / 2, nabla_02 / 2.0)

        return {
            "p_value_1": p_value_01,
            "p_value_2": p_value_02,
            "passed_1": p_value_01 >= self.p_value_threshold,
            "passed_2": p_value_02 >= self.p_value_threshold,
            "nabla_1": nabla_01,
            "nabla_2": nabla_02,
            "pattern_length": pattern_length,
            "sums": sums.tolist()
        }

    # Test 12: Approximate Entropy Test
    def _approximate_entropy_test(self, binary_data: str, pattern_length: int = 10) -> Dict[str, Any]:
        """Approximate Entropy Test."""
        length_of_binary_data = len(binary_data)
        binary_data += binary_data[:pattern_length - 1]

        # Keep track of each pattern's frequency
        vobs_01 = np.zeros(int('1' * pattern_length, 2) + 1)
        vobs_02 = np.zeros(int('1' * (pattern_length + 1), 2) + 1)

        for i in range(length_of_binary_data):
            vobs_01[int(binary_data[i:i + pattern_length], 2)] += 1
            vobs_02[int(binary_data[i:i + pattern_length + 1], 2)] += 1

        # Calculate test statistics and p values
        vobs = [vobs_01, vobs_02]
        sums = np.zeros(2)
        
        for i in range(2):
            for j in range(len(vobs[i])):
                if vobs[i][j] > 0:
                    sums[i] += vobs[i][j] * log(vobs[i][j] / length_of_binary_data)
        
        if length_of_binary_data == 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Zero length data"
            }
        
        sums /= length_of_binary_data
        ape = sums[0] - sums[1]
        chi_squared = 2.0 * length_of_binary_data * (log(2) - ape)
        p_value = gammaincc(pow(2, pattern_length - 1), chi_squared / 2.0)

        return {
            "p_value": p_value,
            "passed": p_value >= self.p_value_threshold,
            "ape": ape,
            "chi_squared": chi_squared,
            "pattern_length": pattern_length,
            "sums": sums.tolist()
        }

    # Test 13, 14: Cumulative Sums Test
    def _cumulative_sums_test(self, binary_data: str, mode: int = 0) -> Dict[str, Any]:
        """Cumulative Sums Test (mode: 0=forward, 1=backward).
        Implementation follows NIST SP800-22 (Cumulative Sums Test) formula.
        """
        n = len(binary_data)
        if n == 0:
            return {
                "p_value": 0.0,
                "passed": False,
                "note": "Zero length data"
            }

        # Reverse for backward mode
        if mode != 0:
            binary_data = binary_data[::-1]

        # convert bits to +/-1 and compute partial sums
        X = np.array([1 if ch == '1' else -1 for ch in binary_data], dtype=int)
        S = np.cumsum(X)              # S_k for k=1..n, stored in S[0..n-1]
        z = float(np.max(np.abs(S)))  # test statistic

        # handle corner case
        if z == 0.0:
            p_value = 1.0
        else:
            sqrt_n = sqrt(n)
            k_min = int(floor(( - (n / z) + 1.0) / 4.0))
            k_max = int(floor((  (n / z) - 1.0) / 4.0))

            sum1 = 0.0
            for k in range(k_min, k_max + 1):
                a = (4*k + 1) * z / sqrt_n
                b = (4*k - 1) * z / sqrt_n
                sum1 += norm.cdf(a) - norm.cdf(b)

            # second sum: k_min2 = floor( ( -n/z - 3 ) / 4 ), k_max2 = floor( ( n/z - 1 ) / 4 )
            k_min2 = int(floor(( - (n / z) - 3.0) / 4.0))
            k_max2 = k_max

            sum2 = 0.0
            for k in range(k_min2, k_max2 + 1):
                a = (4*k + 3) * z / sqrt_n
                b = (4*k + 1) * z / sqrt_n
                sum2 += norm.cdf(a) - norm.cdf(b)

            p_value = 1.0 - sum1 + sum2

        return {
            "p_value": float(p_value),
            "passed": bool(p_value >= self.p_value_threshold),
            "z": z,
            "mode": "forward" if mode == 0 else "backward",
            "cumulative_sums": S.tolist()
        }

    # Test 15: Random Excursions Test
    def _random_excursions_test(self, binary_data: str) -> Dict[str, Any]:
        """Random Excursions Test - returns results for 8 states."""
        length_of_binary_data = len(binary_data)
        
        # Convert to -1, +1 sequence
        sequence_x = np.zeros(length_of_binary_data)
        for i in range(len(binary_data)):
            sequence_x[i] = -1.0 if binary_data[i] == '0' else 1.0

        # Compute cumulative sum
        cumulative_sum = np.cumsum(sequence_x)
        cumulative_sum = np.append(cumulative_sum, [0])
        cumulative_sum = np.append([0], cumulative_sum)

        # States to examine
        x_values = np.array([-4, -3, -2, -1, 1, 2, 3, 4])

        # Find cycles (returns to 0)
        position = np.where(cumulative_sum == 0)[0]
        cycles = []
        for pos in range(len(position) - 1):
            cycles.append(cumulative_sum[position[pos]:position[pos + 1] + 1])
        
        num_cycles = len(cycles)
        if num_cycles == 0:
            return {
                "results": [],
                "passed": False,
                "note": "No complete cycles found"
            }

        # Count state visits
        state_count = []
        for cycle in cycles:
            state_count.append([len(np.where(cycle == state)[0]) for state in x_values])
        state_count = np.transpose(np.clip(state_count, 0, 5))

        # Calculate frequencies
        su = []
        for cycle in range(6):
            su.append([(sct == cycle).sum() for sct in state_count])
        su = np.transpose(su)

        # Calculate expected values and chi-squared
        pi = [[self._get_pi_value(uu, state) for uu in range(6)] for state in x_values]
        inner_term = num_cycles * np.array(pi)
        chi_squared = np.sum(1.0 * (np.array(su) - inner_term) ** 2 / inner_term, axis=1)
        p_values = [gammaincc(2.5, cs / 2.0) for cs in chi_squared]

        # Format results
        states = ['-4', '-3', '-2', '-1', '+1', '+2', '+3', '+4']
        results = []
        for i, p_val in enumerate(p_values):
            results.append({
                "state": states[i],
                "state_value": int(x_values[i]),
                "chi_squared": float(chi_squared[i]),
                "p_value": float(p_val),
                "passed": p_val >= self.p_value_threshold
            })

        return {
            "results": results,
            "num_cycles": num_cycles,
            "overall_passed": all(r["passed"] for r in results)
        }

    # Test 16: Random Excursions Variant Test
    def _random_excursions_variant_test(self, binary_data: str) -> Dict[str, Any]:
        """Random Excursions Variant Test."""
        length_of_binary_data = len(binary_data)
        int_data = np.zeros(length_of_binary_data)

        for count in range(length_of_binary_data):
            int_data[count] = int(binary_data[count])

        sum_int = (2 * int_data) - np.ones(len(int_data))
        cumulative_sum = np.cumsum(sum_int)

        # Collect state frequencies
        li_data = []
        index = []
        for count in sorted(set(cumulative_sum)):
            if abs(count) <= 9:
                index.append(count)
                li_data.append([count, len(np.where(cumulative_sum == count)[0])])

        j = self._get_frequency(li_data, 0) + 1

        # Calculate p-values for each state
        p_values = []
        for count in sorted(set(index)):
            if count != 0:
                den = sqrt(2 * j * (4 * abs(count) - 2))
                p_values.append(erfc(abs(self._get_frequency(li_data, count) - j) / den))

        # Remove 0 from li_data
        for data in li_data[:]:
            if data[0] == 0:
                li_data.remove(data)
                index.remove(0)
                break

        # Format results
        states = []
        for item in index:
            states.append(str(item) if item < 0 else '+' + str(item))

        results = []
        for i, p_val in enumerate(p_values):
            results.append({
                "state": states[i],
                "state_value": li_data[i][0],
                "frequency": li_data[i][1],
                "p_value": float(p_val),
                "passed": p_val >= self.p_value_threshold
            })

        return {
            "results": results,
            "j": j,
            "overall_passed": all(r["passed"] for r in results)
        }

    # Helper methods
    def _berlekamp_massey_algorithm(self, block_data: str) -> int:
        """Return linear complexity L of block_data using Berlekamp-Massey (binary)."""
        # Convert to ints (0/1)
        s = [int(ch) for ch in block_data]
        n = len(s)
        C = [0] * (n + 1)
        B = [0] * (n + 1)
        C[0] = 1
        B[0] = 1
        L = 0
        m = 1
        b = 1  # previous discrepancy (1 initially)

        for N in range(n):
            # compute discrepancy d
            d = s[N]
            for i in range(1, L + 1):
                d ^= (C[i] & s[N - i])
            if d == 1:
                T = C.copy()
                # C = C + x^m * B (over GF(2)) — implement by XOR shifting B
                for i in range(0, n - N + L):   # safe upper bound for indices
                    if B[i] == 1:
                        C[i + m] ^= 1
                if 2 * L <= N:
                    L_new = N + 1 - L
                    B = T
                    L = L_new
                    m = 1
                else:
                    m += 1
            else:
                m += 1
        return int(L)


    def _get_pi_value(self, k: int, x: int) -> float:
        """Helper for random excursions test."""
        if k == 0:
            return 1 - 1.0 / (2 * abs(x))
        elif k >= 5:
            return (1.0 / (2 * abs(x))) * (1 - 1.0 / (2 * abs(x))) ** 4
        else:
            return (1.0 / (4 * x * x)) * (1 - 1.0 / (2 * abs(x))) ** (k - 1)

    def _get_frequency(self, list_data: List, trigger: int) -> int:
        """Helper for random excursions variant test."""
        frequency = 0
        for (x, y) in list_data:
            if x == trigger:
                frequency = y
        return frequency

class BinaryMatrix:
    """Binary matrix rank computation for NIST test 5."""

    def __init__(self, matrix, rows, cols):
        self.M = rows
        self.Q = cols
        self.A = matrix
        self.m = min(rows, cols)

    def compute_rank(self, verbose=False):
        """Compute the binary rank of the matrix."""
        # Forward elimination
        i = 0
        while i < self.m - 1:
            if self.A[i][i] == 1:
                self.perform_row_operations(i, True)
            else:
                found = self.find_unit_element_swap(i, True)
                if found == 1:
                    self.perform_row_operations(i, True)
            i += 1

        # Backward elimination
        i = self.m - 1
        while i > 0:
            if self.A[i][i] == 1:
                self.perform_row_operations(i, False)
            else:
                if self.find_unit_element_swap(i, False) == 1:
                    self.perform_row_operations(i, False)
            i -= 1

        return self.determine_rank()

    def perform_row_operations(self, i, forward_elimination):
        """Perform elementary row operations."""
        if forward_elimination:
            j = i + 1
            while j < self.M:
                if self.A[j][i] == 1:
                    self.A[j, :] = (self.A[j, :] + self.A[i, :]) % 2
                j += 1
        else:
            j = i - 1
            while j >= 0:
                if self.A[j][i] == 1:
                    self.A[j, :] = (self.A[j, :] + self.A[i, :]) % 2
                j -= 1

    def find_unit_element_swap(self, i, forward_elimination):
        """Find and swap rows to get a unit element."""
        row_op = 0
        if forward_elimination:
            index = i + 1
            while index < self.M and self.A[index][i] == 0:
                index += 1
            if index < self.M:
                row_op = self.swap_rows(i, index)
        else:
            index = i - 1
            while index >= 0 and self.A[index][i] == 0:
                index -= 1
            if index >= 0:
                row_op = self.swap_rows(i, index)
        return row_op

    def swap_rows(self, i, ix):
        """Swap two rows in the matrix."""
        temp = copy(self.A[i, :])
        self.A[i, :] = self.A[ix, :]
        self.A[ix, :] = temp
        return 1

    def determine_rank(self):
        """Determine the rank of the transformed matrix."""
        rank = self.m
        i = 0
        while i < self.M:
            all_zeros = 1
            for j in range(self.Q):
                if self.A[i][j] == 1:
                    all_zeros = 0
                    break
            if all_zeros == 1:
                rank -= 1
            i += 1
        return rank
