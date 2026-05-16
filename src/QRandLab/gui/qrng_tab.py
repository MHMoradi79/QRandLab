# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""QRNG tab for generating random data from various sources."""

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import datetime
from pathlib import Path


from ..manager.core_manager import CoreManager
from ..core.types import OperationStatus


class QRNGTab(ttk.Frame):
    """QRNG data generation tab with Internet APIs, EYL, and PRNG sources."""
    
    def __init__(self, parent, manager: CoreManager):
        super().__init__(parent, padding=20)
        self.manager = manager
        
        # API/EYL data storage
        self.api_data = None
        self.eyl_data = None
        
        # Provider-specific settings storage (independent per provider)
        self.api_provider_settings = {
            "anu": {"length": "1024", "data_type": "uint8", "block_size": "1", "api_key": ""},
            "random_org": {"length": "1024", "data_type": "uint8", "block_size": "1", "api_key": ""},
            "hotbits": {"length": "759", "data_type": "uint8", "block_size": "1", "api_key": ""}
        }
        self._current_api_provider = "anu"
        
        # Report tab reference (will be set by main_window)
        self.report_tab = None
        
        # Setup events
        self._setup_events()
        
        # Build UI
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to QRNG events."""
        self.manager.qrng.on_qrng_completed.subscribe(self._on_qrng_completed)
        self.manager.qrng.on_qrng_failed.subscribe(self._on_qrng_failed)
        self.manager.qrng.on_prng_progress.subscribe(self._on_prng_progress)
    
    def _on_prng_progress(self, status: OperationStatus):
        """Handle PRNG progress updates - files saved directly."""
        if status.payload:
            file_index = status.payload.get("file_index", 0)
            total_files = status.payload.get("total_files", 0)
            files_saved = status.payload.get("files_saved", 0)
            saved_path = status.payload.get("saved_path", "")
            self._log_prng_progress(f"💾 Saved file {files_saved}/{total_files}: {Path(saved_path).name}")
            # Update progress bar
            if total_files > 0:
                progress_pct = (files_saved / total_files) * 100
                self.prng_progress['value'] = progress_pct
    
    def _build_ui(self):
        """Build QRNG tab UI."""
        # Create notebook for three sections
        self.qrng_notebook = ttk.Notebook(self)
        self.qrng_notebook.pack(fill=BOTH, expand=YES)
        
        # Create three tabs
        self.api_frame = ttk.Frame(self.qrng_notebook, padding=15)
        self.eyl_frame = ttk.Frame(self.qrng_notebook, padding=15)
        self.prng_frame = ttk.Frame(self.qrng_notebook, padding=15)
        
        self.qrng_notebook.add(self.api_frame, text="  Internet APIs  ")
        self.qrng_notebook.add(self.eyl_frame, text="  EYL Device  ")
        self.qrng_notebook.add(self.prng_frame, text="  PRNG  ")
        
        # Build each section
        self._build_api_section()
        self._build_eyl_section()
        self._build_prng_section()
    
    # ==================== Internet APIs Section ====================
    
    def _build_api_section(self):
        """Build Internet APIs section."""
        # Provider Selection
        provider_frame = ttk.LabelFrame(self.api_frame, text="API Provider", padding=15, bootstyle=INFO)
        provider_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(
            provider_frame,
            text="Select QRNG Service:",
            font=("Helvetica", 10, "bold")
        ).grid(row=0, column=0, sticky=W, pady=5)
        
        self.api_provider_var = tk.StringVar(value="anu")
        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.api_provider_var,
            values=["anu", "random_org", "hotbits"],
            state="readonly",
            width=20
        )
        provider_combo.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=W)
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)
        
        provider_frame.columnconfigure(1, weight=1)
        
        # Container for API Settings and Actions side by side
        api_config_container = ttk.Frame(self.api_frame)
        api_config_container.pack(fill=X, pady=(0, 15))
        api_config_container.columnconfigure(0, weight=1)
        api_config_container.columnconfigure(1, weight=0)
        
        # API Settings 
        settings_frame = ttk.LabelFrame(api_config_container, text="API Settings", padding=15, bootstyle=INFO)
        settings_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        settings_frame.columnconfigure(0, weight=0)
        settings_frame.columnconfigure(1, weight=0)

        # Length
        ttk.Label(settings_frame, text="Length:", font=("Helvetica", 10)).grid(row=0, column=0, sticky=W, pady=5, padx=5)
        self.api_length_var = tk.StringVar(value="1024")
        ttk.Entry(settings_frame, textvariable=self.api_length_var, width=20).grid(row=0, column=1, sticky=W, pady=5, padx=5)
        
        # Data type (dynamic based on provider)
        self.api_data_type_label = ttk.Label(settings_frame, text="Data Type:", font=("Helvetica", 10))
        self.api_data_type_label.grid(row=1, column=0, sticky=W, pady=5, padx=5)
        self.api_data_type_var = tk.StringVar(value="uint8")
        self.api_data_type_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.api_data_type_var,
            values=["uint8", "uint16", "hex16"],
            state="readonly",
            width=18
        )
        self.api_data_type_combo.grid(row=1, column=1, sticky=W, pady=5, padx=5)
        
        # Block size (ANU only)
        self.api_block_size_label = ttk.Label(settings_frame, text="Block Size:", font=("Helvetica", 10))
        self.api_block_size_label.grid(row=2, column=0, sticky=W, pady=5, padx=5)
        self.api_block_size_var = tk.StringVar(value="1")
        self.api_block_size_entry = ttk.Entry(settings_frame, textvariable=self.api_block_size_var, width=20)
        self.api_block_size_entry.grid(row=2, column=1, sticky=W, pady=5, padx=5)
        
        # API Key (random_org only)
        self.api_key_label = ttk.Label(settings_frame, text="API Key:", font=("Helvetica", 10))
        self.api_key_var = tk.StringVar(value="")
        self.api_key_entry = ttk.Entry(settings_frame, textvariable=self.api_key_var, width=20, show="*")
        
        # Info label (dynamic)
        self.api_info_label = ttk.Label(
            settings_frame,
            text="ℹ️ ANU: data_types=[uint8, uint16, hex16], max_length=1024",
            font=("Helvetica", 9, "italic"),
            bootstyle="info"
        )
        self.api_info_label.grid(row=1, column=2, columnspan=2, sticky=W, padx=(10, 0))
        
        # Initialize UI for default provider
        self._on_provider_changed()
        
        # Actions
        actions_frame = ttk.LabelFrame(api_config_container, text="Actions", padding=15, bootstyle="success")
        actions_frame.grid(row=0, column=1, sticky="nsew")
        
        # Fetch button
        self.api_fetch_btn = ttk.Button(actions_frame, text="Fetch", command=self._fetch_api_data, bootstyle="success", width=12)
        self.api_fetch_btn.pack(pady=3, fill='both', anchor='n')  
        
        # Save button
        self.api_save_btn = ttk.Button(actions_frame, text="Save", command=self._save_api_data, bootstyle="primary", width=12, state=DISABLED)
        self.api_save_btn.pack(pady=3, fill='both', anchor='n')  
        
        # Reset button
        self.api_reset_btn = ttk.Button(actions_frame, text="Reset", command=self._clear_api_status, bootstyle="secondary", width=12)
        self.api_reset_btn.pack(pady=3, fill='both', anchor='n')  
        
        # Status
        status_frame = ttk.LabelFrame(self.api_frame, text="Status", padding=15, bootstyle="info")
        status_frame.pack(fill=BOTH, expand=YES)
        
        self.api_status_text = tk.Text(
            status_frame,
            height=6,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            state=DISABLED
        )
        self.api_status_text.pack(fill=BOTH, expand=YES)
        
        # Configure text tags for colored output
        self.api_status_text.tag_configure("success", foreground="#4CAF50")  # Material green
        self.api_status_text.tag_configure("error", foreground="#F44336")    # Material red
        self.api_status_text.tag_configure("warning", foreground="#FF9800")  # Material orange
        
        self._log_api_info("Ready to fetch quantum random data from Internet APIs...")
    
    # ==================== EYL Device Section ====================
    
    def _build_eyl_section(self):
        """Build EYL device section."""
        # Top container for mode settings and connection status side by side
        top_container = ttk.Frame(self.eyl_frame)
        top_container.pack(fill=X, pady=(0, 15))
        top_container.columnconfigure(0, weight=1)
        top_container.columnconfigure(1, weight=0)
        
        # Mode Settings
        mode_frame = ttk.LabelFrame(top_container, text="EYL Generation Mode", padding=15, bootstyle=INFO)
        mode_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Mode selection
        ttk.Label(mode_frame, text="Mode:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky=W, pady=5, padx=5)
        self.eyl_mode_var = tk.StringVar(value="offline")
        mode_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.eyl_mode_var,
            values=["offline", "display", "stream"],
            state="readonly",
            width=18
        )
        mode_combo.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        mode_combo.bind("<<ComboboxSelected>>", self._on_eyl_mode_changed)
        
        # Offline mode - base filename
        self.eyl_filename_label = ttk.Label(mode_frame, text="Base Filename:", font=("Helvetica", 10))
        self.eyl_filename_var = tk.StringVar(value="eyl_data")
        self.eyl_filename_entry = ttk.Entry(mode_frame, textvariable=self.eyl_filename_var, width=20)
        
        # Offline mode - number of files
        self.eyl_num_files_label = ttk.Label(mode_frame, text="Number of Files:", font=("Helvetica", 10))
        self.eyl_num_files_var = tk.StringVar(value="1")
        self.eyl_num_files_entry = ttk.Entry(mode_frame, textvariable=self.eyl_num_files_var, width=20)

        # Progress bar for EYL (files progress)
        self.eyl_progress = ttk.Progressbar(mode_frame, length=120, mode='determinate', bootstyle="success-striped")

        # File counter label for offline mode
        self.eyl_file_counter_label = ttk.Label(mode_frame, text="[0/0]", font=("Helvetica", 9), bootstyle="info")

        # Max files info label
        self.eyl_max_files_label = ttk.Label(mode_frame, text="(max: 1000)", font=("Helvetica", 8), bootstyle="info")
        
        # Single file progress bar and label for offline mode
        self.eyl_single_file_progress = ttk.Progressbar(mode_frame, length=120, mode='determinate', bootstyle="info-striped")
        self.eyl_single_file_label = ttk.Label(mode_frame, text="[0/0]", font=("Helvetica", 9), bootstyle="info")
        # Max file size info label
        self.eyl_max_size_label = ttk.Label(mode_frame, text="(max: 1GB)", font=("Helvetica", 8), bootstyle="info")
        
        # Offline mode - file size
        self.eyl_file_size_label = ttk.Label(mode_frame, text="File Size (bits):", font=("Helvetica", 10))
        self.eyl_file_size_var = tk.StringVar(value="8192")
        self.eyl_file_size_entry = ttk.Entry(mode_frame, textvariable=self.eyl_file_size_var, width=20)
        
        # Output format (for offline mode)
        self.eyl_output_format_label = ttk.Label(mode_frame, text="Output Format:", font=("Helvetica", 10))
        self.eyl_output_format_var = tk.StringVar(value="binary")
        self.eyl_output_format_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.eyl_output_format_var,
            values=["binary", "string01", "hex", "uint8", "uint16", "uint32", "uint64"],
            state="readonly",
            width=18
        )
        
        # Buffer size (stream mode only)
        self.eyl_buffer_size_label = ttk.Label(mode_frame, text="Buffer Size (bytes):", font=("Helvetica", 10))
        self.eyl_buffer_size_var = tk.StringVar(value="1024")
        self.eyl_buffer_size_entry = ttk.Entry(mode_frame, textvariable=self.eyl_buffer_size_var, width=20)
        self.eyl_buffer_max_label = ttk.Label(mode_frame, text="(max: 16384)", font=("Helvetica", 8), bootstyle="info")
        
        # Pause time between requests (to avoid -4 error on high buffer)
        self.eyl_pause_label = ttk.Label(mode_frame, text="Pause Time (ms):", font=("Helvetica", 10))
        self.eyl_pause_var = tk.StringVar(value="0")
        self.eyl_pause_entry = ttk.Entry(mode_frame, textvariable=self.eyl_pause_var, width=20)
        self.eyl_pause_note_label = ttk.Label(mode_frame, text="pause between device requests (0-10000)", font=("Helvetica", 8), bootstyle="info")
        
        # Display mode - save displayed data checkbox
        self.eyl_save_display_var = tk.BooleanVar(value=False)
        self.eyl_save_display_check = ttk.Checkbutton(
            mode_frame,
            text="Save displayed data",
            variable=self.eyl_save_display_var,
            command=self._on_save_display_changed,
            bootstyle="success-round-toggle"
        )
        
        # Stream mode only - network settings
        self.eyl_network_label = ttk.Label(mode_frame, text="Network:", font=("Helvetica", 10, "bold"))
        self.eyl_network_var = tk.StringVar(value="localhost")
        self.eyl_network_combo = ttk.Combobox(
            mode_frame,
            textvariable=self.eyl_network_var,
            values=["localhost", "LAN (custom)"],
            state="readonly",
            width=18
        )
        self.eyl_network_combo.bind("<<ComboboxSelected>>", self._on_eyl_network_changed)
        
        self.eyl_host_label = ttk.Label(mode_frame, text="Host:", font=("Helvetica", 10))
        self.eyl_host_var = tk.StringVar(value="127.0.0.1")
        self.eyl_host_entry = ttk.Entry(mode_frame, textvariable=self.eyl_host_var, width=20)
        
        self.eyl_port_label = ttk.Label(mode_frame, text="Port:", font=("Helvetica", 10))
        self.eyl_port_var = tk.StringVar(value="4000")
        self.eyl_port_entry = ttk.Entry(mode_frame, textvariable=self.eyl_port_var, width=20)
        
        # Stream mode - send termination code checkbox
        self.eyl_send_termcode_var = tk.BooleanVar(value=True)
        self.eyl_send_termcode_check = ttk.Checkbutton(
            mode_frame,
            text="Send termination code (1024 bytes of '1')",
            variable=self.eyl_send_termcode_var,
            bootstyle="success-round-toggle"
        )
        
        # Stream mode - save sent data checkbox
        self.eyl_save_stream_var = tk.BooleanVar(value=False)
        self.eyl_save_stream_check = ttk.Checkbutton(
            mode_frame,
            text="Save sent data",
            variable=self.eyl_save_stream_var,
            command=self._on_save_stream_changed,
            bootstyle="success-round-toggle"
        )
        
        # Info label - will be placed in front of mode combo (row 0)
        self.eyl_info_label = ttk.Label(
            mode_frame,
            text="ℹ️ Offline: Generate and save files locally",
            font=("Helvetica", 9, "italic"),
            bootstyle="info"
        )
        self.eyl_info_label.grid(row=0, column=2, columnspan=3, sticky=W, padx=10)

        # Actions
        self.eyl_actions_frame = ttk.LabelFrame(top_container, text="Actions", padding=15, bootstyle="success")
        self.eyl_actions_frame.grid(row=0, column=2, sticky="nsew")
        
        # Inner frame for centering buttons vertically
        eyl_btn_inner = ttk.Frame(self.eyl_actions_frame)
        eyl_btn_inner.pack(expand=YES, fill=Y, pady=(0, 15))
        
        # Save path display label
        self.eyl_save_path = None

        # Start button
        self.eyl_start_btn = ttk.Button(eyl_btn_inner, text="Start", command=self._start_eyl_generation, bootstyle="success", width=12, state=DISABLED)
        self.eyl_start_btn.pack(pady=3, fill='both', anchor='n')  
        
        # Stop button
        self.eyl_stop_btn = ttk.Button(eyl_btn_inner, text="Stop", command=self._stop_eyl_generation, bootstyle="danger", width=12, state=DISABLED)
        self.eyl_stop_btn.pack(pady=3, fill='both', anchor='n')  
        
        # Save Path button
        self.eyl_path_btn = ttk.Button(eyl_btn_inner, text="Save Path", command=self._browse_eyl_save_folder, bootstyle="primary", width=12)
        self.eyl_path_btn.pack(pady=3, fill='both', anchor='n')  

        # Save Data button
        self.eyl_save_btn = ttk.Button(eyl_btn_inner, text="Save Data", command=self._save_eyl_data, bootstyle="primary", width=12, state=DISABLED)
        self.eyl_save_btn.pack(pady=3, fill='both', anchor='n')  
        
        # Reset button
        self.eyl_reset_btn = ttk.Button(eyl_btn_inner, text="Reset", command=self._clear_eyl_status, bootstyle="secondary", width=12)
        self.eyl_reset_btn.pack(pady=3, fill='both', anchor='n')  
        

        # Rate label for offline mode - shows adaptive algorithm stats
        self.eyl_rate_label = ttk.Label(eyl_btn_inner, text="", font=("Helvetica", 8), bootstyle="info", wraplength=100)
        self.eyl_rate_label.pack(pady=2)
        
        # Transfer label for stream mode - shows bytes transferred
        self.eyl_transfer_label = ttk.Label(
            eyl_btn_inner,
            text="",
            font=("Helvetica", 8),
            bootstyle="info",
            wraplength=100
        )
        self.eyl_transfer_label.pack(pady=2)
        
        # Connection Status
        conn_frame = ttk.LabelFrame(top_container, text="Connection", padding=15, bootstyle="warning")
        conn_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        
        # Combined Connect/Disconnect toggle button (checks DLL and connects)
        self.eyl_connected_var = tk.BooleanVar(value=False)
        self.eyl_connect_btn = ttk.Checkbutton(
            conn_frame,
            text="Connect to EYL",
            variable=self.eyl_connected_var,
            command=self._toggle_eyl_connection,
            bootstyle="success-round-toggle"
        )
        self.eyl_connect_btn.pack(anchor=W, pady=5)
        
        # Status text
        self.eyl_conn_status_label = ttk.Label(
            conn_frame,
            text="Not Connected",
            font=("Helvetica", 10, "bold"),
            foreground="orange"
        )
        self.eyl_conn_status_label.pack(anchor=W, pady=5)
        
        # Auto-retry on disconnect
        self.eyl_auto_retry_var = tk.BooleanVar(value=False)
        self.eyl_auto_retry_check = ttk.Checkbutton(
            conn_frame,
            text="Auto-retry on disconnect",
            variable=self.eyl_auto_retry_var,
            command=self._on_auto_retry_changed,
            bootstyle="success-round-toggle"
        )
        self.eyl_auto_retry_check.pack(anchor=W, pady=5)
        
        # Retry delay entry (milliseconds)
        retry_frame = ttk.Frame(conn_frame)
        retry_frame.pack(anchor=W, pady=2)
        ttk.Label(retry_frame, text="Delay (ms):", font=("Helvetica", 9)).pack(side=LEFT)
        self.eyl_retry_delay_var = tk.StringVar(value="2000")
        self.eyl_retry_delay_entry = ttk.Entry(retry_frame, textvariable=self.eyl_retry_delay_var, width=8, state=DISABLED)
        self.eyl_retry_delay_entry.pack(side=LEFT, padx=5)
        
        # Base name for stream mode save (in Generation Mode frame, initially hidden and disabled)
        self.eyl_basename_label = ttk.Label(mode_frame, text="Base Name:", font=("Helvetica", 10))
        self.eyl_basename_var = tk.StringVar(value="eyl_data")
        self.eyl_basename_entry = ttk.Entry(mode_frame, textvariable=self.eyl_basename_var, width=20, state=DISABLED)
        
        # Timestamp checkbox (for stream mode ONLY - in Generation Mode frame)
        self.eyl_timestamp_var = tk.BooleanVar(value=True)
        self.eyl_timestamp_check = ttk.Checkbutton(
            mode_frame,
            text="Add Timestamp",
            variable=self.eyl_timestamp_var,
            bootstyle="success-round-toggle",
            state=DISABLED
        )
        
        # Legacy variable for compatibility
        self.eyl_save_folder_var = tk.StringVar(value="")
        
        # Status
        self.eyl_status_frame = ttk.LabelFrame(self.eyl_frame, text="Status", padding=15, bootstyle="info")
        self.eyl_status_frame.pack(fill=BOTH, expand=YES)
        
        self.eyl_status_text = tk.Text(
            self.eyl_status_frame,
            height=6,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            state=DISABLED
        )
        self.eyl_status_text.pack(fill=BOTH, expand=YES)
        
        # Configure text tags for colored output
        self.eyl_status_text.tag_configure("success", foreground="#4CAF50")  # Material green
        self.eyl_status_text.tag_configure("error", foreground="#F44336")    # Material red
        self.eyl_status_text.tag_configure("warning", foreground="#FF9800")  # Material orange
        
        self._log_eyl_info("Ready to read from EYL quantum device...")
        
        # Initialize UI for default mode (must be after all widgets created)
        self._on_eyl_mode_changed()
    
    # ==================== PRNG Section ====================
    
    def _build_prng_section(self):
        """Build PRNG section."""
        # Container for all three frames side by side with equal height
        settings_container = ttk.Frame(self.prng_frame)
        settings_container.pack(fill=X, pady=(0, 15))
        settings_container.columnconfigure(0, weight=1)
        settings_container.columnconfigure(1, weight=0)
        settings_container.columnconfigure(2, weight=0)
        settings_container.rowconfigure(0, weight=1)
        
        # DieHarder Settings (left)
        algo_frame = ttk.LabelFrame(settings_container, text="DieHarder PRNG Settings", padding=15, bootstyle=INFO)
        algo_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Generator ID
        ttk.Label(algo_frame, text="Generator ID:", font=("Helvetica", 10)).grid(row=0, column=0, sticky=W, pady=5, padx=5)
        self.prng_generator_id_var = tk.StringVar(value="1")
        ttk.Entry(algo_frame, textvariable=self.prng_generator_id_var, width=20).grid(row=0, column=1, sticky=W, pady=5, padx=5)
        
        # Seed
        ttk.Label(algo_frame, text="Seed:", font=("Helvetica", 10)).grid(row=1, column=0, sticky=W, pady=5, padx=5)
        self.prng_seed_var = tk.StringVar(value="12345")
        ttk.Entry(algo_frame, textvariable=self.prng_seed_var, width=20).grid(row=1, column=1, sticky=W, pady=5, padx=5)
        
        # Number of files
        ttk.Label(algo_frame, text="Number of Files:", font=("Helvetica", 10)).grid(row=2, column=0, sticky=W, pady=5, padx=5)
        self.prng_num_files_var = tk.StringVar(value="1")
        ttk.Entry(algo_frame, textvariable=self.prng_num_files_var, width=20).grid(row=2, column=1, sticky=W, pady=5, padx=5)

        # Frame for max label and progress bar
        prng_files_info_frame = ttk.Frame(algo_frame)
        prng_files_info_frame.grid(row=2, column=2, sticky=W, padx=5)

        # Progress bar
        self.prng_progress = ttk.Progressbar(prng_files_info_frame, length=120, mode='determinate', bootstyle="success-striped")
        self.prng_progress.pack(side=LEFT, padx=(0, 0))

        ttk.Label(prng_files_info_frame, text="(max: 1000)", font=("Helvetica", 9), bootstyle="info").pack(side=LEFT, padx=(10, 0))

        # Count per file (number of uint32 values)
        ttk.Label(algo_frame, text="Count (uint32):", font=("Helvetica", 10)).grid(row=3, column=0, sticky=W, pady=5, padx=5)
        self.prng_size_var = tk.StringVar(value="10000")
        ttk.Entry(algo_frame, textvariable=self.prng_size_var, width=20).grid(row=3, column=1, sticky=W, pady=5, padx=5)
        ttk.Label(algo_frame, text="(max: 268435456)", font=("Helvetica", 9), bootstyle="info").grid(row=3, column=2, sticky=W, padx=5)
        
        # Output format
        ttk.Label(algo_frame, text="Output Format:", font=("Helvetica", 10)).grid(row=4, column=0, sticky=W, pady=5, padx=5)
        self.prng_output_format_var = tk.StringVar(value="uint32")
        self.prng_output_format_combo = ttk.Combobox(
            algo_frame,
            textvariable=self.prng_output_format_var,
            values=["uint32", "binary", "string01", "hex", "uint8", "uint16", "uint64"],
            state="readonly",
            width=18
        )
        self.prng_output_format_combo.grid(row=4, column=1, sticky=W, pady=5, padx=5)
        
        # Info
        info_label = ttk.Label(algo_frame, text="ℹ️ Valid IDs: 0-61, 203-206, 400-405, 500-501", font=("Helvetica", 9, "italic"), bootstyle="info")
        info_label.grid(row=0, column=2, columnspan=3, sticky=W, padx=(10, 0))
        
        # Saving Options
        save_options_frame = ttk.LabelFrame(settings_container, text="Saving Options", padding=15, bootstyle=INFO)
        save_options_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10))
        
        # Include Header checkbox
        self.prng_include_header_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            save_options_frame,
            text="Include Header",
            variable=self.prng_include_header_var,
            bootstyle="round-toggle"
        ).pack(anchor=W, pady=5)
        
        # Separator
        ttk.Separator(save_options_frame, orient="horizontal").pack(fill=X, pady=10)
        
        # Filename options label
        ttk.Label(save_options_frame, text="Filename includes:", font=("Helvetica", 9, "italic")).pack(anchor=W)
        
        # Include Generator ID checkbox
        self.prng_include_gen_id_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            save_options_frame,
            text="Generator ID",
            variable=self.prng_include_gen_id_var,
            bootstyle="round-toggle"
        ).pack(anchor=W, pady=5)
        
        # Include Seed checkbox
        self.prng_include_seed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            save_options_frame,
            text="Seed",
            variable=self.prng_include_seed_var,
            bootstyle="round-toggle"
        ).pack(anchor=W, pady=5)
        
        # Base name entry
        base_name_frame = ttk.Frame(save_options_frame)
        base_name_frame.pack(fill=X, pady=(10, 5))
        ttk.Label(base_name_frame, text="Base name:", font=("Helvetica", 9)).pack(side=LEFT)
        self.prng_base_name_var = tk.StringVar(value="prng")
        ttk.Entry(base_name_frame, textvariable=self.prng_base_name_var, width=12).pack(side=LEFT, padx=5)
        
        # Actions
        actions_frame = ttk.LabelFrame(settings_container, text="Actions", padding=15, bootstyle="success")
        actions_frame.grid(row=0, column=2, sticky="nsew")
        
        # Start button
        self.prng_generate_btn = ttk.Button(actions_frame, text="Start", command=self._generate_prng_data, bootstyle="success", width=12)
        self.prng_generate_btn.pack(pady=3, fill='both', anchor='n')
        
        # Stop button
        self.prng_stop_btn = ttk.Button(actions_frame, text="Stop", command=self._stop_prng_generation, bootstyle="warning", width=12, state=DISABLED)
        self.prng_stop_btn.pack(pady=3, fill='both', anchor='n')
        
        # Save path button
        self.prng_path_btn = ttk.Button(actions_frame, text="Save Path", command=self._choose_prng_save_path, bootstyle="primary", width=12)
        self.prng_path_btn.pack(pady=3, fill='both', anchor='n')
        
        # Reset button
        self.prng_reset_btn = ttk.Button(actions_frame, text="Reset", command=self._clear_prng_status, bootstyle="secondary", width=12)
        self.prng_reset_btn.pack(pady=3, fill='both', anchor='n')
        
        # Save path display
        self.prng_save_path = None
        self.prng_save_path_var = tk.StringVar(value="No save path selected")
        
        # Status
        status_frame = ttk.LabelFrame(self.prng_frame, text="Status", padding=15, bootstyle="info")
        status_frame.pack(fill=BOTH, expand=YES)
        
        self.prng_status_text = tk.Text(
            status_frame,
            height=6,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            state=DISABLED
        )
        self.prng_status_text.pack(fill=BOTH, expand=YES)
        
        # Configure text tags for colored output
        self.prng_status_text.tag_configure("success", foreground="#4CAF50")  # Material green
        self.prng_status_text.tag_configure("error", foreground="#F44336")    # Material red
        self.prng_status_text.tag_configure("warning", foreground="#FF9800")  # Material orange
        
        self._log_prng_info("Ready to generate pseudo-random numbers...")
    
    # ==================== Internet API Methods ====================
    
    def _on_provider_changed(self, event=None):
        """Update UI fields based on selected provider."""
        # Save current provider settings before switching
        if hasattr(self, '_current_api_provider') and self._current_api_provider:
            self.api_provider_settings[self._current_api_provider] = {
                "length": self.api_length_var.get(),
                "data_type": self.api_data_type_var.get(),
                "block_size": self.api_block_size_var.get(),
                "api_key": self.api_key_var.get()
            }
        
        provider = self.api_provider_var.get()
        self._current_api_provider = provider
        
        # Restore settings for new provider
        settings = self.api_provider_settings.get(provider, {})
        self.api_length_var.set(settings.get("length", "1024"))
        self.api_key_var.set(settings.get("api_key", ""))
        
        # Provider-specific configurations
        if provider == "anu":
            # ANU supports all data types and block size; requires API key
            self.api_data_type_combo['values'] = ["uint8", "uint16", "hex16"]
            self.api_data_type_var.set("uint8")
            self.api_block_size_label.grid(row=2, column=0, sticky=W, pady=5, padx=5)
            self.api_block_size_entry.grid(row=2, column=1, sticky=W, pady=5, padx=5)
            # Block size only enabled for hex16
            self._update_block_size_state()
            self.api_key_label.grid(row=3, column=0, sticky=W, pady=5, padx=5)
            self.api_key_entry.grid(row=3, column=1, sticky=W, pady=5, padx=5)
            self.api_info_label.config(text="ℹ️ ANU: data_types=[uint8, uint16, hex16], max_length=1024, REQUIRES API KEY")
            # Bind data type change to update block size state
            self.api_data_type_combo.bind("<<ComboboxSelected>>", self._on_data_type_changed)
            
        elif provider == "random_org":
            # Random.org only supports uint8 and requires API key
            self.api_data_type_combo['values'] = ["uint8"]
            self.api_data_type_var.set("uint8")
            self.api_block_size_label.grid_forget()
            self.api_block_size_entry.grid_forget()
            self.api_key_label.grid(row=2, column=0, sticky=W, pady=5, padx=5)
            self.api_key_entry.grid(row=2, column=1, sticky=W, pady=5, padx=5)
            self.api_info_label.config(text="ℹ️ Random.org: data_type=[uint8], max_length=10000, REQUIRES API KEY")
            
        elif provider == "hotbits":
            # HotBits only supports uint8
            self.api_data_type_combo['values'] = ["uint8"]
            self.api_data_type_var.set("uint8")
            self.api_block_size_label.grid_forget()
            self.api_block_size_entry.grid_forget()
            self.api_key_label.grid_forget()
            self.api_key_entry.grid_forget()
            self.api_info_label.config(text="ℹ️ HotBits: data_type=[uint8], max_length=759, radioactive decay source")
    
    def _on_data_type_changed(self, event=None):
        """Update block size state when data type changes."""
        self._update_block_size_state()
    
    def _update_block_size_state(self):
        """Enable block size only for hex16 data type."""
        data_type = self.api_data_type_var.get()
        if data_type == "hex16":
            self.api_block_size_entry.config(state=NORMAL)
        else:
            self.api_block_size_entry.config(state=DISABLED)
            self.api_block_size_var.set("1")
    
    def _fetch_api_data(self):
        """Fetch data from selected API provider."""
        provider = self.api_provider_var.get()
        data_type = self.api_data_type_var.get()
        
        try:
            length = int(self.api_length_var.get())
        except ValueError:
            self._log_api_error("Please enter a valid length")
            return
        
        # Build kwargs based on provider
        kwargs = {"data_type": data_type}
        
        if provider == "anu":
            # Block size validation (only for hex16, must be 1-10)
            if data_type == "hex16":
                try:
                    block_size = int(self.api_block_size_var.get())
                    if block_size < 1 or block_size > 10:
                        self._log_api_error("Block size must be between 1 and 10")
                        return
                    kwargs["block_size"] = block_size
                except ValueError:
                    self._log_api_error("Block size must be an integer between 1 and 10")
                    return
            
            api_key = self.api_key_var.get()
            if not api_key:
                self._log_api_error("ANU QRNG requires an API key")
                return
            kwargs["api_key"] = api_key
                
        elif provider == "random_org":
            api_key = self.api_key_var.get()
            if not api_key:
                self._log_api_error("Random.org requires an API key")
                return
            kwargs["api_key"] = api_key
        
        # Disable fetch button during fetch
        self.api_fetch_btn.config(state=DISABLED)
        
        self._log_api_info(f"⏳ Fetching data from {provider}...")
        self._log_api_info(f"  Length: {length}, Data type: {data_type}")
        
        # Call manager to fetch API data
        result = self.manager.fetch_api_data(
            provider=provider,
            length=length,
            **kwargs
        )
        
        if result.ok:
            self._log_api_success(result.message)
        else:
            self._log_api_error(result.message)
    
    def _save_api_data(self):
        """Save API data to file."""
        if not self.api_data:
            self._log_api_warning("No API data to save. Fetch data first.")
            return
        
        # Create default filename with provider and timestamp
        provider = self.api_data.get('provider', 'api').lower()
        default_filename = f"{provider}_data.txt"
        
        filename = filedialog.asksaveasfilename(
            title="Save API Data",
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            try:
                data_list = self.api_data.get('data', [])
                with open(filename, 'w') as f:
                    f.write('\n'.join(map(str, data_list)))
                self._log_api_success(f"Saved {len(data_list)} values to: {filename}")
                
                # Add to report after successful save
                if self.report_tab:
                    report_data = {
                        'provider': provider.upper(),
                        'data_type': self.api_data.get('data_type', 'N/A'),
                        'length': len(data_list),
                        'output_file': Path(filename).name,
                        'status_text': 'Success'
                    }
                    self.report_tab.add_api_section(report_data)
            except Exception as e:
                self._log_api_error(f"Save error: {e}")
        else:
            self._log_api_warning("Save cancelled by user")
            return
    # ==================== EYL Device Methods ====================
    
    def _on_eyl_mode_changed(self, event=None):
        """Update UI fields based on selected EYL mode."""
        mode = self.eyl_mode_var.get()
        
        # Clear rate label when switching modes (only for offline mode)
        self.eyl_rate_label.config(text="")
        
        # Hide all mode-specific fields first
        self.eyl_filename_label.grid_forget()
        self.eyl_filename_entry.grid_forget()
        self.eyl_num_files_label.grid_forget()
        self.eyl_num_files_entry.grid_forget()
        self.eyl_progress.grid_forget()
        self.eyl_file_counter_label.grid_forget()
        self.eyl_max_files_label.grid_forget()
        self.eyl_single_file_progress.grid_forget()
        self.eyl_single_file_label.grid_forget()
        self.eyl_max_size_label.grid_forget()
        self.eyl_file_size_label.grid_forget()
        self.eyl_file_size_entry.grid_forget()
        self.eyl_output_format_label.grid_forget()
        self.eyl_output_format_combo.grid_forget()
        self.eyl_buffer_size_label.grid_forget()
        self.eyl_buffer_size_entry.grid_forget()
        self.eyl_buffer_max_label.grid_forget()
        self.eyl_pause_label.grid_forget()
        self.eyl_pause_entry.grid_forget()
        self.eyl_pause_note_label.grid_forget()
        self.eyl_save_display_check.grid_forget()
        self.eyl_network_label.grid_forget()
        self.eyl_network_combo.grid_forget()
        self.eyl_host_label.grid_forget()
        self.eyl_host_entry.grid_forget()
        self.eyl_port_label.grid_forget()
        self.eyl_port_entry.grid_forget()
        self.eyl_save_stream_check.grid_forget()
        self.eyl_send_termcode_check.grid_forget()
        
        # Hide save frame dynamic elements
        self.eyl_basename_label.grid_forget()
        self.eyl_basename_entry.grid_forget()
        self.eyl_timestamp_check.grid_forget()
        
        # Reset Save Data button state on mode change
        self.eyl_save_btn.config(state=DISABLED)
        
        if mode == "offline":
            # Show: filename, num_files, file_size, output_format
            # Files saved automatically - save path mandatory
            self.eyl_filename_label.grid(row=1, column=0, sticky=W, pady=5, padx=5)
            self.eyl_filename_entry.grid(row=1, column=1, sticky=W, pady=5, padx=5)
            self.eyl_num_files_label.grid(row=2, column=0, sticky=W, pady=5, padx=5)
            self.eyl_num_files_entry.grid(row=2, column=1, sticky=W, pady=5, padx=5)
            self.eyl_progress.grid(row=2, column=2, sticky=W, pady=5, padx=5)
            self.eyl_file_counter_label.grid(row=2, column=3, sticky=W, padx=2)
            self.eyl_max_files_label.grid(row=2, column=4, sticky=W, padx=2)
            self.eyl_file_size_label.grid(row=3, column=0, sticky=W, pady=5, padx=5)
            self.eyl_file_size_entry.grid(row=3, column=1, sticky=W, pady=5, padx=5)
            self.eyl_single_file_progress.grid(row=3, column=2, sticky=W, pady=5, padx=5)
            self.eyl_single_file_label.grid(row=3, column=3, sticky=W, padx=2)
            self.eyl_max_size_label.grid(row=3, column=4, sticky=W, padx=2)
            self.eyl_output_format_label.grid(row=4, column=0, sticky=W, pady=5, padx=5)
            self.eyl_output_format_combo.grid(row=4, column=1, sticky=W, pady=5, padx=5)
            self.eyl_info_label.config(text="ℹ️ Offline: Select save path, then Start")
            # Enable save path button in offline mode
            self.eyl_path_btn.config(state=NORMAL)
            # Clear labels
            self.eyl_transfer_label.config(text="")
            
        elif mode == "display":
            # Show: pause time, save displayed data checkbox (NO timestamp in display mode)
            self.eyl_pause_label.grid(row=1, column=0, sticky=W, pady=5, padx=5)
            self.eyl_pause_entry.grid(row=1, column=1, sticky=W, pady=5, padx=5)
            self.eyl_pause_note_label.grid(row=1, column=2, sticky=W, padx=5)            
            self.eyl_save_display_check.grid(row=2, column=0, columnspan=2, sticky=W, pady=5, padx=5)
            # Basename in generation frame (row 3) - visible but disabled until save checked
            self.eyl_basename_label.grid(row=3, column=0, sticky=W, pady=5, padx=5)
            self.eyl_basename_entry.grid(row=3, column=1, sticky=W, pady=5, padx=5)
            self.eyl_info_label.config(text="ℹ️ Display: Opens live data window")
            self.eyl_basename_var.set("eyl_displayed")
            # Display mode doesn't require save path - save path only for optional saving
            self.eyl_path_btn.config(state=DISABLED)
            self._on_save_display_changed()  # Update save options state
            
        elif mode == "stream":
            # Show: network settings, buffer_size, pause_time, save_stream checkbox with timestamp
            self.eyl_network_label.grid(row=1, column=0, sticky=W, pady=5, padx=5)
            self.eyl_network_combo.grid(row=1, column=1, sticky=W, pady=5, padx=5)
            self.eyl_port_label.grid(row=2, column=0, sticky=W, pady=5, padx=5)
            self.eyl_port_entry.grid(row=2, column=1, sticky=W, pady=5, padx=5)
            self.eyl_buffer_size_label.grid(row=4, column=0, sticky=W, pady=5, padx=5)
            self.eyl_buffer_size_entry.grid(row=4, column=1, sticky=W, pady=5, padx=5)
            self.eyl_buffer_max_label.grid(row=4, column=2, sticky=W, padx=5)
            self.eyl_pause_label.grid(row=5, column=0, sticky=W, pady=5, padx=5)
            self.eyl_pause_entry.grid(row=5, column=1, sticky=W, pady=5, padx=5)
            self.eyl_pause_note_label.grid(row=5, column=2, sticky=W, padx=5)
            # Termination code option
            self.eyl_send_termcode_check.grid(row=6, column=0, columnspan=3, sticky=W, pady=5, padx=5)
            # Save sent data on LEFT, Add timestamp on RIGHT (row 7)
            self.eyl_save_stream_check.grid(row=7, column=0, sticky=W, pady=5, padx=5)
            self.eyl_timestamp_check.grid(row=7, column=1, columnspan=2, sticky=W, pady=5, padx=5)
            # Basename in generation frame (row 8) - visible but disabled until save checked
            self.eyl_basename_label.grid(row=8, column=0, sticky=W, pady=5, padx=5)
            self.eyl_basename_entry.grid(row=8, column=1, sticky=W, pady=5, padx=5)
            self.eyl_info_label.config(text="ℹ️ Stream: TCP server for network clients")
            self.eyl_basename_var.set("eyl_stream")
            # Stream mode doesn't require save path - save path only for optional saving
            self.eyl_path_btn.config(state=DISABLED)
            self._on_eyl_network_changed()
            self._on_save_stream_changed()  # Update save options state
        
        # Update start button state based on mode change
        self._update_start_button_state()
    
    def _on_eyl_network_changed(self, event=None):
        """Update host field based on network selection."""
        network = self.eyl_network_var.get()
        
        if network == "localhost":
            self.eyl_host_var.set("127.0.0.1")
            self.eyl_host_label.grid_forget()
            self.eyl_host_entry.grid_forget()
        else:  # LAN (custom)
            self.eyl_host_var.set("192.168.1.1")
            self.eyl_host_label.grid(row=3, column=0, sticky=W, pady=5, padx=5)
            self.eyl_host_entry.grid(row=3, column=1, sticky=W, pady=5, padx=5)
    
    
    def _on_save_display_changed(self):
        """Toggle save options state based on save display checkbox."""
        if self.eyl_mode_var.get() != "display":
            return
        
        if self.eyl_save_display_var.get():
            # Enable basename entry and save path button (NO timestamp in display mode)
            self.eyl_basename_entry.config(state=NORMAL)
            self.eyl_path_btn.config(state=NORMAL)
        else:
            # Disable basename entry and save path button
            self.eyl_basename_entry.config(state=DISABLED)
            self.eyl_path_btn.config(state=DISABLED)
    
    def _on_save_stream_changed(self):
        """Toggle save options state based on save stream checkbox."""
        if self.eyl_mode_var.get() != "stream":
            return
        
        if self.eyl_save_stream_var.get():
            # Enable basename/timestamp entries and save path button
            self.eyl_basename_entry.config(state=NORMAL)
            self.eyl_timestamp_check.config(state=NORMAL)
            self.eyl_path_btn.config(state=NORMAL)
        else:
            # Disable basename/timestamp entries and save path button
            self.eyl_basename_entry.config(state=DISABLED)
            self.eyl_timestamp_check.config(state=DISABLED)
            self.eyl_path_btn.config(state=DISABLED)
    
    def _on_auto_retry_changed(self):
        """Toggle retry delay entry state based on auto-retry checkbox."""
        if self.eyl_auto_retry_var.get():
            self.eyl_retry_delay_entry.config(state=NORMAL)
        else:
            self.eyl_retry_delay_entry.config(state=DISABLED)
    
    def _update_start_button_state(self):
        """Update start button state based on current mode and connection."""
        if not self.eyl_connected_var.get():
            self.eyl_start_btn.config(state=DISABLED)
            return
        
        mode = self.eyl_mode_var.get()
        if mode == "offline":
            # Offline mode requires save path
            if self.eyl_save_path:
                self.eyl_start_btn.config(state=NORMAL)
            else:
                self.eyl_start_btn.config(state=DISABLED)
                self._log_eyl_info("Select save path to enable Start button")
        else:
            # Display and Stream modes don't require save path to start
            self.eyl_start_btn.config(state=NORMAL)
    
    def _toggle_eyl_connection(self):
        """Toggle EYL device connection (combines DLL check + connection)."""
        if self.eyl_connected_var.get():
            # First check DLL
            dll_result = self.manager.check_eyl_dll()
            if not dll_result.ok:
                self.eyl_connected_var.set(False)
                self.eyl_conn_status_label.config(text="DLL Not Found", foreground="red")
                self._log_eyl_error(f"DLL check failed: {dll_result.message}")
                self.eyl_start_btn.config(state=DISABLED)
                return
            
            # DLL OK, now try to connect to device
            result = self.manager.test_eyl_connection()
            if result.ok:
                self.eyl_conn_status_label.config(text="Connected", foreground="green")
                self._log_eyl_success("Connected to EYL device")
                # Enable start button based on mode
                self._update_start_button_state()
                # Start connection monitoring
                self._start_eyl_connection_monitor()
            else:
                self.eyl_connected_var.set(False)
                self.eyl_conn_status_label.config(text="Device Not Found", foreground="red")
                self._log_eyl_error(f"Connection failed: {result.message}")
                # Keep action buttons disabled
                self.eyl_start_btn.config(state=DISABLED)
        else:
            # Disconnect - stop any running generation first (like stop button)
            self._stop_eyl_connection_monitor()
            
            # Stop generation if running
            if self.manager.is_eyl_running():
                self._log_eyl_info("⏳ Stopping EYL generation due to disconnect...")
                self.manager.stop_eyl_generation()
            
            # Close display window if open
            mode = self.eyl_mode_var.get()
            if mode == "display" and hasattr(self, 'eyl_display_window') and self.eyl_display_window.winfo_exists():
                self.eyl_display_window.destroy()
            
            # Close stream file if open
            if hasattr(self, 'eyl_stream_file') and self.eyl_stream_file:
                try:
                    self.eyl_stream_file.close()
                except Exception:
                    pass
                self.eyl_stream_file = None
            
            # Now disconnect from device
            self.manager.disconnect_eyl()
            self.eyl_conn_status_label.config(text="Not Connected", foreground="orange")
            self._log_eyl_info("Disconnected from EYL device")
            
            # Clear rate/transfer labels
            self.eyl_rate_label.config(text="")
            self.eyl_transfer_label.config(text="")
            
            # Clear resume state
            self._eyl_offline_resume_state = None
            
            # Disable action buttons
            self.eyl_start_btn.config(state=DISABLED)
            self.eyl_stop_btn.config(state=DISABLED)
    
    def _start_eyl_connection_monitor(self):
        """Start periodic connection monitoring."""
        self._eyl_monitor_id = self.after(2000, self._check_eyl_connection)
    
    def _stop_eyl_connection_monitor(self):
        """Stop periodic connection monitoring."""
        if hasattr(self, '_eyl_monitor_id') and self._eyl_monitor_id:
            self.after_cancel(self._eyl_monitor_id)
            self._eyl_monitor_id = None
    
    def _check_eyl_connection(self):
        """Check EYL connection status periodically."""
        if not self.eyl_connected_var.get():
            return
        
        result = self.manager.test_eyl_connection()
        if not result.ok:
            # Connection lost - stop everything
            self._log_eyl_error(f"Connection lost: {result.message}")
            self.eyl_connected_var.set(False)
            self.eyl_conn_status_label.config(text="Disconnected", foreground="red")
            
            # Store current operation state for resume (don't stop completely)
            was_running = self.manager.is_eyl_running()
            current_mode = self.eyl_mode_var.get()
            
            if was_running:
                # Store operation state for resume
                self._eyl_resume_state = {
                    'mode': current_mode,
                    'was_running': True
                }
                # Pause generation (core will handle the pause)
                self._log_eyl_warning(f"Connection lost during {current_mode} mode - waiting for reconnection...")
            else:
                self._eyl_resume_state = None
            
            # Disable buttons
            self.eyl_start_btn.config(state=DISABLED)
            self.eyl_stop_btn.config(state=DISABLED)
            
            # Auto-retry if enabled (always try to reconnect and resume)
            if self.eyl_auto_retry_var.get():
                self._schedule_retry()
            else:
                # If auto-retry is disabled, stop the operation
                if was_running:
                    self.manager.stop_eyl_generation()
                    self._log_eyl_warning("Generation stopped due to disconnection")
                # Close display window if open
                if hasattr(self, 'eyl_display_window') and self.eyl_display_window.winfo_exists():
                    self.eyl_display_window.destroy()
        else:
            # Still connected - schedule next check
            self._eyl_monitor_id = self.after(2000, self._check_eyl_connection)
    
    def _auto_retry_connection(self):
        """Attempt to reconnect after disconnection and resume operation if needed."""
        if self.eyl_connected_var.get():
            return  # Already connected
        
        # First check DLL
        dll_result = self.manager.check_eyl_dll()
        if not dll_result.ok:
            self._log_eyl_warning(f"DLL check failed: {dll_result.message}")
            self._schedule_retry()  # Re-read delay and schedule next retry
            return
        
        self._log_eyl_info("Attempting to reconnect...")
        result = self.manager.test_eyl_connection()
        if result.ok:
            self.eyl_connected_var.set(True)
            self.eyl_conn_status_label.config(text="Connected", foreground="green")
            self._log_eyl_success("Reconnected to EYL device")
            self._update_start_button_state()
            self._start_eyl_connection_monitor()
            
            # Resume operation if we were running before disconnection
            if hasattr(self, '_eyl_resume_state') and self._eyl_resume_state:
                resume_mode = self._eyl_resume_state.get('mode')
                self._log_eyl_info(f"Resuming {resume_mode} mode operation...")
                self._eyl_resume_state = None
                
                if resume_mode == "display":
                    # For display mode, reopen window and continue
                    if not hasattr(self, 'eyl_display_window') or not self.eyl_display_window.winfo_exists():
                        self._create_display_window()
                    self._log_eyl_success("Display mode resumed - showing live data")
                elif resume_mode == "stream":
                    # For stream mode, just log - core will continue
                    self._log_eyl_success("Stream mode resumed - waiting for clients")
                elif resume_mode == "offline":
                    # For offline mode, core will continue from where it left off
                    self._log_eyl_success("Offline mode resumed - continuing file generation")
                
                # Re-enable stop button since we're still running
                self.eyl_stop_btn.config(state=NORMAL)
                self.eyl_start_btn.config(state=DISABLED)
        else:
            self._log_eyl_warning(f"Reconnection failed: {result.message}")
            self._schedule_retry()  # Re-read delay and schedule next retry
    
    def _schedule_retry(self):
        """Schedule next retry attempt, re-reading delay value from entry."""
        if not self.eyl_auto_retry_var.get():
            return
        try:
            delay = int(self.eyl_retry_delay_var.get())
            if delay < 100:
                delay = 100
            self._log_eyl_info(f"Retry in {delay}ms...")
            self.after(delay, self._auto_retry_connection)
        except ValueError:
            self._log_eyl_warning("Invalid retry delay, using 2000ms")
            self.after(2000, self._auto_retry_connection)
    
    def _browse_eyl_save_folder(self):
        """Browse for EYL save folder."""
        folder = filedialog.askdirectory(title="Select Save Folder")
        if folder:
            self.eyl_save_path = Path(folder)
            self.eyl_save_folder_var.set(folder)
            self._log_eyl_success(f"Save path set: {folder}")
            # Update start button state
            self._update_start_button_state()
        else:
            self._log_eyl_warning("Save path selection cancelled")
    
    def _start_eyl_generation(self):
        """Start EYL hardware generation."""
        # Check connection first
        if not self.eyl_connected_var.get():
            self._log_eyl_error("Please connect to EYL device first")
            return
        
        mode = self.eyl_mode_var.get()
        save_folder = self.eyl_save_folder_var.get().strip()
        
        try:
            if mode == "offline":
                base_filename = self.eyl_filename_var.get().strip()
                num_files = int(self.eyl_num_files_var.get())
                file_size_bits = int(self.eyl_file_size_var.get())
                
                if not base_filename:
                    self._log_eyl_error("Please enter a base filename")
                    return
                
                if not save_folder or not self.eyl_save_path:
                    self._log_eyl_error("Please select a save path first")
                    return
                
                # Validate limits: max 1000 files, max 1GB (8 billion bits) per file
                if num_files < 1 or num_files > 1000:
                    self._log_eyl_error("Number of files must be between 1 and 1000")
                    return
                
                max_size_bits = 8 * 1024 * 1024 * 1024  # 1GB in bits
                if file_size_bits < 8 or file_size_bits > max_size_bits:
                    self._log_eyl_error(f"File size must be between 8 bits and 1GB ({max_size_bits} bits)")
                    return
                
                # Build full base path
                full_base_path = str(self.eyl_save_path / base_filename)
                
                # Check if we have a resume state from previous stop
                start_from_file = 0
                if hasattr(self, '_eyl_offline_resume_state') and self._eyl_offline_resume_state:
                    resume = self._eyl_offline_resume_state
                    # Only resume if same config
                    if (resume['base_filename'] == base_filename and 
                        resume['file_size_bits'] == file_size_bits and
                        resume['total_files'] == num_files):
                        start_from_file = resume['completed_files']
                        self._log_eyl_info(f"⏳ Continuing EYL offline generation from file {start_from_file + 1}...")
                    else:
                        self._log_eyl_info(f"⏳ Starting EYL offline generation (config changed)...")
                    self._eyl_offline_resume_state = None
                else:
                    self._log_eyl_info(f"⏳ Starting EYL offline generation (adaptive buffer)...")
                
                remaining_files = num_files - start_from_file
                self._log_eyl_info(f"  Files: {remaining_files} remaining (of {num_files}), Size: {file_size_bits} bits")
                self._log_eyl_info(f"  Save to: {self.eyl_save_path}")
                
                # Set progress bars - show current progress
                self.eyl_progress['value'] = start_from_file
                self.eyl_progress['maximum'] = num_files
                self.eyl_file_counter_label.config(text=f"[{start_from_file}/{num_files}]")
                self.eyl_single_file_progress['value'] = 0
                self.eyl_single_file_progress['maximum'] = 100
                self.eyl_single_file_label.config(text="[0/0]")
                
                # Offline mode uses adaptive buffer algorithm - no pause_ms needed
                result = self.manager.start_eyl_offline(
                    base_filename=full_base_path,
                    num_files=num_files,
                    file_size_bits=file_size_bits,
                    start_from_file=start_from_file
                )
                
            elif mode == "display":
                pause_time = int(self.eyl_pause_var.get())
                
                # Validate pause time
                if pause_time < 0 or pause_time > 10000:
                    self._log_eyl_error("Pause time must be between 0 and 10000 ms")
                    return
                
                # Validate save path if saving enabled
                if self.eyl_save_display_var.get() and not self.eyl_save_path:
                    self._log_eyl_error("Please select a save path first")
                    return
                
                self._log_eyl_info(f"⏳ Starting EYL display mode...")
                if pause_time > 0:
                    self._log_eyl_info(f"  Pause time: {pause_time}ms")
                
                # Store save decision at start time
                self._eyl_should_save_display = self.eyl_save_display_var.get()
                
                # Initialize data accumulator only if saving enabled
                if self._eyl_should_save_display:
                    self.eyl_display_data = []
                    self._log_eyl_info(f"  Saving enabled to: {self.eyl_save_path}")
                else:
                    self.eyl_display_data = None
                
                # Create display window
                self._create_display_window()
                
                result = self.manager.start_eyl_display(pause_ms=pause_time)
                
            elif mode == "stream":
                host = self.eyl_host_var.get()
                port = int(self.eyl_port_var.get())
                buffer_size = int(self.eyl_buffer_size_var.get())
                pause_time = int(self.eyl_pause_var.get())
                
                # Validate buffer size
                if buffer_size < 1 or buffer_size > 16384:
                    self._log_eyl_error("Buffer size must be between 1 and 16384 bytes")
                    return
                
                # Validate pause time
                if pause_time < 0 or pause_time > 10000:
                    self._log_eyl_error("Pause time must be between 0 and 10000 ms")
                    return
                
                # Validate save path if saving enabled
                if self.eyl_save_stream_var.get() and not self.eyl_save_path:
                    self._log_eyl_error("Please select a save path first")
                    return
                
                self._log_eyl_info(f"⏳ Starting EYL stream mode...")
                self._log_eyl_info(f"  Host: {host}, Port: {port}, Buffer: {buffer_size}, Pause: {pause_time}ms")
                
                # Get termination code option
                send_termcode = self.eyl_send_termcode_var.get()
                if send_termcode:
                    self._log_eyl_info(f"  Termination code: enabled (1024 bytes of '1')")
                
                # Store save decision at start time - only save if checked before starting
                self._eyl_should_save_stream = self.eyl_save_stream_var.get()
                
                # Initialize stream data accumulator only if saving is enabled
                if self._eyl_should_save_stream:
                    self.eyl_stream_data = []
                    self._log_eyl_info(f"  Saving enabled to: {self.eyl_save_path}")
                else:
                    # Clear any previous stream data
                    self.eyl_stream_data = None
                
                # Clear transfer label
                self.eyl_transfer_label.config(text="")
                
                result = self.manager.start_eyl_stream(host=host, port=port, buffer_size=buffer_size, pause_ms=pause_time, send_termcode=send_termcode)
            
            if result.ok:
                self._log_eyl_success(result.message)
                # Update button states
                self.eyl_start_btn.config(state=DISABLED)
                self.eyl_stop_btn.config(state=NORMAL)
                self.eyl_save_btn.config(state=DISABLED)
            else:
                self._log_eyl_error(result.message)
                # Reset button states on error
                if self.eyl_connected_var.get():
                    self.eyl_start_btn.config(state=NORMAL)
                self.eyl_stop_btn.config(state=DISABLED)
                
        except ValueError as e:
            self._log_eyl_error(f"Invalid input: {e}")
    
    def _stop_eyl_generation(self):
        """Stop EYL hardware generation."""
        mode = self.eyl_mode_var.get()
        
        # Check if EYL is actually running
        if not self.manager.is_eyl_running():
            self._log_eyl_warning("No EYL generation is active")
            # Reset button states anyway
            if self.eyl_connected_var.get():
                self._update_start_button_state()
            self.eyl_stop_btn.config(state=DISABLED)
            return
        
        self._log_eyl_info("⏳ Stopping EYL generation...")
        
        # For offline mode, store current progress so we can continue later
        if mode == "offline":
            # Get current progress from labels
            counter_text = self.eyl_file_counter_label.cget("text")
            try:
                # Parse [completed/total] format
                completed = int(counter_text.split("/")[0].strip("["))
                total = int(counter_text.split("/")[1].strip("]"))
                if completed < total:
                    self._eyl_offline_resume_state = {
                        'completed_files': completed,
                        'total_files': total,
                        'base_filename': self.eyl_filename_var.get().strip(),
                        'file_size_bits': int(self.eyl_file_size_var.get())
                    }
                    self._log_eyl_info(f"  Progress saved: {completed}/{total} files completed")
                else:
                    self._eyl_offline_resume_state = None
            except (ValueError, IndexError):
                self._eyl_offline_resume_state = None
        
        # Close stream file if open
        if hasattr(self, 'eyl_stream_file') and self.eyl_stream_file:
            try:
                self.eyl_stream_file.close()
                self._log_eyl_success(f"Stream file closed: {getattr(self, 'eyl_stream_filename', 'unknown')}")
            except Exception:
                pass
            self.eyl_stream_file = None
        
        result = self.manager.stop_eyl_generation()
        
        if result.ok:
            self._log_eyl_success(result.message)
        else:
            self._log_eyl_error(f"Error: {result.message}")
        
        # Always reset button states after stop attempt
        if self.eyl_connected_var.get():
            self._update_start_button_state()
        self.eyl_stop_btn.config(state=DISABLED)
        
        # Clear rate label (for offline mode)
        self.eyl_rate_label.config(text="")
        
        # Auto-close display window on stop
        if mode == "display" and hasattr(self, 'eyl_display_window') and self.eyl_display_window.winfo_exists():
            self.eyl_display_window.destroy()
        
        # Enable save button only if save was enabled at start time and data exists
        should_save_display = getattr(self, '_eyl_should_save_display', False)
        should_save_stream = getattr(self, '_eyl_should_save_stream', False)
        
        if mode == "display" and should_save_display and hasattr(self, 'eyl_display_data') and self.eyl_display_data:
            self.eyl_save_btn.config(state=NORMAL)
        elif mode == "stream" and should_save_stream and hasattr(self, 'eyl_stream_data') and self.eyl_stream_data:
            self.eyl_save_btn.config(state=NORMAL)
    
    def _save_eyl_data(self):
        """Save EYL data - for display/stream mode accumulated data."""
        mode = self.eyl_mode_var.get()
        
        # Check for data based on mode
        if mode == "display":
            if not hasattr(self, 'eyl_display_data') or not self.eyl_display_data:
                self._log_eyl_error("No display data to save. Run display mode first.")
                return
            binary_string = ''.join(self.eyl_display_data)
        elif mode == "stream":
            if not hasattr(self, 'eyl_stream_data') or not self.eyl_stream_data:
                self._log_eyl_error("No stream data to save. Run stream mode first.")
                return
            binary_string = ''.join(self.eyl_stream_data)
        else:
            self._log_eyl_error("Save only available for display/stream modes")
            return
        
        # Get save folder and basename from UI
        basename = self.eyl_basename_var.get().strip()
        
        if not basename:
            basename = "eyl_data"
        
        # Use the mandatory save path
        if not self.eyl_save_path:
            self._log_eyl_error("No save path selected. Please select a save path first.")
            return
        save_folder = str(self.eyl_save_path)
        
        # Create filename - add timestamp only if checkbox is checked
        if self.eyl_timestamp_var.get():
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{basename}_{timestamp}.bin"
        else:
            filename = f"{basename}.bin"
        save_path = str(Path(save_folder) / filename)
        
        try:
            # Convert binary string to bytes
            if len(binary_string) > 0:
                bytes_data = int(binary_string, 2).to_bytes(len(binary_string) // 8, byteorder='big')
                
                with open(save_path, 'wb') as f:
                    f.write(bytes_data)
                
                self._log_eyl_success(f"Saved {len(bytes_data):,} bytes to: {Path(save_path).name}")
                self._log_eyl_info(f"  Total bits: {len(binary_string):,}")
                
                # Clear data after saving
                if mode == "display":
                    self.eyl_display_data = []
                elif mode == "stream":
                    self.eyl_stream_data = []
                self.eyl_save_btn.config(state=DISABLED)
            else:
                self._log_eyl_warning("No data to save")
            
        except Exception as e:
            self._log_eyl_error(f"Save error: {e}")
    
    def _save_eyl_file(self, filename: str, binary_string: str):
        """Save EYL binary data to file with format conversion."""
        try:
            # Get output format from UI
            output_format = self.eyl_output_format_var.get()
            
            # Determine file extension based on format
            ext_map = {
                "binary": ".bin", "string01": ".txt", "hex": ".txt",
                "uint8": ".txt", "uint16": ".txt", "uint32": ".txt", "uint64": ".txt"
            }
            extension = ext_map.get(output_format, ".bin")
            
            # Update filename extension
            base_path = Path(filename)
            final_path = base_path.with_suffix(extension)
            
            # Convert binary string to bytes
            bytes_data = int(binary_string, 2).to_bytes(len(binary_string) // 8, byteorder='big')
            
            if output_format == "binary":
                # Save as raw binary
                with open(final_path, 'wb') as f:
                    f.write(bytes_data)
            elif output_format == "string01":
                # Save as binary string (0s and 1s)
                with open(final_path, 'w') as f:
                    f.write(binary_string)
            elif output_format == "hex":
                # Save as hex string
                hex_string = bytes_data.hex()
                with open(final_path, 'w') as f:
                    f.write(hex_string)
            elif output_format in ("uint8", "uint16", "uint32", "uint64"):
                # Save as unsigned integers, one per line
                nbytes = {"uint8": 1, "uint16": 2, "uint32": 4, "uint64": 8}[output_format]
                uint_list = []
                for i in range(0, len(bytes_data), nbytes):
                    chunk = bytes_data[i:i+nbytes]
                    if len(chunk) < nbytes:
                        chunk = chunk.ljust(nbytes, b'\0')
                    uint_value = int.from_bytes(chunk, byteorder='big')
                    uint_list.append(str(uint_value))
                with open(final_path, 'w') as f:
                    f.write('\n'.join(uint_list))
        except Exception as e:
            self._log_eyl_error(f"Save error: {e}")
    
    def _create_display_window(self):
        """Create display window for EYL display mode."""
        self.eyl_display_window = tk.Toplevel(self)
        self.eyl_display_window.title("EYL Display Mode - Live Data Stream")
        self.eyl_display_window.geometry("700x450")
        
        # Handle window close as stop generation
        self.eyl_display_window.protocol("WM_DELETE_WINDOW", self._on_display_window_close)
        
        # Data display frame
        display_frame = ttk.LabelFrame(self.eyl_display_window, text="Binary Data Stream (8192 bits per update)", padding=10)
        display_frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # Text widget for displaying binary data
        self.eyl_display_text = tk.Text(
            display_frame,
            height=20,
            wrap=tk.CHAR,
            font=("Courier", 9),
            bg="#0a0a0a",
            fg="#00ff00",
            state=DISABLED
        )
        self.eyl_display_text.pack(side=LEFT, fill=BOTH, expand=YES)
        
        scrollbar = ttk.Scrollbar(display_frame, command=self.eyl_display_text.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.eyl_display_text.config(yscrollcommand=scrollbar.set)
        
        # Stats frame
        stats_frame = ttk.Frame(self.eyl_display_window, padding=5)
        stats_frame.pack(fill=X, padx=10, pady=5)
        
        self.eyl_display_stats = ttk.Label(stats_frame, text="Total bits received: 0 | Updates: 0", font=("Helvetica", 10))
        self.eyl_display_stats.pack()
        
        # Info label
        info_label = ttk.Label(
            self.eyl_display_window,
            text="ℹ️ Close window or use 'Stop Generation' button to stop and save data",
            font=("Helvetica", 9, "italic"),
            bootstyle="info"
        )
        info_label.pack(pady=5)
        
        # Initialize counters
        self.eyl_display_update_count = 0
    
    def _on_display_window_close(self):
        """Handle display window close - same as stop generation."""
        self._stop_eyl_generation()
        if hasattr(self, 'eyl_display_window') and self.eyl_display_window.winfo_exists():
            self.eyl_display_window.destroy()
    
    def _update_display(self, data_chunk: str):
        """Update display window with new 8192-bit data chunk."""
        if not hasattr(self, 'eyl_display_window') or not self.eyl_display_window.winfo_exists():
            return
        
        # Only accumulate data if save was enabled at start time
        should_save = getattr(self, '_eyl_should_save_display', False)
        if should_save and hasattr(self, 'eyl_display_data') and self.eyl_display_data is not None:
            self.eyl_display_data.append(data_chunk)
        
        self.eyl_display_update_count += 1
        
        # Update text display (show the current chunk)
        self.eyl_display_text.config(state=NORMAL)
        self.eyl_display_text.delete(1.0, tk.END)
        
        # Format binary data in 8-bit groups, 8 groups per line
        formatted_lines = []
        for i in range(0, len(data_chunk), 64):  # 64 bits = 8 bytes per line
            line = ' '.join([data_chunk[j:j+8] for j in range(i, min(i+64, len(data_chunk)), 8)])
            formatted_lines.append(line)
        
        formatted_data = '\n'.join(formatted_lines)
        self.eyl_display_text.insert(tk.END, formatted_data)
        self.eyl_display_text.config(state=DISABLED)
        
        # Update stats
        saved_bits = len(self.eyl_display_data) * 8192 if self.eyl_display_data else 0
        save_info = f" | Saved: {saved_bits:,} bits" if should_save else ""
        self.eyl_display_stats.config(text=f"Updates: {self.eyl_display_update_count}{save_info}")
    
    # ==================== PRNG Methods ====================
    
    def _choose_prng_save_path(self):
        """Choose folder for saving PRNG data."""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Folder to Save PRNG Data")
        if folder:
            self.prng_save_path = Path(folder)
            self.prng_save_path_var.set(str(self.prng_save_path))
            self._log_prng_success(f"Save path set: {self.prng_save_path}")
        else:
            self._log_prng_warning("Save path selection cancelled")
    
    def _generate_prng_data(self):
        """Generate pseudo-random data using DieHarder and save directly to files."""
        # Check save path
        if not self.prng_save_path:
            self._log_prng_error("Please choose a save path first")
            return
        
        # Validate inputs
        try:
            generator_id = int(self.prng_generator_id_var.get())
            seed = int(self.prng_seed_var.get())
            num_files = int(self.prng_num_files_var.get())
            size_per_file = int(self.prng_size_var.get())
        except ValueError:
            self._log_prng_error("Please enter valid numeric values")
            return
        
        # Validate limits
        if num_files < 1 or num_files > 1000:
            self._log_prng_error("Number of files must be between 1 and 1000")
            return
        
        if size_per_file < 1 or size_per_file > 268435456:  # max: 256M uint32
            self._log_prng_error("Count must be between 1 and 268435456")
            return
        
        # Get saving options
        include_header = self.prng_include_header_var.get()
        include_gen_id = self.prng_include_gen_id_var.get()
        include_seed = self.prng_include_seed_var.get()
        base_name = self.prng_base_name_var.get().strip() or "prng"
        
        # Get output format
        output_format = self.prng_output_format_var.get()
        
        # Disable generate button, enable stop button during generation
        self.prng_generate_btn.config(state=DISABLED)
        self.prng_path_btn.config(state=DISABLED)
        self.prng_stop_btn.config(state=NORMAL)
        
        # Reset progress bar
        self.prng_progress['value'] = 0
        
        self._log_prng_info(f"⏳ Generating PRNG data using DieHarder...")
        self._log_prng_info(f"  Generator ID: {generator_id}, Seed: {seed}")
        self._log_prng_info(f"  Files: {num_files}, Count: {size_per_file} uint32 values")
        self._log_prng_info(f"  Output format: {output_format}")
        self._log_prng_info(f"  Save path: {self.prng_save_path}")
        self._log_prng_info(f"  Include header: {include_header}")
        
        # Call manager with save path and filename options
        result = self.manager.generate_prng(
            generator_id=generator_id,
            seed=seed,
            save_path=str(self.prng_save_path),
            num_files=num_files,
            size_per_file=size_per_file,
            include_header=include_header,
            include_gen_id=include_gen_id,
            include_seed=include_seed,
            base_name=base_name,
            output_format=output_format
        )
        
        if result.ok:
            self._log_prng_success(result.message)
        else:
            self._log_prng_error(f"Error: {result.message}")
            # Re-enable buttons on error and hide progress bar
            self.prng_generate_btn.config(state=NORMAL)
            self.prng_path_btn.config(state=NORMAL)
            self.prng_stop_btn.config(state=DISABLED)
    
    # ==================== Event Handlers ====================
    
    def _on_qrng_completed(self, status: OperationStatus):
        """Handle QRNG data completion."""
        if status.payload:
            provider = status.payload.get("provider", "unknown")
            mode = status.payload.get("mode", "")
            
            if provider == "anu" or provider == "random_org" or provider == "hotbits":
                # API data - re-enable fetch button and enable save button
                self.api_fetch_btn.config(state=NORMAL)
                self.api_save_btn.config(state=NORMAL)
                self.api_data = status.payload
                self._log_api_success(f"Data received: {len(status.payload.get('data', []))} values")
                
            elif status.payload.get("provider") == "prng":
                # PRNG generation complete or stopped - update button states
                self.prng_generate_btn.config(state=NORMAL)
                self.prng_path_btn.config(state=NORMAL)
                self.prng_stop_btn.config(state=DISABLED)
                # Progress bar stays full after completion
                
                total_files = status.payload.get("total_files", 0)
                files_saved = status.payload.get("files_saved", 0)
                is_stopped = status.payload.get("stopped", False)
                save_path = status.payload.get("save_path", "")
                
                # Get values from GUI variables (more reliable than payload)
                generator_id = self.prng_generator_id_var.get() if hasattr(self, 'prng_generator_id_var') else "N/A"
                seed = self.prng_seed_var.get() if hasattr(self, 'prng_seed_var') else "N/A"
                size_per_file = self.prng_size_var.get() if hasattr(self, 'prng_size_var') else "N/A"
                
                if is_stopped:
                    self._log_prng_warning(f"PRNG generation stopped: {files_saved}/{total_files} files saved")
                else:
                    self._log_prng_success(f"PRNG generation complete: {files_saved}/{total_files} files saved")
                
                if save_path:
                    self._log_prng_info(f"  Files saved to: {save_path}")
                
                # Send to report tab
                if self.report_tab and files_saved > 0:
                    report_data = {
                        'generator': f"DieHarder ID {generator_id}",
                        'seed': seed,
                        'num_files': files_saved,
                        'size_per_file': f"{size_per_file} bytes",
                        'output_path': save_path,
                        'status_ok': not is_stopped,
                        'status_text': 'Stopped' if is_stopped else 'Success'
                    }
                    self.report_tab.add_prng_section(report_data)

            elif mode == "offline":
                event_type = status.payload.get("event", "")
                
                if event_type == "rate_update":
                    # Update rate label with adaptive algorithm stats
                    bytes_per_sec = status.payload.get("bytes_per_sec", 0)
                    bits_per_sec = status.payload.get("bits_per_sec", 0)
                    current_buffer = status.payload.get("current_buffer", 0)
                    current_pause = status.payload.get("current_pause_ms", 0)
                    
                    # Format rate display
                    if bytes_per_sec >= 1024:
                        rate_str = f"{bytes_per_sec/1024:.1f} KB/s"
                    else:
                        rate_str = f"{bytes_per_sec:.0f} B/s"
                    
                    pause_str = f" | Pause: {current_pause}ms" if current_pause > 0 else ""
                    self.eyl_rate_label.config(text=f"Rate: {rate_str} | Buf: {current_buffer}{pause_str}")
                    return
                
                elif event_type == "file_progress":
                    # Update single file progress bar and label
                    bytes_collected = status.payload.get("bytes_collected", 0)
                    file_size_bytes = status.payload.get("file_size_bytes", 0)
                    progress_pct = status.payload.get("progress_pct", 0)
                    file_index = status.payload.get("file_index", 0)
                    total_files = status.payload.get("total_files", 0)
                    
                    self.eyl_single_file_progress['value'] = progress_pct
                    
                    # Format bytes for display
                    if file_size_bytes >= 1024:
                        collected_str = f"{bytes_collected/1024:.1f}"
                        total_str = f"{file_size_bytes/1024:.1f}KB"
                    else:
                        collected_str = str(bytes_collected)
                        total_str = f"{file_size_bytes}B"
                    self.eyl_single_file_label.config(text=f"[{collected_str}/{total_str}]")
                    return
                
                elif event_type == "partial_save":
                    # Handle partial file save on disconnection
                    filename = status.payload.get("filename", "")
                    data = status.payload.get("data", "")
                    bytes_collected = status.payload.get("bytes_collected", 0)
                    
                    if data:
                        self._save_eyl_file(filename, data)
                        self._log_eyl_warning(f"Partial file saved ({bytes_collected} bytes): {filename}")
                    return
                
                # EYL offline mode - save file
                filename = status.payload.get("filename", "")
                data = status.payload.get("data", "")
                file_index = status.payload.get("file_index", 0)
                total_files = status.payload.get("total_files", 0)
                file_size_bits = status.payload.get("size_bits", 0)
                
                if data:
                    self._save_eyl_file(filename, data)
                    self._log_eyl_success(f"File {file_index}/{total_files} saved: {filename}")
                    
                    # Update file counter and progress bar
                    self.eyl_file_counter_label.config(text=f"[{file_index}/{total_files}]")
                    self.eyl_single_file_progress['value'] = 100
                    self.eyl_single_file_label.config(text="Complete")
                    
                    # Update progress bar
                    if total_files > 0:
                        progress_pct = (file_index / total_files) * 100
                        self.eyl_progress['value'] = progress_pct
                    
                    # When last file is saved, reset button states
                    if file_index == total_files:
                        self._log_eyl_success(f"Offline generation complete: {total_files} files saved")
                        # Reset button states - enable start if connected
                        if self.eyl_connected_var.get():
                            self.eyl_start_btn.config(state=NORMAL)
                        self.eyl_stop_btn.config(state=DISABLED)
                        # Clear rate label (progress bar stays full)
                        self.eyl_rate_label.config(text="")
                        
                        # Send to report tab
                        if self.report_tab:
                            # Get output path from EYL settings
                            output_path = self.eyl_save_path if hasattr(self, 'eyl_save_path') and self.eyl_save_path else 'N/A'
                            size_str = f"{file_size_bits} bits" if file_size_bits else 'N/A'
                            report_data = {
                                'mode': 'Offline',
                                'num_files': total_files,
                                'size_per_file': size_str,
                                'output_format': 'Binary',
                                'output_path': output_path,
                                'status_text': 'Success'
                            }
                            self.report_tab.add_eyl_section(report_data)
                    
            elif mode == "display":
                # EYL display mode - continuous data stream
                data_chunk = status.payload.get("data", "")
                
                if data_chunk:
                    # Update display window with new 8192-bit chunk
                    self._update_display(data_chunk)
                            
            elif mode == "stream":
                # EYL stream mode
                event_type = status.payload.get("event", "")
                
                if event_type == "client_connected":
                    client = status.payload.get("client_address", "")
                    self._log_eyl_success(f"Client connected: {client}")
                elif event_type == "stream_ended":
                    total_bytes = status.payload.get("total_bytes_sent", 0)
                    self._log_eyl_success(f"Stream ended. Total sent: {total_bytes} bytes")
                    self._log_eyl_info(f"  Termination message sent to client")
                    
                    # Send to report tab when stream ends
                    if self.report_tab:
                        host = status.payload.get("host", "127.0.0.1")
                        port = status.payload.get("port", 4000)
                        report_data = {
                            'mode': 'Stream',
                            'num_files': '-',
                            'size_per_file': f"{total_bytes} bytes",
                            'output_format': f"{host}:{port}",
                            'output_path': 'TCP Stream',
                            'status_text': 'Success'
                        }
                        self.report_tab.add_eyl_section(report_data)
                else:
                    # Regular stream data
                    data = status.payload.get("data", "")
                    total_bytes = status.payload.get("total_bytes_sent", 0)
                    
                    # Update transfer label
                    if total_bytes >= 1024 * 1024:
                        transfer_str = f"{total_bytes / (1024*1024):.2f} MB"
                    elif total_bytes >= 1024:
                        transfer_str = f"{total_bytes / 1024:.1f} KB"
                    else:
                        transfer_str = f"{total_bytes} B"
                    self.eyl_transfer_label.config(text=f"Sent: {transfer_str}")
                    
                    if total_bytes % 10000 < 1024:  # Log every ~10KB
                        self._log_eyl_info(f"  Streaming... {total_bytes} bytes sent")
                    
                    # Only save stream data if save was enabled at start time
                    should_save = getattr(self, '_eyl_should_save_stream', False)
                    if should_save and data and hasattr(self, 'eyl_stream_data') and self.eyl_stream_data is not None:
                        self.eyl_stream_data.append(data)
    
    def _on_qrng_failed(self, status: OperationStatus):
        """Handle QRNG operation failure."""
        error_msg = status.message
        # Determine which tab the error belongs to based on payload
        payload = status.payload or {}
        source = payload.get("source", "")
        
        if source == "api" or "api" in error_msg.lower():
            self.api_fetch_btn.config(state=NORMAL)  # Re-enable fetch button
            self._log_api_error(f"Error: {error_msg}")
        elif source == "eyl" or "eyl" in error_msg.lower():
            self._log_eyl_error(f"Error: {error_msg}")
            # Reset EYL button states on error
            if self.eyl_connected_var.get():
                self.eyl_start_btn.config(state=NORMAL)
            self.eyl_stop_btn.config(state=DISABLED)
            # Clear rate label
            self.eyl_rate_label.config(text="")
        elif source == "prng" or "prng" in error_msg.lower() or "dieharder" in error_msg.lower():
            self.prng_generate_btn.config(state=NORMAL)  # Re-enable generate button
            self.prng_stop_btn.config(state=DISABLED)  # Disable stop button
            self._log_prng_error(f"Error: {error_msg}")
        else:
            # If source is unclear, only log to the currently active tab
            current_tab = self.qrng_notebook.index(self.qrng_notebook.select())
            if current_tab == 0:
                self.api_fetch_btn.config(state=NORMAL)  # Re-enable fetch button
                self._log_api_error(f"Error: {error_msg}")
            elif current_tab == 1:
                self._log_eyl_error(f"Error: {error_msg}")
            else:
                self.prng_generate_btn.config(state=NORMAL)  # Re-enable generate button
                self.prng_stop_btn.config(state=DISABLED)  # Disable stop button
                self._log_prng_error(f"Error: {error_msg}")
    
    # ==================== Logging Methods ====================
    
    # API logging methods
    def _log_api(self, message: str):
        """Log to API status (alias for _log_api_info)."""
        self._log_api_info(message)
    
    def _log_api_success(self, message: str):
        """Log success message in green with checkmark."""
        self.api_status_text.config(state=NORMAL)
        self.api_status_text.insert(tk.END, f"✓ {message}\n", "success")
        self.api_status_text.see(tk.END)
        self.api_status_text.config(state=DISABLED)
    
    def _log_api_error(self, message: str):
        """Log error message in red with cross mark."""
        self.api_status_text.config(state=NORMAL)
        self.api_status_text.insert(tk.END, f"✗ {message}\n", "error")
        self.api_status_text.see(tk.END)
        self.api_status_text.config(state=DISABLED)
    
    def _log_api_warning(self, message: str):
        """Log warning message in orange with exclamation mark."""
        self.api_status_text.config(state=NORMAL)
        self.api_status_text.insert(tk.END, f"⚠ {message}\n", "warning")
        self.api_status_text.see(tk.END)
        self.api_status_text.config(state=DISABLED)
    
    def _log_api_info(self, message: str):
        """Log info message in default color."""
        self.api_status_text.config(state=NORMAL)
        self.api_status_text.insert(tk.END, f"{message}\n")
        self.api_status_text.see(tk.END)
        self.api_status_text.config(state=DISABLED)
    
    # EYL logging methods
    def _log_eyl(self, message: str):
        """Log to EYL status (alias for _log_eyl_info)."""
        self._log_eyl_info(message)
    
    def _log_eyl_success(self, message: str):
        """Log success message in green with checkmark."""
        self.eyl_status_text.config(state=NORMAL)
        self.eyl_status_text.insert(tk.END, f"✓ {message}\n", "success")
        self.eyl_status_text.see(tk.END)
        self.eyl_status_text.config(state=DISABLED)
    
    def _log_eyl_error(self, message: str):
        """Log error message in red with cross mark."""
        self.eyl_status_text.config(state=NORMAL)
        self.eyl_status_text.insert(tk.END, f"✗ {message}\n", "error")
        self.eyl_status_text.see(tk.END)
        self.eyl_status_text.config(state=DISABLED)
    
    def _log_eyl_warning(self, message: str):
        """Log warning message in orange with exclamation mark."""
        self.eyl_status_text.config(state=NORMAL)
        self.eyl_status_text.insert(tk.END, f"⚠ {message}\n", "warning")
        self.eyl_status_text.see(tk.END)
        self.eyl_status_text.config(state=DISABLED)
    
    def _log_eyl_info(self, message: str):
        """Log info message in default color."""
        self.eyl_status_text.config(state=NORMAL)
        self.eyl_status_text.insert(tk.END, f"{message}\n")
        self.eyl_status_text.see(tk.END)
        self.eyl_status_text.config(state=DISABLED)
    
    # PRNG logging methods
    def _log_prng(self, message: str):
        """Log to PRNG status (alias for _log_prng_info)."""
        self._log_prng_info(message)
    
    def _log_prng_success(self, message: str):
        """Log success message in green with checkmark."""
        self.prng_status_text.config(state=NORMAL)
        self.prng_status_text.insert(tk.END, f"✓ {message}\n", "success")
        self.prng_status_text.see(tk.END)
        self.prng_status_text.config(state=DISABLED)
    
    def _log_prng_error(self, message: str):
        """Log error message in red with cross mark."""
        self.prng_status_text.config(state=NORMAL)
        self.prng_status_text.insert(tk.END, f"✗ {message}\n", "error")
        self.prng_status_text.see(tk.END)
        self.prng_status_text.config(state=DISABLED)
    
    def _log_prng_warning(self, message: str):
        """Log warning message in orange with exclamation mark."""
        self.prng_status_text.config(state=NORMAL)
        self.prng_status_text.insert(tk.END, f"⚠ {message}\n", "warning")
        self.prng_status_text.see(tk.END)
        self.prng_status_text.config(state=DISABLED)
    
    def _log_prng_info(self, message: str):
        """Log info message in default color."""
        self.prng_status_text.config(state=NORMAL)
        self.prng_status_text.insert(tk.END, f"{message}\n")
        self.prng_status_text.see(tk.END)
        self.prng_status_text.config(state=DISABLED)
    
    def _log_prng_progress(self, message: str):
        """Log PRNG progress by replacing the last line."""
        self.prng_status_text.config(state=NORMAL)
        # Delete the last line and replace it
        self.prng_status_text.delete("end-2l", "end-1l")
        self.prng_status_text.insert(tk.END, f"{message}\n")
        self.prng_status_text.see(tk.END)
        self.prng_status_text.config(state=DISABLED)
    
    # ==================== Clear Status Methods ====================
    
    def _clear_api_status(self):
        """Reset API tab - clear status and entries, terminate any fetch."""
        # Terminate any running API fetch
        if self.manager.is_api_running():
            self.manager.stop_api_fetch()
            self._log_api("⚠ Fetch operation terminated")
        
        # Clear status
        self.api_status_text.config(state=NORMAL)
        self.api_status_text.delete('1.0', tk.END)
        self.api_status_text.insert(tk.END, "Ready to fetch quantum random data from Internet APIs...\n")
        self.api_status_text.config(state=DISABLED)
        
        # Reset all provider settings to defaults
        self.api_provider_settings = {
            "anu": {"length": "1024", "data_type": "uint8", "block_size": "1", "api_key": ""},
            "random_org": {"length": "1024", "data_type": "uint8", "block_size": "1", "api_key": ""},
            "hotbits": {"length": "759", "data_type": "uint8", "block_size": "1", "api_key": ""}
        }
        
        # Reset entries to defaults
        self.api_length_var.set("1024")
        self.api_data_type_var.set("uint8")
        self.api_block_size_var.set("1")
        self.api_key_var.set("")  # Clear API key
        self.api_provider_var.set("anu")
        self._current_api_provider = "anu"
        self._on_provider_changed()  # Update UI for default provider
        
        # Clear stored data
        self.api_data = None
        
        # Re-enable fetch button, disable save button
        self.api_fetch_btn.config(state=NORMAL)
        self.api_save_btn.config(state=DISABLED)
    
    def _clear_eyl_status(self):
        """Reset EYL tab - stop running, clear status, entries, and data."""
        # Stop connection monitoring first
        self._stop_eyl_connection_monitor()
        
        # Stop any running generation
        if self.manager.qrng.eyl.is_running():
            self.manager.stop_eyl_generation()
        
        # Disconnect from device
        self.manager.qrng.eyl.disconnect()
        
        # Close display window if open
        if hasattr(self, 'eyl_display_window') and self.eyl_display_window.winfo_exists():
            self.eyl_display_window.destroy()
        
        # Clear status
        self.eyl_status_text.config(state=NORMAL)
        self.eyl_status_text.delete('1.0', tk.END)
        self.eyl_status_text.insert(tk.END, "Ready to read from EYL quantum device...\n")
        self.eyl_status_text.config(state=DISABLED)
        
        # Reset entries to defaults
        self.eyl_mode_var.set("offline")
        self.eyl_filename_var.set("eyl_data")
        self.eyl_num_files_var.set("1")
        self.eyl_file_size_var.set("8192")
        self.eyl_output_format_var.set("binary")
        self.eyl_buffer_size_var.set("1024")
        self.eyl_pause_var.set("0")
        self.eyl_basename_var.set("eyl_data")
        self.eyl_timestamp_var.set(True)
        self.eyl_network_var.set("localhost")
        self.eyl_host_var.set("127.0.0.1")
        self.eyl_port_var.set("4000")
        self.eyl_save_stream_var.set(False)
        self.eyl_save_display_var.set(False)
        self.eyl_save_folder_var.set("")
        
        # Reset save path
        self.eyl_save_path = None
        
        # Reset progress bars
        self.eyl_progress['value'] = 0
        self.eyl_single_file_progress['value'] = 0
        self.eyl_file_counter_label.config(text="[0/0]")
        self.eyl_single_file_label.config(text="[0/0]")
        self.eyl_transfer_label.config(text="")
        
        # Reset auto-retry settings
        self.eyl_auto_retry_var.set(False)
        self.eyl_retry_delay_var.set("2000")
        self.eyl_retry_delay_entry.config(state=DISABLED)
        self.eyl_send_termcode_var.set(True)
        
        # Reset save decision flags
        self._eyl_should_save_display = False
        self._eyl_should_save_stream = False
        
        # Reset offline resume state
        self._eyl_offline_resume_state = None
        
        # Reset connection state
        self.eyl_connected_var.set(False)
        self.eyl_conn_status_label.config(text="Not Connected", foreground="orange")
        
        # Reset button states - all disabled until connected
        self.eyl_start_btn.config(state=DISABLED)
        self.eyl_stop_btn.config(state=DISABLED)
        self.eyl_save_btn.config(state=DISABLED)
        
        # Clear rate label
        self.eyl_rate_label.config(text="")
        
        # Update UI for default mode
        self._on_eyl_mode_changed()
        
        # Clear stored data
        self.eyl_data = None
        if hasattr(self, 'eyl_display_data'):
            self.eyl_display_data = []
        if hasattr(self, 'eyl_stream_data'):
            self.eyl_stream_data = []
    
    def _stop_prng_generation(self):
        """Stop PRNG generation - files already saved up to stop point."""
        if self.manager.is_prng_running():
            self.manager.stop_prng_generation()
            self._log_prng("⚠ Stopping PRNG generation...")
            # Note: completion event will update button states and show final count
    
    def _clear_prng_status(self):
        """Reset PRNG tab - stop any running generation, clear status and entries."""
        # Stop any running generation
        if self.manager.is_prng_running():
            self.manager.stop_prng_generation()
        
        # Clear status
        self.prng_status_text.config(state=NORMAL)
        self.prng_status_text.delete('1.0', tk.END)
        self.prng_status_text.insert(tk.END, "Ready to generate pseudo-random numbers...\n")
        self.prng_status_text.config(state=DISABLED)
        
        # Reset entries to defaults
        self.prng_generator_id_var.set("1")
        self.prng_seed_var.set("12345")
        self.prng_num_files_var.set("1")
        self.prng_size_var.set("10000")
        self.prng_output_format_var.set("uint32")
        
        # Reset all saving options to defaults
        self.prng_include_header_var.set(True)
        self.prng_include_gen_id_var.set(True)
        self.prng_include_seed_var.set(True)
        self.prng_base_name_var.set("prng")
        
        # Clear save path
        self.prng_save_path = None
        self.prng_save_path_var.set("No save path selected")
        
        # Reset button states (progress bar reset to 0)
        self.prng_generate_btn.config(state=NORMAL)
        self.prng_path_btn.config(state=NORMAL)
        self.prng_stop_btn.config(state=DISABLED)
        self.prng_progress['value'] = 0
