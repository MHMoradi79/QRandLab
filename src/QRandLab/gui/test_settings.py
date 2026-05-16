# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Settings dialog windows for tests and preprocessing algorithms."""

import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from typing import Optional, List, Tuple, Dict
# Import dieharder settings
from .dieharder_settings import DieharderSettingsWindow, DieharderTestSelectorDialog, DIEHARDER_TESTS

class ENTSettingsWindow:
    """Modal dialog for ENT test settings."""
    
    ENT_OPTIONS = [
        "Bit stream",
        "Occurrence count",
        "Fold",
        "CSV output"
    ]
    
    def __init__(self, parent, current_states: List[int] = None, 
                 save_raw: bool = False, raw_output_path: str = ""):
        self.parent = parent
        self.current_states = current_states or [0, 0, 0, 0]
        self.save_raw = save_raw
        self.raw_output_path = raw_output_path
        self._result: Optional[Dict] = None
    
    def show(self) -> Optional[Dict]:
        """Show the modal dialog and return settings dict or None if cancelled."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("ENT Test Settings")
        # self._dialog.geometry("500x280")
        self._dialog.resizable(True, True)
        self._dialog.minsize(400, 250)
        
        # Build UI
        self._build_ui()
        
        # Make modal
        self._dialog.transient(self.parent)
        self._dialog.grab_set()
        self.parent.wait_window(self._dialog)
        
        return self._result
    
    def _build_ui(self):
        """Build the settings UI."""
        main_frame = ttk.Frame(self._dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Checkboxes label frame
        check_labelframe = ttk.Labelframe(
            main_frame,
            text="Select ENT Test Options",
            padding=10
        )
        check_labelframe.pack(fill=tk.X, pady=(0, 5))
        
        check_frame = check_labelframe
        
        # Configure grid to span whole frame
        check_frame.columnconfigure(0, weight=1)
        check_frame.columnconfigure(1, weight=1)
        
        self.check_vars = []
        for i, option in enumerate(self.ENT_OPTIONS):
            var = tk.BooleanVar(value=bool(self.current_states[i]))
            self.check_vars.append(var)
            
            cb = ttk.Checkbutton(
                check_frame,
                text=f"{i+1}. {option}",
                variable=var,
                bootstyle="primary"
            )
            row = i // 2
            col = i % 2
            cb.grid(row=row, column=col, sticky=tk.EW, padx=15, pady=5)
        
        # Save raw output option
        save_labelframe = ttk.Labelframe(
            main_frame,
            text="Raw Output",
            padding=10
        )
        save_labelframe.pack(fill=tk.X, pady=(5, 5))
        
        # Checkbox for save raw output
        self.save_raw_var = tk.BooleanVar(value=self.save_raw)
        ttk.Checkbutton(
            save_labelframe,
            text="Save raw output to folder",
            variable=self.save_raw_var,
            bootstyle="primary",
            command=self._toggle_path_entry
        ).pack(anchor=tk.W)
        
        # Path entry frame
        path_frame = ttk.Frame(save_labelframe)
        path_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(path_frame, text="Folder:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=self.raw_output_path)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=40)
        self.path_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_btn = ttk.Button(
            path_frame,
            text="Browse",
            command=self._browse_path,
            bootstyle="info-outline",
            width=8
        )
        self.browse_btn.pack(side=tk.LEFT)
        
        # Set initial state of path entry
        self._toggle_path_entry()
        
        # Buttons label frame
        button_labelframe = ttk.Labelframe(
            main_frame,
            text="Actions",
            padding=5
        )
        button_labelframe.pack(fill=tk.X, pady=(5, 0))
        
        # Create inner frame to center buttons
        button_inner = ttk.Frame(button_labelframe)
        button_inner.pack(anchor=tk.CENTER)
        
        ttk.Button(
            button_inner,
            text="Submit",
            command=self._submit,
            bootstyle="success",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Reset",
            command=self._reset,
            bootstyle="warning",
            width=10
        ).pack(side=tk.LEFT, padx=3)
    
    def _submit(self):
        """Submit the selected options."""
        self._result = {
            "states": [int(var.get()) for var in self.check_vars],
            "save_raw": self.save_raw_var.get(),
            "raw_output_path": self.path_var.get()
        }
        self._dialog.destroy()
    
    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self._dialog.destroy()
    
    def _reset(self):
        """Reset values without closing window."""
        for var in self.check_vars:
            var.set(False)
        self.save_raw_var.set(False)
        self.path_var.set("")
        self._toggle_path_entry()
    
    def _toggle_path_entry(self):
        """Enable/disable path entry based on save raw checkbox."""
        if self.save_raw_var.get():
            self.path_entry.config(state="normal")
            self.browse_btn.config(state="normal")
        else:
            self.path_entry.config(state="disabled")
            self.browse_btn.config(state="disabled")
    
    def _browse_path(self):
        """Open folder dialog to select save folder."""
        path = filedialog.askdirectory(
            parent=self._dialog,
            title="Select Folder for ENT Raw Output"
        )
        if path:
            self.path_var.set(path)


class NISTSettingsWindow:
    """Modal dialog for NIST test settings."""
    
    NIST_TESTS = [
        "01. Frequency Test (Monobit)",
        "02. Frequency Test within a Block",
        "03. Run Test",
        "04. Longest Run of Ones in a Block",
        "05. Binary Matrix Rank Test",
        "06. Discrete Fourier Transform (Spectral) Test",
        "07. Non-Overlapping Template Matching Test",
        "08. Overlapping Template Matching Test",
        "09. Maurer's Universal Statistical test",
        "10. Linear Complexity Test",
        "11. Serial test",
        "12. Approximate Entropy Test",
        "13. Cumulative Sums (Forward) Test",
        "14. Cumulative Sums (Reverse) Test",
        "15. Random Excursions Test",
        "16. Random Excursions Variant Test",
    ]
    
    def __init__(self, parent, current_states: List[int] = None, sequence_length: int = 1000000, use_whole_data: bool = False, p_value_threshold: float = 0.01):
        self.parent = parent
        self.current_states = current_states or [0] * 16
        self.sequence_length = sequence_length
        self.use_whole_data = use_whole_data
        self.p_value_threshold = p_value_threshold
        self._result: Optional[tuple] = None
    
    def show(self) -> Optional[tuple]:
        """Show the modal dialog and return (states, sequence_length, use_whole_data, p_value_threshold) or None if cancelled."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("NIST Test Settings")
        # self._dialog.geometry("800x400")
        self._dialog.resizable(True, True)
        self._dialog.minsize(700, 350)
        
        # Build UI
        self._build_ui()
        
        # Make modal
        self._dialog.transient(self.parent)
        self._dialog.grab_set()
        self.parent.wait_window(self._dialog)
        
        return self._result
    
    def _build_ui(self):
        """Build the settings UI."""
        main_frame = ttk.Frame(self._dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Checkboxes label frame
        check_labelframe = ttk.Labelframe(
            main_frame,
            text="Select NIST Statistical Tests",
            padding=10
        )
        check_labelframe.pack(fill=tk.X, pady=(0, 5))
        
        # Grid layout: 2 columns x 8 rows
        check_labelframe.columnconfigure(0, weight=1)
        check_labelframe.columnconfigure(1, weight=1)
        
        self.check_vars = []
        for i, test_name in enumerate(self.NIST_TESTS):
            var = tk.BooleanVar(value=bool(self.current_states[i]))
            self.check_vars.append(var)
            
            row = i % 8
            col = i // 8
            
            cb = ttk.Checkbutton(
                check_labelframe,
                text=test_name,
                variable=var,
                bootstyle="primary"
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=10, pady=2)
        
        # Sequence length settings label frame
        seq_labelframe = ttk.Labelframe(
            main_frame,
            text="Sequence Length",
            padding=10
        )
        seq_labelframe.pack(fill=tk.X, pady=(5, 5))
        
        ttk.Label(
            seq_labelframe,
            text="Sequence Length:",
            font=("Helvetica", 10)
        ).grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.seq_length_var = tk.StringVar(value=str(self.sequence_length))
        self.seq_length_entry = ttk.Entry(
            seq_labelframe,
            textvariable=self.seq_length_var,
            width=15
        )
        self.seq_length_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Use whole data checkbox
        self.use_whole_var = tk.BooleanVar(value=self.use_whole_data)
        ttk.Checkbutton(
            seq_labelframe,
            text="Use whole data",
            variable=self.use_whole_var,
            command=self._toggle_seq_length,
            bootstyle="primary"
        ).grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        
        # P-value threshold
        ttk.Label(
            seq_labelframe,
            text="P-value threshold:",
            font=("Helvetica", 10)
        ).grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.p_value_var = tk.StringVar(value=str(self.p_value_threshold))
        self.p_value_entry = ttk.Entry(
            seq_labelframe,
            textvariable=self.p_value_var,
            width=15
        )
        self.p_value_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(
            seq_labelframe,
            text="(0.0 - 1.0, default: 0.01)",
            font=("Helvetica", 8)
        ).grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        
        # Set initial state
        if self.use_whole_data:
            self._toggle_seq_length()
        
        # Buttons label frame
        button_labelframe = ttk.Labelframe(
            main_frame,
            text="Actions",
            padding=5
        )
        button_labelframe.pack(fill=tk.X, pady=(5, 0))
        
        # Create inner frame to center buttons
        button_inner = ttk.Frame(button_labelframe)
        button_inner.pack(anchor=tk.CENTER)
        
        ttk.Button(
            button_inner,
            text="Submit",
            command=self._submit,
            bootstyle="success",
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_inner,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_inner,
            text="Reset",
            command=self._reset,
            bootstyle="warning",
            width=10
        ).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(
            button_inner,
            text="Select All",
            command=self._select_all,
            bootstyle="info",
            width=10
        ).pack(side=tk.LEFT, padx=2)
    
    def _toggle_seq_length(self):
        """Toggle sequence length entry based on checkbox."""
        if self.use_whole_var.get():
            # Get actual data length if available
            try:
                if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                    with open(self.parent.manager.input_meta.file_path, 'r') as f:
                        data = f.read().strip()
                    self.seq_length_var.set(str(len(data)))
                else:
                    self.seq_length_var.set("N/A")
            except:
                self.seq_length_var.set("N/A")
            self.seq_length_entry.config(state='disabled')
        else:
            self.seq_length_entry.config(state='normal')
            if self.seq_length_var.get() in ["N/A", ""]:
                self.seq_length_var.set(str(self.sequence_length))
    
    def _submit(self):
        """Submit the selected tests."""
        try:
            use_whole = self.use_whole_var.get()
            
            if use_whole:
                # Get actual length from file
                if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                    with open(self.parent.manager.input_meta.file_path, 'r') as f:
                        data = f.read().strip()
                    seq_length = len(data)
                else:
                    seq_length = -1  # Indicator for use whole data
            else:
                seq_length = int(self.seq_length_var.get())
                if seq_length < 1:
                    messagebox.showerror("Invalid Input", "Sequence length must be at least 1")
                    return
                
                # Check if sequence length exceeds actual data length
                if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                    try:
                        with open(self.parent.manager.input_meta.file_path, 'r') as f:
                            data = f.read().strip()
                        actual_length = len(data)
                        if seq_length > actual_length:
                            messagebox.showerror("Invalid Input", f"Sequence length ({seq_length}) exceeds actual data length ({actual_length})")
                            return
                    except:
                        pass  # If we can't read the file, let the test handle it
            
            # Validate p-value threshold
            p_value_threshold = float(self.p_value_var.get())
            if p_value_threshold < 0.0 or p_value_threshold > 1.0:
                messagebox.showerror("Invalid Input", "P-value threshold must be between 0.0 and 1.0")
                return
            
            states = [int(var.get()) for var in self.check_vars]
            self._result = (states, seq_length, use_whole, p_value_threshold)
            self._dialog.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values")
    
    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self._dialog.destroy()
    
    def _reset(self):
        """Reset values without closing window."""
        for var in self.check_vars:
            var.set(False)
        self.seq_length_var.set("1000000")  # Default value
        self.use_whole_var.set(False)
        self.seq_length_entry.config(state='normal')
        self.p_value_var.set("0.01")
    
    def _select_all(self):
        """Select all tests."""
        for var in self.check_vars:
            var.set(True)
        messagebox.showwarning(
            "Warning",
            "Running all NIST tests may take a considerable amount of time."
        )

class BorelSettingsWindow:
    """Modal dialog for Borel test settings."""
    
    def __init__(self, parent, min_length: int = 2, max_length: int = 10, auto_mode: bool = False):
        self.parent = parent
        self.min_length = min_length
        self.max_length = max_length
        self.auto_mode = auto_mode
        self._result: Optional[Tuple[int, int, bool]] = None
    
    def show(self) -> Optional[Tuple[int, int]]:
        """Show the modal dialog and return (min_length, max_length) or None if cancelled."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("Borel Test Settings")
        # self._dialog.geometry("450x200")
        self._dialog.resizable(True, True)
        self._dialog.minsize(350, 180)
        
        # Build UI
        self._build_ui()
        
        # Make modal
        self._dialog.transient(self.parent)
        self._dialog.grab_set()
        self.parent.wait_window(self._dialog)
        
        return self._result
    
    def _build_ui(self):
        """Build the settings UI."""
        main_frame = ttk.Frame(self._dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Settings label frame
        settings_labelframe = ttk.Labelframe(
            main_frame,
            text="Borel Test Configuration",
            padding=10
        )
        settings_labelframe.pack(fill=tk.X, pady=(0, 5))
        
        settings_frame = settings_labelframe
        
        # Min Length
        ttk.Label(
            settings_frame,
            text="Minimum Pattern Length:",
            font=("Helvetica", 10)
        ).grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.min_var = tk.StringVar(value=str(self.min_length))
        ttk.Entry(
            settings_frame,
            textvariable=self.min_var,
            width=15
        ).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Max Length
        ttk.Label(
            settings_frame,
            text="Maximum Pattern Length:",
            font=("Helvetica", 10)
        ).grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.max_var = tk.StringVar(value=str(self.max_length))
        self.max_entry = ttk.Entry(
            settings_frame,
            textvariable=self.max_var,
            width=15
        )
        self.max_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Auto Max Length checkbox
        self.auto_max_var = tk.BooleanVar(value=self.auto_mode)
        auto_max_cb = ttk.Checkbutton(
            settings_frame,
            text="Auto",
            variable=self.auto_max_var,
            command=self._toggle_max_entry,
            bootstyle="primary"
        )
        auto_max_cb.grid(row=1, column=2, sticky=tk.W, pady=5, padx=5)
        
        # Set initial state
        if self.auto_mode:
            self._toggle_max_entry()
        
        # Buttons label frame
        button_labelframe = ttk.Labelframe(
            main_frame,
            text="Actions",
            padding=5
        )
        button_labelframe.pack(fill=tk.X, pady=(5, 0))
        
        # Create inner frame to center buttons
        button_inner = ttk.Frame(button_labelframe)
        button_inner.pack(anchor=tk.CENTER)
        
        ttk.Button(
            button_inner,
            text="Submit",
            command=self._submit,
            bootstyle="success",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Reset",
            command=self._reset,
            bootstyle="warning",
            width=10
        ).pack(side=tk.LEFT, padx=3)
    
    def _toggle_max_entry(self):
        """Toggle max entry field based on checkbox."""
        if self.auto_max_var.get():
            # Try to get data length from parent (testing_tab)
            try:
                if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                    # Read data to compute max
                    import numpy as np
                    with open(self.parent.manager.input_meta.file_path, 'r') as f:
                        data = f.read().strip()
                    computed_max = int(np.log2(len(data)))
                    self.max_var.set(str(computed_max))
                else:
                    self.max_var.set("10")
            except:
                self.max_var.set("10")
            self.max_entry.config(state='disabled')
        else:
            self.max_entry.config(state='normal')
            if self.max_var.get() in [""]:
                self.max_var.set(str(self.max_length))
    
    def _submit(self):
        """Submit the settings."""
        try:
            min_val = int(self.min_var.get())
            auto_mode = self.auto_max_var.get()
            
            # Get max value
            if auto_mode:
                max_str = self.max_var.get()
                if max_str.startswith("("):
                    # Compute actual max from data
                    if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                        import numpy as np
                        with open(self.parent.manager.input_meta.file_path, 'r') as f:
                            data = f.read().strip()
                        max_val = int(np.log2(len(data)))
                    else:
                        max_val = 10  # Default
                else:
                    max_val = int(max_str)
            else:
                max_val = int(self.max_var.get())
            
            # Validate minimum
            if min_val < 1:
                messagebox.showerror("Invalid Input", "Minimum pattern length must be at least 1")
                return
            
            # Validate maximum is reasonable (not too large)
            if max_val > 64:
                messagebox.showerror("Invalid Input", "Maximum pattern length should not exceed 64 bits")
                return
            
            # Validate logical relationship
            if max_val < min_val:
                messagebox.showerror("Invalid Input", "Maximum length must be >= minimum length")
                return
            
            # Validate against data length
            if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                try:
                    with open(self.parent.manager.input_meta.file_path, 'r') as f:
                        data = f.read().strip()
                    data_length = len(data)
                    # For Borel test, we need at least 2^max_val bits of data
                    required_length = 2 ** max_val
                    if data_length < required_length:
                        messagebox.showwarning("Warning", 
                            f"Data length ({data_length}) is less than recommended minimum ({required_length}) for max pattern length {max_val}.\n\nTest may not produce reliable results.")
                        # Allow to proceed with warning, not error
                except:
                    pass  # If we can't read the file, let the test handle it
            
            self._result = (min_val, max_val, auto_mode)
            self._dialog.destroy()
        
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integer values")
    
    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self._dialog.destroy()
    
    def _reset(self):
        """Reset values without closing window."""
        self.min_var.set("1")
        self.max_var.set("10")
        self.auto_max_var.set(False)
        self.max_entry.config(state='normal')


class AutocorrelationSettingsWindow:
    """Modal dialog for Autocorrelation test settings."""
    
    def __init__(self, parent, max_lag: int = 100, use_whole_data: bool = False):
        self.parent = parent
        self.max_lag = max_lag
        self.use_whole_data = use_whole_data
        self._result: Optional[tuple] = None
    
    def show(self) -> Optional[tuple]:
        """Show the modal dialog and return (max_lag, use_whole_data) or None if cancelled."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("Autocorrelation Test Settings")
        # self._dialog.geometry("450x160")
        self._dialog.resizable(True, True)
        self._dialog.minsize(350, 150)
        
        # Build UI
        self._build_ui()
        
        # Make modal
        self._dialog.transient(self.parent)
        self._dialog.grab_set()
        self.parent.wait_window(self._dialog)
        
        return self._result
    
    def _build_ui(self):
        """Build the settings UI."""
        main_frame = ttk.Frame(self._dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Settings label frame
        settings_labelframe = ttk.Labelframe(
            main_frame,
            text="Configuration",
            padding=10
        )
        settings_labelframe.pack(fill=tk.X, pady=(0, 5))
        
        # Max lag
        ttk.Label(
            settings_labelframe,
            text="Maximum Lag:",
            font=("Helvetica", 10)
        ).grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        self.max_lag_var = tk.StringVar(value=str(self.max_lag))
        self.max_lag_entry = ttk.Entry(
            settings_labelframe,
            textvariable=self.max_lag_var,
            width=15
        )
        self.max_lag_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        
        # Use whole data checkbox
        self.use_whole_var = tk.BooleanVar(value=self.use_whole_data)
        ttk.Checkbutton(
            settings_labelframe,
            text="Use whole data",
            variable=self.use_whole_var,
            command=self._toggle_max_lag,
            bootstyle="primary"
        ).grid(row=0, column=2, sticky=tk.W, pady=5, padx=5)
        
        # Set initial state
        if self.use_whole_data:
            self._toggle_max_lag()
        
        # Buttons label frame
        button_labelframe = ttk.Labelframe(
            main_frame,
            text="Actions",
            padding=5
        )
        button_labelframe.pack(fill=tk.X, pady=(5, 0))
        
        # Center buttons
        button_inner = ttk.Frame(button_labelframe)
        button_inner.pack(anchor=tk.CENTER)
        
        ttk.Button(
            button_inner,
            text="Submit",
            command=self._submit,
            bootstyle="success",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Reset",
            command=self._reset,
            bootstyle="warning",
            width=10
        ).pack(side=tk.LEFT, padx=3)
    
    def _toggle_max_lag(self):
        """Toggle max lag entry based on checkbox."""
        if self.use_whole_var.get():
            # Get actual data length if available
            try:
                if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                    with open(self.parent.manager.input_meta.file_path, 'r') as f:
                        data = f.read().strip()
                    self.max_lag_var.set(str(len(data) - 1))
                else:
                    self.max_lag_var.set(str(self.max_lag))
            except:
                self.max_lag_var.set(str(self.max_lag))
            self.max_lag_entry.config(state='disabled')
        else:
            self.max_lag_entry.config(state='normal')
            if self.max_lag_var.get() == "":
                self.max_lag_var.set(str(self.max_lag))
    
    def _submit(self):
        """Submit the settings."""
        try:
            use_whole = self.use_whole_var.get()
            
            if use_whole:
                max_lag = -1  # Special value indicating use whole data
            else:
                max_lag = int(self.max_lag_var.get())
                if max_lag < 1:
                    messagebox.showerror("Invalid Input", "Maximum lag must be at least 1")
                    return
                
                # Check if max_lag exceeds actual data length - 1
                if hasattr(self.parent, 'manager') and self.parent.manager.input_meta.file_path:
                    try:
                        with open(self.parent.manager.input_meta.file_path, 'r') as f:
                            data = f.read().strip()
                        actual_length = len(data)
                        if max_lag >= actual_length:
                            messagebox.showerror("Invalid Input", f"Maximum lag ({max_lag}) must be less than data length ({actual_length})")
                            return
                    except:
                        pass  # If we can't read the file, let the test handle it
            
            self._result = (max_lag, use_whole)
            self._dialog.destroy()
        
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer value")
    
    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self._dialog.destroy()
    
    def _reset(self):
        """Reset values without closing window."""
        self.max_lag_var.set("100")  # Default value
        self.use_whole_var.set(False)
        self.max_lag_entry.config(state='normal')


class TZExtractorSettingsWindow:
    """Modal dialog for Toeplitz Extractor settings."""
    
    def __init__(self, parent, settings: Dict = None, input_filename: str = None):
        self.parent = parent
        self.input_filename = input_filename or "output"
        # Generate default filenames based on input file
        default_output = f"{self.input_filename}_TZE.bin"
        default_tzm = f"{self.input_filename}_TZM.txt"
        self.settings = settings or {
            'n': '256',
            'l': '128',
            'output': default_output,
            'tzm_file': default_tzm,
            'save_tzm': False,
            'submitted': False
        }
        # Update output filenames if they are default values
        if self.settings['output'] in ('output_TZE.bin', default_output):
            self.settings['output'] = default_output
        if self.settings['tzm_file'] in ('output_TZM.txt', default_tzm):
            self.settings['tzm_file'] = default_tzm
        self._result: Optional[Dict] = None
    
    def show(self) -> Optional[Dict]:
        """Show the modal dialog and return settings dict or None if cancelled."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("Toeplitz Extractor Settings")
        # self._dialog.geometry("500x380")
        self._dialog.resizable(True, True)
        self._dialog.minsize(400, 320)
        
        # Build UI
        self._build_ui()
        
        # Make modal
        self._dialog.transient(self.parent)
        self._dialog.grab_set()
        self.parent.wait_window(self._dialog)
        
        return self._result
    
    def _build_ui(self):
        """Build the settings UI."""
        main_frame = ttk.Frame(self._dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Parameters labelframe
        params_labelframe = ttk.Labelframe(
            main_frame,
            text="Parameters",
            padding=10
        )
        params_labelframe.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # n parameter
        ttk.Label(
            params_labelframe,
            text="n (multiple of 64):",
            font=("Helvetica", 10)
        ).grid(row=0, column=0, sticky=tk.W, pady=6, padx=5)
        
        self.n_var = tk.StringVar(value=self.settings['n'])
        ttk.Entry(
            params_labelframe,
            textvariable=self.n_var,
            width=20
        ).grid(row=0, column=1, sticky=tk.W, pady=6, padx=5)
        
        # l parameter
        ttk.Label(
            params_labelframe,
            text="l (multiple of 64):",
            font=("Helvetica", 10)
        ).grid(row=1, column=0, sticky=tk.W, pady=6, padx=5)
        
        self.l_var = tk.StringVar(value=self.settings['l'])
        ttk.Entry(
            params_labelframe,
            textvariable=self.l_var,
            width=20
        ).grid(row=1, column=1, sticky=tk.W, pady=6, padx=5)
        
        # Output file
        ttk.Label(
            params_labelframe,
            text="Output File:",
            font=("Helvetica", 10)
        ).grid(row=2, column=0, sticky=tk.W, pady=6, padx=5)
        
        self.output_var = tk.StringVar(value=self.settings['output'])
        ttk.Entry(
            params_labelframe,
            textvariable=self.output_var,
            width=30
        ).grid(row=2, column=1, sticky=tk.W, pady=6, padx=5)
        
        # Save TZM checkbox
        self.save_tzm_var = tk.BooleanVar(value=self.settings['save_tzm'])
        ttk.Checkbutton(
            params_labelframe,
            text="Save TZM Matrix File",
            variable=self.save_tzm_var,
            command=self._toggle_tzm,
            bootstyle="round-toggle"
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=6, padx=5)
        
        # TZM file
        ttk.Label(
            params_labelframe,
            text="TZM File:",
            font=("Helvetica", 10)
        ).grid(row=4, column=0, sticky=tk.W, pady=6, padx=5)
        
        self.tzm_var = tk.StringVar(value=self.settings['tzm_file'])
        self.tzm_entry = ttk.Entry(
            params_labelframe,
            textvariable=self.tzm_var,
            width=30,
            state=tk.NORMAL if self.settings['save_tzm'] else tk.DISABLED
        )
        self.tzm_entry.grid(row=4, column=1, sticky=tk.W, pady=6, padx=5)
        
        # Info label
        info_label = ttk.Label(
            params_labelframe,
            text="ℹ️ Both n and l must be non-zero multiples of 64",
            font=("Helvetica", 9, "italic"),
            bootstyle="info",
        )
        info_label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Actions labelframe
        actions_labelframe = ttk.Labelframe(
            main_frame,
            text="Actions",
            padding=10
        )
        actions_labelframe.pack(fill=tk.X, pady=(10, 0))
        
        # Create inner frame to center buttons
        button_inner = ttk.Frame(actions_labelframe)
        button_inner.pack(anchor=tk.CENTER, pady=5)
        
        ttk.Button(
            button_inner,
            text="Submit",
            command=self._submit,
            bootstyle="success",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Default",
            command=self._default,
            bootstyle="info",
            width=10
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Clear",
            command=self._clear,
            bootstyle="secondary",
            width=10
        ).pack(side=tk.LEFT, padx=3)
    
    def _toggle_tzm(self):
        """Toggle TZM entry state."""
        if self.save_tzm_var.get():
            self.tzm_entry.config(state=tk.NORMAL)
        else:
            self.tzm_entry.config(state=tk.DISABLED)
    
    def _submit(self):
        """Submit the settings."""
        try:
            n_val = int(self.n_var.get())
            l_val = int(self.l_var.get())
            
            # Validation
            if n_val % 64 != 0 or l_val % 64 != 0 or n_val == 0 or l_val == 0:
                messagebox.showerror("Invalid Input", "Both 'n' and 'l' must be non-zero multiples of 64")
                return
            
            # Validate reasonable range (prevent excessive values)
            if n_val > 1000000 or l_val > 1000000:
                messagebox.showerror("Invalid Input", "Values for 'n' and 'l' should not exceed 1,000,000")
                return
            
            # Validate output file is specified
            if not self.output_var.get().strip():
                messagebox.showerror("Invalid Input", "Please specify an output file")
                return
            
            # Validate TZM file if save_tzm is enabled
            if self.save_tzm_var.get() and not self.tzm_var.get().strip():
                messagebox.showerror("Invalid Input", "Please specify a TZM matrix file or uncheck 'Save TZM'")
                return
            
            self._result = {
                'n': str(n_val),
                'l': str(l_val),
                'output': self.output_var.get(),
                'tzm_file': self.tzm_var.get(),
                'save_tzm': self.save_tzm_var.get(),
                'submitted': True
            }
            self._dialog.destroy()
        
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid integer values for 'n' and 'l'")
    
    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self._dialog.destroy()
    
    def _default(self):
        """Set default values based on input filename."""
        self.n_var.set("256")
        self.l_var.set("128")
        self.output_var.set(f"{self.input_filename}_TZE.bin")
        self.tzm_var.set(f"{self.input_filename}_TZM.txt")
        self.save_tzm_var.set(False)
        self._toggle_tzm()
    
    def _clear(self):
        """Clear all values to defaults based on input filename."""
        self.n_var.set("256")
        self.l_var.set("128")
        self.output_var.set(f"{self.input_filename}_TZE.bin")
        self.tzm_var.set(f"{self.input_filename}_TZM.txt")
        self.save_tzm_var.set(False)
        self._toggle_tzm()
