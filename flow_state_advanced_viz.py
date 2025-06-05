"""
Flow State: Advanced Visualization Engine
GPU-accelerated audio visualizations with custom shaders
"""

import numpy as np
import moderngl
import pygame # Pygame is used for windowing and event handling here
from pygame.locals import *
import glm # PyGLM
import time
import math
from typing import List, Dict, Tuple, Optional, Any 
from dataclasses import dataclass
import struct # Not directly used in latest versions, but often for buffer packing
from abc import ABC, abstractmethod
import colorsys
import random
import tkinter as tk
from tkinter import ttk, messagebox # Added messagebox
import threading
import queue
from PIL import Image, ImageTk # Added ImageTk for UI
import io
from pathlib import Path # For potential asset loading

logger = logging.getLogger(__name__)


@dataclass
class VisualizationConfig:
    """Configuration for visualizations"""
    width: int = 1280 # Default to a more common window size for testing
    height: int = 720
    fps: int = 60
    fft_size: int = 2048
    smoothing: float = 0.75 # Adjusted default
    sensitivity: float = 1.5 # Adjusted default
    color_scheme: str = "flow_spectrum" # Custom default
    particle_count: int = 15000 # Adjusted default
    bloom_enabled: bool = True
    motion_blur: bool = False # Default to off, can be intensive
    post_processing: bool = True


class ShaderProgram:
    """Wrapper for OpenGL shader programs"""
    def __init__(self, ctx: moderngl.Context, vertex_shader: str, fragment_shader: str, geometry_shader: Optional[str] = None):
        self.ctx = ctx
        self.program: Optional[moderngl.Program] = None
        vs_str = vertex_shader
        fs_str = fragment_shader
        gs_str = geometry_shader

        try:
            self.program = ctx.program(
                vertex_shader=vs_str,
                fragment_shader=fs_str,
                geometry_shader=gs_str
            )
        except Exception as e:
            logger.error("Shader Compilation Error:")
            # Try to get GLSL error details if possible (moderngl specific error might have it)
            glsl_error_log = getattr(e, 'pgraph', None) # pgraph often contains error details
            if not glsl_error_log and hasattr(e, 'args') and e.args: glsl_error_log = e.args[0]
            logger.error(f"Details: {glsl_error_log or str(e)}")
            
            # Log the shader source for easier debugging
            logger.error("--- Vertex Shader ---")
            for i, line in enumerate(vs_str.splitlines()): logger.error(f"{i+1:03d}: {line}")
            if gs_str:
                logger.error("--- Geometry Shader ---")
                for i, line in enumerate(gs_str.splitlines()): logger.error(f"{i+1:03d}: {line}")
            logger.error("--- Fragment Shader ---")
            for i, line in enumerate(fs_str.splitlines()): logger.error(f"{i+1:03d}: {line}")
            raise # Re-raise the exception
        
        self.uniforms: Dict[str, moderngl.Uniform] = {}
        if self.program: # Ensure program was created
            for i in range(self.program.num_uniforms): # Use num_uniforms attribute
                try: # Uniforms might not be active if not used
                    uniform = self.program.get_uniform_by_index(i) # Use get_uniform_by_index
                    self.uniforms[uniform.name] = uniform
                except KeyError: # moderngl < 5.7 might raise KeyError for inactive uniforms
                    pass 
                except Exception as e_uni: # Catch other potential errors getting uniform info
                    logger.warning(f"Could not retrieve uniform at index {i}: {e_uni}")


    def set_uniform(self, name: str, value: Any):
        if name in self.uniforms:
            try:
                self.uniforms[name].value = value
            except struct.error as se: # Often due to wrong data type/size for uniform block
                logger.error(f"Struct Error setting uniform '{name}' (expected {self.uniforms[name].shape}, {self.uniforms[name].dimension}): {se}. Value type: {type(value)}")
            except Exception as e: 
                logger.error(f"Error setting uniform '{name}' with value '{value}' (type {type(value)}): {e}")
                # logger.debug(f"Uniform '{name}' details: Shape={self.uniforms[name].shape}, Dim={self.uniforms[name].dimension}, ArrayLen={self.uniforms[name].array_length}")
        # else:
            # logger.debug(f"Uniform '{name}' not found or not active in shader program.")

    def set_uniforms(self, uniforms_dict: Dict[str, Any]):
        for name, value in uniforms_dict.items():
            self.set_uniform(name, value)

    def release(self):
        if self.program:
            self.program.release()
            self.program = None


