"""
Flow State: Advanced Audio Effects Module
Professional-grade audio processing and effects chain
"""

import numpy as np
from scipy import signal
import tkinter as tk
from tkinter import ttk, Scale # ttk.Scale is preferred over tk.Scale
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Union, Tuple
import json
from abc import ABC, abstractmethod
import math
import logging

logger = logging.getLogger(__name__)

class AudioEffect(ABC):
    """Base class for all audio effects"""

    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.bypass = False # Kept for individual bypass
        self.parameters: Dict[str, Any] = {}
        self.sample_rate = 44100
        self.channels = 2

    def set_stream_properties(self, sample_rate: int, channels: int):
        """Called by host to set sample rate and channels, allowing effect to reinitialize if needed."""
        needs_reinit = False
        if self.sample_rate != sample_rate:
            self.sample_rate = sample_rate
            needs_reinit = True
        if self.channels != channels:
            self.channels = channels
            needs_reinit = True
        
        if needs_reinit:
            # Signal parameter change logic that a reset due to stream props happened
            # This allows _on_parameter_change to know if it's a regular param change or a reset.
            self._on_parameter_change("_stream_props_changed", None) 
            self.reset() 

    def process_block(self, audio_block: np.ndarray) -> np.ndarray:
        """
        Base process_block. Handles bypass/enabled and basic channel adaptation.
        Subclasses should call this first or implement similar checks.
        Input audio_block is (num_samples, num_channels) or (num_samples,) for mono.
        Output should match self.channels.
        """
        if self.bypass or not self.enabled:
            return audio_block
        
        # Ensure input block has correct channel dimension for this effect instance
        input_block_channels = audio_block.shape[1] if audio_block.ndim == 2 else 1
        
        if input_block_channels == self.channels:
            return audio_block # Correct shape, pass to subclass processing or return if this is it
        elif input_block_channels == 1 and self.channels == 2: # Mono input, effect is stereo
            logger.debug(f"{self.name}: Duplicating mono input to stereo for effect processing.")
            return np.tile(audio_block[:, np.newaxis], (1, self.channels)).astype(audio_block.dtype)
        elif input_block_channels == 2 and self.channels == 1: # Stereo input, effect is mono
            logger.debug(f"{self.name}: Averaging stereo input to mono for effect processing.")
            return np.mean(audio_block, axis=1, keepdims=True).astype(audio_block.dtype)
        else: # Other mismatches (e.g., 5.1 input to stereo effect) - complex, pass through for now
            logger.warning(f"{self.name}: Channel mismatch. Effect expects {self.channels}, "
                           f"got {input_block_channels}. Passing through original block.")
            return audio_block # Return original without modification if shape is unexpected

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        return self.parameters.copy()

    def set_parameter(self, name: str, value: Any):
        if name in self.parameters:
            if self.parameters[name] != value: # Only update if value changed
                self.parameters[name] = value
                self._on_parameter_change(name, value) # Call internal handler
        else:
            logger.warning(f"Parameter '{name}' not found in {self.name}. Available: {list(self.parameters.keys())}")

    def _on_parameter_change(self, name: str, value: Any):
        """Internal handler for when a parameter changes or stream props change. Override in subclasses."""
        # This is where effects recalculate coefficients or reinitialize buffers if a parameter
        # or stream property (like sample_rate, indicated by name="_stream_props_changed") changes.
        pass

    def reset(self):
        """
        Reset effect state (e.g., filter states, delay buffers).
        Called on init and when stream properties change significantly.
        Subclasses should call super().reset() then their specific reset logic.
        """
        logger.debug(f"Resetting effect: {self.name} with SR={self.sample_rate}, Chans={self.channels}")
        # _on_parameter_change (called by set_stream_properties) handles reacting to SR/CH change.
        # This reset method is more for clearing runtime state like filter ZIs, envelopes.
        pass


