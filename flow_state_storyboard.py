"""
Flow State: Storyboard Generator Module
AI-powered visual storyboard generation from music and lyrics
"""

import tkinter as tk
from tkinter import ttk, Canvas, messagebox
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageColor # Added ImageColor
import threading
import queue 
import json
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import colorsys
import random
import concurrent.futures

# For NLP analysis
import nltk
try:
    nltk.data.find('tokenizers/punkt', quiet=True)
except LookupError: nltk.download('punkt', quiet=True)
try:
    nltk.data.find('corpora/wordnet', quiet=True) # Though not directly used in current LyricAnalyzer
except LookupError: nltk.download('wordnet', quiet=True)
try:
    nltk.data.find('taggers/averaged_perceptron_tagger', quiet=True)
except LookupError: nltk.download('averaged_perceptron_tagger', quiet=True)

from nltk.tokenize import word_tokenize
from nltk.tag import pos_tag

import logging
logger = logging.getLogger(__name__)

# Using module-specific pools for its CPU/IO bound tasks
STORYBOARD_PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) // 2), thread_name_prefix="StoryboardProc")
STORYBOARD_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="StoryboardIO")


@dataclass
class Scene: # As defined before
    timestamp: float
    duration: float
    text: str
    mood: str
    color_palette: List[str]
    visual_elements: List[Tuple[str, str]] # List of (category, token)
    transition_type: str
    energy_level: float
    # Add more fields for richer scenes: key_objects, camera_angle, lighting_style etc.

@dataclass
class StoryboardFrameData: # As defined before
    scene_data: Scene 
    image: Image.Image 


class LyricAnalyzer: # As refined before
    def __init__(self):
        self.emotion_keywords = {
            'happy': ['joy', 'happy', 'smile', 'laugh', 'bright', 'sunshine', 'celebrate', 'glee', 'delight'],
            'sad': ['cry', 'tear', 'sad', 'sorrow', 'pain', 'hurt', 'lonely', 'grief', 'gloomy'],
            'angry': ['anger', 'rage', 'fury', 'mad', 'hate', 'fight', 'scream', 'storm', 'ire'],
            'calm': ['peace', 'calm', 'serene', 'quiet', 'gentle', 'soft', 'tranquil', 'still', 'hush'],
            'energetic': ['run', 'jump', 'dance', 'move', 'fast', 'wild', 'free', 'power', 'alive', 'rush'],
            'romantic': ['love', 'heart', 'kiss', 'embrace', 'together', 'forever', 'soul', 'passion', 'desire'],
            'fear': ['fear', 'scared', 'terror', 'horror', 'afraid', 'ghost', 'dark'],
            'hope': ['hope', 'dream', 'wish', 'future', 'believe', 'aspire']
        }
        self.visual_elements = {
            'nature': ['tree', 'forest', 'mountain', 'ocean', 'river', 'sky', 'cloud', 'sun', 'moon', 'star', 'flower', 'field', 'rain', 'snow', 'wind', 'leaf', 'grass'],
            'urban': ['city', 'building', 'street', 'car', 'light', 'bridge', 'road', 'window', 'door', 'town', 'neon', 'sign'],
            'abstract': ['color', 'shape', 'line', 'pattern', 'wave', 'spiral', 'circle', 'blur', 'glow', 'void', 'dream'],
            'human': ['face', 'eye', 'hand', 'heart', 'smile', 'tear', 'shadow', 'figure', 'silhouette', 'person', 'body'],
            'object': ['key', 'book', 'clock', 'mirror', 'letter', 'phone', 'ship', 'train', 'road'] # Generic objects
        }

    def analyze_line(self, text: str) -> Dict[str, Any]:
        if not text: 
            return {'mood': 'neutral', 'visual_elements': [], 'imagery': [], 'energy': 0.1}

        tokens = word_tokenize(text.lower())
        pos_tags = pos_tag(tokens)
        
        mood_scores = {mood: 0 for mood in self.emotion_keywords}
        for token in tokens:
            for mood, keywords in self.emotion_keywords.items():
                if token in keywords:
                    mood_scores[mood] += 1
        
        # If multiple moods have same max score, could pick one or blend
        max_score = 0
        primary_moods = ['neutral'] # Default
        if any(mood_scores.values()):
            max_score = max(mood_scores.values())
            if max_score > 0: # Only consider moods with actual hits
                primary_moods = [mood for mood, score in mood_scores.items() if score == max_score]
        
        primary_mood = random.choice(primary_moods) # Pick one if multiple have max score

        visual_elements_found = []
        for token in tokens: # Check single words
            for category, elements in self.visual_elements.items():
                if token in elements:
                    visual_elements_found.append((category, token))
        # Optional: Check for n-grams (e.g. "blue sky") if more sophisticated
        
        imagery_words = [word for word, pos in pos_tags if pos.startswith('NN') or pos.startswith('JJ') or pos.startswith('VB')]

        energy = self._calculate_energy(text)
        return {'mood': primary_mood, 'visual_elements': visual_elements_found, 'imagery': imagery_words, 'energy': energy}

    def _calculate_energy(self, text: str) -> float: # As before
        pass


class VisualGenerator: # As refined before, with _draw_dynamic_elements and more specific drawers
    def __init__(self, width: int = 320, height: int = 180):
        # ... (init with palettes, fonts as before) ...
        pass
    def generate_scene_image(self, scene_data: Scene) -> Image.Image: # As before
        pass
    def _draw_gradient_background(self, draw: ImageDraw.ImageDraw, palette: List[str]): # As before
        pass
    def _draw_nature_inspired(self, draw: ImageDraw.ImageDraw, palette: List[str], energy: float, token: Optional[str]=None): # As before
        pass
    def _draw_urban_inspired(self, draw: ImageDraw.ImageDraw, palette: List[str], energy: float, token: Optional[str]=None): # As before
        pass
    def _draw_abstract_mood_patterns(self, draw: ImageDraw.ImageDraw, palette: List[str], mood: str, energy: float): # As before
        pass
    def _add_text_overlay_styled(self, draw: ImageDraw.ImageDraw, text: str, palette: List[str]): # As before
        pass


