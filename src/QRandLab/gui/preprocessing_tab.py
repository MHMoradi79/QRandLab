# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Preprocessing tab for multi-file data extraction algorithms."""

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path

from ..manager.core_manager import CoreManager
from ..core.types import OperationStatus, FileItem, FileType
from .test_settings import TZExtractorSettingsWindow


class PreprocessingTab(ttk.Frame):
    """Multi-file preprocessing algorithms tab."""
    
    def __init__(self, parent, manager: CoreManager):
        super().__init__(parent, padding=20)
        self.manager = manager
        self.preprocess_results = []
        self.saved_paths = []
        self.report_tab = None
        
        # TZ Extractor settings
        self.tz_settings = {
            'n': '256',
            'l': '128',
            'output': 'output_TZE.bin',
            'tzm_file': 'output_TZM.txt',
            'save_tzm': False,
            'submitted': False
        }
        
        self._setup_events()
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to manager events."""
        self.manager.on_files_preprocessed.subscribe(self._on_files_preprocessed)
        self.manager.on_files_added.subscribe(self._on_files_changed)
        self.manager.on_files_removed.subscribe(self._on_files_changed)
        self.manager.on_file_type_changed.subscribe(self._on_files_changed)
        self.manager.on_files_cleared.subscribe(self._on_files_cleared)
        self.manager.on_preprocess_progress.subscribe(self._on_preprocess_progress)
    
    def _build_ui(self):
        """Build preprocessing tab UI."""
        # Source Files Section
        source_frame = ttk.LabelFrame(self, text="Source Files", padding=15, bootstyle=INFO)
        source_frame.pack(fill=X, pady=(0, 10))
        
        select_label = ttk.Label(source_frame, text="Select Files:", font=("Helvetica", 10, "bold"))
        select_label.grid(row=0, column=0, sticky=W, pady=5)
        
        self.file_selector_var = tk.StringVar(value="-- All Files --")
        self.file_selector = ttk.Combobox(
            source_frame,
            textvariable=self.file_selector_var,
            state="readonly",
            width=50
        )
        self.file_selector.grid(row=0, column=1, sticky=EW, padx=(10, 0), pady=5)
        source_frame.columnconfigure(1, weight=1)
        
        # Container for Algorithm+Options and Actions
        main_container = ttk.Frame(self)
        main_container.pack(fill=X, pady=(0, 10))
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=0)
        
        # Algorithm & Options
        algo_frame = ttk.LabelFrame(main_container, text="Algorithm & Options", padding=15, bootstyle=INFO)
        algo_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Algorithm selector row
        algo_label = ttk.Label(algo_frame, text="Algorithm:", font=("Helvetica", 10, "bold"))
        algo_label.grid(row=0, column=0, sticky=W, pady=5, padx=5)
        
        self.algorithm_var = tk.StringVar(value="VonNeuman")
        algo_combo = ttk.Combobox(
            algo_frame,
            textvariable=self.algorithm_var,
            values=["VonNeuman", "XOR1", "XOR2", "TZ Extractor"],
            state="readonly",
            width=18
        )
        algo_combo.grid(row=0, column=1, pady=5, padx=5, sticky=W)
        algo_combo.bind("<<ComboboxSelected>>", self._on_algorithm_changed)
        
        # Toeplitz Settings button (shown only for TZ Extractor)
        self.tz_settings_btn = ttk.Button(
            algo_frame,
            text="Toeplitz Settings",
            command=self._show_tz_settings,
            bootstyle="info-outline",
            width=15
        )
        
        # Separator
        sep = ttk.Separator(algo_frame, orient=HORIZONTAL)
        sep.grid(row=1, column=0, columnspan=3, sticky=EW, pady=10)
        
        # Options container
        options_frame = ttk.Frame(algo_frame)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=EW)
        
        # Output tag
        tag_label = ttk.Label(options_frame, text="Output Tag:", font=("Helvetica", 10))
        tag_label.grid(row=0, column=0, sticky=W, pady=3, padx=5)
        self.output_tag_var = tk.StringVar(value="")
        tag_entry = ttk.Entry(options_frame, textvariable=self.output_tag_var, width=18)
        tag_entry.grid(row=0, column=1, sticky=W, pady=3, padx=5)
        
        # Auto-convert option
        self.auto_convert_var = tk.BooleanVar(value=False)
        auto_convert_check = ttk.Checkbutton(
            options_frame,
            text="Auto-convert to required format",
            variable=self.auto_convert_var,
            bootstyle="round-toggle"
        )
        auto_convert_check.grid(row=1, column=0, columnspan=2, sticky=W, pady=3, padx=5)
        
        # Convert back option
        self.convert_back_var = tk.BooleanVar(value=False)
        convert_back_check = ttk.Checkbutton(
            options_frame,
            text="Convert back to original format",
            variable=self.convert_back_var,
            bootstyle="round-toggle"
        )
        convert_back_check.grid(row=2, column=0, columnspan=2, sticky=W, pady=3, padx=5)
        
        # Add to input table option
        self.add_to_table_var = tk.BooleanVar(value=False)
        add_table_check = ttk.Checkbutton(
            options_frame,
            text="Add preprocessed files to Input table",
            variable=self.add_to_table_var,
            bootstyle="round-toggle"
        )
        add_table_check.grid(row=3, column=0, columnspan=2, sticky=W, pady=3, padx=5)
        
        
        # Actions Section
        actions_frame = ttk.LabelFrame(main_container, text="Actions", padding=15, bootstyle=SUCCESS)
        actions_frame.grid(row=0, column=1, sticky="nsew")
        
        btn_inner = ttk.Frame(actions_frame)
        btn_inner.pack(expand=YES, anchor='n')
        
        # Run button
        self.run_btn = ttk.Button(btn_inner, text="Run", command=self._run_preprocessing, bootstyle=SUCCESS, width=12)
        self.run_btn.pack(pady=3, fill='both', anchor='n')

        # Progress bar for preprocessing
        self.preprocess_progress = ttk.Progressbar(btn_inner, length=80, mode='determinate', bootstyle="success-striped")
        self.preprocess_progress.pack(pady=3, fill='both', anchor='n')

        # Save button
        self.save_btn = ttk.Button(btn_inner, text="Save", command=self._save_results, bootstyle=PRIMARY, width=12, state=DISABLED)
        self.save_btn.pack(pady=3, fill='both', anchor='n')
        
        # Reset button
        reset_btn = ttk.Button(btn_inner, text="Reset", command=self._reset_tab, bootstyle=SECONDARY, width=12)
        reset_btn.pack(pady=3, fill='both', anchor='n')
        
        # Status Section
        status_frame = ttk.LabelFrame(self, text="Processing Status", padding=15, bootstyle=INFO)
        status_frame.pack(fill=BOTH, expand=YES)
        
        self.status_text = tk.Text(
            status_frame,
            height=10,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            state=DISABLED
        )
        self.status_text.pack(fill=BOTH, expand=YES, pady=5)
        
        self.status_text.tag_configure("success", foreground="#4CAF50")
        self.status_text.tag_configure("error", foreground="#F44336")
        self.status_text.tag_configure("warning", foreground="#FF9800")
        
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        self._update_file_selector()
        self._log_info("Ready to run preprocessing algorithms...")
    
    def _format_size(self, size_bytes):
        """Format file size for display."""
        if not size_bytes:
            return "0 B"
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        if size_mb >= 1:
            return f"{size_mb:.1f} MB"
        elif size_kb >= 1:
            return f"{size_kb:.1f} KB"
        return f"{size_bytes} B"
    
    def _update_file_selector(self):
        """Update file selector with available files."""
        files = self.manager.get_all_files()
        
        if not files:
            self.file_selector['values'] = ["-- No files loaded --"]
            self.file_selector_var.set("-- No files loaded --")
            return
        
        options = ["-- All Files --"]
        for f in files:
            size_str = self._format_size(f.file_size)
            type_str = f.file_type.value if f.file_type else "?"
            options.append(f"{f.file_name}{f.file_ext.value} ({size_str}) [{type_str}]")
        
        self.file_selector['values'] = options
        current = self.file_selector_var.get()
        if current not in options:
            self.file_selector_var.set("-- All Files --")
    
    def _get_selected_file(self):
        """Get FileItem for selected file."""
        selected = self.file_selector_var.get()
        if selected in ("-- All Files --", "-- No files loaded --"):
            return None
        
        files = self.manager.get_all_files()
        for f in files:
            display_name = f"{f.file_name}{f.file_ext.value}"
            if selected.startswith(display_name):
                return f
        return None
    
    def _get_files_to_process(self):
        """Get list of FileItems to preprocess."""
        selected = self.file_selector_var.get()
        if selected == "-- No files loaded --":
            return []
        if selected == "-- All Files --":
            return self.manager.get_all_files()
        file_item = self._get_selected_file()
        return [file_item] if file_item else []
    
    def _on_files_changed(self, status: OperationStatus):
        """Handle files added/removed events."""
        self._update_file_selector()
    
    def _on_files_cleared(self, status: OperationStatus):
        """Handle files cleared event."""
        self._update_file_selector()
        self.preprocess_results = []
        self.saved_paths = []
        self.save_btn.config(state=DISABLED)
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready to run preprocessing algorithms...")
    
    def _on_algorithm_changed(self, event=None):
        """Handle algorithm selection change."""
        algorithm = self.algorithm_var.get()
        
        if algorithm == "TZ Extractor":
            self.tz_settings_btn.grid(row=0, column=2, padx=(10, 0), pady=5)
        else:
            self.tz_settings_btn.grid_forget()
    
    def _show_tz_settings(self):
        """Show Toeplitz Extractor settings window."""
        # Use first file's name or generic
        files = self._get_files_to_process()
        input_filename = files[0].file_name if files else "output"
        settings_window = TZExtractorSettingsWindow(self, self.tz_settings, input_filename)
        result = settings_window.show()
        if result is not None:
            self.tz_settings = result
            self._log_info(f"TZ settings updated: n={result['n']}, l={result['l']}")
    
    def _on_files_preprocessed(self, status: OperationStatus):
        """Handle multi-file preprocessing completion."""
        self.run_btn.config(state=NORMAL)
        # Progress bar stays full after completion
        
        if status.ok and status.payload:
            self.preprocess_results = status.payload.get('results', [])
            success_count = status.payload.get('success_count', 0)
            fail_count = status.payload.get('fail_count', 0)
            
            self._log_success(f"Preprocessing complete: {success_count} succeeded, {fail_count} failed")
            
            for r in self.preprocess_results:
                if r.get('ok'):
                    self._log_info(f"  ✓ {r['file_name']}")
                else:
                    self._log_warning(f"  ✗ {r['file_name']}: {r.get('message', 'Unknown error')}")
            
            if success_count > 0:
                self.save_btn.config(state=NORMAL)
        else:
            self._log_error(f"Preprocessing failed: {status.message}")
    
    def _run_preprocessing(self):
        """Run preprocessing on selected files."""
        files_to_process = self._get_files_to_process()
        
        if not files_to_process:
            self._log_warning("No files to preprocess. Please load files first.")
            return
        
        algorithm = self.algorithm_var.get()
        if not algorithm:
            self._log_warning("Please select an algorithm")
            return
        
        # For TZ Extractor, check settings submitted
        if algorithm == "TZ Extractor" and not self.tz_settings.get('submitted', False):
            self._log_error("Toeplitz settings not submitted. Please click 'Toeplitz Settings' and submit.")
            return
        
        auto_convert = self.auto_convert_var.get()
        convert_back = self.convert_back_var.get()
        output_tag = self.output_tag_var.get().strip()  # Allow empty tag
        
        # Validate file types if auto-convert is off
        if not auto_convert:
            required_type = FileType.BINARY if algorithm == "TZ Extractor" else FileType.STRING01
            incompatible = [f for f in files_to_process if f.file_type != required_type]
            if incompatible:
                self._log_warning(f"{len(incompatible)} file(s) have incompatible type for {algorithm}")
                self._log_info("Enable 'Auto-convert to required format' to convert them automatically")
        
        self.run_btn.config(state=DISABLED)
        self.preprocess_results = []
        self.saved_paths = []
        self.save_btn.config(state=DISABLED)
        
        self._log_info(f"⏳ Running {algorithm} on {len(files_to_process)} file(s)...")
        
        # Reset progress bar
        self.preprocess_progress['value'] = 0
        
        tz_settings = self.tz_settings if algorithm == "TZ Extractor" else None
        result = self.manager.preprocess_files(files_to_process, algorithm, auto_convert, convert_back, tz_settings, output_tag)
        
        if not result.ok:
            self.run_btn.config(state=NORMAL)
            self._log_error(f"Failed to start preprocessing: {result.message}")
    
    def _save_results(self):
        """Save preprocessing results to folder."""
        if not self.preprocess_results:
            self._log_warning("No preprocessing results to save")
            return
        
        successful = [r for r in self.preprocess_results if r.get('ok')]
        if not successful:
            self._log_warning("No successful preprocessing results to save")
            return
        
        output_dir = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.manager.get_last_directory()
        )
        
        if not output_dir:
            self._log_warning("Save cancelled by user")
            return
        
        self.manager.set_last_directory(output_dir)
        output_path = Path(output_dir)
        
        algorithm = self.algorithm_var.get()
        convert_back = self.convert_back_var.get()
        saved_count = 0
        self.saved_paths = []
        output_types = []
        
        try:
            for result in successful:
                file_name = result['file_name']
                data = result.get('data')
                suggested_name = result.get('suggested_name', f"{file_name}_preprocessed.bin")
                output_type = result.get('output_type', FileType.STRING01)
                
                # Handle convert back
                if convert_back and output_type != result.get('original_type'):
                    # For now, just save as-is (convert back would need original type info)
                    pass
                
                # Save main output
                out_path = output_path / suggested_name
                if isinstance(data, bytes):
                    with open(out_path, 'wb') as f:
                        f.write(data)
                else:
                    with open(out_path, 'w') as f:
                        f.write(str(data))
                
                self._log_success(f"Saved: {suggested_name}")
                self.saved_paths.append(out_path)
                output_types.append(output_type)
                saved_count += 1
                
                # Save TZM file if present
                if 'tzm_data' in result:
                    tzm_name = result.get('tzm_name', f"{file_name}_TZM.txt")
                    tzm_path = output_path / tzm_name
                    with open(tzm_path, 'w') as f:
                        f.write(result['tzm_data'])
                    self._log_success(f"Saved TZM: {tzm_name}")
                    
        except Exception as e:
            self._log_error(f"Save failed: {e}")
        
        self._log_info(f"Save complete: {saved_count} file(s) saved")
        
        # Add to input table if checkbox is checked
        if self.add_to_table_var.get() and self.saved_paths:
            str_paths = [str(p) for p in self.saved_paths]
            add_result = self.manager.add_files(str_paths)
            if add_result.ok:
                # Set correct file type for each added file
                added_items = add_result.payload.get('added', [])
                for i, item in enumerate(added_items):
                    if i < len(output_types):
                        # Convert FileType enum to string value
                        type_str = output_types[i].value if hasattr(output_types[i], 'value') else str(output_types[i])
                        self.manager.set_file_type_for_item(item.id, type_str)
                self._log_success(f"Added {len(self.saved_paths)} preprocessed file(s) to Input table")
            else:
                self._log_warning(f"Could not add files to Input table: {add_result.message}")
        
        # Add to report - one row per file
        if self.report_tab is not None and saved_count > 0:
            for i, result in enumerate(successful):
                if i < len(self.saved_paths):
                    out_name = self.saved_paths[i].name
                else:
                    out_name = result.get('suggested_name', 'unknown')
                preprocess_data = {
                    'input_file': result.get('file_name', 'N/A'),
                    'algorithm': algorithm,
                    'output_file': out_name,
                    'status_text': 'Success'
                }
                self.report_tab.add_preprocess_section(preprocess_data)
    
    def _reset_tab(self):
        """Reset tab to default state."""
        self.preprocess_results = []
        self.saved_paths = []
        self.save_btn.config(state=DISABLED)
        self.run_btn.config(state=NORMAL)
        
        # Reset progress bar
        self.preprocess_progress['value'] = 0
        
        self.file_selector_var.set("-- All Files --")
        self.algorithm_var.set("VonNeuman")
        self.output_tag_var.set("")
        self.auto_convert_var.set(False)
        self.convert_back_var.set(False)
        self.add_to_table_var.set(False)
        self.tz_settings_btn.grid_forget()
        
        self.tz_settings = {
            'n': '256',
            'l': '128',
            'output': 'output_TZE.bin',
            'tzm_file': 'output_TZM.txt',
            'save_tzm': False,
            'submitted': False
        }
        
        self._update_file_selector()
        
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready to run preprocessing algorithms...")
    
    def _log_success(self, message: str):
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"✓ {message}\n", "success")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _log_error(self, message: str):
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"✗ {message}\n", "error")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _log_warning(self, message: str):
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"⚠ {message}\n", "warning")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _log_info(self, message: str):
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _on_preprocess_progress(self, status: OperationStatus):
        """Handle preprocessing progress update."""
        if status.payload:
            current = status.payload.get('current', 0)
            total = status.payload.get('total', 1)
            if total > 0:
                progress_pct = (current / total) * 100
                self.preprocess_progress['value'] = progress_pct
