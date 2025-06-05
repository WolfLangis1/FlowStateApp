"""
Flow State: Music Library Database Module
Advanced music library management with search, tagging, and smart playlists
"""

import sqlite3
import os
import json
import hashlib
import threading
from datetime import datetime, timedelta # Added timedelta for date_added/last_played rules
from typing import List, Dict, Optional, Tuple, Any, Callable, Union # Added Union
from dataclasses import dataclass, asdict, field
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog # Added simpledialog
from pathlib import Path
import mutagen
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.wave import WAVE
from mutagen.mp4 import MP4
import concurrent.futures
import logging

logger = logging.getLogger(__name__)

# Assuming global DB_THREAD_POOL and SCAN_THREAD_POOL are defined in launcher or a shared utility
# For standalone, define them here:
DB_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='MusicLibDBWriteThread')
SCAN_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 2, thread_name_prefix='MusicLibScanThread')

@dataclass
class Track: # As defined before, ensure consistency
    id: Optional[int] = None
    file_path: str = ""
    title: Optional[str] = "Unknown"
    artist: Optional[str] = "Unknown"
    album: Optional[str] = "Unknown"
    album_artist: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    duration: float = 0.0
    bitrate: int = 0
    sample_rate: int = 44100
    channels: int = 2
    file_size: int = 0
    date_added: str = field(default_factory=lambda: datetime.now().isoformat())
    last_played: Optional[str] = None
    play_count: int = 0
    rating: int = 0
    bpm: Optional[float] = None
    key: Optional[str] = None
    energy: Optional[float] = None
    valence: Optional[float] = None
    danceability: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    speechiness: Optional[float] = None
    mood_tags: List[str] = field(default_factory=list)
    file_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]: # As before
        data = asdict(self)
        data['mood_tags'] = json.dumps(data.get('mood_tags', []))
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track': # As before
        if 'mood_tags' in data and isinstance(data['mood_tags'], str):
            try: data['mood_tags'] = json.loads(data['mood_tags'])
            except json.JSONDecodeError: data['mood_tags'] = []
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        return cls(**filtered_data)


@dataclass
class Playlist: # As defined before
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_date: str = field(default_factory=lambda: datetime.now().isoformat())
    is_smart: bool = False
    rules: Optional[str] = None # JSON string for smart playlist rules
    track_ids: List[int] = field(default_factory=list) # For regular playlists, stores actual track IDs


# --- Constants for Smart Playlists --- (as defined before)
SMART_PLAYLIST_FIELDS = { # field_key: (Display Name, Value Type, Operators)
    "title": ("Title", "text", ["contains", "is", "is_not", "starts_with", "ends_with"]),
    "artist": ("Artist", "text", ["contains", "is", "is_not", "starts_with", "ends_with"]),
    "album": ("Album", "text", ["contains", "is", "is_not", "starts_with", "ends_with"]),
    "genre": ("Genre", "text", ["is", "is_not", "contains"]),
    "year": ("Year", "number", ["is", "is_not", "greater_than", "less_than", "greater_equal", "less_equal", "in_range_year"]),
    "duration_seconds": ("Duration (sec)", "number", ["greater_than", "less_than", "greater_equal", "less_equal"]),
    "play_count": ("Play Count", "number", ["is", "greater_than", "less_than", "greater_equal", "less_equal"]),
    "rating": ("Rating (0-5)", "number", ["is", "is_not", "greater_than", "less_than", "greater_equal", "less_equal"]),
    "bpm": ("BPM", "number", ["is", "greater_than", "less_than", "greater_equal", "less_equal", "in_range"]),
    "key": ("Key", "text", ["is", "is_not"]),
    "date_added_days_ago": ("Added (days ago <=)", "number_special", ["less_equal", "greater_equal"]),
    "last_played_days_ago": ("Played (days ago <=)", "number_special", ["less_equal", "greater_equal", "is_not_played_in_last_days", "is_never_played"]),
    "mood_tags": ("Mood Tag", "text_list_special", ["contains_all", "contains_any", "does_not_contain"]),
    "energy": ("Energy (0-1)", "float", ["greater_than", "less_than", "greater_equal", "less_equal"]),
    "valence": ("Valence (0-1)", "float", ["greater_than", "less_than", "greater_equal", "less_equal"]),
}
SMART_PLAYLIST_OPERATORS = { # Default operators per value_type
    "text": ["contains", "does_not_contain", "is", "is_not", "starts_with", "ends_with"],
    "number": ["is", "is_not", "greater_than", "less_than", "greater_equal", "less_equal"],
    "float": ["greater_than", "less_than", "greater_equal", "less_equal"],
    "number_special": ["less_equal", "greater_equal"], # For date_added_days_ago, last_played_days_ago
    "text_list_special": ["contains_all", "contains_any", "does_not_contain"], # For mood_tags
    # Specific fields can override these with their own list in SMART_PLAYLIST_FIELDS
}