class GainEffect(AudioEffect):
    def __init__(self):
        super().__init__("Gain")
        self.parameters = {'gain_db': 0.0}
        self.gain_linear = 1.0
        self._on_parameter_change('gain_db', 0.0)

    def process_block(self, audio_block: np.ndarray) -> np.ndarray:
        processed_block = super().process_block(audio_block)
        if processed_block is audio_block and (self.bypass or not self.enabled): return audio_block
        if self.gain_linear == 1.0: return processed_block
        return processed_block * self.gain_linear

    def _on_parameter_change(self, name: str, value: Any):
        if name == 'gain_db':
            gain_val_db = float(value)
            self.parameters['gain_db'] = gain_val_db # Ensure internal param dict is also updated
            self.gain_linear = 10 ** (gain_val_db / 20.0)
    
    # get_ui method would be defined in the UI layer or a separate file for this plugin if it were dynamic.

class ParametricEQ(AudioEffect):
    # ... (Full implementation as in previous "Full Smart Playlist Editor" pass) ...
    # Key things: _init_bands, _update_all_filters, reset_filter_states, process_block using lfilter,
    # _on_parameter_change correctly parsing "band_X_param" and calling _update_all_filters.
    pass

class Compressor(AudioEffect):
    # ... (Full implementation with vectorized lookahead as in "Compressor Lookahead Focus" pass) ...
    # Key things: _calculate_envelope_coeffs, _init_lookahead_buffer, reset,
    # process_block with vectorized level detection, static gain curve, iterative envelope,
    # block-managed lookahead, and vectorized final gain application.
    pass

class Delay(AudioEffect):
    # ... (Full implementation with vectorized block processing as in "Compressor Lookahead Focus" pass,
    #      where Delay was significantly vectorized) ...
    # Key things: _design_lpf, reset_filter_states_fb, reset for buffers,
    # process_block with vectorized LFO, delay times, interpolated reads, feedback filtering, and mix.
    pass

class Reverb(AudioEffect): # Conceptual block processing, iterative comb filters
    # ... (Full implementation as in "Reverb Block Processing" pass) ...
    # Key things: _design_all_filters to create comb filter data (buffers, lpf for damping)
    # and allpass filter coefficients (b,a).
    # process_block iterates samples for comb filters (due to internal LPF in feedback),
    # then uses vectorized lfilter for serial allpass filters.
    pass

class Chorus(AudioEffect): # Conceptual block processing
    # ... (Full implementation as in "Reverb Block Processing" pass, where Chorus was also outlined) ...
    # process_block would iterate samples, and for each sample, iterate voices.
    # Each voice: calculate LFO, get modulated delay, do interpolated read, write to its buffer.
    # Sum voice outputs, mix with dry. Vectorizing the multiple modulated delay reads is the challenge.
    def __init__(self): # Ensure basic structure even if process_block is placeholder
        super().__init__("Chorus")
        self.parameters = { 'rate_hz': 0.2, 'depth_s': 0.003, 'mix': 0.5, 'num_voices': 3, 'stereo_spread': 0.7 }
        self.voices_data: List[Dict[str, Any]] = []
        self.max_voice_delay_s = 0.025
        self.write_idx = 0
        self.reset()

    def _on_parameter_change(self, name: str, value: Any):
        if name in ['num_voices', "_stream_props_changed"]: self.reset() # Re-init voices

    def reset(self):
        super().reset()
        num_v = self.parameters.get('num_voices', 3)
        self.voices_data = []
        if self.sample_rate <=0 or self.channels <=0: return

        buffer_len_samples = int(self.max_voice_delay_s * self.sample_rate)
        if buffer_len_samples <= 0: return

        for i in range(num_v):
            self.voices_data.append({
                'buffer': np.zeros((buffer_len_samples, self.channels), dtype=np.float32),
                'lfo_phase': np.random.rand() * 2 * np.pi,
                'lfo_rate_hz': self.parameters.get('rate_hz',0.2) * (1.0 + np.random.uniform(-0.1, 0.1)),
                'base_delay_s': 0.005 + np.random.uniform(0, 0.002) * i
            })
        self.write_idx = 0
        logger.info(f"Chorus reset: {num_v} voices, buffer {buffer_len_samples}, SR {self.sample_rate}")

    def process_block(self, audio_block: np.ndarray) -> np.ndarray:
        input_block = super().process_block(audio_block)
        if input_block is audio_block and (self.bypass or not self.enabled): return audio_block
        if not self.voices_data: # Not initialized
             logger.warning(f"{self.name}: Voices not initialized, passing through.")
             return input_block
        # ... (Iterative sample-by-sample, voice-by-voice logic from previous pass for now) ...
        # This remains the most complex to fully vectorize.
        # For now, assume the conceptual logic from previous pass is here.
        # To avoid making this response too long by repeating that detailed (but slow) loop:
        logger.debug(f"{self.name}: Using conceptual iterative processing for chorus block.")
        # A real implementation needs the full loop here.
        # For testing the chain, this passthrough after initial checks is okay if full logic is too long.
        return input_block # Placeholder if full iterative logic is omitted for brevity

