# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Comprehensive Dieharder test settings window implementation."""

import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from typing import Optional, Dict, List, Any


# List of all 32 dieharder tests with reliability ratings
DIEHARDER_TESTS = [
    (0, "Diehard Birthdays Test", "Good"),
    (1, "Diehard OPERM5 Test", "Good"),
    (2, "Diehard 32x32 Binary Rank Test", "Good"),
    (3, "Diehard 6x8 Binary Rank Test", "Good"),
    (4, "Diehard Bitstream Test", "Good"),
    (5, "Diehard OPSO", "Suspect"),
    (6, "Diehard OQSO Test", "Suspect"),
    (7, "Diehard DNA Test", "Suspect"),
    (8, "Diehard Count the 1s (stream) Test", "Good"),
    (9, "Diehard Count the 1s Test (byte)", "Good"),
    (10, "Diehard Parking Lot Test", "Good"),
    (11, "Diehard Minimum Distance (2d Circle) Test", "Good"),
    (12, "Diehard 3d Sphere (Minimum Distance) Test", "Good"),
    (13, "Diehard Squeeze Test", "Good"),
    (14, "Diehard Sums Test", "Do Not Use"),
    (15, "Diehard Runs Test", "Good"),
    (16, "Diehard Craps Test", "Good"),
    (17, "Marsaglia and Tsang GCD Test", "Good"),
    (100, "STS Monobit Test", "Good"),
    (101, "STS Runs Test", "Good"),
    (102, "STS Serial Test (Generalized)", "Good"),
    (200, "RGB Bit Distribution Test", "Good"),
    (201, "RGB Generalized Minimum Distance Test", "Good"),
    (202, "RGB Permutations Test", "Good"),
    (203, "RGB Lagged Sum Test", "Good"),
    (204, "RGB Kolmogorov-Smirnov Test Test", "Good"),
    (205, "Byte Distribution", "Good"),
    (206, "DAB DCT", "Good"),
    (207, "DAB Fill Tree Test", "Good"),
    (208, "DAB Fill Tree 2 Test", "Good"),
    (209, "DAB Monobit 2 Test", "Good"),
    (210, "DAB Diehard Birthdays Test", "Good"),
]


