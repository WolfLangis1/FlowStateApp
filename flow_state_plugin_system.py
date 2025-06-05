"""
Flow State: Plugin System Module
Extensible plugin architecture for audio effects, visualizers, and features
"""

import os
import sys
import json
import importlib.util
import inspect
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Type, Union # Added Union
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np # For AudioEffectPlugin and VisualizerPlugin data types
import concurrent.futures
import logging
from pathlib import Path # For plugin directory management

logger = logging.getLogger(__name__)

# Using a module-specific pool for plugin loading which can be I/O or CPU bound during init
PLUGIN_LOAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="PluginLoad")

class PluginType(Enum):
    AUDIO_EFFECT = "Audio Effect" # User-friendly names
    VISUALIZER = "Visualizer"
    ANALYZER = "Audio Analyzer"
    EXPORT = "Export Format"
    UI_EXTENSION = "UI Extension"
    # Add more types as needed (e.g., LYRICS_PROVIDER, METADATA_FETCHER)

@dataclass
class PluginInfo:
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType # Use the Enum
    # Default config can be specified by the plugin itself in its __init__
    # This config in PluginInfo could be for storing user-overrides or plugin manager specific settings.
    # For now, let's assume plugin's self.config is the source of truth for its operational parameters.
    enabled: bool = True # Whether the plugin is enabled by the user in the manager
    # path: Optional[str] = None # Path to the plugin file, useful for identification

    # To make it easier for UI display, allow direct access to plugin_type.value
    @property
    def type_str(self) -> str:
        return self.plugin_type.value


class PluginBase(ABC):
    def __init__(self):
        # Plugins *must* override this info in their __init__
        self.info = PluginInfo(
            name="Unnamed Base Plugin",
            version="0.0.0",
            author="N/A",
            description="This is a base plugin and should not be instantiated directly.",
            plugin_type=PluginType.AUDIO_EFFECT # Default, overridden by subclasses
        )
        self.enabled = True # Runtime enabled state, can be toggled by user
        self.config: Dict[str, Any] = {} # Plugin-specific configuration parameters
        self.host_app_ref: Optional[Any] = None

    def initialize(self, host_app_ref: Any):
        self.host_app = host_app_ref # Changed from self.host_app_ref to self.host_app
        # Generic initialization logic, plugins can override and call super().
        # Example: load config specific to this plugin instance
        # if self.host_app and self.host_app.plugin_manager_ref:
        #     loaded_conf = self.host_app.plugin_manager_ref.get_plugin_instance_config(self)
        #     if loaded_conf: self.load_config(loaded_conf)
        logger.info(f"Plugin '{self.info.name}' initialized.")

    @abstractmethod
    def process(self, data: Any) -> Any:
        if not self.enabled:
            return data
        return data

    def get_ui(self, parent_widget: tk.Widget) -> Optional[ttk.Frame]:
        """
        Return a Tkinter Frame (or None) to be embedded in the plugin's configuration dialog.
        The frame should contain controls to modify self.config or self.parameters.
        Changes made in this UI should ideally call self.set_parameter or modify self.config,
        and then the PluginManager will call save_plugin_config.
        """
        # Example basic UI:
        # frame = ttk.Frame(parent_widget)
        # ttk.Label(frame, text=f"No specific UI for {self.info.name}.").pack(padx=10, pady=10)
        # return frame
        return None # Default: no UI

    def cleanup(self):
        """Cleanup resources when plugin is unloaded or app closes."""
        logger.info(f"Plugin '{self.info.name}' cleaned up.")
        pass

    def save_config(self) -> Dict[str, Any]:
        """Return a dictionary of the plugin's current configuration to be saved."""
        # This should ideally reflect parameters managed by its get_ui controls.
        # For effects that use self.parameters:
        if hasattr(self, 'parameters') and isinstance(getattr(self, 'parameters'), dict):
            return getattr(self, 'parameters').copy()
        return self.config.copy() # Fallback to generic config

    def load_config(self, saved_config_dict: Dict[str, Any]):
        """Load configuration from a dictionary."""
        if isinstance(saved_config_dict, dict):
            # If effect uses self.parameters (like AudioEffect subclasses):
            if hasattr(self, 'parameters') and isinstance(getattr(self, 'parameters'), dict):
                for key, value in saved_config_dict.items():
                    if hasattr(self, 'set_parameter'): # If it has a set_parameter method
                        # Use set_parameter to ensure any internal updates happen (like filter redesign)
                        getattr(self, 'set_parameter')(key, value)
                    elif key in getattr(self, 'parameters'):
                        getattr(self, 'parameters')[key] = value
                # If no set_parameter, just update the dict.
                # getattr(self, 'parameters').update(saved_config_dict)
            else: # Fallback to generic self.config
                self.config.update(saved_config_dict)
            logger.info(f"Plugin '{self.info.name}' loaded configuration: {list(saved_config_dict.keys())}")
        else:
            logger.warning(f"Invalid config format for {self.info.name}: {type(saved_config_dict)}")


class AudioEffectPlugin(PluginBase): # As refined before for AudioEffects module
    # ... (AudioEffectPlugin structure with set_stream_properties, process_audio_block)
    # Its `process` method calls `process_audio_block`.
    # This is the base for plugins that go into the AudioEffectsChain.
    pass

class VisualizerPlugin(PluginBase): # As refined before
    # ... (VisualizerPlugin structure with set_render_properties, render_frame)
    # Its `process` method calls `render_frame`.
    pass