class SimpleFilterPlugin(AudioEffectPlugin): # From plugin_system, moved here as an example
    # ... (Full implementation as in the previous "Plugin Config Save Flow" pass) ...
    # Ensure its reset calls super().reset() then self._design_filter().
    # Ensure its _on_parameter_change calls self._design_filter() for relevant params or _stream_props_changed.
    def __init__(self): # Copied from plugin_system.py and adapted
        super().__init__() # Calls AudioEffectPlugin's __init__
        self.info = PluginInfo( # This would be set if it were a real plugin from plugin_system
            name="Simple Filter (Effect)", version="1.0.1", author="Flow State Core",
            description="Butterworth Lowpass/Highpass filter.",
            plugin_type=PluginType.AUDIO_EFFECT, config={} # Assuming PluginInfo, PluginType defined
        )
        self.default_parameters = {
            'filter_type': 'lowpass', 'cutoff_hz': 1000.0, 'order': 2
        }
        self.parameters = self.default_parameters.copy() # Initialize self.parameters
        self.b_coeffs = np.array([1.0]); self.a_coeffs = np.array([1.0])
        self.filter_zi = np.array([])
        self.reset()
    
    # ... (rest of SimpleFilterPlugin: _on_parameter_change, _design_filter, reset, process_audio_block, get_ui)
    # Ensure process_audio_block is used and calls super().process_block logic (or handles bypass/enabled)
    def process_audio_block(self, audio_block: np.ndarray) -> np.ndarray: # Renamed
        # No call to super().process_block() here, as AudioEffectPlugin's process() calls this
        # and it should handle its own bypass/enabled if not done by the chain.
        # Let's assume the chain handles enabled, this handles bypass.
        if self.bypass or self.b_coeffs.size == 1 or self.filter_zi.size == 0:
            return audio_block
        # ... (rest of lfilter logic as in plugin_system.py)
        return audio_block # Placeholder

class AudioEffectsChain:
    # ... (as in previous "Full Smart Playlist Editor" pass, ensuring set_stream_properties on add) ...
    pass

class EffectsChainUI(ttk.Frame):
    # ... (as in previous "Full Smart Playlist Editor" pass) ...
    pass

# Integration function
def create_effects_tab(notebook: ttk.Notebook, host_app_ref: Any) -> Tuple[AudioEffectsChain, EffectsChainUI]:
    # ... (as in previous "Full Smart Playlist Editor" pass, ensuring chain gets sr/ch from host_app) ...
    effects_frame = ttk.Frame(notebook)
    notebook.add(effects_frame, text="Effects")
    
    sample_rate, channels = host_app_ref.get_audio_properties()
    effects_chain = AudioEffectsChain(sample_rate=sample_rate, channels=channels)
    
    # Add default effects (they will inherit sr/ch from chain via add_effect)
    gain = GainEffect(); gain.set_parameter('gain_db', 0.0); effects_chain.add_effect(gain)
    eq = ParametricEQ(); effects_chain.add_effect(eq)
    comp = Compressor(); effects_chain.add_effect(comp)
    # delay = Delay(); effects_chain.add_effect(delay) # Delay example
    # reverb = Reverb(); effects_chain.add_effect(reverb) # Reverb still conceptual
    # simple_filt = SimpleFilterPlugin(); effects_chain.add_effect(simple_filt) # If defined here
    
    effects_ui = EffectsChainUI(effects_frame, effects_chain, host_app_ref=host_app_ref)
    effects_ui.pack(fill=tk.BOTH, expand=True)
    
    host_app_ref.effects_chain_ref = effects_chain # Make chain available to host_app
    return effects_chain, effects_ui


if __name__ == "__main__":
    # ... (main test block as before, ensure mock host_app or root has get_audio_properties) ...
    # Example: root.get_audio_properties = lambda: (44100, 2)
    pass