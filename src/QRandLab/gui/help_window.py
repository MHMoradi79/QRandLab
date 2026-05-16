# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Help window GUI component."""

import tkinter as tk
from tkinter import scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

try:
    import tkinterweb
    TKINTERWEB_AVAILABLE = True
except ImportError:
    TKINTERWEB_AVAILABLE = False

from ..utils.help_generator import HelpGenerator


class HelpWindow:
    """Help documentation window with navigation and HTML viewer."""
    
    def __init__(self, parent_window, help_generator: HelpGenerator):
        """Initialize help window.
        
        Args:
            parent_window: Parent tkinter window
            help_generator: HelpGenerator instance for rendering content
        """
        self.help_generator = help_generator
        self.temp_help_file = None
        self.current_file = None  # Track currently displayed file
        
        # Create help window
        self.window = tk.Toplevel(parent_window)
        self.window.title("QRandLab Help")
        # self.window.geometry("1100x750")
        self.window.minsize(900, 600)
        
        # Build UI
        self._build_ui()
        
        # Load first help file
        self._load_first_help_file()
    
    def _build_ui(self):
        """Build the help window user interface."""
        # Main container
        main_frame = ttk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Navigation
        nav_frame = ttk.LabelFrame(main_frame, text="Help Topics", padding=10)
        nav_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        nav_frame.config(width=250)
        
        # Content viewer
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Create HTML viewer for content
        if TKINTERWEB_AVAILABLE:
            self.html_viewer = tkinterweb.HtmlFrame(content_frame, messages_enabled=False)
            self.html_viewer.pack(fill=tk.BOTH, expand=True)
            self.viewer_type = 'html'
        else:
            # Fallback if tkinterweb is not available
            self.html_viewer = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD)
            self.html_viewer.pack(fill=tk.BOTH, expand=True)
            self.viewer_type = 'text'
        
        # Build navigation
        self._build_navigation(nav_frame)
    
    def _build_navigation(self, nav_frame):
        """Build navigation buttons.
        
        Args:
            nav_frame: Frame to place navigation buttons in
        """
        # Get help sections from generator
        help_sections = self.help_generator.get_help_sections()
        
        # Create navigation buttons
        for section_title, topics in help_sections:
            # Section label
            section_lbl = ttk.Label(
                nav_frame,
                text=section_title,
                font=("Helvetica", 10, "bold"),
                bootstyle=PRIMARY
            )
            section_lbl.pack(anchor=tk.W, pady=(10, 5))
            
            # Topic buttons
            for topic_title, topic_file in topics:
                btn = ttk.Button(
                    nav_frame,
                    text="  " + topic_title,
                    command=lambda f=topic_file: self.load_help_file(f),
                    bootstyle="link",
                    width=25
                )
                btn.pack(anchor=tk.W, padx=(10, 0), pady=2)
    
    def load_help_file(self, filename: str):
        """Load and display a help file.
        
        Args:
            filename: Name of help file to load
        """
        # Store current file for reloading
        self.current_file = filename
        
        file_path = self.help_generator.help_sections_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Wrap in styled HTML template
                wrapped_html = self.help_generator.render_help_content(content)
                
                # Load in viewer
                if self.viewer_type == 'html':
                    self.html_viewer.load_html(wrapped_html)
                else:
                    # Fallback for text widget
                    self.html_viewer.delete('1.0', tk.END)
                    self.html_viewer.insert('1.0', content)
            except Exception as e:
                pass
        else:
            pass
    
    def _load_first_help_file(self):
        """Load the first help file by default."""
        help_sections = self.help_generator.get_help_sections()
        if help_sections and help_sections[0][1]:
            first_file = help_sections[0][1][0][1]
            self.load_help_file(first_file)
    
    def reload_current_content(self):
        """Reload the currently displayed help file with updated theme."""
        if self.current_file:
            self.load_help_file(self.current_file)
    
    def is_open(self) -> bool:
        """Check if the help window is still open."""
        try:
            return self.window.winfo_exists()
        except:
            return False


def show_help_window(parent_window, help_generator: HelpGenerator):
    """Show the help window.
    
    Args:
        parent_window: Parent tkinter window
        help_generator: HelpGenerator instance for rendering content
    
    Returns:
        HelpWindow: The created help window instance
    """
    return HelpWindow(parent_window, help_generator)