class DieharderTestSelectorDialog:
    """Dialog for selecting specific dieharder tests."""
    
    def __init__(self, parent, selected_tests: List[int] = None):
        self.parent = parent
        self.selected_tests = selected_tests or []
        self._result: Optional[List[int]] = None
    
    def show(self) -> Optional[List[int]]:
        """Show the test selector dialog."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("Select Dieharder Tests")
        # self._dialog.geometry("450x500")
        self._dialog.resizable(True, True)
        self._dialog.minsize(400, 400)
        
        self._build_ui()
        
        # Make modal
        self._dialog.transient(self.parent)
        self._dialog.grab_set()
        self.parent.wait_window(self._dialog)
        
        return self._result
    
    def _build_ui(self):
        """Build the test selector UI."""
        main_frame = ttk.Frame(self._dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Select Dieharder Tests (32 total)",
            font=("Helvetica", 11, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Scrollable frame for tests
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        canvas = tk.Canvas(canvas_frame, height=300)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # ensure we unbind before destroying dialog
        def _on_close():
            canvas.unbind_all("<MouseWheel>")
            self._dialog.destroy()

        self._dialog.protocol("WM_DELETE_WINDOW", _on_close)

        # Group tests by category
        test_groups = [
            ("Diehard Tests", [(n, name, rel) for n, name, rel in DIEHARDER_TESTS if 0 <= n <= 16]),
            ("Marsaglia Tests", [(n, name, rel) for n, name, rel in DIEHARDER_TESTS if n == 17]),
            ("STS Tests", [(n, name, rel) for n, name, rel in DIEHARDER_TESTS if 100 <= n <= 102]),
            ("RGB Tests", [(n, name, rel) for n, name, rel in DIEHARDER_TESTS if 200 <= n <= 205]),
            ("DAB Tests", [(n, name, rel) for n, name, rel in DIEHARDER_TESTS if 206 <= n <= 211]),
        ]
        
        # Create checkboxes grouped by category
        self.test_vars = []
        for group_name, tests in test_groups:
            if not tests:
                continue
            
            # Create label frame for group
            group_frame = ttk.Labelframe(scrollable_frame, text=group_name, padding=10)
            group_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Use grid layout within group
            row = 0
            col = 0
            max_cols = 1  # One column for better readability
            
            for test_num, test_name, reliability in tests:
                var = tk.BooleanVar(value=(test_num in self.selected_tests))
                self.test_vars.append((test_num, var))
                
                # Color code by reliability
                style = "success" if reliability == "Good" else "warning" if reliability == "Suspect" else "danger"
                
                cb = ttk.Checkbutton(
                    group_frame,
                    text=f"{test_num:3d} - {test_name}",
                    variable=var,
                    bootstyle=style
                )
                cb.grid(row=row, column=col, sticky=tk.W+tk.E, padx=5, pady=2)
                
                # Add reliability label if not Good
                if reliability != "Good":
                    ttk.Label(
                        group_frame,
                        text=f"({reliability})",
                        font=("Helvetica", 8, "italic"),
                        bootstyle=style
                    ).grid(row=row, column=col+1, sticky=tk.W, padx=(5, 0), pady=2)
                
                row += 1
                if row >= 99:  # Prevent overflow, though unlikely
                    row = 0
                    col += max_cols
            
            # Configure grid weights for expansion
            group_frame.columnconfigure(0, weight=1)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Actions labelframe 
        actions_frame = ttk.LabelFrame(main_frame, text="Actions")
        actions_frame.pack(fill=tk.X, pady=(0, 10))

        buttons_row = ttk.Frame(actions_frame)
        buttons_row.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(
            buttons_row,
            text="Select All",
            command=self._select_all,
            bootstyle="info-outline",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_row,
            text="Deselect All",
            command=self._deselect_all,
            bootstyle="secondary-outline",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_row,
            text="Select Good Only",
            command=self._select_good,
            bootstyle="success-outline",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_row,
            text="OK",
            command=self._ok,
            bootstyle="success",
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            buttons_row,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
        ).pack(side=tk.LEFT, padx=5)

    def _select_all(self):
        """Select all tests."""
        for _, var in self.test_vars:
            var.set(True)
    
    def _deselect_all(self):
        """Deselect all tests."""
        for _, var in self.test_vars:
            var.set(False)
    
    def _select_good(self):
        """Select only tests marked as 'Good'."""
        for i, (test_num, var) in enumerate(self.test_vars):
            reliability = DIEHARDER_TESTS[i][2]
            var.set(reliability == "Good")
    
    def _ok(self):
        """Confirm selection."""
        selected = [test_num for test_num, var in self.test_vars if var.get()]
        if not selected:
            messagebox.showerror("Error", "Please select at least one test")
            return
        self._result = selected
        self._dialog.destroy()
    
    def _cancel(self):
        """Cancel selection."""
        self._result = None
        self._dialog.destroy()


class DieharderSettingsWindow:
    """Modal dialog for Dieharder test settings."""
    
    def __init__(self, parent, current_settings: Dict[str, Any] = None):
        self.parent = parent
        # Default settings
        self.settings = current_settings or {
            'test_mode': 'specific',
            'selected_tests': [],
            'psamples': 100,
            'tentities': 10000,
            'multiplier': 1,
            'ks_mode': 2,
            'weak_threshold': 0.005,
            'fail_threshold': 0.000001,
            'use_overlap': True,
            'test_strategy': 0,
            'reseed_strategy': 0,
            'save_raw_output': False,
            'raw_output_folder': ''
        }
        self._result: Optional[Dict[str, Any]] = None
    
    def show(self) -> Optional[Dict[str, Any]]:
        """Show the modal dialog and return settings dict or None if cancelled."""
        self._dialog = tk.Toplevel(self.parent)
        self._dialog.title("Dieharder Test Settings")
        # self._dialog.geometry("500x760")
        self._dialog.resizable(True, True)
        self._dialog.minsize(450, 600)
        
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

        # Build all sections in scrollable frame
        self._build_test_selection(main_frame)
        self._build_test_parameters(main_frame)
        self._build_statistical_options(main_frame)
        self._build_advanced_options(main_frame)
        self._build_action_buttons(main_frame)
        
    def _build_test_selection(self, parent):
        """Build test selection and raw output sections side by side."""
        # Container for both sections
        top_container = ttk.Frame(parent)
        top_container.pack(fill=tk.X, pady=(0, 5))
        
        # Test Selection section
        test_section = ttk.Labelframe(top_container, text="Test Selection", padding=10)
        test_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Store test_mode_var for compatibility (always 'specific' now since we removed 'all' radiobutton)
        self.test_mode_var = tk.StringVar(value=self.settings['test_mode'])
        
        # Number of selected tests
        selected_count = len(self.settings['selected_tests'])
        if selected_count == len(DIEHARDER_TESTS):
            btn_text = "Select Tests (All 32)"
        else:
            btn_text = f"Select Tests ({selected_count} selected)"
        
        self.select_tests_btn = ttk.Button(
            test_section,
            text=btn_text,
            command=self._show_test_selector,
            bootstyle="info-outline",
            width=25
        )
        self.select_tests_btn.pack(pady=5)
        
        ttk.Label(
            test_section,
            text="Click to choose which tests to run",
            font=("Helvetica", 8)
        ).pack()
        
        # Raw Output section
        raw_section = ttk.Labelframe(top_container, text="Save Raw Output", padding=10)
        raw_section.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Checkbox for enabling raw output saving
        self.save_raw_var = tk.BooleanVar(value=self.settings.get('save_raw_output', False))
        ttk.Checkbutton(
            raw_section,
            text="Save stdout/stderr to folder",
            variable=self.save_raw_var,
            command=self._toggle_raw_output,
            bootstyle="primary"
        ).pack(anchor=tk.W, pady=(0, 5))
        
        # Folder entry and browse button
        folder_frame = ttk.Frame(raw_section)
        folder_frame.pack(fill=tk.X)
        
        self.raw_folder_var = tk.StringVar(value=self.settings.get('raw_output_folder', ''))
        self.raw_folder_entry = ttk.Entry(
            folder_frame,
            textvariable=self.raw_folder_var,
            width=20
        )
        self.raw_folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.browse_btn = ttk.Button(
            folder_frame,
            text="Browse",
            command=self._browse_folder,
            bootstyle="secondary-outline",
            width=8
        )
        self.browse_btn.pack(side=tk.LEFT)
        
        # Initial state
        self._toggle_raw_output()
    
    def _build_test_parameters(self, parent):
        """Build test parameters section."""
        section = ttk.Labelframe(parent, text="Test Parameters", padding=10)
        section.pack(fill=tk.X, pady=5)
        
        # P-value samples
        ttk.Label(section, text="P-value samples (-p):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.psamples_var = tk.StringVar(value=str(self.settings['psamples']))
        ttk.Entry(section, textvariable=self.psamples_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(section, text="(1 - 1,000,000)", font=("Helvetica", 8)).grid(row=0, column=2, sticky=tk.W, pady=5)
        
        # Random entities
        ttk.Label(section, text="Random entities (-t):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.tentities_var = tk.StringVar(value=str(self.settings['tentities']))
        ttk.Entry(section, textvariable=self.tentities_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(section, text="(1 - 1,000,000,000)", font=("Helvetica", 8)).grid(row=1, column=2, sticky=tk.W, pady=5)
        
        # Multiplier
        ttk.Label(section, text="Multiplier (-m):").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.multiplier_var = tk.StringVar(value=str(self.settings['multiplier']))
        ttk.Entry(section, textvariable=self.multiplier_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(section, text="(1 - 1,000)", font=("Helvetica", 8)).grid(row=2, column=2, sticky=tk.W, pady=5)
        
        # Ntuple
        ttk.Label(section, text="Ntuple (-n):").grid(row=3, column=0, sticky=tk.W, pady=5, padx=5)
        self.ntuple_var = tk.StringVar(value=str(self.settings.get('ntuple', 0)))
        ttk.Entry(section, textvariable=self.ntuple_var, width=15).grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(section, text="(0=default, 1-32 for bit tests)", font=("Helvetica", 8)).grid(row=3, column=2, sticky=tk.W, pady=5)
    
    def _build_statistical_options(self, parent):
        """Build statistical options section."""
        section = ttk.Labelframe(parent, text="Statistical Options", padding=10)
        section.pack(fill=tk.X, pady=5)
        
        # KS Mode
        ks_frame = ttk.Frame(section)
        ks_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(ks_frame, text="KS Mode (-k):").pack(side=tk.LEFT, padx=(0, 10))
        
        self.ks_mode_var = tk.IntVar(value=self.settings['ks_mode'])
        for i in range(4):
            ttk.Radiobutton(
                ks_frame,
                text=str(i),
                variable=self.ks_mode_var,
                value=i,
                bootstyle="primary"
            ).pack(side=tk.LEFT, padx=5)
        
        # Thresholds
        threshold_frame = ttk.Frame(section)
        threshold_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(threshold_frame, text="Weak Threshold (-W):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.weak_threshold_var = tk.StringVar(value=str(self.settings['weak_threshold']))
        ttk.Entry(threshold_frame, textvariable=self.weak_threshold_var, width=12).grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(threshold_frame, text="(0.0 - 1.0)", font=("Helvetica", 8)).grid(row=0, column=2, sticky=tk.W, pady=5)
        
        ttk.Label(threshold_frame, text="Fail Threshold (-X):").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.fail_threshold_var = tk.StringVar(value=str(self.settings['fail_threshold']))
        ttk.Entry(threshold_frame, textvariable=self.fail_threshold_var, width=12).grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        ttk.Label(threshold_frame, text="(0.0 - 1.0)", font=("Helvetica", 8)).grid(row=1, column=2, sticky=tk.W, pady=5)
    
    def _build_advanced_options(self, parent):
        """Build advanced options section."""
        section = ttk.Labelframe(parent, text="Advanced Options", padding=10)
        section.pack(fill=tk.X, pady=5)
        
        # Overlap checkbox
        self.use_overlap_var = tk.BooleanVar(value=self.settings['use_overlap'])
        ttk.Checkbutton(
            section,
            text="Use Overlap (-L 1)",
            variable=self.use_overlap_var,
            bootstyle="primary"
        ).pack(anchor=tk.W, pady=5)
        
        # Test strategy
        strategy_frame = ttk.Frame(section)
        strategy_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(strategy_frame, text="Test Strategy (-Y):").pack(anchor=tk.W, pady=(0, 5))
        
        self.test_strategy_var = tk.IntVar(value=self.settings['test_strategy'])
        
        ttk.Radiobutton(
            strategy_frame,
            text="Standard (0)",
            variable=self.test_strategy_var,
            value=0,
            bootstyle="primary"
        ).pack(anchor=tk.W, padx=20)
        
        ttk.Radiobutton(
            strategy_frame,
            text="Resolve Ambiguity (1)",
            variable=self.test_strategy_var,
            value=1,
            bootstyle="primary"
        ).pack(anchor=tk.W, padx=20)
        
        ttk.Radiobutton(
            strategy_frame,
            text="Test to Destruction (2)",
            variable=self.test_strategy_var,
            value=2,
            bootstyle="primary"
        ).pack(anchor=tk.W, padx=20)
        
        # Reseed strategy
        reseed_frame = ttk.Frame(section)
        reseed_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(reseed_frame, text="Reseed Strategy (-s):").pack(side=tk.LEFT, padx=(0, 10))
        self.reseed_strategy_var = tk.StringVar(value=str(self.settings['reseed_strategy']))
        ttk.Entry(reseed_frame, textvariable=self.reseed_strategy_var, width=12).pack(side=tk.LEFT)
        ttk.Label(reseed_frame, text="(0 or higher)", font=("Helvetica", 8)).pack(side=tk.LEFT, padx=(5, 0))
    
    def _build_action_buttons(self, parent):
        """Build action buttons."""
        button_frame = ttk.Labelframe(parent, text="Actions", padding=10)
        button_frame.pack(fill=tk.X, pady=5)
        
        button_inner = ttk.Frame(button_frame)
        button_inner.pack(anchor=tk.CENTER)
        
        ttk.Button(
            button_inner,
            text="Submit",
            command=self._submit,
            bootstyle="success",
            width=12
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Cancel",
            command=self._cancel,
            bootstyle="secondary",
            width=12
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Reset",
            command=self._reset,
            bootstyle="warning",
            width=12
        ).pack(side=tk.LEFT, padx=3)
        
        ttk.Button(
            button_inner,
            text="Help",
            command=self._show_help,
            bootstyle="info",
            width=12
        ).pack(side=tk.LEFT, padx=3)
    
    def _toggle_raw_output(self):
        """Enable/disable raw output folder entry based on checkbox."""
        if self.save_raw_var.get():
            self.raw_folder_entry.config(state=tk.NORMAL)
            self.browse_btn.config(state=tk.NORMAL)
        else:
            self.raw_folder_entry.config(state=tk.DISABLED)
            self.browse_btn.config(state=tk.DISABLED)
    
    def _browse_folder(self):
        """Browse for raw output folder."""
        folder = filedialog.askdirectory(
            title="Select folder for raw output",
            parent=self._dialog
        )
        if folder:
            self.raw_folder_var.set(folder)
    
    def _show_test_selector(self):
        """Show test selector dialog."""
        # Pass current selected tests (empty list means none selected)
        dialog = DieharderTestSelectorDialog(self._dialog, self.settings['selected_tests'])
        
        result = dialog.show()
        if result is not None:
            self.settings['selected_tests'] = result
            self.test_mode_var.set('specific')  # Always specific now
            if len(result) == len(DIEHARDER_TESTS):
                self.select_tests_btn.config(text="Select Tests (All 32)")
            else:
                self.select_tests_btn.config(text=f"Select Tests ({len(result)} selected)")
    
    def _submit(self):
        """Validate and submit settings."""
        try:
            # Validate test selection
            if self.test_mode_var.get() == 'specific':
                if not self.settings['selected_tests']:
                    messagebox.showerror("Error", "Please select at least one test")
                    return
            
            # Validate numeric fields
            psamples = int(self.psamples_var.get())
            if not (1 <= psamples <= 1000000):
                messagebox.showerror("Error", "P-samples must be between 1 and 1,000,000")
                return
            
            tentities = int(self.tentities_var.get())
            if not (1 <= tentities <= 1000000000):
                messagebox.showerror("Error", "Random entities must be between 1 and 1,000,000,000")
                return
            
            multiplier = int(self.multiplier_var.get())
            if not (1 <= multiplier <= 1000):
                messagebox.showerror("Error", "Multiplier must be between 1 and 1,000")
                return
            
            ntuple = int(self.ntuple_var.get())
            if not (0 <= ntuple <= 32):
                messagebox.showerror("Error", "Ntuple must be between 0 and 32 (0 = default)")
                return
            
            # Validate float thresholds
            weak = float(self.weak_threshold_var.get())
            fail = float(self.fail_threshold_var.get())
            
            if not (0.0 <= weak <= 1.0):
                messagebox.showerror("Error", "Weak threshold must be between 0.0 and 1.0")
                return
            
            if not (0.0 <= fail <= 1.0):
                messagebox.showerror("Error", "Fail threshold must be between 0.0 and 1.0")
                return
            
            if fail >= weak:
                messagebox.showerror("Error", "Fail threshold must be less than weak threshold")
                return
            
            # Validate reseed strategy
            reseed = int(self.reseed_strategy_var.get())
            if reseed < 0:
                messagebox.showerror("Error", "Reseed strategy must be non-negative")
                return
            
            # Validate raw output folder if saving is enabled
            save_raw = self.save_raw_var.get()
            raw_folder = self.raw_folder_var.get().strip()
            if save_raw and not raw_folder:
                messagebox.showerror("Error", "Please specify a folder for raw output")
                return
            
            # Build settings dict
            self._result = {
                'test_mode': self.test_mode_var.get(),
                'selected_tests': self.settings['selected_tests'],
                'psamples': psamples,
                'tentities': tentities,
                'multiplier': multiplier,
                'ntuple': ntuple,
                'ks_mode': self.ks_mode_var.get(),
                'weak_threshold': weak,
                'fail_threshold': fail,
                'use_overlap': self.use_overlap_var.get(),
                'test_strategy': self.test_strategy_var.get(),
                'reseed_strategy': reseed,
                'save_raw_output': save_raw,
                'raw_output_folder': raw_folder
            }
            
            self._dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid numeric value: {str(e)}")
    
    def _cancel(self):
        """Cancel the dialog."""
        self._result = None
        self._dialog.destroy()
    
    def _reset(self):
        """Reset to default values."""
        self.test_mode_var.set("specific")
        self.settings['selected_tests'] = []
        self.select_tests_btn.config(text="Select Tests (0 selected)")
        self.psamples_var.set("100")
        self.tentities_var.set("10000")
        self.multiplier_var.set("1")
        self.ntuple_var.set("0")
        self.ks_mode_var.set(2)
        self.weak_threshold_var.set("0.005")
        self.fail_threshold_var.set("0.000001")
        self.use_overlap_var.set(True)
        self.test_strategy_var.set(0)
        self.reseed_strategy_var.set("0")
        self.save_raw_var.set(False)
        self.raw_folder_var.set("")
        self._toggle_raw_output()
    
    def _show_help(self):
        """Show help information."""
        help_text = """Dieharder Test Settings Help

Test Selection:
- Select Tests: Choose which tests to run (32 available)
- All Tests runs all 32 tests individually

Parameters:
- P-samples: Number of p-value samples per test
- Random entities: Number of random values per test
- Multiplier: Multiply default psamples in all runs

Statistical:
- KS Mode: Kolmogorov-Smirnov test accuracy
  0: Fast (default for large samples)
  1: Slower, more accurate
  2: Slowest, machine precision (recommended)
  3: Kuiper KS (deprecated)
- Weak/Fail: Thresholds for test assessment

Advanced:
- Overlap: Use overlapping samples
- Test Strategy:
  0: Standard
  1: Resolve Ambiguity
  2: Test to Destruction
- Reseed: 0=once, >0=per test
"""
        
        messagebox.showinfo("Dieharder Settings Help", help_text)
