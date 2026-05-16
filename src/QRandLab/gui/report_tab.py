# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Report tab for displaying HTML reports."""

from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinterweb import HtmlFrame
from datetime import datetime

from ..manager.core_manager import CoreManager
from ..utils.report_generator import ReportGenerator


class ReportTab(ttk.Frame):
    """Report display tab with HTML rendering."""
    
    def __init__(self, parent, manager: CoreManager, theme_name: str = "darkly"):
        super().__init__(parent, padding=20)
        self.manager = manager
        
        # Get style object from parent window
        try:
            style_obj = ttk.Style.get_instance()
        except:
            style_obj = None
        
        self.report_generator = ReportGenerator(theme_name=theme_name, style_obj=style_obj)
        self.temp_report_file = None
        
        # Initialize report with header
        self.report_generator.initialize_report()
        
        # Build UI
        self._build_ui()
        
        # Display initial report
        self.refresh_report()
    
    def _build_ui(self):
        """Build report tab UI."""
        # Control panel at top
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=X, pady=(0, 10))
        
        # Buttons on the left
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=LEFT)
        
        # Save button
        save_btn = ttk.Button(
            button_frame,
            text="💾 Save Report",
            command=self._save_report,
            bootstyle=SUCCESS,
            width=15
        )
        save_btn.pack(side=LEFT, padx=5)
        
        # Clear button
        clear_btn = ttk.Button(
            button_frame,
            text="🗑 Clear Report",
            command=self._clear_report,
            bootstyle=DANGER,
            width=15
        )
        clear_btn.pack(side=LEFT, padx=5)
        
        # Refresh button
        refresh_btn = ttk.Button(
            button_frame,
            text="🔄 Refresh",
            command=self.refresh_report,
            bootstyle=INFO,
            width=12
        )
        refresh_btn.pack(side=LEFT, padx=5)
        
        # Undo button
        self.undo_btn = ttk.Button(
            button_frame,
            text="↩ Undo",
            command=self._undo,
            bootstyle="secondary",
            width=10
        )
        self.undo_btn.pack(side=LEFT, padx=5)
        
        # Redo button
        self.redo_btn = ttk.Button(
            button_frame,
            text="↪ Redo",
            command=self._redo,
            bootstyle="secondary",
            width=10
        )
        self.redo_btn.pack(side=LEFT, padx=5)
        
        # Initialize button states (disabled at start)
        self.undo_btn.config(state=DISABLED)
        self.redo_btn.config(state=DISABLED)
        
        # Info label on the right
        info_label = ttk.Label(
            control_frame,
            text="View generated reports from your operations",
            font=("Helvetica", 10),
            bootstyle=INFO
        )
        info_label.pack(side=RIGHT, padx=10)
        
        # HTML viewer frame
        viewer_frame = ttk.Frame(self, bootstyle=INFO)
        viewer_frame.pack(fill=BOTH, expand=YES)
        
        # Create HTML viewer with scrollbar
        self.html_viewer = HtmlFrame(
            viewer_frame,
            messages_enabled=False
        )
        self.html_viewer.pack(fill=BOTH, expand=YES, padx=2, pady=2)
    
    def _update_undo_redo_buttons(self):
        """Update undo/redo button states based on history availability."""
        if self.report_generator.can_undo():
            self.undo_btn.config(state=NORMAL)
        else:
            self.undo_btn.config(state=DISABLED)
        
        if self.report_generator.can_redo():
            self.redo_btn.config(state=NORMAL)
        else:
            self.redo_btn.config(state=DISABLED)
    
    def _undo(self):
        """Undo last report action."""
        if self.report_generator.undo():
            self.refresh_report()
        self._update_undo_redo_buttons()
    
    def _redo(self):
        """Redo last undone action."""
        if self.report_generator.redo():
            self.refresh_report()
        self._update_undo_redo_buttons()
    
    def _save_report(self):
        """Save the current report to an HTML file."""
        # Get save file path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        default_filename = "QRandLab_Report_{}.html".format(timestamp)
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            initialfile=default_filename,
            filetypes=[
                ("HTML Files", "*.html"),
                ("All Files", "*.*")
            ],
            title="Save Report As"
        )
        
        if file_path:
            success = self.report_generator.save_report(file_path)
            if success:
                # Report saved successfully
                pass
            else:
                messagebox.showerror(
                    "Error",
                    "Failed to save report. Please check file permissions."
                )
    
    def _clear_report(self):
        """Clear the report and reinitialize with header."""
        result = messagebox.askyesno(
            "Clear Report",
            "Are you sure you want to clear the entire report?\nThis action cannot be undone."
        )
        
        if result:
            self.report_generator.clear_report()
            self.report_generator.initialize_report()
            self.refresh_report()
            # Report cleared successfully
    
    def refresh_report(self, scroll_to_end: bool = True):
        """Refresh the HTML viewer with current report content.
        
        Args:
            scroll_to_end: If True, scroll to end of report after refresh
        """
        try:
            # Get HTML content
            html_content = self.report_generator.get_full_report()
            self.html_viewer.load_html(html_content)
            
            # Update undo/redo button states
            self._update_undo_redo_buttons()
            
            # Scroll to end after a short delay to ensure content is loaded
            if scroll_to_end:
                self.after(100, self._scroll_to_end)

        except Exception as e:
            try:
                html_content = self.report_generator.get_full_report()
                self.html_viewer.load_html(html_content)
            except:
                pass
    
    def _scroll_to_end(self):
        """Scroll the HTML viewer to the end of content."""
        try:
            # HtmlFrame uses yview_moveto(1.0) to scroll to end
            self.html_viewer.yview_moveto(1.0)
        except:
            pass
    
    def set_theme(self, theme_name: str):
        """Update the theme and refresh the report.
        
        Args:
            theme_name: New theme name
        """
        # Get current style object for fresh theme colors
        try:
            style_obj = ttk.Style.get_instance()
        except:
            style_obj = None
        
        # Update theme with fresh style object - sections are preserved automatically
        self.report_generator.set_theme(theme_name, style_obj)
        
        # Refresh display
        self.refresh_report()
    
    def add_input_file_section(self, file_meta: dict):
        """Add input file information to the report.
        
        Args:
            file_meta: Dictionary containing file metadata
        """
        # Prepare file metadata
        meta_dict = {
            'file_path': file_meta.get('file_path', 'N/A'),
            'file_dir': file_meta.get('file_dir', 'N/A'),
            'file_name': file_meta.get('file_name', 'N/A'),
            'file_size': file_meta.get('file_size', 'N/A'),
            'file_ext': file_meta.get('file_ext', 'N/A'),
            'file_type': file_meta.get('file_type', 'Not Set'),
            'validation': file_meta.get('validation', 'Unvalidated')
        }
        
        # Add to report
        self.report_generator.add_input_file(meta_dict)
        self.refresh_report()
    
    def remove_input_file(self, file_path: str):
        """Remove input file from the report.
        
        Args:
            file_path: Path of the file to remove
        """
        self.report_generator.remove_input_file(file_path)
        self.refresh_report(scroll_to_end=False)
    
    def update_input_file_validation(self, file_path: str, validation_status: str):
        """Update validation status for an input file.
        
        Args:
            file_path: Path of the file to update
            validation_status: New validation status ('Validated', 'Failed', etc.)
        """
        self.report_generator.update_input_file_validation(file_path, validation_status)
        self.refresh_report(scroll_to_end=False)
    
    def update_input_file_type(self, file_path: str, file_type: str):
        """Update file type for an input file.
        
        Args:
            file_path: Path of the file to update
            file_type: New file type
        """
        self.report_generator.update_input_file_type(file_path, file_type)
        self.refresh_report(scroll_to_end=False)
    
    def clear_input_files(self):
        """Clear all input files from the report."""
        self.report_generator.clear_input_files()
        self.refresh_report(scroll_to_end=False)
    
    def add_converter_section(self, conversion_data: dict):
        """Add file converter information to the report.
        
        Args:
            conversion_data: Dictionary containing conversion details
        """
        self.report_generator.add_conversion(conversion_data)
        self.refresh_report()
    
    def add_preprocess_section(self, preprocess_data: dict):
        """Add preprocessing information to the report.
        
        Args:
            preprocess_data: Dictionary containing preprocessing details
        """
        self.report_generator.add_preprocessing(preprocess_data)
        self.refresh_report()
    
    def add_slicer_section(self, slicer_data: dict):
        """Add slicer information to the report.
        
        Args:
            slicer_data: Dictionary containing slicer details
        """
        self.report_generator.add_slicing(slicer_data)
        self.refresh_report()
    
    def add_test_section(self, test_name: str, test_data: dict):
        """Add test results to the report.
        
        Args:
            test_name: Name of the test (ent, dieharder, nist, nist_coarse, nist_fine, borel, autocorrelation)
            test_data: Dictionary containing test results
        """
        if test_name == "ent":
            self.report_generator.add_ent_report(test_data)
        elif test_name == "dieharder":
            self.report_generator.add_dieharder_report(test_data)
        elif test_name == "nist":
            self.report_generator.add_nist_report(test_data)
        elif test_name == "borel":
            self.report_generator.add_borel_report(test_data)
        elif test_name == "autocorrelation":
            self.report_generator.add_autocorrelation_report(test_data)
        
        self.refresh_report()
    
    def add_api_section(self, api_data: dict):
        """Add API QRNG operation to the report.
        
        Args:
            api_data: Dictionary containing API operation details
        """
        self.report_generator.add_api_operation(api_data)
        self.refresh_report()
    
    def add_prng_section(self, prng_data: dict):
        """Add PRNG operation to the report.
        
        Args:
            prng_data: Dictionary containing PRNG operation details
        """
        self.report_generator.add_prng_operation(prng_data)
        self.refresh_report()
    
    def add_eyl_section(self, eyl_data: dict):
        """Add EYL Hardware QRNG operation to the report.
        
        Args:
            eyl_data: Dictionary containing EYL operation details
        """
        self.report_generator.add_eyl_operation(eyl_data)
        self.refresh_report()
