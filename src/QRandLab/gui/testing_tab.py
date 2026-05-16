# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Testing tab for running statistical tests (ENT, NIST, Dieharder)."""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from ..manager.core_manager import CoreManager
from ..core.types import OperationStatus, FileItem, FileType
from .test_settings import (ENTSettingsWindow, NISTSettingsWindow, DieharderSettingsWindow,
                             BorelSettingsWindow, AutocorrelationSettingsWindow)


class TestingTab(ttk.Frame):
    """Statistical testing tab."""
    
    def __init__(self, parent, manager: CoreManager):
        super().__init__(parent, padding=20)
        self.manager = manager
        self.report_tab = None  # Will be set by main_window
        
        # Test settings
        self.ent_settings = [0, 0, 0, 0]
        self.ent_save_raw = False
        self.ent_raw_output_path = ""
        self.nist_settings = [0] * 16
        self.nist_sequence_length = 1000000
        self.nist_use_whole = False
        self.nist_p_value_threshold = 0.01
        self.dieharder_settings = {
            'test_mode': 'specific',
            'selected_tests': [],
            'psamples': 100,
            'tentities': 10000,
            'multiplier': 1,
            'ntuple': 0,
            'ks_mode': 2,
            'weak_threshold': 0.005,
            'fail_threshold': 0.000001,
            'use_overlap': True,
            'test_strategy': 0,
            'reseed_strategy': 0,
            'save_raw_output': False,
            'raw_output_folder': ''
        }
        self.borel_settings = (1, 10)  # (min_length, max_length)
        self.borel_auto_mode = False  # Auto calculate max length
        self.autocorr_max_lag = 100
        self.autocorr_use_whole = False
        
        # Test running state
        self._test_running = False
        self._multi_file_mode = False  # Track if running multi-file test
        
        # Button references for enable/disable during tests
        self._test_buttons = []  # Will be populated in _build_ui
        
        # Progress tracking
        self._current_file_idx = 0
        self._total_files = 0
        
        self._setup_events()
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to manager events."""
        self.manager.on_file_loaded.subscribe(self._on_file_loaded)
        self.manager.on_file_metadata_updated.subscribe(self._on_metadata_updated)
        self.manager.on_file_cleared.subscribe(self._on_file_cleared)
        self.manager.tests.on_test.subscribe(self._on_test_completed)
        self.manager.on_operation_progress.subscribe(self._on_test_progress)
        self.manager.on_files_added.subscribe(self._on_files_changed)
        self.manager.on_files_removed.subscribe(self._on_files_changed)
        self.manager.on_file_type_changed.subscribe(self._on_files_changed)
        self.manager.on_files_cleared.subscribe(self._on_files_changed)
        self.manager.on_files_tested.subscribe(self._on_multi_test_completed)
    
    def _build_ui(self):
        """Build testing tab UI."""
        # Source Files Section
        source_frame = ttk.LabelFrame(self, text="Source Files", padding=15, bootstyle="info")
        source_frame.pack(fill=X, pady=(0, 15))
        
        ttk.Label(source_frame, text="Select Files:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, sticky=W, pady=5)
        self.file_selector_var = tk.StringVar(value="-- No files loaded --")
        self.file_selector = ttk.Combobox(
            source_frame,
            textvariable=self.file_selector_var,
            state="readonly",
            width=50
        )
        self.file_selector.grid(row=0, column=1, sticky=EW, padx=(10, 0), pady=5)
        
        # Auto-convert option
        self.auto_convert_var = tk.BooleanVar(value=False)
        auto_convert_check = ttk.Checkbutton(
            source_frame,
            text="Auto-convert to required format",
            variable=self.auto_convert_var,
            bootstyle="round-toggle"
        )
        auto_convert_check.grid(row=1, column=0, columnspan=2, sticky=W, pady=5)
        
        source_frame.columnconfigure(1, weight=1)
        
        # Legacy single-file vars for backward compatibility
        self.source_file_var = tk.StringVar(value="No file loaded")
        self.source_type_var = tk.StringVar(value="--")
        
        # Container for Tests and Actions side by side
        top_container = ttk.Frame(self)
        top_container.pack(fill=X, pady=(0, 10))
        top_container.columnconfigure(0, weight=1)
        top_container.columnconfigure(1, weight=1)
        top_container.columnconfigure(2, weight=0)
        
        # Column 1: NIST, Borel, Autocorr (string01 tests)
        col1_frame = ttk.LabelFrame(top_container, text="String01 Tests", padding=10, bootstyle="warning")
        col1_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # NIST - progress for 16 tests + file counter
        nist_container = ttk.Frame(col1_frame)
        nist_container.pack(fill=X, pady=3)
        ttk.Label(nist_container, text="NIST:", font=("Helvetica", 10, "bold"), width=12).pack(side=LEFT)
        btn_nist_settings = ttk.Button(nist_container, text="Settings", command=self._show_nist_settings, bootstyle="info-outline", width=8)
        btn_nist_settings.pack(side=LEFT, padx=2)
        btn_nist_run = ttk.Button(nist_container, text="Run", command=self._run_nist, bootstyle="success", width=8)
        btn_nist_run.pack(side=LEFT, padx=2)
        self.nist_progress = ttk.Progressbar(nist_container, length=120, mode='determinate', maximum=16, bootstyle="info-striped")
        self.nist_progress.pack(side=LEFT, padx=3)
        self.nist_test_label = ttk.Label(nist_container, text="[0/16]", font=("Helvetica", 9), bootstyle="info")
        self.nist_test_label.pack(side=LEFT, padx=2)
        self.nist_file_label = ttk.Label(nist_container, text="[0/0]", font=("Helvetica", 9), bootstyle="info")
        self.nist_file_label.pack(side=LEFT, padx=2)
        self._test_buttons.extend([btn_nist_settings, btn_nist_run])
        
        # Borel - progress for patterns + file counter
        borel_container = ttk.Frame(col1_frame)
        borel_container.pack(fill=X, pady=3)
        ttk.Label(borel_container, text="Borel:", font=("Helvetica", 10, "bold"), width=12).pack(side=LEFT)
        btn_borel_settings = ttk.Button(borel_container, text="Settings", command=self._show_borel_settings, bootstyle="info-outline", width=8)
        btn_borel_settings.pack(side=LEFT, padx=2)
        btn_borel_run = ttk.Button(borel_container, text="Run", command=self._run_borel, bootstyle="success", width=8)
        btn_borel_run.pack(side=LEFT, padx=2)
        self.borel_progress = ttk.Progressbar(borel_container, length=120, mode='determinate', maximum=10, bootstyle="info-striped")
        self.borel_progress.pack(side=LEFT, padx=3)
        self.borel_test_label = ttk.Label(borel_container, text="[0/0]", font=("Helvetica", 9), bootstyle="info")
        self.borel_test_label.pack(side=LEFT, padx=2)
        self.borel_file_label = ttk.Label(borel_container, text="[0/0]", font=("Helvetica", 9), bootstyle="info")
        self.borel_file_label.pack(side=LEFT, padx=2)
        self._test_buttons.extend([btn_borel_settings, btn_borel_run])
        
        # Autocorrelation - one test per file, just file counter
        autocorr_container = ttk.Frame(col1_frame)
        autocorr_container.pack(fill=X, pady=3)
        ttk.Label(autocorr_container, text="Autocorr:", font=("Helvetica", 10, "bold"), width=12).pack(side=LEFT)
        btn_autocorr_settings = ttk.Button(autocorr_container, text="Settings", command=self._show_autocorr_settings, bootstyle="info-outline", width=8)
        btn_autocorr_settings.pack(side=LEFT, padx=2)
        btn_autocorr_run = ttk.Button(autocorr_container, text="Run", command=self._run_autocorr, bootstyle="success", width=8)
        btn_autocorr_run.pack(side=LEFT, padx=2)
        self.autocorr_progress = ttk.Progressbar(autocorr_container, length=120, mode='determinate', bootstyle="info-striped")
        self.autocorr_progress.pack(side=LEFT, padx=3)
        self.autocorr_file_label = ttk.Label(autocorr_container, text="[0/0]", font=("Helvetica", 9), bootstyle="info")
        self.autocorr_file_label.pack(side=LEFT, padx=2)
        self._test_buttons.extend([btn_autocorr_settings, btn_autocorr_run])
        
        # Column 2: ENT, Dieharder (binary tests)
        col2_frame = ttk.LabelFrame(top_container, text="Binary Tests", padding=10, bootstyle="warning")
        col2_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 5))
        
        # ENT - one test per file, just file counter
        ent_container = ttk.Frame(col2_frame)
        ent_container.pack(fill=X, pady=3)
        ttk.Label(ent_container, text="ENT:", font=("Helvetica", 10, "bold"), width=12).pack(side=LEFT)
        btn_ent_settings = ttk.Button(ent_container, text="Settings", command=self._show_ent_settings, bootstyle="info-outline", width=8)
        btn_ent_settings.pack(side=LEFT, padx=2)
        btn_ent_run = ttk.Button(ent_container, text="Run", command=self._run_ent, bootstyle="success", width=8)
        btn_ent_run.pack(side=LEFT, padx=2)
        self.ent_progress = ttk.Progressbar(ent_container, length=120, mode='determinate', bootstyle="warning-striped")
        self.ent_progress.pack(side=LEFT, padx=3)
        self.ent_file_label = ttk.Label(ent_container, text="[0/0]", font=("Helvetica", 9), bootstyle="warning")
        self.ent_file_label.pack(side=LEFT, padx=2)
        self._test_buttons.extend([btn_ent_settings, btn_ent_run])
        
        # Dieharder - progress for tests per file + file counter
        dh_container = ttk.Frame(col2_frame)
        dh_container.pack(fill=X, pady=3)
        ttk.Label(dh_container, text="Dieharder:", font=("Helvetica", 10, "bold"), width=12).pack(side=LEFT)
        btn_dh_settings = ttk.Button(dh_container, text="Settings", command=self._show_dieharder_settings, bootstyle="info-outline", width=8)
        btn_dh_settings.pack(side=LEFT, padx=2)
        btn_dh_run = ttk.Button(dh_container, text="Run", command=self._run_dieharder, bootstyle="warning", width=8)
        btn_dh_run.pack(side=LEFT, padx=2)
        self.dh_progress = ttk.Progressbar(dh_container, length=120, mode='determinate', bootstyle="warning-striped")
        self.dh_progress.pack(side=LEFT, padx=3)
        self.dh_test_label = ttk.Label(dh_container, text="[0/0]", font=("Helvetica", 9), bootstyle="warning")
        self.dh_test_label.pack(side=LEFT, padx=2)
        self.dh_file_label = ttk.Label(dh_container, text="[0/0]", font=("Helvetica", 9), bootstyle="warning")
        self.dh_file_label.pack(side=LEFT, padx=2)
        self._test_buttons.extend([btn_dh_settings, btn_dh_run])
        
        # Actions column (right) - vertical buttons
        actions_frame = ttk.LabelFrame(top_container, text="Actions", padding=10, bootstyle="success")
        actions_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        
        # Reset button
        self._reset_btn = ttk.Button(actions_frame, text="Reset", command=self._reset_tab, bootstyle="secondary", width=12)
        self._reset_btn.pack(pady=5, anchor='n')

        # Stop button
        self._stop_btn = ttk.Button(actions_frame, text="STOP", command=self._stop_test, bootstyle="danger", width=12)
        self._stop_btn.pack(pady=5, anchor='n')
        
        # Results
        results_frame = ttk.LabelFrame(self, text="Test Results", padding=15, bootstyle="info")
        results_frame.pack(fill=BOTH, expand=YES)
        
        self.results_text = tk.Text(results_frame, wrap=tk.WORD, font=("Courier", 9), bg="#2b2b2b", fg="#ffffff", state=DISABLED)
        self.results_text.pack(side=LEFT, fill=BOTH, expand=YES)
        
        # Configure text tags for colored output (colors visible in both dark and light themes)
        self.results_text.tag_configure("pass", foreground="#4CAF50")  # Material green
        self.results_text.tag_configure("fail", foreground="#F44336")  # Material red
        self.results_text.tag_configure("weak", foreground="#FF9800")  # Material orange
        self.results_text.tag_configure("success", foreground="#4CAF50")  # Material green
        self.results_text.tag_configure("error", foreground="#F44336")    # Material red
        self.results_text.tag_configure("warning", foreground="#FF9800")  # Material orange
        
        scrollbar = ttk.Scrollbar(results_frame, command=self.results_text.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.results_text.config(yscrollcommand=scrollbar.set)
        
        self._log_info("Ready to run tests...")
    
    def _on_file_loaded(self, status: OperationStatus):
        """Update UI when file is loaded."""
        if status.ok:
            self._update_ui_from_meta()
    
    def _on_metadata_updated(self, status: OperationStatus):
        """Update UI when file metadata changes."""
        if status.ok:
            self._update_ui_from_meta()
    
    def _on_file_cleared(self, status: OperationStatus):
        """Update UI when file is cleared."""
        self.source_file_var.set("No file loaded")
        self.source_type_var.set("--")
    
    def _update_ui_from_meta(self):
        """Update UI elements from current metadata."""
        meta = self.manager.input_meta
        if meta.file_path:
            file_name = f"{meta.file_name}{meta.file_ext.value if meta.file_ext else ''}"
            self.source_file_var.set(file_name)
            self.source_type_var.set(meta.file_type.value if meta.file_type else "--")
        else:
            self.source_file_var.set("No file loaded")
            self.source_type_var.set("--")
        self._update_file_selector()
    
    def _on_files_changed(self, status: OperationStatus):
        """Handle files added/removed events."""
        self._update_file_selector()
    
    def _update_file_selector(self):
        """Update file selector dropdown with current files."""
        files = self.manager.get_all_files()
        if not files:
            self.file_selector['values'] = ["-- No files loaded --"]
            self.file_selector_var.set("-- No files loaded --")
        else:
            options = ["-- All Files --"]
            for f in files:
                display = f"{f.file_name}{f.file_ext.value}" if f.file_ext else f.file_name
                type_str = f" [{f.file_type.value}]" if f.file_type else " [type not set]"
                options.append(f"{display}{type_str}")
            self.file_selector['values'] = options
            if self.file_selector_var.get() not in options:
                self.file_selector_var.set("-- All Files --")
    
    def _get_files_to_test(self):
        """Get list of FileItems to test based on selection."""
        selected = self.file_selector_var.get()
        if selected == "-- No files loaded --":
            return []
        if selected == "-- All Files --":
            return self.manager.get_all_files()
        # Single file selected - parse name
        files = self.manager.get_all_files()
        for f in files:
            display = f"{f.file_name}{f.file_ext.value}" if f.file_ext else f.file_name
            if selected.startswith(display):
                return [f]
        return []
    
    def _on_multi_test_completed(self, status: OperationStatus):
        """Handle multi-file test completion."""
        self.after(0, self._set_buttons_state, True)
        self._test_running = False
        self._multi_file_mode = False
        
        if status.ok and status.payload:
            results = status.payload.get('results', [])
            test_name = status.payload.get('test_name', '')
            success_count = status.payload.get('success_count', 0)
            fail_count = status.payload.get('fail_count', 0)
            
            self._log_success(f"Multi-file {test_name} test complete: {success_count} succeeded, {fail_count} failed")
            
            for r in results:
                if r.get('ok'):
                    self._log_info(f"  ✓ {r['file_name']}")
                else:
                    self._log_warning(f"  ✗ {r['file_name']}: {r.get('message', 'Unknown error')}")
        else:
            self._log_error(f"Multi-file test failed: {status.message}")
    
    def _on_test_completed(self, status: OperationStatus):
        """Handle test completion."""
        # Only re-enable buttons if not in multi-file mode (wait for _on_multi_test_completed)
        if not self._multi_file_mode:
            self.after(0, self._set_buttons_state, True)
            self._test_running = False
        
        if status.ok:
            self._log_success("Test completed!")
            if status.payload:
                test_type = status.payload.get('test_type', '')
                
                # Update file counter for this test type
                self._current_file_idx += 1
                self.after(0, lambda t=test_type: self._update_file_counter(t))
                
                # Format status display based on test type
                if test_type == 'ENT':
                    self._display_ent_status(status.payload)
                    self._wire_ent_report(status.payload)
                elif test_type == 'Borel':
                    self._display_borel_status(status.payload)
                    self._wire_borel_report(status.payload)
                elif test_type == 'NIST':
                    self._display_nist_status(status.payload)
                    self._wire_nist_report(status.payload)
                elif test_type == 'Autocorrelation':
                    self._display_autocorr_status(status.payload)
                    self._wire_autocorr_report(status.payload)
                elif test_type == 'DieHarder':
                    self._display_dieharder_status(status.payload)
                    self._wire_dieharder_report(status.payload)
                else:
                    self._log_info(str(status.payload))
        else:
            self._log_error(f"Test failed: {status.message}")
    
    def _update_file_counter(self, test_type: str):
        """Update file counter label and progress bar for the given test type."""
        if test_type == 'ENT':
            self.ent_progress['value'] = self._current_file_idx
            self.ent_file_label.config(text=f"[{self._current_file_idx}/{self._total_files}]")
        elif test_type == 'NIST':
            self.nist_file_label.config(text=f"[{self._current_file_idx}/{self._total_files}]")
            # Reset test progress for next file
            self.nist_progress['value'] = 0
        elif test_type == 'Borel':
            self.borel_file_label.config(text=f"[{self._current_file_idx}/{self._total_files}]")
            # Reset pattern progress for next file
            self.borel_progress['value'] = 0
        elif test_type == 'Autocorrelation':
            self.autocorr_progress['value'] = self._current_file_idx
            self.autocorr_file_label.config(text=f"[{self._current_file_idx}/{self._total_files}]")
        elif test_type == 'DieHarder':
            self.dh_file_label.config(text=f"[{self._current_file_idx}/{self._total_files}]")
            # Reset test progress for next file
            self.dh_progress['value'] = 0
    
    def _on_test_progress(self, status: OperationStatus):
        """Handle test progress updates (e.g., dieharder individual test completion)."""
        if not status.ok:
            return
        
        payload = status.payload
        if not payload:
            return
        
        test_type = payload.get('test_type', '')
        if test_type == 'DieHarder':
            # Display progress for dieharder with colored assessment
            completed = payload.get('completed', 0)
            total = payload.get('total', 0)
            test_name = payload.get('test_name', 'Unknown')
            assessment = payload.get('assessment', 'UNKNOWN')
            
            # Update progress bar and label
            self.after(0, lambda c=completed, t=total: self._update_dh_progress(c, t))
            
            # Build progress message - assessment will be colored
            msg_prefix = f"  [{completed}/{total}] {test_name}: "
            
            # Determine color based on assessment
            if assessment == 'PASSED':
                status_type = 'pass'
            elif assessment == 'FAILED':
                status_type = 'fail'
            else:
                status_type = 'weak'
            
            # Use after() to update UI from event thread with colored status
            self.after(0, lambda p=msg_prefix, a=assessment, s=status_type: self._log_result_with_status(p, a, s))
        
        elif test_type == 'Borel':
            # Display dynamic progress for Borel (single-line update)
            completed = payload.get('completed', 0)
            total = payload.get('total', 0)
            message = payload.get('message', '')
            
            # Update progress bar and label
            self.after(0, lambda c=completed, t=total: self._update_borel_progress_bar(c, t))
            
            # Update single line dynamically
            self.after(0, lambda c=completed, t=total, m=message: self._update_borel_progress(c, t, m))
        
        elif test_type == 'NIST':
            # NIST progress - update per test completed
            completed = payload.get('completed', 0)
            total = payload.get('total', 0)
            self.after(0, lambda c=completed, t=total: self._update_nist_progress(c, t))
    
    def _update_nist_progress(self, completed: int, total: int):
        """Update NIST progress bar and label."""
        self.nist_progress['maximum'] = total
        self.nist_progress['value'] = completed
        self.nist_test_label.config(text=f"[{completed}/{total}]")
    
    def _update_borel_progress_bar(self, completed: int, total: int):
        """Update Borel progress bar and label."""
        self.borel_progress['maximum'] = total
        self.borel_progress['value'] = completed
        self.borel_test_label.config(text=f"[{completed}/{total}]")
    
    def _update_dh_progress(self, completed: int, total: int):
        """Update Dieharder progress bar and label."""
        self.dh_progress['maximum'] = total
        self.dh_progress['value'] = completed
        self.dh_test_label.config(text=f"[{completed}/{total}]")
    
    def _update_borel_progress(self, completed: int, total: int, message: str):
        """Update Borel progress on a single line (overwriting previous)."""
        self.results_text.config(state=NORMAL)
        # Delete last line if it's a Borel progress line
        last_line_start = self.results_text.index("end-2l linestart")
        last_line_content = self.results_text.get(last_line_start, "end-1c")
        if "Borel:" in last_line_content and "[" in last_line_content:
            self.results_text.delete(last_line_start, "end-1c")
        # Insert new progress line
        self.results_text.insert(tk.END, f"  Borel: [{completed}/{total}] {message} done\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=DISABLED)
    
    def _set_buttons_state(self, enabled: bool):
        """Enable or disable all test buttons.
        
        Args:
            enabled: True to enable buttons, False to disable
        """
        state = NORMAL if enabled else DISABLED
        for btn in self._test_buttons:
            btn.config(state=state)
    
    def _show_ent_settings(self):
        """Show ENT settings."""
        # Generate default folder path based on input file
        default_path = self.ent_raw_output_path
        if not default_path and self.manager.input_meta.file_path:
            input_path = Path(self.manager.input_meta.file_path)
            default_path = str(input_path.parent)
        
        dialog = ENTSettingsWindow(
            self, self.ent_settings, 
            save_raw=self.ent_save_raw, 
            raw_output_path=default_path
        )
        result = dialog.show()
        if result is not None:
            self.ent_settings = result["states"]
            self.ent_save_raw = result["save_raw"]
            self.ent_raw_output_path = result["raw_output_path"]
            
            options = []
            if self.ent_settings[0]: options.append("Bit stream")
            if self.ent_settings[1]: options.append("Occurrence count")
            if self.ent_settings[2]: options.append("Fold")
            if self.ent_settings[3]: options.append("CSV output")
            if options:
                self._log_info(f"ENT test set: {', '.join(options)}")
            else:
                self._log_info("ENT test set: Default options")
            if self.ent_save_raw:
                self._log_info(f"Raw output will be saved to: {self.ent_raw_output_path}")
        else:
            self._log_warning("ENT test not set")
    
    def _show_nist_settings(self):
        """Show NIST settings."""
        dialog = NISTSettingsWindow(self, self.nist_settings, self.nist_sequence_length, self.nist_use_whole, self.nist_p_value_threshold)
        result = dialog.show()
        if result is not None:
            self.nist_settings, self.nist_sequence_length, self.nist_use_whole, self.nist_p_value_threshold = result
            test_count = sum(self.nist_settings)
            seq_info = "whole data" if self.nist_use_whole else f"seq_len={self.nist_sequence_length}"
            self._log_info(f"NIST test set: {test_count}/16 tests, {seq_info}, p-value={self.nist_p_value_threshold}")
        else:
            self._log_warning("NIST test not set")
    
    def _show_dieharder_settings(self):
        """Show Dieharder settings."""
        dialog = DieharderSettingsWindow(self, self.dieharder_settings)
        result = dialog.show()
        if result is not None:
            self.dieharder_settings = result
            # Build summary message - only show test count
            if result['test_mode'] == 'all':
                self._log_info("Dieharder settings: All 32 tests")
            else:
                test_count = len(result['selected_tests'])
                self._log_info(f"Dieharder settings: {test_count} tests selected")
        else:
            self._log_warning("Dieharder settings not set")
    
    def _run_ent(self):
        """Run ENT test."""
        files_to_test = self._get_files_to_test()
        if not files_to_test:
            self._log_warning("No files to test. Please load files first.")
            return
        
        # Filter out files without file type set
        valid_files = [f for f in files_to_test if f.file_type is not None]
        skipped = len(files_to_test) - len(valid_files)
        if skipped > 0:
            self._log_warning(f"Skipping {skipped} file(s) with no type set")
        if not valid_files:
            self._log_warning("No files with type set. Please set file types first.")
            return
        files_to_test = valid_files
        
        # Disable buttons during test
        self._set_buttons_state(False)
        self._test_running = True
        self._multi_file_mode = len(files_to_test) > 1
        
        # Build test config
        test_config = {
            'binary': self.ent_settings[0] == 1,
            'chi_square': bool(self.ent_settings[1]),
            'fold': bool(self.ent_settings[2]),
            'terse': bool(self.ent_settings[3])
        }
        auto_convert = self.auto_convert_var.get()
        
        self._log_info(f"⏳ Running ENT test on {len(files_to_test)} file(s)...")
        
        # Initialize progress for ENT (one test per file)
        self._total_files = len(files_to_test)
        self._current_file_idx = 0
        self.ent_progress['maximum'] = self._total_files
        self.ent_progress['value'] = 0
        self.ent_file_label.config(text=f"[0/{self._total_files}]")
        
        # Run multi-file test
        result = self.manager.run_test_on_files(files_to_test, "ent", auto_convert, test_config)
        if not result.ok:
            self._set_buttons_state(True)
            self._test_running = False
            self._log_error(f"Failed to start test: {result.message}")
    
    def _run_nist(self):
        """Run NIST test."""
        files_to_test = self._get_files_to_test()
        if not files_to_test:
            self._log_warning("No files to test. Please load files first.")
            return
        
        # Filter out files without file type set
        valid_files = [f for f in files_to_test if f.file_type is not None]
        skipped = len(files_to_test) - len(valid_files)
        if skipped > 0:
            self._log_warning(f"Skipping {skipped} file(s) with no type set")
        if not valid_files:
            self._log_warning("No files with type set. Please set file types first.")
            return
        files_to_test = valid_files
        
        # Disable buttons during test
        self._set_buttons_state(False)
        self._test_running = True
        self._multi_file_mode = len(files_to_test) > 1
        
        # Build test config
        test_config = {
            'enabled_tests': self.nist_settings,
            'sequence_length': self.nist_sequence_length,
            'use_whole_data': self.nist_use_whole,
            'verbose': 1,
            'p_value_threshold': self.nist_p_value_threshold
        }
        auto_convert = self.auto_convert_var.get()
        
        self._log_info(f"⏳ Running NIST test on {len(files_to_test)} file(s)...")
        
        # Initialize progress for NIST
        self._total_files = len(files_to_test)
        self._current_file_idx = 0
        num_tests = sum(self.nist_settings)
        self.nist_progress['maximum'] = num_tests if num_tests > 0 else 16
        self.nist_progress['value'] = 0
        self.nist_test_label.config(text=f"[0/{num_tests if num_tests > 0 else 16}]")
        self.nist_file_label.config(text=f"[0/{self._total_files}]")
        
        # Run multi-file test
        result = self.manager.run_test_on_files(files_to_test, "nist", auto_convert, test_config)
        if not result.ok:
            self._set_buttons_state(True)
            self._test_running = False
            self._log_error(f"Failed to start test: {result.message}")
    
    def _run_dieharder(self):
        """Run Dieharder test."""
        files_to_test = self._get_files_to_test()
        if not files_to_test:
            self._log_warning("No files to test. Please load files first.")
            return
        
        # Filter out files without file type set
        valid_files = [f for f in files_to_test if f.file_type is not None]
        skipped = len(files_to_test) - len(valid_files)
        if skipped > 0:
            self._log_warning(f"Skipping {skipped} file(s) with no type set")
        if not valid_files:
            self._log_warning("No files with type set. Please set file types first.")
            return
        files_to_test = valid_files
        
        # Show warning only if running all tests
        if self.dieharder_settings.get('test_mode') == 'all':
            response = messagebox.askyesno(
                "Confirm",
                "Running all 32 Dieharder tests may take 30-60 minutes per file.\n\nContinue?"
            )
            if not response:
                return
        
        # Disable buttons during test
        self._set_buttons_state(False)
        self._test_running = True
        self._multi_file_mode = len(files_to_test) > 1
        
        auto_convert = self.auto_convert_var.get()
        
        self._log_info(f"⏳ Running Dieharder test on {len(files_to_test)} file(s)...")
        
        # Initialize progress for Dieharder
        self._total_files = len(files_to_test)
        self._current_file_idx = 0
        num_tests = len(self.dieharder_settings.get('selected_tests', []))
        if self.dieharder_settings.get('test_mode') == 'all':
            num_tests = 32
        self.dh_progress['maximum'] = num_tests if num_tests > 0 else 1
        self.dh_progress['value'] = 0
        self.dh_test_label.config(text=f"[0/{num_tests if num_tests > 0 else 0}]")
        self.dh_file_label.config(text=f"[0/{self._total_files}]")
        
        # Run multi-file test
        result = self.manager.run_test_on_files(files_to_test, "dieharder", auto_convert, self.dieharder_settings)
        if not result.ok:
            self._set_buttons_state(True)
            self._test_running = False
            self._log_error(f"Failed to start test: {result.message}")
    
    def _show_borel_settings(self):
        """Show Borel test settings."""
        dialog = BorelSettingsWindow(
            self, 
            min_length=self.borel_settings[0], 
            max_length=self.borel_settings[1],
            auto_mode=self.borel_auto_mode
        )
        result = dialog.show()
        if result is not None:
            min_len, max_len, auto_mode = result
            self.borel_settings = (min_len, max_len)
            self.borel_auto_mode = auto_mode
            max_info = "auto" if auto_mode else str(max_len)
            self._log_info(f"Borel test set: min={min_len}, max={max_info}")
        else:
            self._log_warning("Borel test not set")
    
    def _run_borel(self):
        """Run Borel test."""
        files_to_test = self._get_files_to_test()
        if not files_to_test:
            self._log_warning("No files to test. Please load files first.")
            return
        
        # Disable buttons during test
        self._set_buttons_state(False)
        self._test_running = True
        self._multi_file_mode = len(files_to_test) > 1
        
        # Build test config
        test_config = {
            'min_pattern_length': self.borel_settings[0],
            'max_pattern_length': self.borel_settings[1],
            'auto_mode': self.borel_auto_mode
        }
        auto_convert = self.auto_convert_var.get()
        
        max_display = "Auto" if self.borel_auto_mode else str(self.borel_settings[1])
        self._log_info(f"⏳ Running Borel test on {len(files_to_test)} file(s)...")
        self._log_info(f"Pattern range: {self.borel_settings[0]} to {max_display}")
        
        # Initialize progress for Borel
        self._total_files = len(files_to_test)
        self._current_file_idx = 0
        num_patterns = self.borel_settings[1] - self.borel_settings[0] + 1
        self.borel_progress['maximum'] = num_patterns
        self.borel_progress['value'] = 0
        self.borel_test_label.config(text=f"[0/{num_patterns}]")
        self.borel_file_label.config(text=f"[0/{self._total_files}]")
        
        # Run multi-file test
        result = self.manager.run_test_on_files(files_to_test, "borel", auto_convert, test_config)
        if not result.ok:
            self._set_buttons_state(True)
            self._test_running = False
            self._log_error(f"Failed to start test: {result.message}")
    
    def _show_autocorr_settings(self):
        """Show Autocorrelation test settings."""
        dialog = AutocorrelationSettingsWindow(self, max_lag=self.autocorr_max_lag, use_whole_data=self.autocorr_use_whole)
        result = dialog.show()
        if result is not None:
            self.autocorr_max_lag, self.autocorr_use_whole = result
            lag_info = "whole data" if self.autocorr_use_whole else f"max_lag={self.autocorr_max_lag}"
            self._log_info(f"Autocorrelation test set: {lag_info}")
        else:
            self._log_warning("Autocorrelation test not set")
    
    def _run_autocorr(self):
        """Run Autocorrelation test."""
        files_to_test = self._get_files_to_test()
        if not files_to_test:
            self._log_warning("No files to test. Please load files first.")
            return
        
        # Disable buttons during test
        self._set_buttons_state(False)
        self._test_running = True
        self._multi_file_mode = len(files_to_test) > 1
        
        # Build test config
        test_config = {
            'nlags': self.autocorr_max_lag,
            'generate_plot': True,
            'use_whole_data': self.autocorr_use_whole
        }
        auto_convert = self.auto_convert_var.get()
        
        self._log_info(f"⏳ Running Autocorrelation test on {len(files_to_test)} file(s)...")
        if self.autocorr_use_whole:
            self._log_info("Using whole data for autocorrelation")
        else:
            self._log_info(f"Maximum lag: {self.autocorr_max_lag}")
        
        # Initialize progress for Autocorr (one test per file)
        self._total_files = len(files_to_test)
        self._current_file_idx = 0
        self.autocorr_progress['maximum'] = self._total_files
        self.autocorr_progress['value'] = 0
        self.autocorr_file_label.config(text=f"[0/{self._total_files}]")
        
        # Run multi-file test
        result = self.manager.run_test_on_files(files_to_test, "autocorrelation", auto_convert, test_config)
        if not result.ok:
            self._set_buttons_state(True)
            self._test_running = False
            self._log_error(f"Failed to start test: {result.message}")
    
    def _stop_test(self):
        """Stop any running test immediately by killing the process."""
        if self._test_running:
            self.manager.tests.force_stop()
            self._test_running = False
            self._multi_file_mode = False
            self._set_buttons_state(True)
            self._log_warning("Test stopped!")
            self._reset_all_progress()
        else:
            self._log_warning("No test is currently running.")
    
    def _reset_tab(self):
        """Reset tab's created data, settings and status. Stops any running test."""
        # Stop any running tests
        if self._test_running:
            self.manager.tests.force_stop()
            self._test_running = False
            self._multi_file_mode = False
            self._log_warning("Test cancelled.")
        
        # Reset all settings to defaults
        self.ent_settings = [0, 0, 0, 0]
        self.ent_save_raw = False
        self.ent_raw_output_path = ""
        self.nist_settings = [0] * 16
        self.nist_sequence_length = 1000000
        self.nist_use_whole = False
        self.nist_p_value_threshold = 0.01
        self.dieharder_settings = {
            'test_mode': 'specific',
            'selected_tests': [],
            'psamples': 100,
            'tentities': 10000,
            'multiplier': 1,
            'ntuple': 0,
            'ks_mode': 2,
            'weak_threshold': 0.005,
            'fail_threshold': 0.000001,
            'use_overlap': True,
            'test_strategy': 0,
            'reseed_strategy': 0,
            'save_raw_output': False,
            'raw_output_folder': ''
        }
        self.borel_settings = (1, 10)
        self.borel_auto_mode = False
        self.autocorr_max_lag = 100
        self.autocorr_use_whole = False
        
        # Reset file selection
        self.file_selector_var.set("-- All Files --")
        self.auto_convert_var.set(False)
        self._update_file_selector()
        
        # Reset all progress bars and labels
        self._reset_all_progress()
        
        # Re-enable buttons
        self._set_buttons_state(True)
        
        # Clear results
        self.results_text.config(state=NORMAL)
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state=DISABLED)
        self._log_info("Ready to run tests...")
    
    def _reset_all_progress(self):
        """Reset all progress bars and counter labels."""
        # NIST
        self.nist_progress['value'] = 0
        self.nist_test_label.config(text="[0/16]")
        self.nist_file_label.config(text="[0/0]")
        
        # Borel
        self.borel_progress['value'] = 0
        self.borel_test_label.config(text="[0/0]")
        self.borel_file_label.config(text="[0/0]")
        
        # Autocorr
        self.autocorr_progress['value'] = 0
        self.autocorr_file_label.config(text="[0/0]")
        
        # ENT
        self.ent_progress['value'] = 0
        self.ent_file_label.config(text="[0/0]")
        
        # Dieharder
        self.dh_progress['value'] = 0
        self.dh_test_label.config(text="[0/0]")
        self.dh_file_label.config(text="[0/0]")
        
        # Reset progress tracking
        self._current_file_idx = 0
        self._total_files = 0
    
    def _display_ent_status(self, payload: dict):
        """Display ENT test status with formatted components."""
        self._log_info("\n=== ENT Test Results ===")
        
        parsed = payload.get('parsed', {})
        options = payload.get('options', {})
        
        # Save raw output if enabled (to folder with timestamped files)
        if self.ent_save_raw and self.ent_raw_output_path:
            try:
                stdout = payload.get('stdout', '')
                if stdout:
                    from datetime import datetime
                    folder_path = Path(self.ent_raw_output_path)
                    folder_path.mkdir(parents=True, exist_ok=True)
                    
                    # Get input file name for the output filename
                    input_name = self.manager.input_meta.file_name or "unknown"
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_filename = f"{input_name}_ent_raw_{timestamp}.txt"
                    output_path = folder_path / output_filename
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(stdout)
                    self._log_result(f"Raw output saved to: {output_path}")
            except Exception as e:
                self._log_result(f"Warning: Could not save raw output: {e}")
        
        if payload.get('returncode') == 0 and parsed:
            # Display parsed results in a formatted way
            mode = "Bit stream" if options.get('binary') else "Byte stream"
            self._log_result(f"Mode: {mode}")
            
            # File size
            file_size = parsed.get('file_size')
            file_unit = parsed.get('file_unit', 'bytes')
            if file_size is not None:
                self._log_result(f"File Size: {file_size:,} {file_unit}")
            
            # Entropy
            entropy = parsed.get('entropy')
            entropy_unit = parsed.get('entropy_unit', 'bits per byte')
            if entropy is not None:
                max_entropy = 1.0 if options.get('binary') else 8.0
                entropy_pct = (entropy / max_entropy) * 100
                self._log_result(f"Entropy: {entropy:.6f} {entropy_unit} ({entropy_pct:.2f}% of max)")
            
            # Compression
            compression = parsed.get('compression_reduction')
            if compression is not None:
                self._log_result(f"Compression Potential: {compression:.1f}%")
            
            # Chi-square
            chi_sq = parsed.get('chi_square')
            chi_exceed = parsed.get('chi_square_exceed_percent')
            if chi_sq is not None:
                chi_result = "PASS" if chi_exceed and chi_exceed > 1.0 else "WEAK" if chi_exceed and chi_exceed > 0.01 else "FAIL"
                chi_info = f" (exceed {chi_exceed}%)" if chi_exceed is not None else ""
                status_type = "pass" if chi_result == "PASS" else "fail" if chi_result == "FAIL" else "weak"
                self._log_result_with_status(f"Chi-square: {chi_sq:.2f}{chi_info} ", f"[{chi_result}]", status_type)
            
            # Mean
            mean = parsed.get('mean')
            mean_ideal = parsed.get('mean_ideal')
            if mean is not None and mean_ideal is not None:
                mean_deviation = abs(mean - mean_ideal) / mean_ideal * 100
                self._log_result(f"Mean: {mean:.4f} (ideal: {mean_ideal}, deviation: {mean_deviation:.3f}%)")
            
            # Monte Carlo Pi
            pi_val = parsed.get('monte_carlo_pi')
            pi_err = parsed.get('monte_carlo_error_percent')
            if pi_val is not None:
                err_info = f" (error: {pi_err}%)" if pi_err is not None else ""
                self._log_result(f"Monte Carlo Pi: {pi_val:.6f}{err_info}")
            
            # Serial Correlation
            serial = parsed.get('serial_correlation')
            if serial is not None:
                serial_result = "PASS" if abs(serial) < 0.01 else "WEAK" if abs(serial) < 0.05 else "FAIL"
                status_type = "pass" if serial_result == "PASS" else "fail" if serial_result == "FAIL" else "weak"
                self._log_result_with_status(f"Serial Correlation: {serial:.6f} ", f"[{serial_result}]", status_type)
            
            # Occurrence count info (not displayed in status, but saved in parsed for reports)
            occ_count = parsed.get('occurrence_count', [])
            if occ_count:
                self._log_result(f"Occurrence count: {len(occ_count)} values captured (for report)")
        else:
            # Fall back to raw output
            self._log_result(f"Return Code: {payload.get('returncode', 'N/A')}")
            stdout = payload.get('stdout', '')
            if stdout:
                self._log_result("\nOutput:")
                self._log_result(stdout)
            stderr = payload.get('stderr', '')
            if stderr:
                self._log_result(f"Error: {stderr}")
    
    def _display_borel_status(self, payload: dict):
        """Display Borel test status with overall result only."""
        self._log_info("\n=== Borel Test Results ===")
        overall = payload.get('overall_assessment', 'N/A')
        status_type = "pass" if overall == "PASS" else "fail"
        self._log_result_with_status("Overall Result: ", f"[{overall}]", status_type)
    
    def _display_nist_status(self, payload: dict):
        """Display NIST test status with overall pass/total."""
        self._log_info("\n=== NIST Test Results ===")
        results = payload.get('results', [])
        total_tests = len(results)
        
        # Count passed tests - handle both simple and multi-subtest results
        passed_tests = 0
        for r in results:
            result = r.get('result', {})
            error = r.get('error')
            test_id = r.get('test_id', -1)
            
            if error:
                continue  # Error tests don't pass
            
            # Tests 15 and 16 (indices 14, 15) have subtests with overall_passed
            if test_id in [14, 15] and 'results' in result:
                if result.get('overall_passed', False):
                    passed_tests += 1
            elif 'p_value_1' in result:
                # Serial test with two p-values
                if result.get('passed_1', False) and result.get('passed_2', False):
                    passed_tests += 1
            else:
                # Standard test
                if result.get('passed', False):
                    passed_tests += 1
        
        status_type = "pass" if passed_tests == total_tests else "fail" if passed_tests == 0 else "weak"
        overall_text = "[PASS]" if passed_tests == total_tests else "[FAIL]" if passed_tests == 0 else "[PARTIAL]"
        self._log_result_with_status(f"Overall: {passed_tests}/{total_tests} tests passed ", overall_text, status_type)
    
    def _display_autocorr_status(self, payload: dict):
        """Display Autocorrelation test status."""
        self._log_success("Autocorrelation test complete")
    
    def _display_dieharder_status(self, payload: dict):
        """Display Dieharder test status with summary."""
        completed_count = payload.get('completed_count', 0)
        parsed_results = payload.get('parsed_results', {})
        
        # Count results by assessment
        passed = 0
        failed = 0
        weak = 0
        for test_num, result in parsed_results.items():
            assessment = result.get('overall_assessment', 'UNKNOWN')
            if assessment == 'PASSED':
                passed += 1
            elif assessment == 'FAILED':
                failed += 1
            elif assessment == 'WEAK':
                weak += 1
        
        # Log summary
        self._log_info(f"Dieharder complete: {completed_count} tests run")
        # Determine overall status
        if failed == 0 and weak == 0:
            overall_status = "pass"
            overall_text = "[PASS]"
        elif failed > 0:
            overall_status = "fail"
            overall_text = "[FAIL]"
        else:
            overall_status = "weak"
            overall_text = "[WEAK]"
        self._log_result_with_status(f"  PASSED: {passed}, FAILED: {failed}, WEAK: {weak} ", overall_text, overall_status)
        
        # Note if raw output was saved (done incrementally in core)
        if self.dieharder_settings.get('save_raw_output', False):
            raw_folder = self.dieharder_settings.get('raw_output_folder', '')
            if raw_folder:
                self._log_result(f"  Raw output saved to: {raw_folder}")
    
    def _wire_ent_report(self, payload: dict):
        """Wire ENT test results to report tab."""
        if not self.report_tab:
            return
        
        try:
            # Prepare data for ENT report with parsed structured data
            ent_data = {
                'input_file': self.manager.input_meta.file_name or 'N/A',
                'result_file': 'N/A',
                'output': payload.get('stdout', 'No output available'),
                'parsed': payload.get('parsed', {}),
                'options': payload.get('options', {})
            }
            
            self.report_tab.add_test_section('ent', ent_data)
        except Exception as e:
            self._log_result(f"Warning: Could not add to report: {e}")
    
    def _wire_borel_report(self, payload: dict):
        """Wire Borel test results to report tab with chi-square results."""
        if not self.report_tab:
            return
        
        try:
            # Prepare data for Borel report
            results = payload.get('results', [])
            rows = []
            
            for result in results:
                pattern_len = result.get('pattern_length', 'N/A')
                passed = result.get('passed', False)
                chi_square = result.get('chi_square', 0)
                critical_value = result.get('critical_value', 0)
                
                rows.append({
                    'pattern_length': f"{pattern_len}-bit",
                    'chi_square': f"{chi_square:.4f}",
                    'critical_value': f"{critical_value:.4f}",
                    'passed': passed,
                    'result_text': 'PASS' if passed else 'FAIL'
                })
            
            # Add final overall result row
            overall = payload.get('overall_assessment', 'PASS')
            overall_passed = overall == 'PASS'
            rows.append({
                'pattern_length': 'Overall Result',
                'chi_square': '',
                'critical_value': '',
                'passed': overall_passed,
                'result_text': overall,
                'is_final': True
            })
            
            borel_data = {
                'input_file': self.manager.input_meta.file_name or 'N/A',
                'result_file': 'N/A',
                'sequence_length': payload.get('data_length', 'N/A'),
                'max_pattern_length': payload.get('pattern_length_range', [1, 10])[1],
                'rows': rows
            }
            
            self.report_tab.add_test_section('borel', borel_data)
        except Exception as e:
            self._log_result(f"Warning: Could not add to report: {e}")
    
    def _wire_nist_report(self, payload: dict):
        """Wire NIST test results to report tab."""
        if not self.report_tab:
            return
        
        try:
            # Prepare data for NIST report
            results = payload.get('results', [])
            rows = []
            
            for test_result in results:
                test_name = test_result.get('test_name', 'Unknown')
                test_id = test_result.get('test_id', -1)
                result = test_result.get('result', {})
                error = test_result.get('error')
                
                # Check for insufficient data error
                is_insufficient_data = error and 'insufficient' in error.lower() if error else False
                
                # Handle tests 15 and 16 with multiple subsections - create nested table
                if test_id in [14, 15] and 'results' in result and not error:
                    # Tests 15 and 16 have multiple subsections - store as nested structure
                    subsection_results = result.get('results', [])
                    subtests = []
                    for subsection in subsection_results:
                        state = subsection.get('state', 'N/A')
                        p_value = subsection.get('p_value', 0)
                        passed = subsection.get('passed', False)
                        
                        subtests.append({
                            'state': state,
                            'p_value': f"{p_value:.6f}",
                            'passed': passed,
                            'result_text': 'PASS' if passed else 'FAIL'
                        })
                    
                    # Calculate overall pass/fail for the test
                    overall_passed = result.get('overall_passed', all(s.get('passed', False) for s in subsection_results))
                    
                    rows.append({
                        'test_number': test_id + 1,
                        'test_name': test_name,
                        'p_value': 'See subtests',
                        'passed': overall_passed,
                        'result_text': 'PASS' if overall_passed else 'FAIL',
                        'has_error': False,
                        'is_warning': False,
                        'has_subtests': True,
                        'subtests': subtests
                    })
                else:
                    # Handle tests with single or multiple p-values
                    if 'p_value' in result:
                        p_value = result.get('p_value', 0)
                        passed = result.get('passed', False)
                    elif 'p_value_1' in result:
                        # Serial test has two p-values - use first one for display
                        p_value = result.get('p_value_1', 0)
                        passed = result.get('passed_1', False) and result.get('passed_2', False)
                    else:
                        p_value = 0
                        passed = False
                    
                    if error:
                        if is_insufficient_data:
                            result_text = f"Insufficient data"
                        else:
                            result_text = f"ERROR: {error}"
                    else:
                        result_text = 'PASS' if passed else 'FAIL'
                    
                    rows.append({
                        'test_number': test_id + 1,
                        'test_name': test_name,
                        'p_value': f"{p_value:.6f}" if not error else "N/A",
                        'passed': passed,
                        'result_text': result_text,
                        'has_error': bool(error) and not is_insufficient_data,
                        'is_warning': is_insufficient_data,
                        'has_subtests': False
                    })
            
            # Calculate overall
            total_tests = len(rows)
            passed_tests = sum(1 for row in rows if row['passed'])
            
            nist_data = {
                'input_file': self.manager.input_meta.file_name or 'N/A',
                'sequence_length': payload.get('sequence_length', 'N/A'),
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'rows': rows
            }
            
            self.report_tab.add_test_section('nist', nist_data)
        except Exception as e:
            self._log_result(f"Warning: Could not add NIST to report: {e}")
    
    def _wire_autocorr_report(self, payload: dict):
        """Wire Autocorrelation test results to report tab."""
        if not self.report_tab:
            return
        
        try:
            autocorr_data = {
                'input_file': self.manager.input_meta.file_name or 'N/A',
                'data_length': payload.get('data_length', 'N/A'),
                'nlags': payload.get('nlags', 'N/A'),
                'plot_base64': payload.get('plot_base64', ''),
                'analysis': payload.get('analysis', {})
            }
            
            self.report_tab.add_test_section('autocorrelation', autocorr_data)
        except Exception as e:
            self._log_result(f"Warning: Could not add Autocorrelation to report: {e}")
    
    def _wire_dieharder_report(self, payload: dict):
        """Wire Dieharder test results to report tab."""
        if not self.report_tab:
            return
        
        try:
            settings = payload.get('settings', {})
            parsed_results = payload.get('parsed_results', {})
            
            # Determine test mode string
            if settings.get('test_mode') == 'all':
                test_mode = "All tests"
                selected_tests = ""
            else:
                test_count = len(settings.get('selected_tests', []))
                test_mode = f"Specific tests ({test_count} selected)"
                selected_tests = ", ".join(str(t) for t in settings.get('selected_tests', []))
            
            # Map test strategy to name
            strategy_names = {0: "Standard", 1: "Resolve Ambiguity", 2: "Test to Destruction"}
            test_strategy = settings.get('test_strategy', 0)
            test_strategy_name = strategy_names.get(test_strategy, "Unknown")
            
            # Calculate summary statistics
            passed = sum(1 for r in parsed_results.values() if r.get('overall_assessment') == 'PASSED')
            failed = sum(1 for r in parsed_results.values() if r.get('overall_assessment') == 'FAILED')
            weak = sum(1 for r in parsed_results.values() if r.get('overall_assessment') == 'WEAK')
            
            dieharder_data = {
                'input_file': self.manager.input_meta.file_name or 'N/A',
                'test_mode': test_mode,
                'selected_tests': selected_tests,
                'psamples': settings.get('psamples', 100),
                'tentities': settings.get('tentities', 10000),
                'ks_mode': settings.get('ks_mode', 2),
                'weak_threshold': settings.get('weak_threshold', 0.005),
                'fail_threshold': settings.get('fail_threshold', 0.000001),
                'test_strategy': test_strategy,
                'test_strategy_name': test_strategy_name,
                'output': payload.get('stdout', 'No output available'),
                'parsed_results': parsed_results,
                'summary': {'passed': passed, 'failed': failed, 'weak': weak}
            }
            
            self.report_tab.add_test_section('dieharder', dieharder_data)
        except Exception as e:
            self._log_result(f"Warning: Could not add Dieharder to report: {e}")
    
    def _log_result(self, message: str):
        """Log to results (alias for _log_info)."""
        self._log_info(message)
    
    def _log_success(self, message: str):
        """Log success message in green with checkmark."""
        self.results_text.config(state=NORMAL)
        self.results_text.insert(tk.END, f"✓ {message}\n", "success")
        self.results_text.see(tk.END)
        self.results_text.config(state=DISABLED)
    
    def _log_error(self, message: str):
        """Log error message in red with cross mark."""
        self.results_text.config(state=NORMAL)
        self.results_text.insert(tk.END, f"✗ {message}\n", "error")
        self.results_text.see(tk.END)
        self.results_text.config(state=DISABLED)
    
    def _log_warning(self, message: str):
        """Log warning message in orange with exclamation mark."""
        self.results_text.config(state=NORMAL)
        self.results_text.insert(tk.END, f"⚠ {message}\n", "warning")
        self.results_text.see(tk.END)
        self.results_text.config(state=DISABLED)
    
    def _log_info(self, message: str):
        """Log info message in default color."""
        self.results_text.config(state=NORMAL)
        self.results_text.insert(tk.END, f"{message}\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=DISABLED)
    
    def _log_result_with_status(self, text: str, status_text: str, status_type: str):
        """Log text with a colored status tag.
        
        Args:
            text: The main text to log
            status_text: The status text to color (e.g., "[PASS]", "[FAIL]")
            status_type: One of "pass", "fail", "weak"
        """
        self.results_text.config(state=NORMAL)
        self.results_text.insert(tk.END, text)
        start_idx = self.results_text.index(f"end-{len(status_text)+1}c")
        self.results_text.insert(tk.END, status_text, status_type)
        self.results_text.insert(tk.END, "\n")
        self.results_text.see(tk.END)
        self.results_text.config(state=DISABLED)
