# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Help system generator with theme support and HTML rendering."""

from pathlib import Path
from typing import List, Tuple
import ttkbootstrap as ttk
from jinja2 import Environment, FileSystemLoader
import sys


class HelpGenerator:
    """Generates help documentation HTML with theme support."""
    
    def __init__(self, theme_name: str = "darkly", style_obj=None):
        """Initialize the help generator.
        
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
        self.help_sections_dir = self.templates_dir / "help_sections"
        
        # Setup Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        self.theme_name = theme_name
        self.style_obj = style_obj
        self._update_theme(theme_name)
    
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
    
    def set_theme(self, theme_name: str):
        """Change the theme for help display.
        
        Args:
            theme_name: New theme name
        """
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
    
    def render_help_content(self, help_content: str) -> str:
        """Wrap help content in styled HTML template.
        
        Args:
            help_content: Raw HTML content from help file
            
        Returns:
            str: Fully styled HTML page
        """
        return self._render_template("help_wrapper.html", help_content=help_content)
    
    def get_help_sections(self) -> List[Tuple[str, List[Tuple[str, str]]]]:
        """Get the structured help sections for navigation.
        
        Returns:
            List of tuples: (section_title, [(topic_title, topic_file), ...])
        """
        return [
            ("Getting Started", [
                ("Input Files", "input_tab_help.html"),
                ("RNG Sources", "qrng_tab_help.html"),
            ]),
            ("Data Processing", [
                ("Preprocessing", "preprocessing_tab_help.html"),
                ("Format Converter", "converter_tab_help.html"),
                ("Data Slicer", "slicer_tab_help.html"),
            ]),
            ("Testing & Reports", [
                ("Statistical Tests", "tests_tab_help.html"),
                ("Reports", "report_tab_help.html"),
            ]),
        ]
