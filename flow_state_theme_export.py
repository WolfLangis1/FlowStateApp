"""
Flow State: Theme System & Export Module
Customizable themes and export/streaming capabilities
"""

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Callable, Any
import numpy as np # For ExportManager frame generation example
from PIL import Image, ImageDraw, ImageFont, ImageTk # For ThemeEditor preview
import threading # For ExportManager/StreamingServer background tasks
import queue # Potentially for ExportManager progress
import subprocess # For FFmpeg in ExportManager
# import socket # http.server handles this
# import struct # Not used
# import wave # Not used
import datetime # For ExportManager (if needed for naming)
import tempfile # For ExportManager video frames
import shutil # For ExportManager cleanup
import logging
import concurrent.futures # For ExportManager tasks
import re # For StreamingServer range requests

logger = logging.getLogger(__name__)

# Assuming global EXPORT_PROCESS_POOL, EXPORT_THREAD_POOL are defined in launcher or a shared utility
# For standalone module:
if 'EXPORT_PROCESS_POOL' not in globals(): # Check if already defined by another import (unlikely)
    EXPORT_PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) // 2 -1), thread_name_prefix="ExportProc")
if 'EXPORT_THREAD_POOL' not in globals():
    EXPORT_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="ExportIO")


@dataclass
class Theme:
    name: str
    primary_bg: str = "#1e1e1e"
    secondary_bg: str = "#2e2e2e"
    accent_bg: str = "#3e3e3e" # Used for selected tabs, active elements
    primary_fg: str = "#ffffff"
    secondary_fg: str = "#cccccc" # Slightly dimmer text
    accent_color: str = "#00ffff" # For highlights, progress bars, important icons/text
    highlight_color: str = "#0099cc" # For selections, hover states
    error_color: str = "#ff4444"
    success_color: str = "#44ff44"
    warning_color: str = "#ffaa44"
    
    viz_bg: str = "#000000"
    viz_primary: str = "#00ffff"
    viz_secondary: str = "#ff00ff"
    viz_tertiary: str = "#ffff00"
    waveform_color: str = "#00ff00"
    spectrum_colors: List[str] = field(default_factory=lambda: ["#ff0000", "#ff8800", "#ffff00", "#00ff00", "#00ffff", "#0088ff", "#ff00ff"])
    
    font_family: str = "Arial" # Consider system fonts: Segoe UI (Win), San Francisco (macOS), Cantarell (GNOME)
    font_size_small: int = 8   # Adjusted sizes
    font_size_normal: int = 10
    font_size_large: int = 11
    font_size_title: int = 13
    
    def to_dict(self) -> Dict: return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Theme':
        # Ensure all fields are present or provide defaults if loading from older format
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        # Filter out extra keys and provide defaults for missing ones from class definition
        valid_data = {k: data[k] for k in data if k in field_names}
        # For fields not in valid_data but in field_names, dataclass defaults will apply
        return cls(**valid_data)


class ThemeManager:
    # ... (Full implementation as in "Theme System & Export Module" pass, including:
    #      __init__(app_root), load_builtin_themes, load_custom_themes, save_theme,
    #      apply_theme (updates ttk.Style), register_callback, get_theme_names, get_current_theme) ...
    # Key: apply_theme should robustly update ttk styles and then call registered callbacks.
    def __init__(self, app_root_tk_widget: tk.Tk): # Renamed param
        self.root = app_root_tk_widget
        self.current_theme: Optional[Theme] = None
        self.themes: Dict[str, Theme] = {}
        # Use consistent app data path
        self.base_app_dir = Path.home() / ".flowstate"
        self.theme_dir = self.base_app_dir / "themes"
        self.theme_dir.mkdir(parents=True, exist_ok=True)
        
        self.callbacks: List[Callable[[Theme], None]] = []
        
        self.load_builtin_themes()
        self.load_custom_themes()
        
        default_theme_name = "Dark Cyan" # Default theme
        if default_theme_name in self.themes:
            self.apply_theme(default_theme_name)
        elif self.themes: # Fallback to first available theme if default is missing
            first_theme = list(self.themes.keys())[0]
            logger.warning(f"Default theme '{default_theme_name}' not found. Applying '{first_theme}'.")
            self.apply_theme(first_theme)
        else: # No themes at all
            logger.error("No themes loaded (builtin or custom). UI will use Tkinter defaults.")
            # Create a very basic fallback theme to prevent errors if current_theme is accessed
            self.current_theme = Theme(name="Fallback Default Theme")
            # No ttk styling applied in this case.

    # ... rest of ThemeManager (load_builtin_themes, load_custom_themes, save_theme, apply_theme, etc.)
    # Ensure apply_theme calls self.root.update_idletasks() at the end.
    pass


class ThemeEditor(tk.Toplevel): # As refined in "UI Polish" pass
    # ... (Full implementation including __init__(parent, theme_manager, host_app_ref, base_theme),
    #      create_ui with color pickers, font settings, preview,
    #      pick_color, pick_spectrum_color, update_color, update_preview,
    #      save_theme (uses theme_manager.save_theme), apply_and_save_theme) ...
    # Ensure it uses host_app_ref.root for parenting if that's the convention.
    pass


class ExportManager: # As refined in "UI Polish" pass
    # ... (Full implementation including __init__(progress_callback), audio_formats, video_formats,
    #      _run_ffmpeg_command, export_audio_async, export_visualization_async,
    #      _generate_frames_cpu_pil (placeholder for CPU viz frame gen),
    #      batch_export_audio_async, stop_current_export, export_audio_snippet_async) ...
    pass

