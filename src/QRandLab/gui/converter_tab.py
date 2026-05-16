# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""File converter tab for multi-file format conversion."""

import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path

from ..manager.core_manager import CoreManager
from ..core.types import OperationStatus, FileItem, FileType


class ConverterTab(ttk.Frame):
    """Multi-file format converter tab."""
    
    def __init__(self, parent, manager: CoreManager):
        super().__init__(parent, padding=20)
        self.manager = manager
        self.conversion_results = []  # Store results for multi-file
        self.report_tab = None  # Will be set by main window
        
        # Subscribe to events
        self._setup_events()
        
        # Build UI
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to manager events."""
        self.manager.on_files_converted.subscribe(self._on_files_converted)
        self.manager.on_files_added.subscribe(self._on_files_changed)
        self.manager.on_files_removed.subscribe(self._on_files_changed)
        self.manager.on_file_type_changed.subscribe(self._on_files_changed)
        self.manager.on_files_cleared.subscribe(self._on_files_cleared)
        self.manager.on_convert_progress.subscribe(self._on_convert_progress)
    
    def _build_ui(self):
        """Build converter tab UI."""
        # Source Files Section
        source_frame = ttk.LabelFrame(self, text="Source Files", padding=15, bootstyle=INFO)
        source_frame.pack(fill=X, pady=(0, 15))
        
        # File selection row
        select_label = ttk.Label(source_frame, text="Select Files:", font=("Helvetica", 10, "bold"))
        select_label.grid(row=0, column=0, sticky=W, pady=5)
        
        # File selector combobox
        self.file_selector_var = tk.StringVar(value="-- All Files --")
        self.file_selector = ttk.Combobox(
            source_frame,
            textvariable=self.file_selector_var,
            state="readonly",
            width=40
        )
        self.file_selector.grid(row=0, column=1, sticky=EW, padx=(10, 0), pady=5)
        self.file_selector.bind("<<ComboboxSelected>>", self._on_file_selection_changed)
        
        source_frame.columnconfigure(1, weight=1)
        
        # File types info label
        type_label = ttk.Label(source_frame, text="Source Types:", font=("Helvetica", 10, "bold"))
        type_label.grid(row=1, column=0, sticky=W, pady=5)
        
        self.source_types_var = tk.StringVar(value="--")
        type_value = ttk.Label(source_frame, textvariable=self.source_types_var, font=("Helvetica", 10))
        type_value.grid(row=1, column=1, sticky=W, padx=(10, 0), pady=5)
        
        # Container for Configuration and Actions side by side
        config_container = ttk.Frame(self)
        config_container.pack(fill=X, pady=(0, 15))
        config_container.columnconfigure(0, weight=1)
        config_container.columnconfigure(1, weight=0)
        
        # Conversion Options Section
        config_frame = ttk.LabelFrame(config_container, text="Conversion Options", padding=15, bootstyle=INFO)
        config_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        # Target format selection
        target_label = ttk.Label(config_frame, text="Convert To:", font=("Helvetica", 10, "bold"))
        target_label.grid(row=0, column=0, sticky=W, pady=5)
        
        self.target_format_var = tk.StringVar()
        self.format_combo = ttk.Combobox(
            config_frame,
            textvariable=self.target_format_var,
            values=["binary", "string01", "hex", "uint8", "uint16", "uint32", "uint64"],
            state="readonly",
            width=18
        )
        self.format_combo.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=W)
        self.format_combo.set("hex")
        self.format_combo.bind("<<ComboboxSelected>>", self._update_default_tag)
        
        # Output tag entry
        tag_label = ttk.Label(config_frame, text="Output Tag:", font=("Helvetica", 10, "bold"))
        tag_label.grid(row=1, column=0, sticky=W, pady=5)
        
        self.tag_var = tk.StringVar(value="")
        self.tag_entry = ttk.Entry(config_frame, textvariable=self.tag_var, width=20)
        self.tag_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=W)
        
        # Checkbox to add converted files to input table
        self.add_to_table_var = tk.BooleanVar(value=False)
        add_checkbox = ttk.Checkbutton(
            config_frame,
            text="Add converted files to Input table",
            variable=self.add_to_table_var,
            bootstyle="info-round-toggle"
        )
        add_checkbox.grid(row=2, column=0, columnspan=2, sticky=W, pady=10)
        
        config_frame.columnconfigure(1, weight=1)
        
        # Actions Section
        actions_frame = ttk.LabelFrame(config_container, text="Actions", padding=15, bootstyle="success")
        actions_frame.grid(row=0, column=1, sticky="nsew")
        
        # Inner frame
        btn_inner = ttk.Frame(actions_frame)
        btn_inner.pack(expand=YES, anchor='n')

        # Convert button
        self.convert_btn = ttk.Button( btn_inner, text="Convert", command=self._convert_files, bootstyle="success", width=12)
        self.convert_btn.pack(pady=3, fill='both', anchor='n')    

        # Progress bar for conversion
        self.convert_progress = ttk.Progressbar(btn_inner, length=80, mode='determinate', bootstyle="success-striped")
        self.convert_progress.pack(pady=3, fill='both', anchor='n')
        
        # Save button
        self.save_btn = ttk.Button( btn_inner, text="Save", command=self._save_converted, bootstyle="primary", width=12, state=DISABLED)
        self.save_btn.pack(pady=3, fill='both', anchor='n')
        
        # Reset button
        reset_btn = ttk.Button( btn_inner, text="Reset", command=self._reset_tab, bootstyle="secondary", width=12)
        reset_btn.pack(pady=3, fill='both', anchor='n')
        
        # Status Section
        status_frame = ttk.LabelFrame(self, text="Conversion Status", padding=15, bootstyle="info")
        status_frame.pack(fill=BOTH, expand=YES)
        
        self.status_text = tk.Text(
            status_frame,
            height=12,
            wrap=tk.WORD,
            font=("Courier", 9),
            bg="#2b2b2b",
            fg="#ffffff",
            state=DISABLED
        )
        self.status_text.pack(fill=BOTH, expand=YES, pady=5)
        
        # Configure text tags for colored output
        self.status_text.tag_configure("success", foreground="#4CAF50")
        self.status_text.tag_configure("error", foreground="#F44336")
        self.status_text.tag_configure("warning", foreground="#FF9800")
        
        # Scrollbar for status text
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Initial state
        self._update_file_selector()
        self._log_info("Ready to convert files...")
    
    def _update_file_selector(self):
        """Update the file selector combobox with available files."""
        files = self.manager.get_all_files()
        
        if not files:
            self.file_selector['values'] = ["-- No files loaded --"]
            self.file_selector_var.set("-- No files loaded --")
            self.source_types_var.set("--")
            return
        
        # Build options list
        options = ["-- All Files --"]
        for f in files:
            type_str = f.file_type.value if f.file_type else "no type"
            options.append(f"{f.file_name}{f.file_ext.value} ({type_str})")
        
        self.file_selector['values'] = options
        
        # Keep current selection if valid, otherwise reset to All Files
        current = self.file_selector_var.get()
        if current not in options:
            self.file_selector_var.set("-- All Files --")
        
        self._update_source_types()
    
    def _on_file_selection_changed(self, event=None):
        """Handle file selection change."""
        self._update_source_types()
    
    def _update_source_types(self):
        """Update source types display based on selected files."""
        selected = self.file_selector_var.get()
        
        if selected == "-- All Files --":
            # Show all unique types
            files = self.manager.get_all_files()
            types_with_type = [f.file_type.value for f in files if f.file_type]
            if types_with_type:
                unique_types = sorted(set(types_with_type))
                self.source_types_var.set(", ".join(unique_types))
            else:
                self.source_types_var.set("-- (no types set)")
        elif selected == "-- No files loaded --":
            self.source_types_var.set("--")
        else:
            # Get specific file type
            file_item = self._get_selected_file()
            if file_item and file_item.file_type:
                self.source_types_var.set(file_item.file_type.value)
            else:
                self.source_types_var.set("-- (type not set)")
    
    def _get_selected_file(self):
        """Get the FileItem for the selected file (if single file selected)."""
        selected = self.file_selector_var.get()
        if selected in ("-- All Files --", "-- No files loaded --"):
            return None
        
        # Parse file name from selection
        files = self.manager.get_all_files()
        for f in files:
            display_name = f"{f.file_name}{f.file_ext.value}"
            if selected.startswith(display_name):
                return f
        return None
    
    def _get_files_to_convert(self):
        """Get list of FileItems to convert based on selection."""
        selected = self.file_selector_var.get()
        
        if selected == "-- No files loaded --":
            return []
        
        if selected == "-- All Files --":
            # Return all files that have a type set
            files = self.manager.get_all_files()
            return [f for f in files if f.file_type]
        
        # Single file
        file_item = self._get_selected_file()
        return [file_item] if file_item and file_item.file_type else []
    
    def _update_default_tag(self, event=None):
        """Update default tag based on selected format."""
        format_val = self.target_format_var.get()
        self.tag_var.set(f"_{format_val}" if format_val else "")
    
    def _on_files_changed(self, status: OperationStatus):
        """Handle files added/removed/type changed events."""
        self._update_file_selector()
    
    def _on_files_cleared(self, status: OperationStatus):
        """Handle files cleared event."""
        self._update_file_selector()
        self.conversion_results = []
        self.save_btn.config(state=DISABLED)
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready to convert files...")
    
    def _on_files_converted(self, status: OperationStatus):
        """Handle multi-file conversion completion."""
        self.convert_btn.config(state=NORMAL)
        # Progress bar stays full after completion
        
        if status.ok and status.payload:
            results = status.payload.get('results', [])
            self.conversion_results = results
            
            success_count = status.payload.get('success_count', 0)
            fail_count = status.payload.get('fail_count', 0)
            
            self._log_success(f"Conversion complete: {success_count} succeeded, {fail_count} failed")
            
            # Log details
            for r in results:
                if r['ok']:
                    self._log_info(f"  ✓ {r['file_name']}: {r.get('source_type', '?')} → {r.get('output_format', '?')}")
                else:
                    self._log_warning(f"  ✗ {r['file_name']}: {r['message']}")
            
            if success_count > 0:
                self.save_btn.config(state=NORMAL)
        else:
            self._log_error(f"Conversion failed: {status.message}")
    
    def _convert_files(self):
        """Convert selected files to target format."""
        files_to_convert = self._get_files_to_convert()
        
        if not files_to_convert:
            self._log_warning("No files to convert. Make sure files have types set.")
            return
        
        target_format = self.target_format_var.get()
        if not target_format:
            self._log_warning("Please select a target format")
            return
        
        tag = self.tag_var.get().strip()
        
        # Disable convert button
        self.convert_btn.config(state=DISABLED)
        self.conversion_results = []
        self.save_btn.config(state=DISABLED)
        
        # Log start
        self._log_info(f"⏳ Converting {len(files_to_convert)} file(s) to {target_format}...")
        
        # Reset progress bar
        self.convert_progress['value'] = 0
        
        # Start conversion
        result = self.manager.convert_files(files_to_convert, target_format, tag)
        
        if not result.ok:
            self.convert_btn.config(state=NORMAL)
            self._log_error(f"Failed to start conversion: {result.message}")
    
    def _save_converted(self):
        """Save converted files to a folder."""
        if not self.conversion_results:
            self._log_warning("No conversion results to save")
            return
        
        # Filter only successful results
        successful = [r for r in self.conversion_results if r.get('ok') and r.get('data')]
        
        if not successful:
            self._log_warning("No successful conversions to save")
            return
        
        # Open folder dialog
        output_dir = filedialog.askdirectory(
            title="Select Output Folder",
            initialdir=self.manager.get_last_directory()
        )
        
        if not output_dir:
            self._log_warning("Save cancelled by user")
            return
        
        self.manager.set_last_directory(output_dir)
        output_path = Path(output_dir)
        
        saved_count = 0
        failed_count = 0
        saved_paths = []
        
        for result in successful:
            try:
                out_name = result.get('suggested_name', f"{result['file_name']}_converted")
                out_path = output_path / out_name
                data = result['data']
                output_format = result.get('output_format', 'binary')
                
                # Save based on format
                if output_format == "binary":
                    with open(out_path, 'wb') as f:
                        if isinstance(data, str):
                            f.write(bytes.fromhex(data))
                        else:
                            f.write(data)
                else:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        if isinstance(data, bytes):
                            f.write(data.decode('utf-8', errors='ignore'))
                        else:
                            f.write(str(data))
                
                saved_count += 1
                saved_paths.append(out_path)
                self._log_success(f"Saved: {out_name}")
                
            except Exception as e:
                failed_count += 1
                self._log_error(f"Failed to save {result.get('file_name', '?')}: {e}")
        
        self._log_info(f"Save complete: {saved_count} saved, {failed_count} failed")
        
        # Add to input table if checkbox is checked
        if self.add_to_table_var.get() and saved_paths:
            str_paths = [str(p) for p in saved_paths]
            add_result = self.manager.add_files(str_paths)
            if add_result.ok:
                # Set file type for newly added files based on output format
                target_format = self.target_format_var.get()
                added_items = add_result.payload.get('added', [])
                for item in added_items:
                    self.manager.set_file_type_for_item(item.id, target_format)
                self._log_success(f"Added {len(saved_paths)} converted file(s) to Input table")
            else:
                self._log_warning(f"Could not add files to Input table: {add_result.message}")
        
        # Update main window status bar
        self._update_main_status_bar()
        
        # Add to report - one row per file
        if self.report_tab is not None and saved_count > 0:
            target_format = self.target_format_var.get()
            for i, result in enumerate(successful):
                if i < len(saved_paths):
                    out_name = saved_paths[i].name
                else:
                    out_name = result.get('suggested_name', 'unknown')
                conversion_data = {
                    'input_file': result.get('file_name', 'N/A'),
                    'input_type': result.get('source_type', 'N/A'),
                    'output_type': target_format,
                    'output_file': out_name,
                    'status_text': 'Success'
                }
                self.report_tab.add_converter_section(conversion_data)
    
    def _reset_tab(self):
        """Reset tab to default state."""
        # Clear conversion results
        self.conversion_results = []
        self.save_btn.config(state=DISABLED)
        self.convert_btn.config(state=NORMAL)
        
        # Reset progress bar
        self.convert_progress['value'] = 0
        
        # Reset to defaults
        self.file_selector_var.set("-- All Files --")
        self.target_format_var.set("hex")
        self.tag_var.set("")
        self.add_to_table_var.set(False)
        
        # Refresh file selector
        self._update_file_selector()
        
        # Clear status
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready to convert files...")
    
    def _update_main_status_bar(self):
        """Update main window status bar."""
        main_window = self.winfo_toplevel()
        if hasattr(main_window, 'update_file_info'):
            main_window.update_file_info()
    
    def _log_success(self, message: str):
        """Log success message in green."""
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"✓ {message}\n", "success")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _log_error(self, message: str):
        """Log error message in red."""
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"✗ {message}\n", "error")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _log_warning(self, message: str):
        """Log warning message in orange."""
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"⚠ {message}\n", "warning")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _log_info(self, message: str):
        """Log info message."""
        self.status_text.config(state=NORMAL)
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=DISABLED)
    
    def _on_convert_progress(self, status: OperationStatus):
        """Handle conversion progress update."""
        if status.payload:
            current = status.payload.get('current', 0)
            total = status.payload.get('total', 1)
            if total > 0:
                progress_pct = (current / total) * 100
                self.convert_progress['value'] = progress_pct