class MusicLibraryDB:
    # ... (__init__, init_database, get_connection, add_track, get_track_by_path_or_hash, get_track,
    #      search_tracks (refined), get_all_tracks, update_track_async, _update_track_worker,
    #      increment_play_count_async, _increment_play_count_worker,
    #      _calculate_file_hash, get_statistics as refined previously) ...

    def create_playlist(self, name: str, description: str = "", is_smart: bool = False, rules_json: Optional[str] = None) -> Optional[int]:
        # ... (as implemented in previous "Full Smart Playlist Editor" pass) ...
        pass

    def update_playlist(self, playlist_id: int, name: str, description: str, 
                        is_smart: bool, rules_json: Optional[str]) -> bool:
        # ... (as implemented in previous "Full Smart Playlist Editor" pass) ...
        pass

    def get_playlist_by_id(self, playlist_id: int) -> Optional[Playlist]:
        # ... (as implemented in previous "Full Smart Playlist Editor" pass, ensure it returns Playlist object) ...
        pass

    def get_all_playlists(self) -> List[Playlist]:
        # ... (as implemented in previous "Full Smart Playlist Editor" pass, ensuring Playlist objects with track_ids or count) ...
        pass

    def add_tracks_to_playlist(self, playlist_id: int, track_ids: List[int]): # Expects list of track LIBRARY IDs
        # ... (as implemented in previous "Full Smart Playlist Editor" pass) ...
        pass
    
    def get_playlist_tracks(self, playlist_id: int) -> List[Track]: # For regular playlists
        conn = self.get_connection()
        cursor = conn.execute("""
            SELECT t.* FROM tracks t
            JOIN playlist_tracks pt ON t.id = pt.track_id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position
        """, (playlist_id,))
        return [Track.from_dict(dict(row)) for row in cursor.fetchall()]


    def get_smart_playlist_tracks(self, rules_json: str) -> List[Track]:
        # ... (as refined in previous "Enhanced Search & Smart Playlist Logic" pass,
        #      ensure it handles date_added_days_ago and last_played_days_ago by converting
        #      "X days ago" into an actual date string for comparison with date_added/last_played columns) ...
        # Example for date_added_days_ago <= X:
        #   target_date = (datetime.now() - timedelta(days=int(value))).strftime('%Y-%m-%dT%H:%M:%S')
        #   conditions.append("date_added >= ?") # Added on or after target_date means <= X days ago
        #   params.append(target_date)
        # For last_played_days_ago IS NEVER PLAYED:
        #   conditions.append("last_played IS NULL")
        pass # Assume robust implementation from previous pass

    def rename_playlist(self, playlist_id: int, new_name: str) -> bool: # As before
        pass
    def delete_playlist(self, playlist_id: int) -> bool: # As before
        pass
    
    def get_all_distinct_values_for_field(self, field_name: str) -> List[str]:
        """Gets all distinct non-null, non-empty values for a given field from tracks table."""
        # Whitelist field_name to prevent SQL injection
        valid_fields = ['artist', 'album', 'album_artist', 'genre', 'year', 'key'] # Add more as needed
        if field_name not in valid_fields:
            logger.warning(f"Attempt to get distinct values for invalid field: {field_name}")
            return []
        conn = self.get_connection()
        try:
            # Cast to TEXT to handle numbers like 'year' correctly for distinct list of strings
            cursor = conn.execute(f"SELECT DISTINCT CAST({field_name} AS TEXT) FROM tracks WHERE {field_name} IS NOT NULL AND TRIM({field_name}) != '' ORDER BY 1 COLLATE NOCASE")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting distinct values for field {field_name}: {e}")
            return []


class MusicScanner: # As before
    pass

class SmartPlaylistRuleDialog(tk.Toplevel): # As before
    pass

class SmartPlaylistEditorDialog(tk.Toplevel): # As before, with Move Up/Down buttons implemented
    pass

class AddToPlaylistDialog(tk.Toplevel): # As before
    pass

class LibraryManagerUI(ttk.Frame):
    # ... (__init__, _create_layout (now includes now_viewing_label_var),
    #      _setup_event_subscriptions, event handlers, refresh_playlist_list_async,
    #      on_playlist_or_source_selected (updates now_viewing_label_var),
    #      refresh_library_view_async, _populate_track_treeview_and_stats, _populate_track_treeview,
    #      _update_library_stats_ui_cb, _create_track_context_menu,
    #      show_playlist_context_menu (calls rename_playlist_dialog, delete_playlist_confirm),
    #      play_selected_playlist, rename_playlist_dialog, delete_playlist_confirm,
    #      add_selected_to_playlist_dialog, create_new_regular_playlist,
    #      open_smart_playlist_editor as implemented/refined previously) ...
    pass

# Integration function
def create_library_tab(notebook: ttk.Notebook, host_app_ref: Any) -> Tuple[MusicLibraryDB, LibraryManagerUI]:
    # ... (as before, ensuring LibraryManagerUI and its MusicScanner get host_app_ref) ...
    library_frame = ttk.Frame(notebook)
    notebook.add(library_frame, text="Library")
    
    db_file = Path.home() / ".flowstate" / "data" / "flow_state_library.db"
    db_file.parent.mkdir(parents=True, exist_ok=True)
    db = MusicLibraryDB(db_path=str(db_file))
    
    library_ui = LibraryManagerUI(library_frame, db, host_app_ref=host_app_ref)
    library_ui.pack(fill=tk.BOTH, expand=True)
    
    return db, library_ui