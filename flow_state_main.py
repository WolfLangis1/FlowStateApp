#!/usr/bin/env python3
"""
Flow State: Next-Generation Music Player - Core UI and Engine
AudioEngine now uses sounddevice for playback and streaming decode.
"""

import os
import sys
import json # For session state, not directly used by AudioEngine/FlowStateApp UI logic itself
import time
import queue
import threading
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Any, Callable
import logging
from pathlib import Path # For LRC file path handling

# Audio and Analysis
import librosa # Still used by AudioAnalyzer
import sounddevice as sd # For playback
import soundfile as sf # For reading audio files block by block
import mutagen # For metadata (mutagen.File is generic)
# from mutagen.mp3 import MP3 # Specific, but mutagen.File is often enough
# from mutagen.id3 import ID3

# Visualization (Matplotlib-based basic visualizer)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation
from scipy.signal import find_peaks
from scipy.fft import rfft, rfftfreq

logger = logging.getLogger("FlowStateMainApp")

@dataclass
class AudioMetadata: # This should ideally be in a shared types.py
    title: str = "Unknown"
    artist: str = "Unknown"
    album: str = "Unknown"
    duration: float = 0.0
    sample_rate: int = 44100
    channels: int = 2
    file_path: Optional[str] = None # Added to store the path this metadata refers to
    id: Optional[int] = None # If it corresponds to a library ID

    # AI-populated fields (optional)
    key: Optional[str] = None
    bpm: Optional[float] = None
    energy: Optional[float] = None
    mood: Optional[str] = None # Or List[str] for mood_tags


class AudioEngine:
    def __init__(self, host_app_ref: Optional[Any] = None):
        self.host_app_ref = host_app_ref
        logger.info("Initializing AudioEngine with sounddevice.")

        self.current_file: Optional[str] = None
        self.is_playing = False
        self.is_paused = False
        self.playback_position_sec = 0.0
        self.duration_sec = 0.0
        self.volume = 0.7
        self.is_muted = False
        self.previous_volume_before_mute = self.volume

        self.playlist: List[str] = [] # List of file paths
        self.original_playlist_order: List[str] = []
        self.shuffled_indices: List[int] = [] # Stores original indices in shuffled order
        self.current_index = -1 # Index in self.playlist (which may be shuffled)
        self.current_shuffled_play_order_idx = -1 # Index into self.shuffled_indices array

        self.current_metadata_obj: Optional[AudioMetadata] = None

        self.sample_rate = 44100
        self.channels = 2
        self.block_size = 1024 # Samples per processing block
        self.dtype_playback = 'float32'

        self.stream: Optional[sd.OutputStream] = None
        self.stream_output_queue = queue.Queue(maxsize=15) # Buffer for sounddevice callback

        self._playback_thread: Optional[threading.Thread] = None
        self._stop_playback_event = threading.Event()
        self._seek_request_sec: Optional[float] = None
        self._pause_event = threading.Event()
        self._pause_event.set() # True = can run

        self.effects_output_buffer_for_viz = np.zeros(2048, dtype=np.float32) # Mono, post-fx
        logger.info("AudioEngine initialized (sounddevice based).")

    def _sounddevice_callback(self, outdata: np.ndarray, frames: int, time_info, status: sd.CallbackFlags):
        # ... (as in previous version, applies volume/mute) ...
        if status.output_underflow: logger.warning(f"Sounddevice output underflow! {status}")
        elif status: logger.debug(f"Sounddevice callback status: {status}")
        try:
            block = self.stream_output_queue.get(timeout=max(0.001, self.block_size / self.sample_rate * 0.5)) # Shorter timeout
            if block.shape[0] == frames and block.shape[1] == outdata.shape[1]:
                effective_volume = self.volume if not self.is_muted else 0.0
                outdata[:] = block * effective_volume
            else: outdata.fill(0); logger.warning(f"SD CB: Block/frame mismatch. Blk: {block.shape if block is not None else 'None'}, Frames: {frames}, OutCh: {outdata.shape[1]}")
        except queue.Empty: outdata.fill(0); logger.debug("SD CB: Queue empty (underrun).")
        except Exception as e: outdata.fill(0); logger.error(f"Error in SD CB: {e}", exc_info=True)


    def _start_sound_stream(self):
        if self.stream and self.stream.active: return True
        if self.sample_rate <= 0 or self.channels <= 0: # ... (error logging) ...
            return False
        try:
            if self.stream: self._stop_sound_stream(close_existing=True) # Ensure old one is gone
            logger.info(f"Starting sounddevice stream: SR={self.sample_rate}, Ch={self.channels}, Block={self.block_size}")
            self.stream = sd.OutputStream(samplerate=self.sample_rate, channels=self.channels,
                                          blocksize=self.block_size, callback=self._sounddevice_callback,
                                          dtype=self.dtype_playback)
            self.stream.start()
            return True
        except Exception as e: # ... (error logging, messagebox) ...
            return False

    def _stop_sound_stream(self, close_existing: bool = True): # As before
        pass # Assume previous robust implementation

    def _playback_thread_func(self):
        # ... (as in previous version: setup, sf.SoundFile context, main while loop) ...
        # Key parts within the loop:
        #   - self._pause_event.wait()
        #   - Handle self._seek_request_sec: audio_file_sf.seek(...), clear queue
        #   - raw_audio_block = audio_file_sf.read(...)
        #   - EOF check -> break / publish "playback_track_transition_request"
        #   - Update self.playback_position_sec
        #   - Pad block if needed
        #   - Apply effects chain: processed_audio_block = host_app.effects_chain_ref.process_block(...)
        #   - Put processed_audio_block into self.stream_output_queue
        #   - Prepare/update self.effects_output_buffer_for_viz (mono)
        #   - Send processed_audio_block (stereo) to host_app.visualization_ui_ref.update_audio_for_viz(...)
        pass # Assume previous robust implementation

    def load_track(self, filepath: str, playlist_context: Optional[List[str]] = None, playlist_index: Optional[int] = None) -> bool:
        # ... (as in previous version: stop current, sf.info, update SR/CH/duration,
        #      mutagen for metadata, update self.current_metadata_obj,
        #      handle playlist_context for self.playlist/self.current_index,
        #      inform effects_chain of SR/CH change, publish "audio_track_loaded_basic") ...
        # CRITICAL: If stream properties (SR, CH) change, the _sounddevice_callback and _playback_thread_func
        # are now correctly using self.sample_rate and self.channels.
        # The _start_sound_stream() which is called by play() will use these new values.
        # The old stream is stopped by self.stop() which is called at the beginning of load_track.
        pass # Assume previous robust implementation

    def play(self, start_offset_sec: Optional[float] = None, track_path_to_load: Optional[str] = None):
        # ... (as in previous version: handle track_path_to_load by calling self.load_track,
        #      check if already playing, stop old thread/stream, clear events, set seek,
        #      _start_sound_stream, start _playback_thread, update states, publish event) ...
        pass # Assume previous robust implementation

    def pause(self): # As before
        pass
    def resume(self): # As before
        pass
    def stop(self): # As before
        pass
    def set_position(self, position_seconds: float): # As before
        pass
    def get_position(self) -> float: # As before
        return self.playback_position_sec

    def set_volume(self, volume_float: float): # As before
        pass
    def toggle_mute(self): # As before
        pass
    def cleanup(self): # As before
        pass

    def set_shuffle_mode(self, enable: bool): # As before
        pass
    def _apply_shuffle(self): # As before
        pass
    def set_repeat_mode(self, mode: str): # As before
        pass
    def get_next_track_info(self) -> Tuple[Optional[str], Optional[int]]: # As before
        pass
    def next_track(self): # As before
        pass
    def previous_track(self): # As before
        pass
    def remove_track_from_playlist_at_index(self, index_in_current_playlist: int) -> bool: # As before
        pass
    def play_track_at_playlist_index(self, index_in_current_playlist: int): # As before
        pass
    def force_sync_playback_to_state(self, library_track_id_to_play: int, target_position_seconds: float, target_is_playing: bool): # As before
        pass


