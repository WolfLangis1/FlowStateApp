"""
Flow State: Voice Control System
Natural language voice commands for hands-free music control
"""

import speech_recognition as sr
import pyttsx3 # Synchronous, needs its own thread for speaking
import threading
import queue
import time
import re
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Tuple, Any
from enum import Enum
import numpy as np
# import librosa # Not directly used here, but sr can use it for VAD
# import sounddevice as sd # sr.Microphone uses PortAudio
from fuzzywuzzy import fuzz, process
import nltk
from word2number import w2n
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import concurrent.futures
import random # For choosing responses

logger = logging.getLogger(__name__)

# NLTK data downloads (ensure they are quiet and run once)
try:
    nltk.data.find('tokenizers/punkt', quiet=True)
except LookupError: nltk.download('punkt', quiet=True)
try:
    nltk.data.find('taggers/averaged_perceptron_tagger', quiet=True)
except LookupError: nltk.download('averaged_perceptron_tagger', quiet=True)
try:
    nltk.data.find('corpora/wordnet', quiet=True) # For lemmatization if used
except LookupError: nltk.download('wordnet', quiet=True)


# Module-specific thread pool for intent parsing and command handling logic if it becomes heavy
VOICE_COMMAND_PROCESS_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="VoiceCmdProcess")

class CommandType(Enum): # As defined before
    PLAYBACK = "playback"
    NAVIGATION = "navigation"
    VOLUME = "volume"
    SEARCH = "search"
    PLAYLIST = "playlist"
    INFORMATION = "information"
    SYSTEM = "system"
    MOOD = "mood"
    DISCOVERY = "discovery"
    # Add more specific types if needed, e.g., UI_CONTROL, SETTINGS

@dataclass
class VoiceCommand: # As defined before
    command_type: CommandType
    action: str
    parameters: Dict[str, Any] # Allow Any for parameter values
    confidence: float
    raw_text: str
    timestamp: float

@dataclass
class CommandPattern: # As defined before
    pattern: str # Regex string
    command_type: CommandType
    action: str
    # Parameter extractors now take Match object and return Dict or None
    parameter_extractors: List[Callable[[re.Match], Optional[Dict[str, Any]]]]
    aliases: List[str] = field(default_factory=list)
    compiled_pattern: Optional[re.Pattern] = None # Store compiled regex

    def __post_init__(self):
        try:
            self.compiled_pattern = re.compile(self.pattern, re.IGNORECASE) # Compile regex on init
        except re.error as e:
            logger.error(f"Invalid regex pattern for action '{self.action}': {self.pattern} - {e}")
            self.compiled_pattern = None


