#!/usr/bin/env python3
"""
Flow State Music Player - Application Launcher
Main entry point that integrates all modules
"""

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import importlib
import subprocess # For dev mode module running
import json # For potential future config loading here
from pathlib import Path # Using pathlib
import concurrent.futures
from typing import Dict, Any, Optional, Tuple, List, Callable

# --- Constants ---
DEFAULT_WINDOW_WIDTH = 1600
DEFAULT_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 1200
MIN_WINDOW_HEIGHT = 750
APP_DATA_BASE_DIR_NAME = ".flowstate" # Folder name in user's home

# --- Logging Configuration ---
APP_DATA_BASE_PATH = Path.home() / APP_DATA_BASE_DIR_NAME
LOG_DIR = APP_DATA_BASE_PATH / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True) # Create log dir

logging.basicConfig(
    level=logging.INFO, # Change to DEBUG for more verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "flow_state_launcher.log", mode='a') # Append mode
    ]
)
logger = logging.getLogger("FlowStateLauncher")

# --- Global Thread Pools ---
APP_STARTUP_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="AppStartup")


class HostAppInterface:
    """
    Provides a structured way for modules (tabs, services) to interact with the main application
    and other core components without direct circular dependencies.
    """
    def __init__(self, tk_root: tk.Tk, main_notebook_widget: ttk.Notebook):
        self.root: tk.Tk = tk_root
        self.notebook: ttk.Notebook = main_notebook_widget # Main tab container
        self.status_bar_var: Optional[tk.StringVar] = None # For updating status bar text

        # --- Core Service References (to be populated during initialization) ---
        self.theme_manager: Optional[Any] = None
        self.audio_engine_ref: Optional[Any] = None
        self.music_library_db_ref: Optional[Any] = None
        self.effects_chain_ref: Optional[Any] = None
        self.plugin_manager_ref: Optional[Any] = None
        self.recommendation_engine_ref: Optional[Any] = None
        self.collab_client_ui_ref: Optional[Any] = None
        self.mobile_sync_server_ui_ref: Optional[Any] = None
        self.voice_control_ui_ref: Optional[Any] = None

        # --- UI Component References ---
        self.main_player_ui_ref: Optional[Any] = None
        self.visualization_ui_ref: Optional[Any] = None
        self.lyrics_display_ref: Optional[Any] = None
        self.storyboard_generator_ui_ref: Optional[Any] = None
        self.library_ui_ref: Optional[Any] = None # Reference to LibraryManagerUI

        self.loaded_modules: Dict[str, Any] = {}
        self._event_callbacks: Dict[str, List[Callable]] = {}
        self.root_tk_after_id_map: Dict[str, str] = {}

    def get_audio_properties(self) -> Tuple[int, int]:
        if self.audio_engine_ref and hasattr(self.audio_engine_ref, 'sample_rate') and hasattr(self.audio_engine_ref, 'channels'):
            return int(self.audio_engine_ref.sample_rate), int(self.audio_engine_ref.channels)
        logger.warning("HostApp: Audio properties requested but audio engine not ready.")
        return 44100, 2

    def get_render_properties(self) -> Tuple[int, int, int]:
        if self.visualization_ui_ref and hasattr(self.visualization_ui_ref, 'engine_instance') and self.visualization_ui_ref.engine_instance:
            cfg = self.visualization_ui_ref.engine_instance.config
            return cfg.width, cfg.height, cfg.fps
        return 1280, 720, 30

    def get_current_track_metadata(self) -> Optional[Any]:
        if self.audio_engine_ref and hasattr(self.audio_engine_ref, 'current_metadata_obj'):
            return self.audio_engine_ref.current_metadata_obj
        return None

    def get_current_lyrics_data(self) -> Optional[List[Tuple[float, str]]]:
        if self.lyrics_display_ref and hasattr(self.lyrics_display_ref, 'lyrics'):
            lyrics_full = self.lyrics_display_ref.lyrics
            if lyrics_full and isinstance(lyrics_full[0], tuple) and len(lyrics_full[0]) >= 2:
                return [(ts, line_text) for ts, line_text, *_ in lyrics_full]
        return None
    
    def get_current_playback_position(self) -> float:
        return self.audio_engine_ref.get_position() if self.audio_engine_ref else 0.0

    def request_playback_action(self, action: str, params: Optional[Dict] = None, 
                                callback: Optional[Callable[[bool, Optional[str]], None]] = None):
        if not self.audio_engine_ref:
            msg = "Playback action requested, but audio engine not available."
            logger.warning(msg)
            if self.status_bar_var: self.status_bar_var.set("Error: Audio engine not ready.")
            if callback: self.root.after(0, callback, False, msg)
            return

        params = params or {}
        logger.info(f"Host: Playback action '{action}' with params {params}")
        success = False
        err_msg = None

        try:
            if action == "load_track_from_path":
                if self.main_player_ui_ref and hasattr(self.main_player_ui_ref, 'load_track'):
                    self.main_player_ui_ref.load_track(params['filepath'])
                    success = True
            elif action == "load_and_play_path":
                if self.main_player_ui_ref and hasattr(self.main_player_ui_ref, 'load_track_and_play'):
                    self.main_player_ui_ref.load_track_and_play(params['filepath'])
                    success = True
            elif action == "play_track_by_id":
                 if self.main_player_ui_ref and hasattr(self.main_player_ui_ref, 'play_track_by_id_from_library'):
                     self.main_player_ui_ref.play_track_by_id_from_library(params['track_id'])
                     success = True
            elif action == "play_track_at_playlist_index": # New action for queue interaction
                if hasattr(self.audio_engine_ref, 'play_track_at_playlist_index'):
                    self.audio_engine_ref.play_track_at_playlist_index(params['index'])
                    success = True
            elif action == "play": self.audio_engine_ref.play(**params.get('play_args', {})); success = True
            elif action == "pause": self.audio_engine_ref.pause(); success = True
            elif action == "resume":
                if hasattr(self.audio_engine_ref, 'resume'): self.audio_engine_ref.resume(); success = True
                else: self.audio_engine_ref.play(); success=True
            elif action == "stop": self.audio_engine_ref.stop(); success = True
            elif action == "next": self.audio_engine_ref.next_track(); success = True
            elif action == "previous": self.audio_engine_ref.previous_track(); success = True
            elif action == "set_volume":
                self.audio_engine_ref.set_volume(params.get('level', 0.7))
                success = True
            elif action == "seek":
                self.audio_engine_ref.set_position(params.get('position_seconds', 0.0))
                success = True
            elif action == "toggle_mute":
                if hasattr(self.audio_engine_ref, 'toggle_mute'): self.audio_engine_ref.toggle_mute(); success = True
            elif action == "add_to_queue_path":
                if self.main_player_ui_ref and hasattr(self.main_player_ui_ref, 'add_to_playback_queue'):
                    self.main_player_ui_ref.add_to_playback_queue(params['filepath'])
                    success = True
            elif action == "load_playlist_paths": # New action for LibraryUI to load a playlist
                if hasattr(self.audio_engine_ref, 'load_playlist'):
                    self.audio_engine_ref.load_playlist(
                        params.get('paths', []),
                        play_first=params.get('play_first', True),
                        replace_queue=params.get('replace_queue', True)
                    )
                    success = True
            elif action == "set_shuffle_mode":
                if hasattr(self.audio_engine_ref, 'set_shuffle_mode'):
                    self.audio_engine_ref.set_shuffle_mode(params.get('state', False))
                    success = True
            elif action == "set_repeat_mode":
                 if hasattr(self.audio_engine_ref, 'set_repeat_mode'):
                    self.audio_engine_ref.set_repeat_mode(params.get('mode', 'off'))
                    success = True
            elif action == "force_sync_playback": # For collaboration client sync
                if self.main_player_ui_ref and hasattr(self.main_player_ui_ref, 'force_sync_local_player_to_state'):
                    self.main_player_ui_ref.force_sync_local_player_to_state(
                        params['library_track_id'], params['position_seconds'], params['is_playing_target']
                    )
                    success = True
            else:
                err_msg = f"Unknown playback action: {action}"
                logger.warning(err_msg)

            if success and self.status_bar_var:
                 self.status_bar_var.set(f"Playback: {action} processed.")
            elif err_msg and self.status_bar_var:
                self.status_bar_var.set(f"Error: {err_msg}")

        except AttributeError as ae: # ... (error handling) ...
            err_msg = f"Component missing method for action '{action}': {ae}"
        except Exception as e: # ... (error handling) ...
            err_msg = f"Error executing playback action '{action}': {e}"
        
        if callback:
            self.root.after(0, callback, success, err_msg)

    def request_library_action(self, action: str, params: Optional[Dict] = None, 
                               callback: Optional[Callable[[Optional[Any]], None]] = None):
        if not self.music_library_db_ref:
            logger.warning("Library action requested, but DB not available.")
            if callback: self.root.after(0, callback, None)
            return None
        
        params = params or {}
        logger.info(f"Host: Library action '{action}' with params {params}")

        def _worker():
            result = None
            try:
                if action == "search_tracks": result = self.music_library_db_ref.search_tracks(params.get('query', ''), limit=params.get('limit',100))
                elif action == "get_track_by_id": result = self.music_library_db_ref.get_track(params.get('track_id'))
                elif action == "get_all_playlists": result = self.music_library_db_ref.get_all_playlists()
                elif action == "get_playlist_by_id": result = self.music_library_db_ref.get_playlist_by_id(params.get('playlist_id'))
                elif action == "get_playlist_tracks": result = self.music_library_db_ref.get_playlist_tracks(params.get('playlist_id'))
                elif action == "get_smart_playlist_tracks": result = self.music_library_db_ref.get_smart_playlist_tracks(params.get('rules_json')) # Pass rules_json
                elif action == "create_playlist": result = self.music_library_db_ref.create_playlist(params['name'], params.get('description',''), params.get('is_smart',False), params.get('rules_json'))
                elif action == "update_playlist": result = self.music_library_db_ref.update_playlist(params['playlist_id'], params['name'], params.get('description',''), params['is_smart'], params.get('rules_json'))
                elif action == "add_tracks_to_playlist": self.music_library_db_ref.add_tracks_to_playlist(params['playlist_id'], params['track_ids']); result = True # Assuming void or returns success
                elif action == "rename_playlist": result = self.music_library_db_ref.rename_playlist(params['playlist_id'], params['new_name'])
                elif action == "delete_playlist": result = self.music_library_db_ref.delete_playlist(params['playlist_id'])
                elif action == "get_all_distinct_values_for_field": result = self.music_library_db_ref.get_all_distinct_values_for_field(params.get('field_name'))
                else: logger.warning(f"Unknown library action: {action}")
            except Exception as e: logger.error(f"Error executing library action '{action}': {e}", exc_info=True)
            if callback: self.root.after(0, callback, result)
            return result

        if callback: APP_STARTUP_THREAD_POOL.submit(_worker); return None 
        else: return _worker()

    def request_ui_focus_tab(self, tab_text_name: str): # As before
        pass
    def update_status_bar(self, message: str): # As before
        pass
    def subscribe_to_event(self, event_name: str, callback: Callable): # As before
        pass
    def publish_event(self, event_name: str, *args, **kwargs): # As before
        pass

