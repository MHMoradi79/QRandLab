# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Main application window with tabbed interface."""
import sys

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk

from ..manager import CoreManager
from ..core.types import OperationStatus
from ..core.observer import set_tk_root
from ..utils.help_generator import HelpGenerator
from ..gui.help_window import show_help_window

from ..gui.input_tab import InputTab
from ..gui.converter_tab import ConverterTab
from ..gui.preprocessing_tab import PreprocessingTab
from ..gui.slicer_tab import SlicerTab
from ..gui.testing_tab import TestingTab
from ..gui.qrng_tab import QRNGTab
from ..gui.report_tab import ReportTab


class QRandLabApp(ttk.Window):
    """Main application window."""
    
    def __init__(self):
        super().__init__(themename="darkly")
        
        # Register this window for thread-safe event notifications
        set_tk_root(self)
        
        self.title("QRandLab - v1.0")
        # self.geometry("1200x800")
        self.minsize(900, 600)
        
        # Store current theme
        self.current_theme = "darkly"
        self.theme_var = tk.StringVar(value="darkly")
        
        # Initialize CoreManager
        self.manager = CoreManager()
        
        # Initialize HelpGenerator
        self.help_generator = None
        # Track open help windows
        self.help_windows = []
        
        # Setup event subscriptions
        self._setup_events()
        
        # Build menu bar
        self._build_menu_bar()
        
        # Status bar at bottom
        self._build_status_bar()
        
        # Build UI
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to CoreManager events for status updates."""
        self.manager.on_operation_started.subscribe(self._on_operation_started)
        self.manager.on_operation_completed.subscribe(self._on_operation_completed)
        self.manager.on_operation_failed.subscribe(self._on_operation_failed)
    
    def _build_menu_bar(self):
        """Build menu bar with theme and help options."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Settings", menu=settings_menu)
        
        # Theme submenu
        theme_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="Theme", menu=theme_menu)
        
        # Available themes from ttkbootstrap - grouped by light and dark
        light_themes = [
            "cosmo", "flatly", "journal", "litera", "lumen",
            "minty", "pulse", "sandstone", "united", "yeti",
            "morph", "simplex", "cerculean"
        ]
        dark_themes = [
            "solar", "superhero", "darkly", "cyborg", "vapor"
        ]
        
        # Add light themes with radio buttons
        for theme_name in light_themes:
            theme_menu.add_radiobutton(
                label=theme_name.capitalize(),
                variable=self.theme_var,
                value=theme_name,
                command=lambda t=theme_name: self._change_theme(t)
            )
        
        # Add separator
        theme_menu.add_separator()
        
        # Add dark themes with radio buttons
        for theme_name in dark_themes:
            theme_menu.add_radiobutton(
                label=theme_name.capitalize(),
                variable=self.theme_var,
                value=theme_name,
                command=lambda t=theme_name: self._change_theme(t)
            )
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View Help", command=self._show_help)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self._show_about)
    
    def _build_ui(self):
        """Build main user interface."""
        # Main container
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # Title/Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame,
            text="QRandLab",
            font=("Helvetica", 20, "bold"),
            bootstyle=PRIMARY
        )
        title_label.pack(side=LEFT)
        
        subtitle_label = ttk.Label(
            header_frame,
            text="RNG File Management and Statistical Testing Suite",
            font=("Helvetica", 10),
            bootstyle=INFO
        )
        subtitle_label.pack(side=LEFT, padx=(10, 0))
        
        # Company logo on the right
        self._load_logo(header_frame)
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(main_frame, bootstyle=INFO)
        self.notebook.pack(fill=BOTH, expand=YES)
        
        # Create tabs
        self.qrng_tab = QRNGTab(self.notebook, self.manager)
        self.input_tab = InputTab(self.notebook, self.manager)
        self.converter_tab = ConverterTab(self.notebook, self.manager)
        self.preprocessing_tab = PreprocessingTab(self.notebook, self.manager)
        self.slicer_tab = SlicerTab(self.notebook, self.manager)
        self.testing_tab = TestingTab(self.notebook, self.manager)
        self.report_tab = ReportTab(self.notebook, self.manager, theme_name=self.current_theme)
        
        # Link report tab to other tabs for report generation
        self.qrng_tab.report_tab = self.report_tab
        self.input_tab.report_tab = self.report_tab
        self.converter_tab.report_tab = self.report_tab
        self.preprocessing_tab.report_tab = self.report_tab
        self.slicer_tab.report_tab = self.report_tab
        self.testing_tab.report_tab = self.report_tab
        
        # Add tabs to notebook
        self.notebook.add(self.qrng_tab, text="  RNG Sources  ")
        self.notebook.add(self.input_tab, text="  Input File  ")
        self.notebook.add(self.converter_tab, text="  File Converter  ")
        self.notebook.add(self.preprocessing_tab, text="  Preprocessing  ")
        self.notebook.add(self.slicer_tab, text="  Slicer  ")
        self.notebook.add(self.testing_tab, text="  Testing  ")
        self.notebook.add(self.report_tab, text="  Report  ")
    
    def _build_status_bar(self):
        """Build status bar at bottom of window."""
        self.status_frame = ttk.Frame(self, bootstyle="dark")
        self.status_frame.pack(fill=X, side=BOTTOM)
        
        # Status message
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            self.status_frame,
            textvariable=self.status_var,
            bootstyle="inverse-dark",
            padding=5
        )
        self.status_label.pack(side=LEFT, fill=X, expand=YES)
        
        # File info
        self.file_info_var = tk.StringVar(value="No file loaded")
        self.file_info_label = ttk.Label(
            self.status_frame,
            textvariable=self.file_info_var,
            bootstyle="inverse-info",
            padding=5
        )
        self.file_info_label.pack(side=RIGHT)
    
    def _on_operation_started(self, status: OperationStatus):
        """Handle operation started event."""
        if status.ok:
            self.status_var.set("⏳ " + status.message + "...")
            self.update_idletasks()
    
    def _on_operation_completed(self, status: OperationStatus):
        """Handle operation completed event."""
        if status.ok:
            self.status_var.set("✓ " + status.message)
            self.update_file_info()
    
    def _on_operation_failed(self, status: OperationStatus):
        """Handle operation failed event."""
        if not status.ok:
            self.status_var.set("✗ " + status.message)
    
    def update_file_info(self):
        """Update file info in status bar."""
        meta = self.manager.input_meta
        file_count = meta.get_file_count()
        
        # Multi-file display
        if file_count > 0:
            if file_count == 1:
                # Single file - show details
                item = meta.file_items[0]
                file_type = item.file_type.value if item.file_type else "Not set"
                size_kb = item.file_size / 1024 if item.file_size else 0
                file_ext = item.file_ext.value if item.file_ext else ''
                file_info = "📄 {} {} | Type: {} | Size: {:.2f} KB".format(
                    item.file_name, file_ext, file_type, size_kb
                )
            else:
                # Multiple files - show count
                total_size = sum(f.file_size or 0 for f in meta.file_items)
                total_kb = total_size / 1024
                if total_kb >= 1024:
                    total_mb = total_kb / 1024
                    file_info = f"📁 {file_count} files loaded | Total: {total_mb:.2f} MB"
                else:
                    file_info = f"📁 {file_count} files loaded | Total: {total_kb:.2f} KB"
            self.file_info_var.set(file_info)
        elif meta.file_path:
            # Legacy single-file fallback
            file_type = meta.file_type.value if meta.file_type else "Unknown"
            size_kb = meta.file_size / 1024 if meta.file_size else 0
            file_ext = meta.file_ext.value if meta.file_ext else ''
            file_info = "📄 {} {} | Type: {} | Size: {:.2f} KB".format(
                meta.file_name, file_ext, file_type, size_kb
            )
            self.file_info_var.set(file_info)
        else:
            self.file_info_var.set("No files loaded")
    
    def _change_theme(self, theme_name: str):
        """Change the application theme.
        
        Args:
            theme_name: Name of the theme to apply
        """
        try:
            self.style.theme_use(theme_name)
            self.current_theme = theme_name
            self.theme_var.set(theme_name)  # Update checkmark
            
            # Notify tabs that need to update their styles
            if hasattr(self, 'input_tab'):
                self.input_tab.event_generate("<<ThemeChanged>>")
            
            # Update report tab theme
            if hasattr(self, 'report_tab'):
                self.report_tab.set_theme(theme_name)
            # Update help generator theme
            if self.help_generator:
                self.help_generator.set_theme(theme_name)
                # Reload content in all open help windows
                self._reload_help_windows()
        except Exception as e:
            error_msg = "Failed to apply theme '{}':\n{}".format(theme_name, str(e))
            messagebox.showerror("Theme Error", error_msg)
    
    def _show_help(self):
        """Open help window with HTML documentation."""
        # Initialize help generator if not already created
        if not self.help_generator:
            self.help_generator = HelpGenerator(
                theme_name=self.current_theme,
                style_obj=self.style
            )
        
        # Show help window and track it
        help_window = show_help_window(self, self.help_generator)
        self.help_windows.append(help_window)
    
    def _reload_help_windows(self):
        """Reload content in all open help windows with new theme."""
        # Clean up closed windows and reload open ones
        self.help_windows = [hw for hw in self.help_windows if hw.is_open()]
        for help_window in self.help_windows:
            help_window.reload_current_content()
    
    def _load_logo(self, parent_frame):
        """Load and display company logo in header."""
        try:
            if hasattr(sys, '_MEIPASS'):
                logo_path = Path(sys._MEIPASS) / "assets" / "images" / "logo.png"
            else:
                project_path = Path(__file__).resolve().parent.parent
                logo_path = project_path / "assets" / "logo.png"
            if logo_path.exists():
                # Load and resize logo
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((64, 64), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_img)
                
                logo_label = ttk.Label(parent_frame, image=self.logo_photo)
                logo_label.pack(side=RIGHT, padx=(10, 0))
        except Exception:
            pass  # Logo not available, skip silently
    
    def _show_about(self):
        """Show about dialog with image."""
        if hasattr(sys, '_MEIPASS'):
            about_path = Path(sys._MEIPASS) / "assets" / "images" / "aboutus.png"
        else:
            project_path = Path(__file__).resolve().parent.parent
            about_path = project_path / "assets" / "aboutus.png"
        # Create about window
        about_window = tk.Toplevel(self)
        about_window.title("About QRandLab")
        about_window.resizable(False, False)
        about_window.transient(self)
        about_window.grab_set()
        
        if about_path.exists():
            try:
                # Load and display about image
                about_img = Image.open(about_path)
                self.about_photo = ImageTk.PhotoImage(about_img)
                
                img_label = ttk.Label(about_window, image=self.about_photo)
                img_label.pack(padx=10, pady=10)
                
                # Center window on parent
                about_window.update_idletasks()
                x = self.winfo_x() + (self.winfo_width() - about_window.winfo_width()) // 2
                y = self.winfo_y() + (self.winfo_height() - about_window.winfo_height()) // 2
                about_window.geometry(f"+{x}+{y}")
            except Exception:
                self._show_about_fallback(about_window)
        else:
            self._show_about_fallback(about_window)
        
        # Close button
        ttk.Button(
            about_window,
            text="Close",
            command=about_window.destroy,
            bootstyle="secondary"
        ).pack(pady=(0, 10))
    
    def _show_about_fallback(self, window):
        """Show text-based about if image not available."""
        text = (
            """
            QRandLab v1.0\n\n
                Comprehensive Software for Managing, Preprocessing, Extracting and Statistical Testing of RNG Files

                Features:
                Format conversion between binary, hex, uint8-64, and string01
                Preprocessing algorithms (Von Neumann, XOR folding, Toeplitz)
                Sampling from large RNG files
                Statistical tests including NIST, Dieharder, ENT, Borel, Autocorrelation
                Hardware interface with external commercial modules (EYL) quantum device
                Online/offline QRNG/PRNG APIs including ANU, Random.org, HotBits and Dieharder based algorithms
                Comprehensive user report
                Multiple input file handling

                Developed by MHM under supervision of AMF at Quantum Sensing and Metrology Group, TAKFAN Co, I.R. Iran.
            """
        )
        ttk.Label(
            window,
            text=text,
            font=("Helvetica", 10),
            justify=tk.CENTER
        ).pack(padx=20, pady=20)
    
    def run(self):
        """Start the application main loop."""
        self.mainloop()


def main():
    """Entry point for the application."""
    app = QRandLabApp()
    app.run()


if __name__ == "__main__":
    main()