class StreamingServer: # Conceptual, as before
    # ... (Full implementation from previous "Theme System & Export Module" pass,
    #      using http.server in a thread. Aware of its limitations for concurrency.) ...
    pass


class ThemeExportMainUI(ttk.Frame): # As refined in "UI Polish" pass
    # ... (Full implementation including __init__(parent, host_app_ref), create_ui,
    #      open_detailed_batch_audio_export_dialog, open_detailed_viz_export_dialog.
    #      These dialog launchers use self.host_app to get library data or current track info,
    #      and then call self.export_manager methods.) ...
    pass


# Integration functions for launcher
def create_theme_export_main_tab(notebook: ttk.Notebook, host_app_ref: Any) -> ThemeExportMainUI:
    """Creates the main tab for Export and Streaming related controls."""
    main_frame = ttk.Frame(notebook) # Style from theme
    notebook.add(main_frame, text="Manage") # Tab name like "Manage" or "Output"
    
    ui = ThemeExportMainUI(main_frame, host_app_ref=host_app_ref)
    ui.pack(fill=tk.BOTH, expand=True)
    
    # Store ExportManager on host_app if it's created here and needed globally
    host_app_ref.export_manager_ref = ui.export_manager 
    return ui


def create_theme_menu_items(menubar_widget: tk.Menu, host_app_ref: Any):
    """Populates the 'Themes' cascade menu. Called by launcher."""
    if not host_app_ref.theme_manager:
        logger.warning("ThemeManager not available on host_app, cannot create theme menu.")
        return

    tm = host_app_ref.theme_manager
    theme_menu_cascade = tk.Menu(menubar_widget, tearoff=0)
    # Apply theme to menu itself (basic example, full theming of tk.Menu is limited)
    if tm.current_theme:
        try:
            theme_menu_cascade.configure(bg=tm.current_theme.secondary_bg, fg=tm.current_theme.primary_fg,
                                         activebackground=tm.current_theme.accent_bg, 
                                         activeforeground=tm.current_theme.primary_fg)
        except tk.TclError as e:
            logger.debug(f"Could not apply full theme to theme menu: {e}")


    menubar_widget.add_cascade(label="Themes", menu=theme_menu_cascade)
    
    for theme_name_val in tm.get_theme_names():
        theme_menu_cascade.add_command(label=theme_name_val,
            command=lambda name=theme_name_val: tm.apply_theme(name))
    theme_menu_cascade.add_separator()
    
    theme_editor_module = host_app_ref.loaded_modules.get('theme_export') # This module itself
    if theme_editor_module and hasattr(theme_editor_module, 'ThemeEditor'):
        theme_menu_cascade.add_command(label="Create New Theme...",
            command=lambda: theme_editor_module.ThemeEditor(host_app_ref.root, tm, host_app_ref, None)) # base_theme=None for new
        theme_menu_cascade.add_command(label="Edit Current Theme...",
            command=lambda: theme_editor_module.ThemeEditor(host_app_ref.root, tm, host_app_ref, tm.current_theme))


# Example helper for export dialogs if they become complex Toplevels themselves
# def create_export_dialog_launcher(parent_tk_window: tk.Widget, export_manager: ExportManager, host_app_ref: Any):
#     # This function would be defined in this module and called by launcher's menu
#     # It would instantiate a more complex export dialog Toplevel, passing export_manager and host_app_ref
#     # For now, ThemeExportMainUI has buttons that directly open simplified dialogs or logic.
#     pass


if __name__ == "__main__":
    # Standalone test for Theme System & Basic Export UI
    root = tk.Tk()
    root.title("Flow State - Theme & Export Test")
    root.geometry("800x600")

    # Mock HostAppInterface for testing
    class MockHostApp:
        def __init__(self, r):
            self.root = r
            self.theme_manager = None # Will be set by ThemeManager
            self.music_library_db_ref = None # Placeholder
            self.export_manager_ref = None
            self.loaded_modules = {'theme_export': sys.modules[__name__]} # Make this module available
            self.status_bar_var = tk.StringVar(value="Mock Status Ready.")
            # Add dummy methods HostAppInterface has
            def get_audio_properties(): return 44100, 2
            self.get_audio_properties = get_audio_properties
            def update_status_bar(msg): self.status_bar_var.set(msg)
            self.update_status_bar = update_status_bar
            def publish_event(name, **kwargs): print(f"Mock Event: {name}, {kwargs}")
            self.publish_event = publish_event
            def request_library_action(action, params=None, callback=None):
                print(f"Mock Lib Action: {action}, {params}")
                if callback: self.root.after(100, callback, [] if action=="get_all_tracks" else None) # Simulate async empty result
            self.request_library_action = request_library_action


    mock_host = MockHostApp(root)
    mock_host.theme_manager = ThemeManager(root) # Initialize ThemeManager

    # Create main menu (mimicking launcher)
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    create_theme_menu_items(menubar, mock_host) # Populate themes menu

    # Create the main UI tab for this module's features
    notebook_for_test = ttk.Notebook(root)
    notebook_for_test.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    main_ui_tab = create_theme_export_main_tab(notebook_for_test, mock_host)
    mock_host.export_manager_ref = main_ui_tab.export_manager # Store ref if needed

    # Mock status bar
    ttk.Label(root, textvariable=mock_host.status_bar_var).pack(side=tk.BOTTOM, fill=tk.X)

    root.mainloop()