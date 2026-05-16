# [QRandLab]
# Copyright (c) 2026 [M. H. Moradi]
#
# Licensed under the MIT License.
# See the LICENSE file in the project root for full license text.

"""Input tab for multi-file import and management."""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pathlib import Path
import subprocess

from ..manager.core_manager import CoreManager
from ..core.types import OperationStatus, FileType, FileExt


class InputTab(ttk.Frame):
    """Multi-file input management tab with table interface."""
    
    def __init__(self, parent, manager: CoreManager):
        super().__init__(parent, padding=20)
        self.manager = manager
        self.report_tab = None  # Will be set by main window
        self._is_restarting = False  # Flag to suppress logging during restart
        
        # Track file_id -> row mapping for the table
        self._file_rows = {}  # Maps file_id to treeview item id
        
        # Currently selected file for context menu
        self._selected_file_id = None
        
        # Subscribe to events
        self._setup_events()
        
        # Build UI
        self._build_ui()
    
    def _setup_events(self):
        """Subscribe to manager events."""
        # Multi-file events
        self.manager.on_files_added.subscribe(self._on_files_added)
        self.manager.on_files_removed.subscribe(self._on_files_removed)
        self.manager.on_file_type_changed.subscribe(self._on_file_type_changed)
        self.manager.on_file_item_validated.subscribe(self._on_file_item_validated)
        self.manager.on_all_files_validated.subscribe(self._on_all_files_validated)
        self.manager.on_files_cleared.subscribe(self._on_files_cleared)
        self.manager.on_sample_read.subscribe(self._on_sample_read)
        self.manager.on_validation_progress.subscribe(self._on_validation_progress)
        
        # Legacy events for backward compatibility
        self.manager.on_file_cleared.subscribe(self._on_file_cleared)
    
    def _apply_treeview_style(self):
        """Apply custom Treeview style for row height and header."""
        style = ttk.Style()
        
        # Configure row height
        style.configure("Custom.Treeview", rowheight=28)
        
        # Configure header with theme-aware colors
        theme_name = style.theme_use()
        
        # Get theme colors for header
        if 'dark' in theme_name.lower() or theme_name in ['darkly', 'cyborg', 'vapor', 'solar']:
            header_bg = "#3a3a3a"
            header_fg = "#ffffff"
        else:
            header_bg = "#e0e0e0"
            header_fg = "#000000"
        
        style.configure(
            "Custom.Treeview.Heading",
            background=header_bg,
            foreground=header_fg,
            font=("Helvetica", 10, "bold"),
            relief="flat"
        )
        
        # Map for hover/active states
        style.map(
            "Custom.Treeview.Heading",
            background=[("active", header_bg)],
            foreground=[("active", header_fg)]
        )
    
    def _on_theme_changed(self, event=None):
        """Handle theme change - reapply Treeview styles."""
        self._apply_treeview_style()
        
        # Force refresh the table to apply new row height
        if hasattr(self, 'file_table'):
            self.file_table.configure(style="Custom.Treeview")
    
    def _build_ui(self):
        """Build input tab UI with table and action buttons."""
        
        # Configure Treeview style for bigger rows and header
        self._apply_treeview_style()
        
        # Bind to theme change to reapply styles
        self.bind("<<ThemeChanged>>", self._on_theme_changed)
        
        # Main container with two columns: table on left, buttons on right
        main_container = ttk.Frame(self)
        main_container.pack(fill='x', pady=(0, 5))
        
        # Left side: Files Table
        table_frame = ttk.LabelFrame(main_container, text="Input Files", padding=10, bootstyle=INFO)
        table_frame.pack(side=LEFT, fill=BOTH, expand=YES, padx=(0, 10))
        
        # Create Treeview with columns (including folder)
        columns = ("name", "folder", "extension", "size", "type")
        self.file_table = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            style="Custom.Treeview"
        )
        
        # Configure columns
        self.file_table.heading("name", text="Name", anchor=W)
        self.file_table.heading("folder", text="Folder", anchor=W)
        self.file_table.heading("extension", text="Ext", anchor=CENTER)
        self.file_table.heading("size", text="Size", anchor=CENTER)
        self.file_table.heading("type", text="Type", anchor=CENTER)
        
        self.file_table.column("name", width=150, minwidth=100)
        self.file_table.column("folder", width=180, minwidth=100)
        self.file_table.column("extension", width=50, minwidth=40, anchor=CENTER)
        self.file_table.column("size", width=80, minwidth=60, anchor=CENTER)
        self.file_table.column("type", width=80, minwidth=60, anchor=CENTER)
        
        # Scrollbar for table
        table_scroll = ttk.Scrollbar(table_frame, orient=VERTICAL, command=self.file_table.yview)
        self.file_table.configure(yscrollcommand=table_scroll.set)
        
        self.file_table.pack(side=LEFT, fill=BOTH, expand=YES)
        table_scroll.pack(side=RIGHT, fill=Y)
        
        # Bind events for context menu and type selection
        self.file_table.bind("<Button-3>", self._show_context_menu)
        self.file_table.bind("<Double-1>", self._on_double_click)
        self.file_table.bind("<Motion>", self._on_table_motion)  # For tooltip
        
        # Create context menu
        self._create_context_menu()
        
        # Right side: Action Buttons
        button_frame = ttk.LabelFrame(main_container, text="Actions", padding=10, bootstyle=SUCCESS)
        button_frame.pack(side=RIGHT, fill=Y)
        
        # Inner frame for centering buttons vertically
        button_inner = ttk.Frame(button_frame)
        button_inner.pack(expand=YES, anchor='n')
        
        # Add files button (+)
        add_btn = ttk.Button(button_inner, text="+ Add Files", command=self._add_files, bootstyle=SUCCESS, width=12)
        add_btn.pack(pady=3, fill='both', anchor='n')    
        
        # Remove files button (-)
        remove_btn = ttk.Button(button_inner, text="- Remove", command=self._remove_selected_files, bootstyle=DANGER, width=12)
        remove_btn.pack(pady=3, fill='both', anchor='n')    
        
        # Separator
        ttk.Separator(button_inner, orient=HORIZONTAL).pack(fill=X, pady=10)
        
        # Validate all files button
        self.validate_btn = ttk.Button(button_inner, text="Validate Files", command=self._validate_all_files, bootstyle=INFO, width=12)
        self.validate_btn.pack(pady=3, fill='both', anchor='n')    
        
        # Progress bar for validation (always visible)
        self.validation_progress = ttk.Progressbar(button_inner, length=100, mode='determinate', bootstyle="info-striped")
        self.validation_progress.pack(pady=3, fill='both', anchor='n')    
        
        # Separator
        ttk.Separator(button_inner, orient=HORIZONTAL).pack(fill=X, pady=10)

        # Reset button
        reset_btn = ttk.Button(button_inner, text="Reset tab", command=self._reset_tab, bootstyle=SECONDARY, width=12)
        reset_btn.pack(pady=3, fill='both', anchor='n')  

        # Separator
        ttk.Separator(button_inner, orient=HORIZONTAL).pack(fill=X, pady=10)
        
        # Restart button
        restart_btn = ttk.Button( button_inner, text="Restart App", command=self._restart_app, bootstyle=WARNING, width=12)
        restart_btn.pack(pady=3, fill='both', anchor='n')    
    
        # Status Section at bottom - takes remaining space
        status_frame = ttk.LabelFrame(self, text="Status", padding=10, bootstyle=INFO)
        status_frame.pack(fill=BOTH, expand=YES, pady=(5, 0))
        
        # Status text area
        self.status_text = tk.Text(
            status_frame,
            height=8,
            font=("Courier", 9),
            wrap=tk.WORD,
            bg="#2b2b2b",
            fg="#ffffff",
            state=DISABLED
        )
        self.status_text.pack(fill=BOTH, expand=True, pady=5)
        
        # Configure text tags for colored output
        self.status_text.tag_configure("success", foreground="#4CAF50")
        self.status_text.tag_configure("error", foreground="#F44336")
        self.status_text.tag_configure("warning", foreground="#FF9800")
        
        # Scrollbar for status
        scrollbar = ttk.Scrollbar(self.status_text, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        self._log_info("Ready")
    
    def _create_context_menu(self):
        """Create right-click context menu for table rows."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Open Folder", command=self._open_folder)
        self.context_menu.add_command(label="Open File", command=self._open_file)
        self.context_menu.add_command(label="Rename", command=self._rename_file)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Read Sample", command=self._show_read_sample_window)
        self.context_menu.add_separator()
        
        # File type submenu
        self.type_menu = tk.Menu(self.context_menu, tearoff=0)
        self.context_menu.add_cascade(label="Set Type", menu=self.type_menu)
        
        # Tooltip for full path
        self._tooltip = None
        self._tooltip_id = None
    
    def _show_context_menu(self, event):
        """Show context menu on right-click."""
        # Get clicked row
        item = self.file_table.identify_row(event.y)
        if not item:
            return
        
        # Get current selection
        selected_items = self.file_table.selection()
        
        # If clicked item is not in selection, select only clicked item
        if item not in selected_items:
            self.file_table.selection_set(item)
            selected_items = (item,)
        
        # Get file_ids from selected rows
        self._selected_file_ids = [self._get_file_id_from_item(i) for i in selected_items]
        self._selected_file_ids = [fid for fid in self._selected_file_ids if fid]  # Filter None
        
        if not self._selected_file_ids:
            return
        
        # For single selection, also set _selected_file_id for backward compatibility
        self._selected_file_id = self._selected_file_ids[0] if len(self._selected_file_ids) == 1 else None
        
        # Update type submenu based on common valid types for all selected files
        self.type_menu.delete(0, tk.END)
        type_options = self._get_common_type_options(self._selected_file_ids)
        
        if len(self._selected_file_ids) > 1:
            # Multiple files selected - show count in menu
            for type_opt in type_options:
                self.type_menu.add_command(
                    label=f"{type_opt} ({len(self._selected_file_ids)} files)",
                    command=lambda t=type_opt: self._set_file_type_for_selected(t)
                )
        else:
            # Single file selected
            for type_opt in type_options:
                self.type_menu.add_command(
                    label=type_opt,
                    command=lambda t=type_opt: self._set_file_type(self._selected_file_ids[0], t)
                )
        
        # Show menu at mouse position
        self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _get_file_id_from_item(self, item):
        """Get file_id from treeview item."""
        for file_id, row_item in self._file_rows.items():
            if row_item == item:
                return file_id
        return None
    
    def _get_type_options_for_ext(self, file_ext):
        """Get available type options based on file extension."""
        if file_ext in (FileExt.BIN, FileExt.DAT):
            return ["binary"]
        elif file_ext == FileExt.TXT:
            return ["string01", "hex", "uint8", "uint16", "uint32", "uint64"]
        else:
            return ["binary", "string01", "hex", "uint8", "uint16", "uint32", "uint64"]
    
    def _get_common_type_options(self, file_ids):
        """Get type options valid for all selected files (intersection of valid types)."""
        if not file_ids:
            return []
        
        # Start with all possible types
        common_types = None
        
        for file_id in file_ids:
            file_item = self.manager.get_file_by_id(file_id)
            if not file_item:
                continue
            
            file_types = set(self._get_type_options_for_ext(file_item.file_ext))
            
            if common_types is None:
                common_types = file_types
            else:
                common_types = common_types.intersection(file_types)
        
        # Return in consistent order
        all_types = ["binary", "string01", "hex", "uint8", "uint16", "uint32", "uint64"]
        return [t for t in all_types if common_types and t in common_types]
    
    def _set_file_type_for_selected(self, file_type):
        """Set file type for all selected files."""
        if not hasattr(self, '_selected_file_ids') or not self._selected_file_ids:
            return
        
        success_count = 0
        for file_id in self._selected_file_ids:
            result = self.manager.set_file_type_for_item(file_id, file_type)
            if result.ok:
                self._update_table_row(file_id)
                success_count += 1
        
        if success_count > 0:
            self._log_success(f"Set type '{file_type}' for {success_count} file(s)")
    
    def _on_double_click(self, event):
        """Handle double-click on table row to change file type."""
        # Get clicked column
        region = self.file_table.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        column = self.file_table.identify_column(event.x)
        item = self.file_table.identify_row(event.y)
        
        if not item:
            return
        
        # Only respond to type column (column #5 with folder added)
        if column == "#5":
            file_id = self._get_file_id_from_item(item)
            if file_id:
                self._show_type_selector(event, file_id, item)
    
    def _show_type_selector(self, event, file_id, item):
        """Show combobox for type selection."""
        file_item = self.manager.get_file_by_id(file_id)
        if not file_item:
            return
        
        # Get available types
        type_options = self._get_type_options_for_ext(file_item.file_ext)
        
        # Create a combobox overlay
        bbox = self.file_table.bbox(item, column="type")
        if not bbox:
            return
        
        x, y, width, height = bbox
        
        # Create temporary combobox
        combo = ttk.Combobox(
            self.file_table,
            values=type_options,
            state="readonly",
            width=12
        )
        
        current_type = file_item.file_type.value if file_item.file_type else "--"
        if current_type in type_options:
            combo.set(current_type)
        else:
            combo.set(type_options[0] if type_options else "")
        
        combo.place(x=x, y=y, width=width, height=height)
        combo.focus_set()
        
        def on_select(evt):
            selected_type = combo.get()
            combo.destroy()
            if selected_type:
                self._set_file_type(file_id, selected_type)
        
        def on_focus_out(evt):
            combo.destroy()
        
        combo.bind("<<ComboboxSelected>>", on_select)
        combo.bind("<FocusOut>", on_focus_out)
        combo.bind("<Return>", on_select)
        combo.bind("<Escape>", on_focus_out)
    
    def _set_file_type(self, file_id, file_type):
        """Set file type for a specific file."""
        result = self.manager.set_file_type_for_item(file_id, file_type)
        if result.ok:
            self._update_table_row(file_id)
    
    def _update_table_row(self, file_id):
        """Update a single row in the table."""
        file_item = self.manager.get_file_by_id(file_id)
        if not file_item or file_id not in self._file_rows:
            return
        
        item = self._file_rows[file_id]
        
        # Format folder (truncate if too long)
        folder_str = self._truncate_path(file_item.file_dir)
        
        # Format size
        size_str = self._format_size(file_item.file_size)
        
        # Format type
        type_str = file_item.file_type.value if file_item.file_type else "--"
        
        # Update values
        self.file_table.item(item, values=(
            file_item.file_name,
            folder_str,
            file_item.file_ext.value if file_item.file_ext else "--",
            size_str,
            type_str
        ))
    
    def _format_size(self, size_bytes):
        """Format file size for display."""
        if not size_bytes:
            return "--"
        
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        if size_mb >= 1:
            return f"{size_mb:.2f} MB"
        elif size_kb >= 1:
            return f"{size_kb:.2f} KB"
        else:
            return f"{size_bytes} B"
    
    def _truncate_path(self, path, max_length=25):
        """Truncate a path for display, showing end portion."""
        if not path:
            return "--"
        
        if len(path) <= max_length:
            return path
        
        # Show last portion with ellipsis
        return "..." + path[-(max_length-3):]
    
    def _on_table_motion(self, event):
        """Show tooltip with full path when hovering over folder column."""
        # Cancel any pending tooltip
        if self._tooltip_id:
            self.after_cancel(self._tooltip_id)
            self._tooltip_id = None
        
        # Hide existing tooltip
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
        
        # Get item and column under cursor
        item = self.file_table.identify_row(event.y)
        column = self.file_table.identify_column(event.x)
        
        if not item or column != "#2":  # #2 is folder column
            return
        
        # Get file_id and show tooltip after delay
        file_id = self._get_file_id_from_item(item)
        if file_id:
            self._tooltip_id = self.after(500, lambda: self._show_tooltip(event, file_id))
    
    def _show_tooltip(self, event, file_id):
        """Show tooltip with full path."""
        file_item = self.manager.get_file_by_id(file_id)
        if not file_item:
            return
        
        # Create tooltip window
        self._tooltip = tk.Toplevel(self)
        self._tooltip.wm_overrideredirect(True)
        self._tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
        
        label = ttk.Label(
            self._tooltip,
            text=file_item.file_path,
            background="#ffffe0",
            foreground="#000000",
            relief="solid",
            borderwidth=1,
            padding=5
        )
        label.pack()
        
        # Auto-hide after 3 seconds
        self.after(3000, self._hide_tooltip)
    
    def _hide_tooltip(self):
        """Hide the tooltip."""
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None
    
    def _rename_file(self):
        """Rename the selected file."""
        if not self._selected_file_id:
            return
        
        file_item = self.manager.get_file_by_id(self._selected_file_id)
        if not file_item:
            return
        
        # Create rename dialog
        dialog = tk.Toplevel(self)
        dialog.title("Rename File")
        # dialog.geometry("400x120")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 120) // 2
        dialog.geometry(f"+{x}+{y}")
        
        # Current name label
        ttk.Label(dialog, text="Current name:").pack(pady=(10, 0))
        ttk.Label(dialog, text=f"{file_item.file_name}{file_item.file_ext.value}", font=("Helvetica", 10, "bold")).pack()
        
        # New name entry
        ttk.Label(dialog, text="New name (without extension):").pack(pady=(10, 0))
        name_var = tk.StringVar(value=file_item.file_name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        name_entry.select_range(0, tk.END)
        name_entry.focus_set()
        
        def do_rename():
            new_name = name_var.get().strip()
            if not new_name:
                self._log_error("Name cannot be empty")
                return
            
            # Update the file item's name
            old_path = Path(file_item.file_path)
            new_path = old_path.parent / f"{new_name}{file_item.file_ext.value}"
            
            try:
                # Rename actual file
                old_path.rename(new_path)
                
                # Update file item
                file_item.file_name = new_name
                file_item.file_path = new_path.as_posix()
                
                # Update table
                self._update_table_row(file_item.id)
                self._log_success(f"Renamed to '{new_name}{file_item.file_ext.value}'")
                dialog.destroy()
            except Exception as e:
                self._log_error(f"Rename failed: {e}")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Rename", command=do_rename, bootstyle=SUCCESS).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy, bootstyle=SECONDARY).pack(side=LEFT, padx=5)
        
        # Bind Enter key
        name_entry.bind("<Return>", lambda e: do_rename())
    
    # ==================== Action Button Handlers ====================
    
    def _add_files(self):
        """Open file dialog to add multiple files."""
        file_paths = filedialog.askopenfilenames(
            title="Select Input Files",
            initialdir=self.manager.get_last_directory(),
            filetypes=[
                ("Supported Files", "*.bin *.dat *.txt"),
                ("Binary Files", "*.bin"),
                ("Data Files", "*.dat"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ]
        )
        
        if file_paths:
            self.manager.set_last_directory(file_paths[0])
            result = self.manager.add_files(list(file_paths))
            if not result.ok:
                self._log_error(f"Failed to add files: {result.message}")
    
    def _remove_selected_files(self):
        """Remove selected files from the table."""
        selected_items = self.file_table.selection()
        if not selected_items:
            self._log_warning("No files selected to remove")
            return
        
        # Get file_ids for selected items
        file_ids = []
        for item in selected_items:
            file_id = self._get_file_id_from_item(item)
            if file_id:
                file_ids.append(file_id)
        
        if file_ids:
            result = self.manager.remove_files(file_ids)
            if result.ok:
                # Remove from table
                for item in selected_items:
                    file_id = self._get_file_id_from_item(item)
                    if file_id in self._file_rows:
                        del self._file_rows[file_id]
                    self.file_table.delete(item)
                self._update_status_bar()
    
    def _validate_all_files(self):
        """Validate all files that have a type set."""
        file_count = self.manager.get_file_count()
        if file_count == 0:
            self._log_warning("No files loaded to validate")
            return
        
        # Check if any file has a type set
        files = self.manager.get_all_files()
        files_with_type = [f for f in files if f.file_type]
        
        if not files_with_type:
            self._log_warning("No files have type set. Set file types first.")
            return
        
        self.validate_btn.config(state=DISABLED)
        self._log_info(f"Validating {len(files_with_type)} file(s)...")
        
        # Reset progress bar
        self.validation_progress['value'] = 0
        
        result = self.manager.validate_all_files()
        if not result.ok:
            self.validate_btn.config(state=NORMAL)
            self._log_error(f"Validation failed to start: {result.message}")
    
    def _restart_app(self):
        """Restart the app - stop all operations and reset everything."""
        has_running = self.manager.has_running_operations()
        
        if has_running:
            response = messagebox.askyesno(
                "Operations Running",
                "There are operations still running.\n\n"
                "Do you want to terminate them and restart the app?"
            )
            if not response:
                return
        
        self._is_restarting = True
        
        try:
            # Stop all operations
            self.manager.stop_all_operations()
            
            # Clear table
            for item in self.file_table.get_children():
                self.file_table.delete(item)
            self._file_rows.clear()
            
            # Clear status
            self.status_text.config(state=NORMAL)
            self.status_text.delete(1.0, tk.END)
            self.status_text.insert(tk.END, "Ready\n")
            self.status_text.config(state=DISABLED)
            
            # Re-enable validate button and reset progress bar
            self.validate_btn.config(state=NORMAL)
            self.validation_progress['value'] = 0
            
            # Reset manager state
            self.manager.reset_state()
            
            # Reset main window status bar
            main_window = self.winfo_toplevel()
            if hasattr(main_window, 'status_var'):
                main_window.status_var.set("Ready")
            if hasattr(main_window, 'file_info_var'):
                main_window.file_info_var.set("No files loaded")
        finally:
            self._is_restarting = False
    
    def _reset_tab(self):
        """Reset this tab only (clear status, keep files)."""
        self.status_text.config(state=NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=DISABLED)
        self._log_info("Ready")
        
        # Re-enable validate button and reset progress bar
        self.validate_btn.config(state=NORMAL)
        self.validation_progress['value'] = 0
    
    # ==================== Context Menu Handlers ====================
    
    def _open_folder(self):
        """Open the folder containing the selected file."""
        if not self._selected_file_id:
            return
        
        file_item = self.manager.get_file_by_id(self._selected_file_id)
        if not file_item:
            return
        
        try:
            folder_path = Path(file_item.file_dir)
            if folder_path.exists():
                # Windows
                subprocess.run(['explorer', str(folder_path)], check=False)
                self._log_success(f"Opened folder: {file_item.file_dir}")
            else:
                self._log_error(f"Folder does not exist: {file_item.file_dir}")
        except Exception as e:
            self._log_error(f"Failed to open folder: {e}")
    
    def _open_file(self):
        """Open the selected file with default application."""
        if not self._selected_file_id:
            return
        
        file_item = self.manager.get_file_by_id(self._selected_file_id)
        if not file_item:
            return
        
        try:
            file_path = Path(file_item.file_path)
            if file_path.exists():
                # Windows - use os.startfile equivalent
                subprocess.run(['start', '', str(file_path)], shell=True, check=False)
                self._log_success(f"Opened file: {file_item.file_name}")
            else:
                self._log_error(f"File does not exist: {file_item.file_path}")
        except Exception as e:
            self._log_error(f"Failed to open file: {e}")
    
    def _show_read_sample_window(self):
        """Show the read sample popup window."""
        if not self._selected_file_id:
            return
        
        file_item = self.manager.get_file_by_id(self._selected_file_id)
        if not file_item:
            return
        
        if not file_item.file_type:
            self._log_warning(f"Set file type for '{file_item.file_name}' first")
            return
        
        # Create popup window
        self._create_read_sample_window(file_item)
    
    def _create_read_sample_window(self, file_item):
        """Create the read sample popup window."""
        window = tk.Toplevel(self)
        window.title(f"Read Sample - {file_item.file_name}")
        window.geometry("850x550")
        window.transient(self)
        
        # Store file_id for later use
        window.file_id = file_item.id
        window.file_item = file_item
        
        # Top frame for controls
        control_frame = ttk.LabelFrame(window, text='Read Sample', bootstyle=INFO, padding=10)
        control_frame.pack(fill=X, padx=(10,10), pady=(5,5))
        
        # Bytes entry
        ttk.Label(control_frame, text="Bytes to read:").pack(side=LEFT, padx=5)
        bytes_var = tk.StringVar(value="256")
        bytes_entry = ttk.Entry(control_frame, textvariable=bytes_var, width=15)
        bytes_entry.pack(side=LEFT, padx=5)
        
        # Read Sample button
        def do_read_sample():
            try:
                n_bytes = int(bytes_var.get())
                if n_bytes <= 0:
                    self._log_error("Bytes must be positive")
                    return
                # Store window reference for callback
                self._current_sample_window = window
                self._current_sample_text = text_area
                result = self.manager.read_sample_from_item(window.file_id, n_bytes)
                if not result.ok:
                    self._log_error(f"Failed to read sample: {result.message}")
            except ValueError:
                self._log_error("Invalid number of bytes")
        
        read_btn = ttk.Button(control_frame, width=15, text="Read Sample", command=do_read_sample, bootstyle=SUCCESS)
        read_btn.pack(side=LEFT, padx=5)
        
        # Text area for sample display
        text_frame = ttk.Frame(window, padding=10)
        text_frame.pack(fill=BOTH, expand=YES)
        
        text_area = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Courier", 10))
        text_area.pack(fill=BOTH, expand=YES)
        text_area.insert('1.0', "Click 'Read Sample' to read data...")
        text_area.config(state='disabled')
        
        # Store text area reference
        window.text_area = text_area
        
        # Copy button
        def copy_to_clipboard():
            text_area.config(state='normal')
            content = text_area.get('1.0', tk.END).strip()
            text_area.config(state='disabled')
            window.clipboard_clear()
            window.clipboard_append(content)
            self._log_success("Sample data copied to clipboard")
        
        copy_btn = ttk.Button(control_frame,  width=15, text="Copy", command=copy_to_clipboard, bootstyle=PRIMARY)
        copy_btn.pack(side=LEFT, padx=5)
        

    # ==================== Event Handlers ====================
    
    def _on_files_added(self, status: OperationStatus):
        """Handle files added event."""
        if status.ok and status.payload:
            added_items = status.payload.get('added', [])
            for file_item in added_items:
                self._add_file_to_table(file_item)
                # Add to report
                self._add_file_to_report(file_item)
            
            total = status.payload.get('total_files', 0)
            self._log_success(f"Added {len(added_items)} file(s). Total: {total}")
            self._update_status_bar()
            
            # Log any failed files
            failed = status.payload.get('failed', [])
            for fail_msg in failed:
                self._log_warning(f"Skipped: {fail_msg}")
        else:
            self._log_error(f"Add files failed: {status.message}")
    
    def _add_file_to_report(self, file_item):
        """Add a single file to the report."""
        if self.report_tab is not None:
            file_meta = {
                'file_path': file_item.file_path or 'N/A',
                'file_dir': file_item.file_dir or 'N/A',
                'file_name': file_item.file_name or 'N/A',
                'file_size': self._format_size(file_item.file_size) if file_item.file_size else 'N/A',
                'file_ext': file_item.file_ext.value if file_item.file_ext else 'N/A',
                'file_type': file_item.file_type.value if file_item.file_type else 'Not Set',
                'validation': 'Unvalidated'
            }
            self.report_tab.add_input_file_section(file_meta)
    
    def _add_file_to_table(self, file_item):
        """Add a file item to the table."""
        folder_str = self._truncate_path(file_item.file_dir)
        size_str = self._format_size(file_item.file_size)
        type_str = file_item.file_type.value if file_item.file_type else "--"
        
        item = self.file_table.insert("", tk.END, values=(
            file_item.file_name,
            folder_str,
            file_item.file_ext.value if file_item.file_ext else "--",
            size_str,
            type_str
        ))
        
        self._file_rows[file_item.id] = item
    
    def _on_files_removed(self, status: OperationStatus):
        """Handle files removed event."""
        if status.ok and status.payload:
            removed_paths = status.payload.get('removed_paths', [])
            removed = status.payload.get('removed_count', 0)
            total = status.payload.get('total_files', 0)
            
            # Remove from report
            if self.report_tab is not None:
                for file_path in removed_paths:
                    self.report_tab.remove_input_file(file_path)
            
            self._log_success(f"Removed {removed} file(s). Total: {total}")
            self._update_status_bar()
    
    def _on_file_type_changed(self, status: OperationStatus):
        """Handle file type changed event."""
        if status.ok and status.payload:
            file_id = status.payload.get('file_id')
            file_type = status.payload.get('file_type')
            if file_id:
                self._update_table_row(file_id)
                # Update file type in report
                if self.report_tab is not None:
                    item = self.manager.get_file_by_id(file_id)
                    if item and item.file_path:
                        self.report_tab.update_input_file_type(item.file_path, file_type)
            self._log_success(f"Type set to '{file_type}'")
    
    def _on_file_item_validated(self, status: OperationStatus):
        """Handle single file validation event."""
        if status.ok:
            self._log_success(status.message)
            # Update validation status in report
            if self.report_tab is not None and status.payload:
                item = status.payload.get('item')
                file_path = item.file_path if item else status.payload.get('file_path')
                if file_path:
                    self.report_tab.update_input_file_validation(file_path, 'Validated')
        else:
            self._log_error(status.message)
            # Mark as failed in report
            if self.report_tab is not None and status.payload:
                item = status.payload.get('item')
                file_path = item.file_path if item else status.payload.get('file_path')
                if file_path:
                    self.report_tab.update_input_file_validation(file_path, 'Failed')
    
    def _on_all_files_validated(self, status: OperationStatus):
        """Handle all files validation completion."""
        self.validate_btn.config(state=NORMAL)
        # Progress bar stays full after completion
        
        if status.ok:
            payload = status.payload or {}
            passed = payload.get('passed', 0)
            failed = payload.get('failed', 0)
            self._log_success(f"Validation complete: {passed} passed, {failed} failed")
        else:
            self._log_error(f"Validation failed: {status.message}")
    
    def _on_validation_progress(self, status: OperationStatus):
        """Handle validation progress update."""
        if status.payload:
            current = status.payload.get('current', 0)
            total = status.payload.get('total', 1)
            if total > 0:
                progress_pct = (current / total) * 100
                self.validation_progress['value'] = progress_pct
    
    def _on_files_cleared(self, status: OperationStatus):
        """Handle files cleared event."""
        if not self._is_restarting:
            # Clear table
            for item in self.file_table.get_children():
                self.file_table.delete(item)
            self._file_rows.clear()
            self._update_status_bar()
            self._log_success("All files cleared")
            
            # Clear input files from report
            if self.report_tab is not None:
                self.report_tab.clear_input_files()
    
    def _on_file_cleared(self, status: OperationStatus):
        """Handle legacy file cleared event (backward compatibility)."""
        pass  # Multi-file version handles this via on_files_cleared
    
    def _on_sample_read(self, status: OperationStatus):
        """Handle sample read event - update popup window if open."""
        if not status.ok:
            self._log_error(f"Sample read failed: {status.message}")
            return
        
        payload = status.payload
        if not payload:
            return
        
        # Check if payload has 'result' key (multi-file format)
        if 'result' in payload:
            sample_result = payload['result']
            file_type = payload.get('file_type', 'binary')
        else:
            # Legacy format
            sample_result = payload
            file_type = self.manager.input_meta.file_type.value if self.manager.input_meta.file_type else 'binary'
        
        # Update the sample window if it exists
        if hasattr(self, '_current_sample_window') and self._current_sample_window.winfo_exists():
            text_area = self._current_sample_text
            formatted_data = self._format_sample_data(sample_result, file_type)
            
            text_area.config(state='normal')
            text_area.delete('1.0', tk.END)
            text_area.insert('1.0', formatted_data)
            text_area.config(state='disabled')
            
            self._log_success(f"Sample read: {sample_result.title}")
    
    def _format_sample_data(self, sample_result, file_type):
        """Format sample data for display based on file type."""
        if file_type == "string01":
            try:
                return sample_result.data.decode('utf-8', errors='replace')
            except:
                return sample_result.data.hex().upper()
        
        elif file_type == "hex":
            try:
                text = sample_result.data.decode('utf-8', errors='replace')
                hex_str = ''.join(text.split()).upper()
                hex_pairs = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
                lines = []
                for i in range(0, len(hex_pairs), 32):
                    line = ' '.join(hex_pairs[i:i+32])
                    lines.append(line)
                return '\n'.join(lines)
            except:
                return sample_result.data.hex().upper()
        
        elif file_type == "binary":
            hex_str = sample_result.data.hex().upper()
            hex_pairs = [hex_str[i:i+2] for i in range(0, len(hex_str), 2)]
            lines = []
            for i in range(0, len(hex_pairs), 32):
                line = ' '.join(hex_pairs[i:i+32])
                lines.append(line)
            return '\n'.join(lines)
        
        elif file_type in ("uint8", "uint16", "uint32", "uint64"):
            try:
                text = sample_result.data.decode('utf-8', errors='replace')
                lines = text.strip().split('\n')
                numbers = [line.strip() for line in lines if line.strip()]
                return '\n'.join(numbers)
            except:
                return sample_result.data.hex().upper()
        
        else:
            hex_str = sample_result.data.hex().upper()
            return '\n'.join([hex_str[i:i+64] for i in range(0, len(hex_str), 64)])
    
    def _update_status_bar(self):
        """Update main window status bar with file count."""
        main_window = self.winfo_toplevel()
        file_count = self.manager.get_file_count()
        
        if hasattr(main_window, 'file_info_var'):
            if file_count == 0:
                main_window.file_info_var.set("No files loaded")
            elif file_count == 1:
                main_window.file_info_var.set("1 file loaded")
            else:
                main_window.file_info_var.set(f"{file_count} files loaded")
    
    # ==================== Logging Methods ====================
    
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
    
    # ==================== Report Integration ====================
    
    def _add_to_report(self, file_items):
        """Add file information to the report."""
        if self.report_tab is not None:
            # Multi-file report - create summary
            for item in file_items:
                file_meta_dict = {
                    'file_path': item.file_path or 'N/A',
                    'file_dir': item.file_dir or 'N/A',
                    'file_name': item.file_name or 'N/A',
                    'file_size': item.file_size or 'N/A',
                    'file_ext': item.file_ext.value if item.file_ext else 'N/A',
                    'file_type': item.file_type.value if item.file_type else 'N/A'
                }
                self.report_tab.add_input_file_section(file_meta_dict)