# Example Plugin: SimpleFilterPlugin (now based on PluginBase system)
# This would typically be in its own .py file in the plugins/ directory.
# For demonstration, it's here.
class SimpleFilterPluginFromSystem(AudioEffectPlugin): # Inherits from AudioEffectPlugin
    def __init__(self):
        super().__init__() # Calls AudioEffectPlugin's init
        self.info = PluginInfo( # Override default PluginInfo
            name="Simple Filter (Plugin)", version="1.0.0", author="PluginDev",
            description="A basic Lowpass/Highpass filter plugin.",
            plugin_type=PluginType.AUDIO_EFFECT
        )
        # Parameters are defined as attributes or in a self.parameters dict
        # Let's use self.config for parameters managed by get_ui/load_config/save_config
        self.config = {
            'filter_type': 'lowpass', 'cutoff_hz': 1000.0, 'order': 2
        }
        self.b_coeffs = np.array([1.0]); self.a_coeffs = np.array([1.0])
        self.filter_zi = np.array([])
        # `initialize` will be called by PluginManager, where sr/ch can be set.
        # `reset` (called by set_stream_properties) will design initial filter.

    def initialize(self, host_app_ref: Any): # Overrides PluginBase.initialize
        super().initialize(host_app_ref) # Call base initialize
        # Get initial stream properties if host_app provides them
        if self.host_app and hasattr(self.host_app, 'get_audio_properties'):
            sr, ch = self.host_app.get_audio_properties()
            self.set_stream_properties(sr, ch) # This will call reset -> _design_filter
        else: # Fallback if host_app doesn't provide immediately
            self.set_stream_properties(44100, 2) # Default, will be updated if host later calls it

    def _design_filter(self): # Same as SimpleFilterPlugin in audio_effects.py
        if self.sample_rate <= 0 or self.channels <= 0: # ... (passthrough logic) ...
            return
        filter_type = self.config.get('filter_type', 'lowpass')
        cutoff_hz = float(self.config.get('cutoff_hz', 1000.0))
        order = int(self.config.get('order', 2))
        # ... (signal.butter, zi initialization as in audio_effects.SimpleFilterPlugin) ...
        pass

    def reset(self): # Called by set_stream_properties
        super().reset() # Base reset might do logging
        self._design_filter()

    def process_audio_block(self, audio_block: np.ndarray) -> np.ndarray: # From AudioEffectPlugin
        if self.info.enabled is False or self.b_coeffs.size == 1 or self.filter_zi.size == 0: # Check self.info.enabled
            return audio_block
        # ... (lfilter logic per channel as in audio_effects.SimpleFilterPlugin) ...
        return audio_block # Placeholder for full lfilter logic

    def get_ui(self, parent_widget: tk.Widget) -> Optional[ttk.Frame]: # From PluginBase
        frame = ttk.Frame(parent_widget)
        ttk.Label(frame, text=f"{self.info.name} Controls", font=('Arial', 11, 'bold')).pack(pady=(5,10))

        # Filter Type
        type_var = tk.StringVar(value=self.config.get('filter_type', 'lowpass'))
        def _set_type(): self.config['filter_type'] = type_var.get(); self._design_filter()
        # ... (Radiobuttons for type_var, command=_set_type) ...

        # Cutoff
        cutoff_var = tk.DoubleVar(value=self.config.get('cutoff_hz', 1000.0))
        # ... (Scale and Label for cutoff_var, command updates self.config['cutoff_hz'] and calls _design_filter) ...
        
        # Order
        order_var = tk.IntVar(value=self.config.get('order', 2))
        # ... (Spinbox for order_var, command updates self.config['order'] and calls _design_filter) ...
        return frame


class PluginManager: # As refined before
    # ... (__init__(host_app_ref), _load_all_plugins_async, _load_plugin_from_file,
    #      register_plugin (sets stream/render props), _load_plugin_config, save_plugin_config,
    #      process_audio_chain, render_active_visualizers, get_plugin_list, enable_plugin, unregister_plugin) ...
    # Ensure enable_plugin updates plugin.info.enabled AND plugin.enabled, then calls save_plugin_config.
    pass

class PluginManagerUI(ttk.Frame): # As refined before
    # ... (Full implementation including __init__(parent, plugin_manager, host_app_ref),
    #      on_plugin_list_updated_event, create_ui, refresh_list, on_select,
    #      load_plugin_external, toggle_plugin, configure_plugin (parents to host_app.root), cleanup_ui) ...
    pass

class PluginCreator(tk.Toplevel): # As refined before
    # ... (Full implementation including __init__(parent_tk_root, host_app_ref), create_ui, generate_plugin)
    # generate_plugin uses default_plugin_dir from host_app.plugin_manager_ref.plugin_dir.
    pass

# Integration function
def create_plugin_tab(notebook: ttk.Notebook, host_app_ref: Any) -> PluginManager: # Returns manager instance
    # ... (as refined before, PluginManager and PluginManagerUI get host_app_ref.
    #      PluginCreator button uses host_app_ref.root for parent and host_app_ref for context) ...
    # Ensure host_app_ref.plugin_manager_ref is set to the created instance.
    plugin_frame = ttk.Frame(notebook)
    notebook.add(plugin_frame, text="Plugins")
    
    plugin_manager_instance = PluginManager(host_app_ref=host_app_ref)
    plugin_ui = PluginManagerUI(plugin_frame, plugin_manager_instance, host_app_ref=host_app_ref)
    plugin_ui.pack(fill=tk.BOTH, expand=True)
    
    create_plugin_button = ttk.Button(plugin_frame, text="Create New Plugin",
                                     command=lambda: PluginCreator(host_app_ref.root, host_app_ref))
    create_plugin_button.pack(pady=5, side=tk.BOTTOM)
    
    host_app_ref.plugin_manager_ref = plugin_manager_instance
    return plugin_manager_instance