class FlowStateLauncher:
    def __init__(self):
        self.root_dir = Path(__file__).parent.resolve()
        logger.info(f"Application Root Directory: {self.root_dir}")
        self.app_name = "Flow State"

        self.modules_spec = {
            'flow_state_main': ('flow_state_main', "Flow State Core", None, 0),
            'theme_export': ('flow_state_theme_export', "Themes & Management", 'create_theme_export_main_tab', 1),
            'music_library': ('flow_state_music_library', "Music Library", 'create_library_tab', 2),
            'audio_effects': ('flow_state_audio_effects', "Audio Effects", 'create_effects_tab', 3),
            'advanced_viz': ('flow_state_advanced_viz', "Visualizations", 'create_visualization_tab', 4),
            'plugin_system': ('flow_state_plugin_system', "Plugins", 'create_plugin_tab', 5),
            'ai_recommendations': ('flow_state_ai_recommendations', "Discover", 'create_recommendation_tab', 6),
            'storyboard_generator': ('flow_state_storyboard', "Storyboard", 'create_storyboard_tab', 7),
            'collaboration': ('flow_state_collaboration', "Collaborate", 'create_collaboration_tab', 8),
            'mobile_sync': ('flow_state_mobile_sync', "Remote", 'create_remote_control_tab', 9),
            'voice_control': ('flow_state_voice_control', "Voice", 'create_voice_control_tab', 10),
        }
        self.loaded_modules: Dict[str, Any] = {}
        self.check_python_environment()
        self.create_app_directories()

    def check_python_environment(self): # As before
        pass
    def create_app_directories(self): # As before
        pass
    def _import_module(self, module_key: str, import_name: str, friendly_name: str) -> Optional[Any]: # As before
        pass

    def _initialize_core_services(self, host_app: HostAppInterface): # As before
        pass
    def _create_and_integrate_module_tabs(self, host_app: HostAppInterface): # As before
        pass
    def _setup_main_window_ui(self, root: tk.Tk, host_app: HostAppInterface): # As before
        pass

    def run_integrated_application(self): # As before
        logger.info(f"Starting {self.app_name}...")
        sorted_module_keys_for_import = sorted(self.modules_spec.keys(), key=lambda k: self.modules_spec[k][3])
        for key in sorted_module_keys_for_import:
            import_name, friendly_name, _, _ = self.modules_spec[key]
            self._import_module(key, import_name, friendly_name)

        root = tk.Tk()
        root.title(f"{self.app_name} - Next Generation Music Player")
        root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        # ... (icon setting) ...

        host_app = HostAppInterface(root, ttk.Notebook(root))
        host_app.loaded_modules = self.loaded_modules

        self._initialize_core_services(host_app)
        self._setup_main_window_ui(root, host_app) # This now packs host_app.notebook
        self._create_and_integrate_module_tabs(host_app)
        
        # Load session after all UI is ready and services are potentially initialized
        if host_app.main_player_ui_ref and hasattr(host_app, 'request_load_session_state'):
            # Delay slightly to ensure UI is fully drawn and ready
            root.after(200, host_app.request_load_session_state)
        
        host_app.publish_event("app_initialized_and_ready")
        # ... (on_app_close_launcher, root.protocol, root.mainloop as before) ...
        pass

    def _create_main_menu(self, root_tk: tk.Tk, host_app: HostAppInterface):
        menubar = tk.Menu(root_tk)
        root_tk.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        if host_app.main_player_ui_ref:
            file_menu.add_command(label="Open File...", command=host_app.main_player_ui_ref.open_file)
            file_menu.add_command(label="Open Folder...", command=host_app.main_player_ui_ref.open_folder_threaded)
        else:
            file_menu.add_command(label="Open File...", state=tk.DISABLED)
            file_menu.add_command(label="Open Folder...", state=tk.DISABLED)
        file_menu.add_separator()
        # Add Preferences to File menu
        file_menu.add_command(label="Preferences...", command=lambda: PreferencesDialog(host_app.root, host_app) if PreferencesDialog else None)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root_tk.quit)


        # Themes Menu
        if host_app.theme_manager:
            theme_export_module = host_app.loaded_modules.get('theme_export')
            if theme_export_module and hasattr(theme_export_module, 'create_theme_menu_items'):
                 theme_export_module.create_theme_menu_items(menubar, host_app)

        # Tools Menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        if host_app.plugin_manager_ref:
            tools_menu.add_command(label="Plugin Manager...", command=lambda: host_app.request_ui_focus_tab("Plugins"))
        else:
            tools_menu.add_command(label="Plugin Manager...", state=tk.DISABLED)
        
        theme_export_ui_ref = getattr(host_app, 'theme_export_main_ui_ref', None) # If launcher stored it
        if theme_export_ui_ref and hasattr(theme_export_ui_ref, 'open_detailed_batch_audio_export_dialog'):
             tools_menu.add_command(label="Batch Export Audio...", command=theme_export_ui_ref.open_detailed_batch_audio_export_dialog)
        # ... (Add other tools) ...

    def run_development_mode(self): # As before
        pass
    def run_module(self, module_py_filename: str): # As before
        pass

# ... (main function as before) ...