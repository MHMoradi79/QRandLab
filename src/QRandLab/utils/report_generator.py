# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""HTML report generator using Jinja2 templates with modular sections."""

import copy
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import ttkbootstrap as ttk
from markupsafe import Markup
from jinja2 import Environment, FileSystemLoader
import sys

class ReportGenerator:
    """Generates HTML reports with modular, updateable sections."""
    
    def __init__(self, theme_name: str = "darkly", style_obj=None):
        """Initialize the report generator with template environment.
        
        Args:
            theme_name: Current application theme name
            style_obj: ttkbootstrap Style object to extract colors from
        """
        # Get the templates directory
        if hasattr(sys, '_MEIPASS'):
            self.base_dir = Path(sys._MEIPASS)
        else:
            self.base_dir = Path(__file__).resolve().parent.parent
        self.templates_dir = self.base_dir / "html_templates"
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.env.filters['chunk_newlines'] = self._chunk_newlines
        
        # Initialize modular section data storage
        self._init_sections()
        
        # Undo/Redo history (stores up to 20 previous states)
        self._history: List[Dict] = []
        self._redo_stack: List[Dict] = []
        self._max_history = 20
        
        self.version = "1.0"
        self.theme_name = theme_name
        self.style_obj = style_obj
        self._update_theme(theme_name)
    
    def _init_sections(self):
        """Initialize all section data stores."""
        self.sections = {
            'input_files': [],       # List of file dicts
            'conversions': [],       # List of conversion dicts
            'preprocessing': [],     # List of preprocessing dicts
            'slicing': [],           # List of slicing dicts
            'ent_tests': [],         # List of {file_name, results}
            'nist_tests': [],        # List of {file_name, results}
            'dieharder_tests': [],   # List of {file_name, results}
            'borel_tests': [],       # List of {file_name, results}
            'autocorr_tests': [],    # List of {file_name, results}
            'api_operations': [],    # List of API fetch dicts
            'prng_operations': [],   # List of PRNG generation dicts
            'eyl_operations': [],    # List of EYL device dicts
        }
    
    def _update_theme(self, theme_name: str):
        """Update theme settings by extracting colors from ttkbootstrap theme.
        
        Args:
            theme_name: Theme name to apply
        """
        self.theme_name = theme_name
        
        # Extract colors from ttkbootstrap theme
        try:
            # Create a temporary style object if not provided
            if self.style_obj is None:
                temp_style = ttk.Style(theme=theme_name)
            else:
                temp_style = self.style_obj
            
            # Get theme colors from ttkbootstrap
            theme_colors = temp_style.colors
            
            # Detect if theme is dark or light based on background brightness
            bg_color = theme_colors.bg
            # Simple brightness calculation (assuming hex color)
            if bg_color.startswith('#'):
                r = int(bg_color[1:3], 16)
                g = int(bg_color[3:5], 16)
                b = int(bg_color[5:7], 16)
                brightness = (r * 299 + g * 587 + b * 114) / 1000
                is_dark = brightness < 128
            else:
                # Fallback to theme name check
                dark_themes = ["solar", "superhero", "darkly", "cyborg", "vapor"]
                is_dark = theme_name.lower() in dark_themes
            
            # Build color scheme from theme
            self.colors = {
                'primary': theme_colors.primary,
                'accent': theme_colors.info,
                'bg': theme_colors.bg,
                'card_bg': theme_colors.inputbg if hasattr(theme_colors, 'inputbg') else theme_colors.bg,
                'muted': theme_colors.secondary if is_dark else theme_colors.dark,
                'text_color': theme_colors.fg,
                'border_color': theme_colors.border if hasattr(theme_colors, 'border') else theme_colors.secondary,
                'success_bg': self._adjust_brightness(theme_colors.success, -40 if is_dark else 40),
                'success_color': theme_colors.success if is_dark else self._adjust_brightness(theme_colors.success, -60),
                'fail_bg': self._adjust_brightness(theme_colors.danger, -40 if is_dark else 40),
                'fail_color': theme_colors.danger if is_dark else self._adjust_brightness(theme_colors.danger, -60),
                'header_title_bg': theme_colors.primary
            }
        except Exception as e:
            # Fallback to default colors if theme extraction fails
            is_dark = theme_name.lower() in ["solar", "superhero", "darkly", "cyborg", "vapor"]
            if is_dark:
                self.colors = {
                    'primary': '#4da6ff',
                    'accent': '#3399ff',
                    'bg': '#1a1a1a',
                    'card_bg': '#2d2d2d',
                    'muted': '#e0e0e0',
                    'text_color': '#f0f0f0',
                    'border_color': '#404040',
                    'success_bg': '#1e4d2b',
                    'success_color': '#7bc96f',
                    'fail_bg': '#5c1f1f',
                    'fail_color': '#ff9999',
                    'header_title_bg': '#1f4788'
                }
            else:
                self.colors = {
                    'primary': '#007acc',
                    'accent': '#003366',
                    'bg': '#f5f5f5',
                    'card_bg': '#ffffff',
                    'muted': '#333333',
                    'text_color': '#333333',
                    'border_color': '#ddd',
                    'success_bg': '#d4edda',
                    'success_color': '#155724',
                    'fail_bg': '#f8d7da',
                    'fail_color': '#721c24',
                    'header_title_bg': '#003366'
                }
    
    def _adjust_brightness(self, hex_color: str, amount: int) -> str:
        """Adjust the brightness of a hex color.
        
        Args:
            hex_color: Hex color string (e.g., '#RRGGBB')
            amount: Amount to adjust brightness (positive to lighten, negative to darken)
            
        Returns:
            str: Adjusted hex color
        """
        try:
            # Remove '#' if present
            hex_color = hex_color.lstrip('#')
            
            # Parse RGB values
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            # Adjust brightness
            r = max(0, min(255, r + amount))
            g = max(0, min(255, g + amount))
            b = max(0, min(255, b + amount))
            
            # Return adjusted hex color
            return "#{:02x}{:02x}{:02x}".format(r, g, b)
        except:
            return hex_color
    
    @staticmethod
    def _chunk_newlines(s, n=80):
        """Chunk a string into lines of n characters.
        
        Args:
            s: String to chunk
            n: Maximum characters per line (default 80)
            
        Returns:
            Markup: HTML-safe string with newlines
        """
        if s is None:
            return ''
        parts = [s[i:i+n] for i in range(0, len(s), n)]
        return Markup('\n'.join(parts))
    
    def set_theme(self, theme_name: str, style_obj=None):
        """Change the theme for report generation.
        
        Args:
            theme_name: New theme name
            style_obj: Optional updated style object
        """
        # Update style object if provided
        if style_obj is not None:
            self.style_obj = style_obj
        self._update_theme(theme_name)
    
    def _get_render_context(self, **kwargs) -> dict:
        """Get rendering context with color parameters always included.
        
        Args:
            **kwargs: Additional template variables
            
        Returns:
            dict: Complete context with colors and provided variables
        """
        # Always include current theme colors
        context = dict(self.colors)
        # Add/override with provided kwargs
        context.update(kwargs)
        return context
    
    def _render_template(self, template_name: str, **kwargs) -> str:
        """Render a template with color parameters automatically included.
        
        Args:
            template_name: Name of the template file
            **kwargs: Template variables
            
        Returns:
            str: Rendered HTML content
        """
        template = self.env.get_template(template_name)
        context = self._get_render_context(**kwargs)
        return template.render(**context)
    
    # ==================== History Management ====================
    
    def _save_state(self):
        """Save current state to history for undo."""
        state = copy.deepcopy(self.sections)
        self._history.append(state)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        # Clear redo stack on new action
        self._redo_stack.clear()
    
    def undo(self) -> bool:
        """Undo last action. Returns True if successful."""
        if not self._history:
            return False
        # Save current state to redo
        self._redo_stack.append(copy.deepcopy(self.sections))
        # Restore previous state
        self.sections = self._history.pop()
        return True
    
    def redo(self) -> bool:
        """Redo last undone action. Returns True if successful."""
        if not self._redo_stack:
            return False
        # Save current state to history
        self._history.append(copy.deepcopy(self.sections))
        # Restore redo state
        self.sections = self._redo_stack.pop()
        return True
    
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._history) > 0
    
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0
    
    # ==================== Section Update Methods ====================
    
    def add_input_file(self, file_meta: Dict[str, Any]):
        """Add or update input file in the table."""
        self._save_state()
        # Check if file already exists (by path)
        file_path = file_meta.get('file_path', '')
        for i, f in enumerate(self.sections['input_files']):
            if f.get('file_path') == file_path:
                self.sections['input_files'][i] = file_meta
                return
        self.sections['input_files'].append(file_meta)
    
    def remove_input_file(self, file_path: str):
        """Remove input file from the table."""
        self._save_state()
        self.sections['input_files'] = [
            f for f in self.sections['input_files'] if f.get('file_path') != file_path
        ]
    
    def update_input_file_validation(self, file_path: str, validation_status: str):
        """Update validation status for an input file."""
        for f in self.sections['input_files']:
            if f.get('file_path') == file_path:
                f['validation'] = validation_status
                return
    
    def update_input_file_type(self, file_path: str, file_type: str):
        """Update file type for an input file."""
        for f in self.sections['input_files']:
            if f.get('file_path') == file_path:
                f['file_type'] = file_type
                return
    
    def clear_input_files(self):
        """Clear all input files from the table."""
        self._save_state()
        self.sections['input_files'] = []
    
    def update_input_files(self, files: List[Dict[str, Any]]):
        """Replace all input files with new list."""
        self._save_state()
        self.sections['input_files'] = files
    
    def add_conversion(self, conversion_data: Dict[str, Any]):
        """Add a conversion operation to the table."""
        self._save_state()
        conversion_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.sections['conversions'].append(conversion_data)
    
    def add_preprocessing(self, preprocess_data: Dict[str, Any]):
        """Add a preprocessing operation to the table."""
        self._save_state()
        preprocess_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.sections['preprocessing'].append(preprocess_data)
    
    def add_slicing(self, slicer_data: Dict[str, Any]):
        """Add a slicing operation to the table."""
        self._save_state()
        slicer_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.sections['slicing'].append(slicer_data)
    
    def add_ent_test(self, file_name: str, results: Dict[str, Any]):
        """Add ENT test results for a file."""
        self._save_state()
        self.sections['ent_tests'].append({
            'file_name': file_name,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'results': results
        })
    
    def add_nist_test(self, file_name: str, results: Dict[str, Any]):
        """Add NIST test results for a file."""
        self._save_state()
        self.sections['nist_tests'].append({
            'file_name': file_name,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'results': results
        })
    
    def add_dieharder_test(self, file_name: str, results: Dict[str, Any]):
        """Add Dieharder test results for a file."""
        self._save_state()
        self.sections['dieharder_tests'].append({
            'file_name': file_name,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'results': results
        })
    
    def add_borel_test(self, file_name: str, results: Dict[str, Any]):
        """Add Borel test results for a file."""
        self._save_state()
        self.sections['borel_tests'].append({
            'file_name': file_name,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'results': results
        })
    
    def add_autocorr_test(self, file_name: str, results: Dict[str, Any]):
        """Add Autocorrelation test results for a file."""
        self._save_state()
        self.sections['autocorr_tests'].append({
            'file_name': file_name,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'results': results
        })
    
    def add_api_operation(self, api_data: Dict[str, Any]):
        """Add API fetch operation."""
        self._save_state()
        api_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.sections['api_operations'].append(api_data)
    
    def add_prng_operation(self, prng_data: Dict[str, Any]):
        """Add PRNG generation operation."""
        self._save_state()
        prng_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.sections['prng_operations'].append(prng_data)
    
    def add_eyl_operation(self, eyl_data: Dict[str, Any]):
        """Add EYL device operation."""
        self._save_state()
        eyl_data['timestamp'] = datetime.now().strftime("%H:%M:%S")
        self.sections['eyl_operations'].append(eyl_data)
    
    # ==================== Rendering Methods ====================
    
    def _render_header(self) -> str:
        """Render the report header."""
        return self._render_template(
            "header.html",
            version=self.version,
            current_datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    
    def _render_input_files_section(self) -> str:
        """Render input files as a table."""
        if not self.sections['input_files']:
            return ""
        return self._render_template(
            "input_files_table.html",
            files=self.sections['input_files']
        )
    
    def _render_conversions_section(self) -> str:
        """Render conversions as a table."""
        if not self.sections['conversions']:
            return ""
        return self._render_template(
            "conversions_table.html",
            conversions=self.sections['conversions']
        )
    
    def _render_preprocessing_section(self) -> str:
        """Render preprocessing operations as a table."""
        if not self.sections['preprocessing']:
            return ""
        return self._render_template(
            "preprocessing_table.html",
            operations=self.sections['preprocessing']
        )
    
    def _render_slicing_section(self) -> str:
        """Render slicing operations as a table."""
        if not self.sections['slicing']:
            return ""
        return self._render_template(
            "slicing_table.html",
            operations=self.sections['slicing']
        )
    
    def _render_ent_tests_section(self) -> str:
        """Render ENT test results."""
        if not self.sections['ent_tests']:
            return ""
        return self._render_template(
            "ent_tests_table.html",
            tests=self.sections['ent_tests']
        )
    
    def _render_nist_tests_section(self) -> str:
        """Render NIST test results."""
        if not self.sections['nist_tests']:
            return ""
        return self._render_template(
            "nist_tests_section.html",
            tests=self.sections['nist_tests']
        )
    
    def _render_dieharder_tests_section(self) -> str:
        """Render Dieharder test results."""
        if not self.sections['dieharder_tests']:
            return ""
        return self._render_template(
            "dieharder_tests_table.html",
            tests=self.sections['dieharder_tests']
        )
    
    def _render_borel_tests_section(self) -> str:
        """Render Borel test results."""
        if not self.sections['borel_tests']:
            return ""
        return self._render_template(
            "borel_tests_table.html",
            tests=self.sections['borel_tests']
        )
    
    def _render_autocorr_tests_section(self) -> str:
        """Render Autocorrelation test results."""
        if not self.sections['autocorr_tests']:
            return ""
        return self._render_template(
            "autocorr_tests_table.html",
            tests=self.sections['autocorr_tests']
        )
    
    def _render_api_operations_section(self) -> str:
        """Render API operations."""
        if not self.sections['api_operations']:
            return ""
        return self._render_template(
            "api_operations_table.html",
            operations=self.sections['api_operations']
        )
    
    def _render_prng_operations_section(self) -> str:
        """Render PRNG operations."""
        if not self.sections['prng_operations']:
            return ""
        return self._render_template(
            "prng_operations_table.html",
            operations=self.sections['prng_operations']
        )
    
    def _render_eyl_operations_section(self) -> str:
        """Render EYL operations."""
        if not self.sections['eyl_operations']:
            return ""
        return self._render_template(
            "eyl_operations_table.html",
            operations=self.sections['eyl_operations']
        )
    
    def get_full_report(self) -> str:
        """Get the complete HTML report with all sections."""
        sections_html = []
        
        # Header always first
        sections_html.append(self._render_header())
        
        # Render each section in order
        sections_html.append(self._render_input_files_section())
        sections_html.append(self._render_conversions_section())
        sections_html.append(self._render_preprocessing_section())
        sections_html.append(self._render_slicing_section())
        sections_html.append(self._render_ent_tests_section())
        sections_html.append(self._render_nist_tests_section())
        sections_html.append(self._render_dieharder_tests_section())
        sections_html.append(self._render_borel_tests_section())
        sections_html.append(self._render_autocorr_tests_section())
        # QRNG operations at the end
        sections_html.append(self._render_api_operations_section())
        sections_html.append(self._render_eyl_operations_section())
        sections_html.append(self._render_prng_operations_section())
        
        # Filter out empty sections and join
        full_html = "\n".join(s for s in sections_html if s)
        
        return self._render_template("report_wrapper.html", report_content=full_html)
    
    def clear_report(self):
        """Clear all report sections."""
        self._save_state()
        self._init_sections()
    
    def initialize_report(self):
        """Initialize/reset the report."""
        self._init_sections()
        self._history.clear()
        self._redo_stack.clear()
    
    def save_report(self, output_path: str) -> bool:
        """Save the complete report to a file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self.get_full_report())
            return True
        except Exception as e:
            return False
    
    def add_ent_report(self, ent_data: Dict[str, Any]) -> str:
        """ Add ENT test report."""
        file_name = ent_data.get('input_file', ent_data.get('file_name', 'Unknown'))
        self.add_ent_test(file_name, ent_data)
        return ""
    
    def add_dieharder_report(self, dieharder_data: Dict[str, Any]) -> str:
        """ Add Dieharder test report."""
        file_name = dieharder_data.get('input_file', dieharder_data.get('file_name', 'Unknown'))
        self.add_dieharder_test(file_name, dieharder_data)
        return ""
    
    def add_nist_report(self, nist_data: Dict[str, Any]) -> str:
        """ Add NIST test report."""
        file_name = nist_data.get('input_file', nist_data.get('file_name', 'Unknown'))
        self.add_nist_test(file_name, nist_data)
        return ""
    
    def add_borel_report(self, borel_data: Dict[str, Any]) -> str:
        """ Add Borel test report."""
        file_name = borel_data.get('input_file', borel_data.get('file_name', 'Unknown'))
        self.add_borel_test(file_name, borel_data)
        return ""
    
    def add_autocorrelation_report(self, autocorr_data: Dict[str, Any]) -> str:
        """ Add Autocorrelation test report."""
        file_name = autocorr_data.get('input_file', autocorr_data.get('file_name', 'Unknown'))
        self.add_autocorr_test(file_name, autocorr_data)
        return ""
    