class IntentParser: # As refined before
    # ... (Full implementation of __init__ with _initialize_patterns, _initialize_extractors,
    #      parse method using compiled_pattern and fuzzy_match_command,
    #      and all _extract_* parameter helper methods) ...
    # Ensure parameter extractors take `match_group_text: str` and return `Dict` or `None`.
    def __init__(self):
        self.command_patterns = self._initialize_patterns()
        # self.entity_extractors = self._initialize_extractors() # Not directly used if extractors are part of CommandPattern

    def _initialize_patterns(self) -> List[CommandPattern]:
        # Ensure all parameter extractors take the matched group string as input
        # and return a dictionary of parameters, or an empty dict/None.
        # Example parameter extractor signature: def _extract_track_info(text_group: str) -> Dict[str, str]:
        # return {'query': text_group.strip()} if text_group else {}
        # The CommandPattern should store these functions.
        # Parameter extractors should now take the re.Match object to access specific groups.
        # def _extract_track_info_from_match(match: re.Match) -> Optional[Dict[str, str]]:
        #     if match.group(1): return {'query': match.group(1).strip()}
        #     return None

        # This is a placeholder for the full list of CommandPatterns from previous iterations.
        # It needs to be populated with all the patterns.
        return [] # Placeholder, must be filled with CommandPattern list


    def parse(self, text: str) -> Optional[VoiceCommand]:
        text_lower = text.lower().strip()
        if not text_lower: return None

        for cmd_pattern_obj in self.command_patterns:
            if not cmd_pattern_obj.compiled_pattern: continue # Skip if regex failed to compile

            match = cmd_pattern_obj.compiled_pattern.fullmatch(text_lower) # Use fullmatch for stricter matching
            
            # Try aliases if main pattern fails
            if not match and cmd_pattern_obj.aliases:
                for alias in cmd_pattern_obj.aliases:
                    # Simple alias check: if alias is a substring of the command.
                    # More complex alias matching might involve separate regexes or fuzzy matching here.
                    if alias.lower() in text_lower: # Basic check
                        # For alias match, we might not have groups for parameter extractors.
                        # Parameters might need to be extracted from the *whole text* based on alias context.
                        # This part needs careful design if aliases also need parameter extraction.
                        # For now, assume aliases are for commands without complex parameters from groups.
                        logger.debug(f"Matched alias '{alias}' for action '{cmd_pattern_obj.action}'")
                        # Create a conceptual match object or pass None if extractors expect groups
                        # This is simplified; alias matching often needs specific logic.
                        parameters = {} # No group-based params for simple alias match here
                        # Potentially, call a generic entity extractor on `text_lower` if alias matches.
                        
                        return VoiceCommand(
                            command_type=cmd_pattern_obj.command_type, action=cmd_pattern_obj.action,
                            parameters=parameters, confidence=0.75, # Slightly lower confidence for alias
                            raw_text=text, timestamp=time.time()
                        )

            if match:
                parameters = {}
                for extractor_func in cmd_pattern_obj.parameter_extractors:
                    try:
                        # Pass the re.Match object to extractors
                        extracted_params = extractor_func(match)
                        if extracted_params:
                            parameters.update(extracted_params)
                    except Exception as e_ex:
                        logger.error(f"Parameter extractor {extractor_func.__name__} failed for '{text_lower}': {e_ex}")
                
                return VoiceCommand(
                    command_type=cmd_pattern_obj.command_type, action=cmd_pattern_obj.action,
                    parameters=parameters, confidence=0.9, # Higher confidence for direct regex match
                    raw_text=text, timestamp=time.time()
                )
        
        # Fallback to fuzzy matching if no direct regex or simple alias match
        return self._fuzzy_match_command(text, text_lower)


    def _fuzzy_match_command(self, original_text: str, text_lower:str) -> Optional[VoiceCommand]: # As before
        pass
    # ... (All _extract_* helper methods for parameters, taking match group string or re.Match object)

class VoiceRecognizer: # As refined before
    # ... (Full implementation of __init__, _initialize_microphone, start_listening, stop_listening,
    #      _listen_loop, _process_phrase, using sr.Microphone and sr.Recognizer) ...
    pass

class VoiceFeedback: # As refined before
    # ... (Full implementation of __init__, _init_engine_thread, _tts_worker, _setup_voice_properties, speak, stop) ...
    pass

class VoiceCommandHandler: # As refined before
    # ... (Full implementation of __init__(feedback_system, host_app_interface),
    #      _speak_response, _handle_command_callback, handle_command_async, _execute_command_worker
    #      and all private _handle_* methods for different CommandTypes.
    #      These methods use self.host_app.request_playback_action or other host_app methods.) ...
    pass

class VoiceControlUI(ttk.Frame): # As refined before
    # ... (Full implementation of __init__(parent, host_app_ref), create_ui,
    #      toggle_listening, start_listening, stop_listening,
    #      on_voice_input (which calls _process_recognized_text), _process_recognized_text (offloads parsing/handling),
    #      log_command_to_ui, calibrate_microphone, _calibrate_thread, update_wake_word,
    #      monitor_audio_level, on_app_exit) ...
    # Ensures it uses host_app_ref correctly.
    pass

# Integration function
def create_voice_control_tab(notebook: ttk.Notebook, host_app_ref: Any) -> VoiceControlUI: # As refined before
    voice_frame = ttk.Frame(notebook)
    notebook.add(voice_frame, text="Voice")
    
    voice_ui = VoiceControlUI(voice_frame, host_app_ref=host_app_ref)
    voice_ui.pack(fill=tk.BOTH, expand=True)
    
    host_app_ref.voice_control_ui_ref = voice_ui # Store ref on host
    return voice_ui

if __name__ == "__main__": # As refined before
    # ... (Standalone test code for VoiceControlUI, including on_main_exit to call ui.on_app_exit()) ...
    # Test IntentParser separately if needed.
    pass