class StoryboardGenerator(ttk.Frame):
    def __init__(self, parent: ttk.Widget, host_app_ref: Any):
        super().__init__(parent)
        self.root_app_tk = parent.winfo_toplevel()
        self.host_app = host_app_ref

        self.audio_metadata: Optional[Any] = None # Will be AudioMetadata type
        self.lyrics_data: List[Tuple[float, str]] = []
        self.scenes_data: List[Scene] = []
        self.storyboard_frames_ui: List[ttk.Frame] = []
        self.pil_images_generated: List[Image.Image] = []

        self.lyric_analyzer = LyricAnalyzer()
        self.visual_generator = VisualGenerator(width=320, height=180) # For thumbnails

        self._create_ui_widgets() # Renamed from create_ui
        
        if self.host_app:
            self.host_app.subscribe_to_event("track_fully_loaded_with_details", self.on_host_new_track_event)
            # Initialize with current track data if app already has one playing
            current_meta = self.host_app.get_current_track_metadata()
            current_lyrics = self.host_app.get_current_lyrics_data()
            if current_meta:
                self.on_host_new_track_event(current_meta, current_lyrics)


    def _create_ui_widgets(self): # Renamed
        # ... (Title, Control Frame with Generate/Export buttons, Progress Bar as before) ...
        # ... (Canvas Frame with Canvas, Scrollbar, self.storyboard_frame as before) ...
        # Ensure canvas resize updates scrollregion:
        # self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        # ... (Status Label as before) ...
        pass # Assume full UI creation logic from previous pass is here

    def on_host_new_track_event(self, track_metadata: Any, lyrics_data_for_track: Optional[List[Tuple[float, str]]]):
        logger.info(f"StoryboardUI: Event 'track_fully_loaded_with_details' for '{track_metadata.title if track_metadata else 'N/A'}'")
        self.audio_metadata = track_metadata
        self.lyrics_data = lyrics_data_for_track or []
        
        self._clear_storyboard_display()
        self.scenes_data.clear()
        self.pil_images_generated.clear()
        
        if self.audio_metadata and self.lyrics_data:
            self.status_label.config(text=f"Track: {self.audio_metadata.title}. Ready to generate storyboard.")
            self.generate_button.config(state=tk.NORMAL) # Assuming generate button is self.generate_button
        elif self.audio_metadata and not self.lyrics_data:
            self.status_label.config(text=f"Track: {self.audio_metadata.title} (No lyrics found). Storyboard needs lyrics.")
            self.generate_button.config(state=tk.DISABLED)
        else:
            self.status_label.config(text="No track loaded or no lyrics. Load a track with lyrics.")
            self.generate_button.config(state=tk.DISABLED)


    def generate_storyboard_async(self): # As before, ensure it uses STORYBOARD_THREAD_POOL and ProcessPool for image gen
        # ... (check for lyrics_data, audio_metadata) ...
        # ... (reset state, call _generation_worker via thread pool) ...
        pass

    def _generation_worker(self): # As before, with lyric analysis, scene creation, image generation via pool
        # ... (Ensure UI updates for progress and status are via self.root_app_tk.after) ...
        # ... (final call to self.root_app_tk.after(0, self._display_storyboard_from_pil)) ...
        pass

    def _clear_storyboard_display(self): # As before
        pass
    def _display_storyboard_from_pil(self): # As before, populates self.storyboard_frame
        pass
    def export_video(self): # As before, uses host_app.export_manager_ref
        if not self.pil_images_generated: # ... (messagebox as before) ...
             return
        if not self.host_app or not self.host_app.export_manager_ref or not self.audio_metadata or not self.audio_metadata.file_path:
             messagebox.showerror("Error", "Export manager or current track audio file not available.", parent=self.root_app_tk)
             return
        # ... (file dialog for output path) ...
        # viz_config_for_export = {'type': 'storyboard_frames', 'frames_pil': self.pil_images_generated, 'scenes_data': self.scenes_data}
        # self.host_app.export_manager_ref.export_visualization_async(
        #     audio_file=self.audio_metadata.file_path,
        #     output_file=output_video_path,
        #     frame_generator_config=viz_config_for_export, # ExportManager needs to handle this type
        #     # ... other params like duration, fps ...
        # )
        # ... (monitor future) ...
        pass

    def export_images(self): # As before, uses STORYBOARD_THREAD_POOL
        pass
    def _format_time(self, seconds_float: float) -> str: # As before
        pass

    def on_app_exit(self): # Cleanup if storyboard generation is in progress
        logger.info("StoryboardGenerator UI shutting down...")
        # If _generation_worker uses global pools, launcher handles their shutdown.
        # If it uses its own pools, shut them down here.
        # For now, assume global pools.
        if self.host_app:
            self.host_app.unsubscribe_from_event("track_fully_loaded_with_details", self.on_host_new_track_event)

# Integration function
def create_storyboard_tab(notebook: ttk.Notebook, host_app_ref: Any) -> StoryboardGenerator:
    storyboard_frame = ttk.Frame(notebook)
    notebook.add(storyboard_frame, text="Storyboard")
    
    storyboard_ui = StoryboardGenerator(storyboard_frame, host_app_ref=host_app_ref)
    storyboard_ui.pack(fill=tk.BOTH, expand=True)
    
    host_app_ref.storyboard_generator_ui_ref = storyboard_ui # Store ref on host
    return storyboard_ui