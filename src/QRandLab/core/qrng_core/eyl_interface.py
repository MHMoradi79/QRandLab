# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""EYL Hardware QRNG Interface."""

from __future__ import annotations
import sys

import threading
import ctypes
import time
import socket
from typing import Optional, Dict, Any
from pathlib import Path

from ..observer import Event
from ..types import OperationStatus


class EYLInterface:
    """Interface for EYL Hardware QRNG operations."""

    def __init__(self) -> None:
        self.on_eyl_data = Event()  # Data ready for upper layers
        self.on_eyl_error = Event()  # Error occurred
        
        self._stop_event = threading.Event()
        self._eyl_thread: Optional[threading.Thread] = None
        self._qrn_lib = None  # Cached DLL handle
        self._connected = False
    
    def check_dll(self) -> OperationStatus:
        """Check if QRNG.dll can be loaded."""
        try:
            if hasattr(sys, '_MEIPASS'):
                project_root = Path(sys._MEIPASS)
            else:
                project_root = Path(__file__).resolve().parent.parent.parent
            dll_path = project_root / "third_party" / "bin" / "QRNG.dll"
            if not dll_path.exists():
                return OperationStatus(ok=False, message=f"QRNG.dll not found at {dll_path}")
            
            # Try to load DLL
            test_lib = ctypes.CDLL(str(dll_path))
            return OperationStatus(ok=True, message=f"QRNG.dll loaded successfully from {dll_path}")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Failed to load QRNG.dll: {e}")
    
    def test_connection(self) -> OperationStatus:
        """Test connection to EYL hardware using GETQRNDRV (doesn't consume random data).
        
        Error codes from DLL:
        GETQRNDRV: 0=Success, -1=Not Found Drive
        GETQRNARR: 0=Success, -1=iCnt<1, -2=iCnt>16384, -3=Thread problem, 
                   -4=Queue empty (connected but no data), -5=No path (disconnected)
        """
        try:
            if hasattr(sys, '_MEIPASS'):
                project_root = Path(sys._MEIPASS)
            else:
                project_root = Path(__file__).resolve().parent.parent.parent
            dll_path = project_root / "third_party" / "bin" / "QRNG.dll"
            if not dll_path.exists():
                return OperationStatus(ok=False, message="QRNG.dll not found")
            
            qrn_lib = ctypes.CDLL(str(dll_path))
            
            # Try to create connection
            result = qrn_lib.CREATEQRN(2)
            if result != 2:
                return OperationStatus(ok=False, message="Failed to initialize QRNG - DLL error")
            
            # Actually try to read some data to verify USB connection
            buf = (ctypes.c_ubyte * 16)()
            error_code = qrn_lib.GETQRNARR(16, buf)
            
            if error_code != 0:
                return OperationStatus(ok=False, message=f"EYL device not found - check USB connection, error code: {error_code}")

            # Store for later use
            self._qrn_lib = qrn_lib
            self._connected = True
            return OperationStatus(ok=True, message="Connected to EYL hardware")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Connection error: {e}")
    
    def disconnect(self) -> OperationStatus:
        """Disconnect from EYL hardware."""
        self._connected = False
        self._qrn_lib = None
        return OperationStatus(ok=True, message="Disconnected from EYL hardware")

    def start_generation(self, mode: str, **kwargs) -> OperationStatus:
        """Start EYL hardware random number generation.
        
        Args:
            mode: Generation mode ("offline", "display", "stream")
            **kwargs: Mode-specific parameters
            
        Returns:
            OperationStatus indicating success/failure
        """
        if self._eyl_thread and self._eyl_thread.is_alive():
            return OperationStatus(ok=False, message="EYL generation already in progress")

        # Validate mode
        if mode not in ["offline", "display", "stream"]:
            return OperationStatus(ok=False, message=f"Invalid mode: {mode}. Use 'offline', 'display', or 'stream'")

        # Mode-specific validation
        if mode == "offline":
            if not all(k in kwargs for k in ["base_filename", "num_files", "file_size_bits"]):
                return OperationStatus(ok=False, message="Offline mode requires: base_filename, num_files, file_size_bits")
        elif mode == "stream":
            if not all(k in kwargs for k in ["host", "port"]):
                return OperationStatus(ok=False, message="Stream mode requires: host, port")

        def worker():
            try:
                # Load DLL using pathlib
                if hasattr(sys, '_MEIPASS'):
                    project_root = Path(sys._MEIPASS)
                else:
                    project_root = Path(__file__).resolve().parent.parent.parent
                dll_path = project_root / "third_party" / "bin" / "QRNG.dll"
                if not dll_path.exists():
                    self._emit_error(f"QRNG.dll not found at {dll_path}")
                    return

                try:
                    qrn_lib = ctypes.CDLL(str(dll_path))
                except Exception as e:
                    self._emit_error(f"Failed to load QRNG.dll: {e}")
                    return

                # Initialize hardware connection
                if qrn_lib.CREATEQRN(2) != 2:
                    self._emit_error("Failed to create connection to QRNG hardware")
                    return

                # Clear stop event and start generation
                self._stop_event.clear()

                if mode == "offline":
                    self._run_offline_mode(qrn_lib, **kwargs)
                elif mode == "display":
                    self._run_display_mode(qrn_lib, **kwargs)
                elif mode == "stream":
                    self._run_stream_mode(qrn_lib, **kwargs)

            except Exception as e:
                self._emit_error(f"EYL worker error: {e}")

        self._eyl_thread = threading.Thread(target=worker, daemon=True)
        self._eyl_thread.start()
        return OperationStatus(ok=True, message=f"EYL {mode} mode started")

    def _run_offline_mode(self, qrn_lib, base_filename: str, num_files: int, 
                         file_size_bits: int, **kwargs) -> None:
        """Run EYL in offline mode with adaptive buffer/pause algorithm and batch save.
        
        Uses an adaptive algorithm that adjusts buffer size and pause time based on
        hardware response. On success, increases buffer size. On queue empty (-4),
        reduces buffer or increases pause. On disconnect (-5), waits for reconnection.
        
        Args:
            qrn_lib: Loaded QRNG DLL handle
            base_filename: Base path/name for output files (e.g., 'path/data')
            num_files: Number of files to generate
            file_size_bits: Size of each file in bits
            **kwargs: Optional parameters:
                - start_from_file (int): Resume from this file index (default 0)
        
        Emits:
            on_eyl_data: Progress updates, rate updates, file completions
            on_eyl_error: On fatal errors
        """
        try:
            # Validate limits: max 1000 files, max 1GB per file
            max_files = 1000
            max_size_bits = 8 * 1024 * 1024 * 1024  # 1GB in bits
            
            if num_files > max_files:
                self._emit_error(f"Number of files exceeds maximum ({max_files})")
                return
            if file_size_bits > max_size_bits:
                self._emit_error(f"File size exceeds maximum (1GB)")
                return
            
            file_size_bytes = file_size_bits // 8
            
            # Get start_from_file for resume support (default 0)
            start_from_file = kwargs.get('start_from_file', 0)
            
            # Adaptive parameters - start aggressive, back off on errors
            current_buffer = min(16384, file_size_bytes)
            current_pause = 0.0  # seconds
            min_buffer = 64
            max_buffer = 16384
            min_pause = 0.0
            max_pause = 0.5  # 500ms max pause
            
            # Rate tracking
            total_bytes_transferred = 0
            start_time = time.time()
            last_rate_update = start_time
            last_progress_update = start_time
            consecutive_success = 0
            consecutive_errors = 0
            
            for file_index in range(start_from_file, num_files):
                if self._stop_event.is_set():
                    break
                
                filename = f"{base_filename}_{file_index + 1}.txt"
                bytes_collected = 0
                file_data = bytearray()
                
                while bytes_collected < file_size_bytes and not self._stop_event.is_set():
                    # Ensure buffer doesn't exceed remaining bytes needed
                    read_size = min(current_buffer, file_size_bytes - bytes_collected)
                    
                    # Read from hardware
                    buf = (ctypes.c_ubyte * read_size)()
                    request_start = time.time()
                    error_code = qrn_lib.GETQRNARR(read_size, buf)
                    
                    if error_code == -4:
                        # -4: Queue empty - device connected but not enough data yet
                        # This is NOT a disconnection, just need to wait and adjust
                        consecutive_errors += 1
                        consecutive_success = 0
                        
                        # Adaptive: reduce buffer size or increase pause
                        if current_buffer > min_buffer:
                            current_buffer = max(min_buffer, current_buffer // 2)
                        elif current_pause < max_pause:
                            current_pause = min(max_pause, current_pause + 0.05)
                        
                        # Wait and retry
                        time.sleep(0.1)
                        continue
                    
                    elif error_code == -5:
                        # -5: No random number generator path - device disconnected
                        # Wait and retry instead of stopping - allow GUI to handle reconnection
                        consecutive_errors += 1
                        if consecutive_errors >= 50:  # ~5 seconds of retries
                            # Too many consecutive errors - save partial and stop
                            if bytes_collected > 0:
                                self._save_partial_file(filename, file_data, bytes_collected, file_size_bytes)
                            self._emit_error("EYL device disconnected - check USB connection")
                            return
                        # Wait and retry - device may reconnect
                        time.sleep(0.1)
                        continue
                    
                    elif error_code == -3:
                        # -3: Thread problem - need to reset with CLOSEQRNG
                        if bytes_collected > 0:
                            self._save_partial_file(filename, file_data, bytes_collected, file_size_bytes)
                        self._emit_error("EYL internal error - please reconnect device")
                        return
                        
                    elif error_code != 0:
                        # Other error codes (-1, -2 are parameter errors, shouldn't happen)
                        if bytes_collected > 0:
                            self._save_partial_file(filename, file_data, bytes_collected, file_size_bytes)
                        self._emit_error(f"EYL error (code: {error_code})")
                        return
                    
                    # Success - collect data
                    consecutive_success += 1
                    consecutive_errors = 0
                    
                    raw_bytes = bytes(buf)
                    file_data.extend(raw_bytes)
                    bytes_collected += read_size
                    total_bytes_transferred += read_size
                    
                    # Apply pause if needed
                    if current_pause > 0:
                        time.sleep(current_pause)
                    
                    # Adaptive: aggressively increase performance after consecutive successes
                    # Reduce pause faster (every 5 successes) and by larger amounts
                    if consecutive_success >= 5:
                        consecutive_success = 0
                        if current_pause > min_pause:
                            # Reduce pause by 50% each time (faster recovery)
                            current_pause = max(min_pause, current_pause * 0.5)
                        elif current_buffer < max_buffer:
                            # Double buffer size (aggressive increase)
                            current_buffer = min(max_buffer, current_buffer * 2)
                    
                    # Update rate and progress statistics periodically
                    now = time.time()
                    if now - last_rate_update >= 0.5:  # Update every 500ms
                        elapsed = now - start_time
                        if elapsed > 0:
                            bytes_per_sec = total_bytes_transferred / elapsed
                            bits_per_sec = bytes_per_sec * 8
                            self.on_eyl_data.notify(status=OperationStatus(
                                ok=True,
                                message="Rate update",
                                payload={
                                    "mode": "offline",
                                    "event": "rate_update",
                                    "bytes_per_sec": bytes_per_sec,
                                    "bits_per_sec": bits_per_sec,
                                    "current_buffer": current_buffer,
                                    "current_pause_ms": int(current_pause * 1000),
                                    "total_bytes": total_bytes_transferred
                                }
                            ))
                        last_rate_update = now
                    
                    # Update single file progress periodically
                    if now - last_progress_update >= 0.3:  # Update every 300ms
                        progress_pct = (bytes_collected / file_size_bytes) * 100
                        self.on_eyl_data.notify(status=OperationStatus(
                            ok=True,
                            message="File progress",
                            payload={
                                "mode": "offline",
                                "event": "file_progress",
                                "file_index": file_index + 1,
                                "total_files": num_files,
                                "bytes_collected": bytes_collected,
                                "file_size_bytes": file_size_bytes,
                                "progress_pct": progress_pct
                            }
                        ))
                        last_progress_update = now
                
                # Send complete file data to upper layers
                if not self._stop_event.is_set():
                    binary_string = "".join(format(byte, "08b") for byte in file_data)
                    self.on_eyl_data.notify(status=OperationStatus(
                        ok=True,
                        message="File data ready",
                        payload={
                            "mode": "offline",
                            "filename": filename,
                            "data": binary_string,
                            "file_index": file_index + 1,
                            "total_files": num_files,
                            "size_bits": len(binary_string)
                        }
                    ))
            
        except Exception as e:
            self._emit_error(f"Offline mode error: {e}")
    
    def _save_partial_file(self, filename: str, file_data: bytearray, 
                          bytes_collected: int, file_size_bytes: int) -> None:
        """Save partial file data on disconnection (batch save approach)."""
        try:
            if bytes_collected > 0:
                # Save partial data with _partial suffix
                partial_filename = filename.replace('.txt', '_partial.txt')
                binary_string = "".join(format(byte, "08b") for byte in file_data)
                
                self.on_eyl_data.notify(status=OperationStatus(
                    ok=True,
                    message="Partial file saved",
                    payload={
                        "mode": "offline",
                        "event": "partial_save",
                        "filename": partial_filename,
                        "data": binary_string,
                        "bytes_collected": bytes_collected,
                        "file_size_bytes": file_size_bytes,
                        "size_bits": len(binary_string)
                    }
                ))
        except Exception as e:
            self._emit_error(f"Failed to save partial file: {e}")

    def _run_display_mode(self, qrn_lib, buffer_size: int = 1024, pause_ms: int = 0) -> None:
        """Run EYL in display mode - continuous data stream for GUI display.
        
        Continuously reads from hardware and emits binary string data for live display.
        Handles temporary disconnections by waiting and retrying.
        
        Args:
            qrn_lib: Loaded QRNG DLL handle
            buffer_size: Bytes to read per iteration (default 1024)
            pause_ms: Pause between reads in milliseconds (default 0, uses 10ms min)
        
        Emits:
            on_eyl_data: Binary string data chunks for display
            on_eyl_error: On fatal errors
        """
        try:
            pause_sec = pause_ms / 1000.0 if pause_ms > 0 else 0.01
            
            while not self._stop_event.is_set():
                # Read from hardware (8192 bits = 1024 bytes)
                buf = (ctypes.c_ubyte * buffer_size)()
                error_code = qrn_lib.GETQRNARR(buffer_size, buf)
                time.sleep(pause_sec)
                
                if error_code == -4:
                    # Queue empty - wait and retry
                    time.sleep(0.1)
                    continue
                elif error_code == -5:
                    # Device disconnected - wait and retry (allow reconnection)
                    time.sleep(0.5)
                    continue
                elif error_code == -3:
                    self._emit_error("EYL internal error - please reconnect device")
                    return
                elif error_code != 0:
                    self._emit_error(f"EYL error (code: {error_code})")
                    return
                
                raw_bytes = bytes(buf)
                
                # Convert to binary string
                binary_string = "".join(format(byte, "08b") for byte in raw_bytes)
                
                # Send data chunk to GUI for display
                self.on_eyl_data.notify(status=OperationStatus(
                    ok=True,
                    message="Display data received",
                    payload={
                        "mode": "display",
                        "data": binary_string,
                        "bytes_count": len(raw_bytes)
                    }
                ))
                
        except Exception as e:
            self._emit_error(f"Display mode error: {e}")

    def _run_stream_mode(self, qrn_lib, host: str, port: int, 
                        buffer_size: int = 1024, pause_ms: int = 0, 
                        send_termcode: bool = True) -> None:
        """Run EYL in stream mode - TCP streaming to network clients.
        
        Creates a TCP server, waits for client connection (up to 60s), then streams
        random data to connected client. Handles disconnections by waiting and retrying.
        
        Args:
            qrn_lib: Loaded QRNG DLL handle
            host: Host address to bind to (e.g., '127.0.0.1' or '0.0.0.0')
            port: Port number to bind to
            buffer_size: Bytes per chunk (default 1024)
            pause_ms: Pause between sends in milliseconds (default 0, uses 10ms min)
            send_termcode: If True, sends 1024 bytes of '1' when stopping (default True)
        
        Emits:
            on_eyl_data: Connection events, transfer updates, stream end
            on_eyl_error: On fatal errors
        """
        try:
            pause_sec = pause_ms / 1000.0 if pause_ms > 0 else 0.01
            # Create and bind socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(1)
            server_socket.settimeout(1.0)
            
            # Wait for client connection
            connection = None
            client_address = None
            wait_time = 0
            
            while not self._stop_event.is_set() and wait_time < 60:
                try:
                    connection, client_address = server_socket.accept()
                    break
                except socket.timeout:
                    wait_time += 1
                    continue
            
            if not connection:
                server_socket.close()
                self._emit_error("No client connected within timeout (60s)")
                return
            
            # Notify upper layers about connection
            self.on_eyl_data.notify(status=OperationStatus(
                ok=True,
                message=f"Client connected: {client_address}",
                payload={
                    "mode": "stream",
                    "event": "client_connected",
                    "client_address": str(client_address)
                }
            ))
            
            # Stream data to connected client
            total_bytes_sent = 0
            while not self._stop_event.is_set():
                # Read from hardware
                buf = (ctypes.c_ubyte * buffer_size)()
                error_code = qrn_lib.GETQRNARR(buffer_size, buf)
                time.sleep(pause_sec)
                
                if error_code == -4:
                    # Queue empty - wait and retry
                    time.sleep(0.1)
                    continue
                elif error_code == -5:
                    # Device disconnected - wait and retry (allow reconnection)
                    time.sleep(0.5)
                    continue
                elif error_code == -3:
                    self._emit_error("EYL internal error - please reconnect device")
                    break
                elif error_code != 0:
                    self._emit_error(f"EYL error (code: {error_code})")
                    break
                
                raw_bytes = bytes(buf)
                
                # Send raw bytes to TCP client
                try:
                    connection.sendall(raw_bytes)
                    total_bytes_sent += len(raw_bytes)
                except Exception as e:
                    self._emit_error(f"TCP connection error: {e}")
                    break
                
                # Also send data to upper layers for monitoring
                binary_string = "".join(format(byte, "08b") for byte in raw_bytes)
                self.on_eyl_data.notify(status=OperationStatus(
                    ok=True,
                    message="Stream data sent",
                    payload={
                        "mode": "stream",
                        "data": binary_string,
                        "bytes_count": len(raw_bytes),
                        "total_bytes_sent": total_bytes_sent,
                        "client_address": str(client_address)
                    }
                ))
            
            # Send termination message to client before closing (if enabled)
            if connection:
                try:
                    if send_termcode:
                        termination_message = b"1"*1024
                        connection.sendall(termination_message)
                        time.sleep(0.1)  # Give client time to receive
                        self.on_eyl_data.notify(status=OperationStatus(
                            ok=True,
                            message="Stream ended - termination message sent",
                            payload={
                                "mode": "stream",
                                "event": "stream_ended",
                                "total_bytes_sent": total_bytes_sent,
                                "client_address": str(client_address)
                            }
                        ))
                    else:
                        self.on_eyl_data.notify(status=OperationStatus(
                            ok=True,
                            message="Stream ended",
                            payload={
                                "mode": "stream",
                                "event": "stream_ended",
                                "total_bytes_sent": total_bytes_sent,
                                "client_address": str(client_address)
                            }
                        ))
                except:
                    pass
                connection.close()
            server_socket.close()
            
        except Exception as e:
            self._emit_error(f"Stream mode error: {e}")

    def _emit_error(self, message: str) -> None:
        """Emit error event."""
        self.on_eyl_error.notify(status=OperationStatus(ok=False, message=message))

    def stop_generation(self) -> OperationStatus:
        """Stop EYL generation."""
        if not self._eyl_thread or not self._eyl_thread.is_alive():
            return OperationStatus(ok=False, message="No EYL generation is active")
        
        try:
            self._stop_event.set()
            self._eyl_thread.join(timeout=2.0)
            return OperationStatus(ok=True, message="EYL generation stopped")
        except Exception as e:
            return OperationStatus(ok=False, message=f"Error stopping EYL: {e}")

    def is_running(self) -> bool:
        """Check if EYL generation is currently running."""
        return self._eyl_thread is not None and self._eyl_thread.is_alive()
