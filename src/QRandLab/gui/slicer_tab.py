# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Slicer tab for multi-file data slicing operations."""

import tkinter as tk
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path

from ..manager.core_manager import CoreManager
from ..core.types import OperationStatus, FileItem, FileType


class SlicerTab(ttk.Frame):
    """Multi-file data slicing operations tab."""
    
    def __init__(self, parent, manager: CoreManager):
        super().__init__(parent, padding=20)
        self.manager = manager
        self.slice_results = []
        self.saved_paths = []
        self.report_tab = None
        
        self._setup_events()
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to manager events."""
        self.manager.on_files_sliced.subscribe(self._on_files_sliced)
        self.manager.on_files_added.subscribe(self._on_files_changed)
        self.manager.on_files_removed.subscribe(self._on_files_changed)
        self.manager.on_file_type_changed.subscribe(self._on_files_changed)
        self.manager.on_files_cleared.subscribe(self._on_files_cleared)
        self.manager.on_slice_progress.subscribe(self._on_slice_progress)
    
    def _build_ui(self):
        """Build slicer tab UI."""
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
        
        # Container for Operation+Params and Actions
        main_container = ttk.Frame(self)
        main_container.pack(fill=X, pady=(0, 10))
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=0)
        
        # Slicing Operation & Parameters (merged, left side)
        self.ops_params_frame = ttk.LabelFrame(main_container, text="Slicing Operation", padding=15, bootstyle=INFO)
        self.ops_params_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Operation selector row
        op_label = ttk.Label(self.ops_params_frame, text="Operation:", font=("Helvetica", 10, "bold"))
        op_label.grid(row=0, column=0, sticky=W, pady=5, padx=5)
        
        self.operation_var = tk.StringVar(value="Single Slice")
        op_combo = ttk.Combobox(
            self.ops_params_frame,
            textvariable=self.operation_var,
            values=["Single Slice", "Equal Parts", "Random Sampling"],
            state="readonly",
            width=20
        )
        op_combo.grid(row=0, column=1, pady=5, padx=5, sticky=W)
        op_combo.bind("<<ComboboxSelected>>", self._on_operation_changed)
        
        # Separator
        sep = ttk.Separator(self.ops_params_frame, orient=HORIZONTAL)
        sep.grid(row=1, column=0, columnspan=4, sticky=EW, pady=10)
        
        # Parameters container (will be rebuilt dynamically)
        self.params_container = ttk.Frame(self.ops_params_frame)
        self.params_container.grid(row=2, column=0, columnspan=4, sticky=EW)
        self._build_single_slice_params()
        
        # Add to input table checkbox
        self.add_to_table_var = tk.BooleanVar(value=False)
        add_check = ttk.Checkbutton(
            self.ops_params_frame,
            text="Add sliced files to Input table",
            variable=self.add_to_table_var,
            bootstyle="round-toggle"
        )
        add_check.grid(row=4, column=0, columnspan=2, sticky=W, pady=5, padx=5)
        
        # Actions Section 
        actions_frame = ttk.LabelFrame(main_container, text="Actions", padding=15, bootstyle=SUCCESS)
        actions_frame.grid(row=0, column=1, sticky="nsew")
        
        btn_inner = ttk.Frame(actions_frame)
        btn_inner.pack(expand=YES, anchor='n')

        # Slice button
        self.run_btn = ttk.Button(btn_inner, text="Slice", command=self._run_slicing, bootstyle=SUCCESS, width=12)
        self.run_btn.pack(pady=3, fill='both', anchor='n')        

        # Progress bar for slicing 
        self.slice_progress = ttk.Progressbar(btn_inner, length=100, mode='determinate', bootstyle="success-striped")
        self.slice_progress.pack(pady=3, fill='both', anchor='n')

        # Save button
        self.save_btn = ttk.Button(btn_inner, text="Save", command=self._save_slices, bootstyle=PRIMARY, width=12, state=DISABLED)
        self.save_btn.pack(pady=3, fill='both', anchor='n')
        
        reset_btn = ttk.Button(btn_inner, text="Reset", command=self._reset_tab, bootstyle=SECONDARY, width=12)
        reset_btn.pack(pady=3, fill='both', anchor='n')
        
        # Status Section
        status_frame = ttk.LabelFrame(self, text="Slicing Status", padding=15, bootstyle=INFO)
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
        self._log_info("Ready to slice data files...")
    
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
        """Update file selector with available files and their sizes."""
        files = self.manager.get_all_files()
        
        if not files:
            self.file_selector['values'] = ["-- No files loaded --"]
            self.file_selector_var.set("-- No files loaded --")
            return
        
        options = ["-- All Files --"]
        for f in files:
            size_str = self._format_size(f.file_size)
            options.append(f"{f.file_name}{f.file_ext.value} ({size_str})")
        
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
    
    def _get_files_to_slice(self):
        """Get list of FileItems to slice."""
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
        self.slice_results = []
        self.saved_paths = []
        self.save_btn.config(state=DISABLED)
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready to slice data files...")
    
    def _on_operation_changed(self, event=None):
        """Handle operation selection change - rebuild params."""
        for widget in self.params_container.winfo_children():
            widget.destroy()
        
        operation = self.operation_var.get()
        if operation == "Single Slice":
            self._build_single_slice_params()
        elif operation == "Equal Parts":
            self._build_equal_parts_params()
        elif operation == "Random Sampling":
            self._build_random_sampling_params()
    
    def _build_single_slice_params(self):
        """Build parameters for single slice."""
        start_label = ttk.Label(self.params_container, text="Start Position (bytes):", font=("Helvetica", 10))
        start_label.grid(row=0, column=0, sticky=W, pady=5, padx=5)
        self.start_var = tk.StringVar(value="0")
        start_entry = ttk.Entry(self.params_container, textvariable=self.start_var, width=15)
        start_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        
        length_label = ttk.Label(self.params_container, text="Length (bytes):", font=("Helvetica", 10))
        length_label.grid(row=1, column=0, sticky=W, pady=5, padx=5)
        self.length_var = tk.StringVar(value="1000")
        length_entry = ttk.Entry(self.params_container, textvariable=self.length_var, width=15)
        length_entry.grid(row=1, column=1, sticky=W, pady=5, padx=5)
    
    def _build_equal_parts_params(self):
        """Build parameters for equal parts."""
        parts_label = ttk.Label(self.params_container, text="Number of Parts:", font=("Helvetica", 10))
        parts_label.grid(row=0, column=0, sticky=W, pady=5, padx=5)
        self.num_parts_var = tk.StringVar(value="4")
        parts_entry = ttk.Entry(self.params_container, textvariable=self.num_parts_var, width=15)
        parts_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
    
    def _build_random_sampling_params(self):
        """Build parameters for random sampling."""
        samples_label = ttk.Label(self.params_container, text="Number of Samples:", font=("Helvetica", 10))
        samples_label.grid(row=0, column=0, sticky=W, pady=5, padx=5)
        self.num_samples_var = tk.StringVar(value="5")
        samples_entry = ttk.Entry(self.params_container, textvariable=self.num_samples_var, width=15)
        samples_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        
        size_label = ttk.Label(self.params_container, text="Sample Size (bytes):", font=("Helvetica", 10))
        size_label.grid(row=1, column=0, sticky=W, pady=5, padx=5)
        self.sample_size_var = tk.StringVar(value="1000")
        size_entry = ttk.Entry(self.params_container, textvariable=self.sample_size_var, width=15)
        size_entry.grid(row=1, column=1, sticky=W, pady=5, padx=5)
        
        seed_label = ttk.Label(self.params_container, text="Random Seed (optional):", font=("Helvetica", 10))
        seed_label.grid(row=2, column=0, sticky=W, pady=5, padx=5)
        self.seed_var = tk.StringVar(value="")
        seed_entry = ttk.Entry(self.params_container, textvariable=self.seed_var, width=15)
        seed_entry.grid(row=2, column=1, sticky=W, pady=5, padx=5)
    
    def _on_files_sliced(self, status: OperationStatus):
        """Handle multi-file slice completion."""
        self.run_btn.config(state=NORMAL)
        # Progress bar stays full after completion
        
        if status.ok and status.payload:
            self.slice_results = status.payload.get('results', [])
            success_count = status.payload.get('success_count', 0)
            fail_count = status.payload.get('fail_count', 0)
            
            self._log_success(f"Slicing complete: {success_count} succeeded, {fail_count} failed")
            
            for r in self.slice_results:
                if r.get('ok'):
                    self._log_info(f"  ✓ {r['file_name']}")
                else:
                    self._log_warning(f"  ✗ {r['file_name']}: {r.get('message', 'Unknown error')}")
            
            if success_count > 0:
                self.save_btn.config(state=NORMAL)
        else:
            self._log_error(f"Slicing failed: {status.message}")
    
    def _run_slicing(self):
        """Run slicing operation on selected files."""
        files_to_slice = self._get_files_to_slice()
        
        if not files_to_slice:
            self._log_warning("No files to slice. Please load files first.")
            return
        
        operation = self.operation_var.get()
        self.run_btn.config(state=DISABLED)
        self.slice_results = []
        self.saved_paths = []
        self.save_btn.config(state=DISABLED)
        
        try:
            self._log_info(f"⏳ Running {operation} on {len(files_to_slice)} file(s)...")
            
            # Reset progress bar
            self.slice_progress['value'] = 0
            
            if operation == "Single Slice":
                start = int(self.start_var.get())
                length = int(self.length_var.get())
                
                min_size = min(f.file_size for f in files_to_slice if f.file_size)
                if start >= min_size:
                    self._log_error(f"Start position ({start}) exceeds smallest file size ({min_size})")
                    self.run_btn.config(state=NORMAL)
                    return
                
                result = self.manager.slice_files_single(files_to_slice, start, length)
                
            elif operation == "Equal Parts":
                parts = int(self.num_parts_var.get())
                if parts < 1:
                    self._log_error("Number of parts must be at least 1")
                    self.run_btn.config(state=NORMAL)
                    return
                
                for f in files_to_slice:
                    if f.file_size and f.file_size < parts:
                        self._log_warning(f"File '{f.file_name}' is too small ({f.file_size} bytes) for {parts} parts")
                
                result = self.manager.slice_files_equal_parts(files_to_slice, parts)
                
            elif operation == "Random Sampling":
                num_samples = int(self.num_samples_var.get())
                sample_size = int(self.sample_size_var.get())
                seed_str = self.seed_var.get().strip()
                seed = int(seed_str) if seed_str else None
                
                for f in files_to_slice:
                    if f.file_size and sample_size > f.file_size:
                        self._log_warning(f"Sample size ({sample_size}) exceeds file '{f.file_name}' size ({f.file_size})")
                
                result = self.manager.slice_files_random(files_to_slice, num_samples, sample_size, seed)
            
            if not result.ok:
                self.run_btn.config(state=NORMAL)
                self._log_error(f"Failed to start slicing: {result.message}")
                
        except ValueError as e:
            self.run_btn.config(state=NORMAL)
            self._log_error(f"Invalid parameter: {str(e)}")
    
    def _save_slices(self):
        """Save slice results to folder."""
        if not self.slice_results:
            self._log_warning("No slice results to save")
            return
        
        successful = [r for r in self.slice_results if r.get('ok')]
        if not successful:
            self._log_warning("No successful slices to save")
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
        
        operation = self.operation_var.get()
        saved_count = 0
        self.saved_paths = []

        try:
            for result in successful:                
                if operation == "Single Slice":
                    data = result.get('data', b'')
                    suggested = result['suggested_name']
                    out_path = output_path / suggested
                    with open(out_path, 'wb') as f:
                        f.write(data)
                    self._log_success(f"Saved: {suggested}")
                    self.saved_paths.append(out_path)
                    saved_count += 1
                    
                elif operation == "Equal Parts":
                    parts = result.get('parts', [])
                    for part in parts:
                        data = part.get('data', b'')
                        suggested = part['suggested_name']
                        out_path = output_path / suggested
                        with open(out_path, 'wb') as f:
                            f.write(data)
                        self._log_success(f"Saved: {suggested}")
                        self.saved_paths.append(out_path)
                        saved_count += 1
                    
                elif operation == "Random Sampling":
                    samples = result.get('samples', [])
                    for sample in samples:
                        data = sample.get('data', b'')
                        suggested = sample['suggested_name']
                        out_path = output_path / suggested
                        with open(out_path, 'wb') as f:
                            f.write(data)
                        self._log_success(f"Saved: {suggested}")
                        self.saved_paths.append(out_path)
                        saved_count += 1
                        
        except Exception as e:
            self._log_error(f"Save failed: {e}")
        
        self._log_info(f"Save complete: {saved_count} file(s) saved")
        
        # Add to input table if checkbox is checked
        if self.add_to_table_var.get() and self.saved_paths:
            str_paths = [str(p) for p in self.saved_paths]
            add_result = self.manager.add_files(str_paths)
            if add_result.ok:
                # Sliced files are binary
                added_items = add_result.payload.get('added', [])
                for item in added_items:
                    self.manager.set_file_type_for_item(item.id, "binary")
                self._log_success(f"Added {len(self.saved_paths)} sliced file(s) to Input table")
            else:
                self._log_warning(f"Could not add files to Input table: {add_result.message}")
        
        # Add to report - one entry per file
        if self.report_tab is not None and saved_count > 0:
            # Get parameters based on operation
            if operation == "Single Slice":
                params = f"start={self.start_var.get()}, len={self.length_var.get()}"
            elif operation == "Equal Parts":
                params = f"parts={self.num_parts_var.get()}"
            elif operation == "Random Sampling":
                seed_str = self.seed_var.get().strip()
                seed_info = f", seed={seed_str}" if seed_str else ""
                params = f"samples={self.num_samples_var.get()}, size={self.sample_size_var.get()}{seed_info}"
            else:
                params = ""
            
            for result in successful:
                file_name = result.get('file_name', 'Unknown')
                # Determine output files for this input
                if operation == "Single Slice":
                    output_file = result['suggested_name']
                    output_count = 1
                elif operation == "Equal Parts":
                    parts_count = len(result.get('parts', []))
                    output_file = f"{result['file_name']}_parts1-{parts_count}"
                    output_count = parts_count
                elif operation == "Random Sampling":
                    samples_count = len(result.get('samples', []))
                    output_file = f"{result['file_name']}_samples1-{samples_count}"
                    output_count = samples_count
                else:
                    output_file = "Unknown"
                    output_count = 1
                
                slice_data = {
                    'input_file': file_name,
                    'operation': operation,
                    'parameters': params,
                    'output_file': output_file,
                    'output_folder': output_dir,
                    'status_text': f'{output_count} file(s) saved'
                }
                self.report_tab.add_slicer_section(slice_data)
    
    def _reset_tab(self):
        """Reset tab to default state."""
        self.slice_results = []
        self.saved_paths = []
        self.save_btn.config(state=DISABLED)
        self.run_btn.config(state=NORMAL)
        
        # Reset progress bar
        self.slice_progress['value'] = 0
        
        self.file_selector_var.set("-- All Files --")
        self.operation_var.set("Single Slice")
        self.add_to_table_var.set(False)
        self._on_operation_changed(None)
        
        self._update_file_selector()
        
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready to slice data files...")
    
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
    
    def _on_slice_progress(self, status: OperationStatus):
        """Handle slicing progress update."""
        if status.payload:
            current = status.payload.get('current', 0)
            total = status.payload.get('total', 1)
            if total > 0:
                progress_pct = (current / total) * 100
                self.slice_progress['value'] = progress_pct