class FlowStateApp(ttk.Frame):
    # ... (__init__, create_ui_widgets, _setup_playback_control_buttons,
    #      _subscribe_to_host_events, load_track, load_track_and_play,
    #      _update_ui_for_new_track, _analyze_track_and_update_ui_full,
    #      _update_ui_with_detailed_metadata, _parse_lrc_file,
    #      play_pause, stop, toggle_shuffle_mode, cycle_repeat_mode, update_repeat_button_text,
    #      play_track_by_id_from_library, export_current_track_snippet, on_app_exit,
    #      on_playback_track_ended, on_playback_error, on_engine_playback_playlist_changed_event,
    #      on_playback_state_changed_event, _update_queue_highlight, on_queue_double_click,
    #      _create_queue_context_menu, show_queue_context_menu, play_selected_from_queue,
    #      remove_selected_from_queue, add_selected_queue_tracks_to_playlist_dialog,
    #      show_track_info_for_queue_item, gather_session_state, restore_session_state,
    #      on_track_fully_loaded_details_event as implemented/refined previously) ...

    # Ensure all UI actions call self.host_app.request_playback_action(...)
    # or self.host_app.audio_engine_ref methods directly if appropriate and safe.
    # Example: In volume slider command:
    # def update_volume(self, value_str):
    #     volume_percent = float(value_str)
    #     self.host_app.request_playback_action("set_volume", {'level': volume_percent / 100.0})
    #     # self.volume_label.config(text=f"{int(volume_percent)}%") # UI update via event "volume_changed"
    # It's better if UI elements subscribe to events from HostApp/AudioEngine to update themselves,
    # rather than directly configuring after an action. This keeps UI reactive to any state change source.
    pass


class AudioAnalyzer: # As before
    pass
class Visualizer: # Matplotlib based, as before
    pass
class EqualizerFrame: # As before
    pass
class LyricsDisplay: # As before
    pass

def main_standalone_test(): # As before
    pass

if __name__ == '__main__': # As before
    pass