class Visualization(ABC): # As defined in previous "Advanced Viz" refinement
    def __init__(self, ctx: moderngl.Context, config: VisualizationConfig):
        self.ctx = ctx
        self.config = config
        self.time = 0.0
        self.beat_intensity = 0.0
        self.smoothed_frequency_data = np.zeros(config.fft_size // 2, dtype=np.float32)
        self.waveform_data = np.zeros(config.fft_size, dtype=np.float32)
        self._prev_freq_data_for_smoothing = np.zeros(config.fft_size // 2, dtype=np.float32)

    @abstractmethod
    def initialize(self): pass
    @abstractmethod
    def update(self, audio_data_mono: np.ndarray, dt: float):
        self.time += dt
        self.process_audio(audio_data_mono)
    @abstractmethod
    def render(self): pass
    def cleanup(self): pass

    def process_audio(self, audio_data_mono: np.ndarray):
        # ... (Full robust implementation from "Advanced Viz" refinement, including
        #      padding, windowing, FFT, normalization, smoothing, waveform, beat detection) ...
        # This was detailed in the pass focusing on flow-state-advanced-viz.py
        pass # Assume full implementation is here


class SpectrumBarsVisualization(Visualization): # As refined previously
    # ... (Full implementation from "Advanced Viz" refinement, including initialize, update, render, cleanup) ...
    pass

class ParticleFlowVisualization(Visualization): # As refined previously
    # ... (Full implementation from "Advanced Viz" refinement, with vectorized updates) ...
    pass

class WaveformTunnelVisualization(Visualization): # As refined previously
    # ... (Full implementation from "Advanced Viz" refinement) ...
    pass

class PostProcessing: # As refined previously
    # ... (Full implementation from "Advanced Viz" refinement, including bloom pipeline structure,
    #      _create_composite_shader, _create_bright_pass_shader, _create_gaussian_blur_shader,
    #      _create_additive_blend_shader, begin_render_to_scene_fbo, apply_post_processing, cleanup) ...
    # Ensure shader uniform names are consistent (e.g. u_ prefixes)
    pass


class VisualizationEngine:
    # ... (Full implementation from "Advanced Viz" refinement, including __init__, set_visualization,
    #      update_audio (converts to mono), run loop, cleanup, capture_frame) ...
    # Ensure it correctly uses Pygame for windowing and event loop.
    # The run loop should handle Pygame events for window closing and key presses.
    pass


class VisualizationUI(ttk.Frame):
    # ... (Full implementation from "Advanced Viz" refinement, including __init__, create_ui,
    #      _on_setting_change, apply_settings_to_engine, start_visualization_engine,
    #      stop_visualization_engine, change_visualization_type, capture_current_frame,
    #      update_audio_for_viz (which calls engine's update_audio)) ...
    # Ensure it takes host_app_ref if it needs to interact with other parts of the app
    # (e.g., getting default paths for saving frames, theming).
    # For now, assume it's largely self-contained for controlling its VisualizationEngine.
    def __init__(self, parent: ttk.Widget, host_app_ref: Optional[Any] = None): # Added host_app_ref
        super().__init__(parent)
        self.host_app = host_app_ref # Store if needed
        self.engine_instance: Optional[VisualizationEngine] = None
        self.engine_thread: Optional[threading.Thread] = None
        self.is_engine_running = False
        self.create_ui()

    # ... (rest of VisualizationUI)

# Integration function
def create_visualization_tab(notebook: ttk.Notebook, host_app_ref: Any) -> VisualizationUI: # Added host_app_ref
    viz_control_frame = ttk.Frame(notebook)
    notebook.add(viz_control_frame, text="Visualizations") # Tab name for advanced viz
    
    # Pass host_app_ref to VisualizationUI if it uses it
    viz_ui = VisualizationUI(viz_control_frame, host_app_ref=host_app_ref)
    viz_ui.pack(fill=tk.BOTH, expand=True)
    
    # The main application (via host_app_ref) will call viz_ui.update_audio_for_viz(...)
    # host_app_ref.visualization_ui_ref = viz_ui # Launcher already does this
    return viz_ui


if __name__ == "__main__":
    # ... (Standalone test code as in "Advanced Viz" refinement,
    #      ensure root.protocol("WM_DELETE_WINDOW", on_closing) correctly stops engine if running) ...
    # root = tk.Tk()
    # # class DummyHostApp: ... (if UI needs a host_app_ref for testing)
    # # dummy_host = DummyHostApp(root)
    # # ui = VisualizationUI(root, host_app_ref=dummy_host)
    # ui = VisualizationUI(root) # Assuming standalone test doesn't need full host_app
    # ...
    pass