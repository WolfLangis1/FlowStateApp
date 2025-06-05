"""
Flow State: AI Music Recommendation Engine
Advanced machine learning for personalized music discovery
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
# ML Model imports would go here if specific models were being directly used in this file
# e.g. from tensorflow import keras (though models are conceptual for now)

import pickle
import json
import sqlite3
from datetime import datetime, timedelta, timezone # Added timezone
from typing import List, Dict, Tuple, Optional, Any, Set # Added Set
import threading
import queue # Not directly used, but good for async patterns
from dataclasses import dataclass, field
import logging
import concurrent.futures
import os # For os.path.basename
from pathlib import Path # For DB path

logger = logging.getLogger(__name__)

# Constants for this module
RECOMMENDATIONS_DB_FILENAME = "recommendations_engine_data.db" # Specific DB for this engine
FEATURE_EXTRACTION_TIMEOUT_SECONDS = 180 # Increased timeout
# Using module-specific pools to avoid contention with other module's pools
AI_PROCESS_POOL = concurrent.futures.ProcessPoolExecutor(max_workers=max(1, (os.cpu_count() or 4) // 2), thread_name_prefix="AIRecsProc")
AI_THREAD_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="AIRecsIO")


@dataclass
class UserProfile: # As defined before
    user_id: str
    favorite_genres: List[str] = field(default_factory=list)
    favorite_artists: List[str] = field(default_factory=list)
    mood_preferences: Dict[str, float] = field(default_factory=dict) # mood_name -> preference_score (0-1)
    tempo_preference: Tuple[float, float] = (60, 180)
    energy_preference: float = 0.5
    # ... other preferences ...
    listening_history: List[Dict[str, Any]] = field(default_factory=list) # {'track_id': str, 'played_at_utc': str, 'listen_ratio': float}
    skip_history: List[Dict[str, Any]] = field(default_factory=list) # {'track_id': str, 'skipped_at_utc': str, 'skipped_after_sec': float}
    liked_tracks: Set[str] = field(default_factory=set) # Set of track_ids
    disliked_tracks: Set[str] = field(default_factory=set)

    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict_for_db(self) -> Dict[str, Any]:
        d = asdict(self)
        d['liked_tracks'] = json.dumps(list(d.get('liked_tracks', []))) # Convert set to list for JSON
        d['disliked_tracks'] = json.dumps(list(d.get('disliked_tracks', [])))
        # listening_history and skip_history are already lists of dicts, JSON serializable.
        return d

    @classmethod
    def from_db_dict(cls, db_data_json: str) -> 'UserProfile':
        db_data = json.loads(db_data_json)
        db_data['liked_tracks'] = set(db_data.get('liked_tracks', [])) # Convert list back to set
        db_data['disliked_tracks'] = set(db_data.get('disliked_tracks', []))
        
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        init_data = {k: v for k, v in db_data.items() if k in field_names}
        return cls(**init_data)


@dataclass
class TrackFeatures: # As defined before
    track_id: str
    title: str
    artist: str
    genre: Optional[str] = None
    bpm: Optional[float] = None
    key: Optional[str] = None
    energy: Optional[float] = None
    valence: Optional[float] = None
    danceability: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    speechiness: Optional[float] = None
    loudness: Optional[float] = None
    duration: Optional[float] = None
    timbre_features: List[float] = field(default_factory=list)
    mood_vector: List[float] = field(default_factory=list)
    last_analyzed_at: Optional[str] = None

    def to_dict_for_db(self) -> Dict[str, Any]: # As defined before
        d = asdict(self)
        d['timbre_features'] = json.dumps(d.get('timbre_features', []))
        d['mood_vector'] = json.dumps(d.get('mood_vector', []))
        return d

    @classmethod
    def from_db_dict(cls, db_data_json_str: str) -> 'TrackFeatures': # Takes JSON string
        db_data = json.loads(db_data_json_str)
        for key in ['timbre_features', 'mood_vector']:
            if key in db_data and isinstance(db_data[key], str):
                try: db_data[key] = json.loads(db_data[key])
                except json.JSONDecodeError: db_data[key] = []
        field_names = {f.name for f in cls.__dataclass_fields__.values()}
        init_data = {k: v for k, v in db_data.items() if k in field_names}
        return cls(**init_data)


class AudioFeatureExtractor: # As refined before
    # ... (Full implementation of __init__, extract_features, and private helpers
    #      _detect_key_from_chroma, _estimate_valence, _estimate_danceability, etc.) ...
    # Ensure extract_features is robust and returns Optional[TrackFeatures].
    # Import librosa inside extract_features if run in separate process pool.
    pass

class RecommendationEngine:
    def __init__(self, host_app_ref: Any):
        self.host_app = host_app_ref
        self.music_library_db = host_app_ref.music_library_db_ref
        
        rec_data_dir = Path.home() / ".flowstate" / "data"
        rec_data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = str(rec_data_dir / RECOMMENDATIONS_DB_FILENAME) # Engine's own DB
        
        self.feature_extractor = AudioFeatureExtractor()

        self.track_feature_matrix: Optional[np.ndarray] = None
        self.track_id_to_idx_map: Dict[str, int] = {}
        self.idx_to_track_id_map: Dict[int, str] = {}
        self.matrix_scaler: Optional[StandardScaler] = None # Store the scaler

        self.feature_cache: Dict[str, TrackFeatures] = {}
        self.cache_lock = threading.Lock()
        self.pending_extractions: Set[str] = set()

        self._init_recommendation_db()
        self._load_or_build_feature_matrix_async()

    def _db_execute_rec_engine(self, query: str, params: tuple = (), commit: bool = False, fetch_one: bool = False, fetch_all: bool = False):
        """Helper for synchronous DB execution FOR THIS ENGINE'S DB."""
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;") # Good practice
        conn.execute("PRAGMA journal_mode = WAL;")
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            if fetch_one: return cursor.fetchone()
            if fetch_all: return cursor.fetchall()
            return cursor.lastrowid if commit else None
        except Exception as e: logger.error(f"RecEngine DB Error: {e} (Query: {query[:100]})", exc_info=True); conn.rollback(); raise
        finally: conn.close()

    async def _db_action_rec_engine_async(self, query: str, params: tuple = (), commit: bool = False, fetch_one: bool = False, fetch_all: bool = False):
        """Async wrapper for this engine's DB actions."""
        loop = asyncio.get_running_loop() # Assuming called from async context
        return await loop.run_in_executor(AI_THREAD_POOL, self._db_execute_rec_engine, query, params, commit, fetch_one, fetch_all)


    def _init_recommendation_db(self): # As refined before, uses self._db_execute_rec_engine
        # CREATE TABLE IF NOT EXISTS user_profiles (user_id TEXT PRIMARY KEY, profile_json TEXT, ...);
        # CREATE TABLE IF NOT EXISTS extracted_track_features (track_id TEXT PRIMARY KEY, features_json TEXT, ...);
        # CREATE TABLE IF NOT EXISTS user_interactions (...);
        # This method is synchronous, called at __init__.
        self._db_execute_rec_engine("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                profile_json TEXT NOT NULL,
                created_at_utc TEXT,
                updated_at_utc TEXT
            ); """, commit=True)
        self._db_execute_rec_engine("""
            CREATE TABLE IF NOT EXISTS extracted_track_features (
                track_id TEXT PRIMARY KEY, /* String form of MusicLibraryDB track.id */
                features_json TEXT NOT NULL, /* JSON dump of TrackFeatures dataclass */
                last_analyzed_at TEXT
            );""", commit=True)
        # ... (other tables like user_interactions)


    def _load_or_build_feature_matrix_async(self): # As refined before
        pass
    def get_full_track_features(self, track_id_str: str, db_cursor: Optional[sqlite3.Cursor] = None) -> Optional[TrackFeatures]: # As refined
        # Uses self._db_execute_rec_engine or passed cursor
        # Returns TrackFeatures.from_db_dict(json.loads(row['features_json']))
        pass
    def request_feature_extraction(self, track_id_str: str, file_path: str): # As refined before
        pass
    def _save_track_features_to_rec_db(self, features: TrackFeatures): # As refined before
        # features_json = json.dumps(features.to_dict_for_db())
        # self._db_execute_rec_engine("INSERT OR REPLACE ... features_json ...", (..., features_json, ...), commit=True)
        pass
    def get_similar_tracks_content_based(self, track_id_str: str, num_similar: int = 10) -> List[Dict[str, Any]]: # As refined
        pass
    def get_recommendations_for_user_sync_wrapper(self, user_id: str, num_recs: int = 20, context: Optional[Dict]=None) -> List[Dict[str, Any]]: # As refined before
        pass # Assume full diverse strategy implementation
    
    # User Profile Management using this engine's DB
    def get_user_profile(self, user_id: str) -> UserProfile:
        row = self._db_execute_rec_engine("SELECT profile_json FROM user_profiles WHERE user_id = ?", (user_id,), fetch_one=True)
        if row:
            return UserProfile.from_db_dict(row['profile_json'])
        else: # Create new profile
            profile = UserProfile(user_id=user_id)
            self.save_user_profile(profile)
            return profile

    def save_user_profile(self, profile: UserProfile):
        profile.updated_at_utc = datetime.now(timezone.utc).isoformat()
        profile_json = json.dumps(profile.to_dict_for_db())
        self._db_execute_rec_engine(
            "INSERT OR REPLACE INTO user_profiles (user_id, profile_json, created_at_utc, updated_at_utc) VALUES (?, ?, ?, ?)",
            (profile.user_id, profile_json, profile.created_at_utc, profile.updated_at_utc),
            commit=True
        )
    
    # ... (update_user_preferences method would use its own DB for interactions and then save profile)


class RecommendationUI(ttk.Frame):
    # ... (Full implementation as in previous "Robust Similar Tracks" pass, including:
    #      __init__(parent, engine, host_app_ref, user_id)
    #      create_ui (with ForYou and Similar sections, status_label, loading_label)
    #      on_current_track_changed_for_similarity (subscribes to host event, fetches similar)
    #      _clear_foryou_recs_display, _clear_similar_tracks_display
    #      _display_foryou_recommendations, _display_similar_tracks
    #      _create_recommendation_card_ui (calls self.play_recommended_track)
    #      refresh_recommendations (for "For You", uses engine and AI_THREAD_POOL)
    #      play_recommended_track (calls self.host_app.request_playback_action)
    #      on_app_exit (unsubscribes from events)
    # This UI interacts heavily with HostAppInterface for playback and status updates.
    # It also directly uses its self.engine for recommendation/similarity calls.
    pass

# Integration function
def create_recommendation_tab(notebook: ttk.Notebook, host_app_ref: Any) -> Tuple[Optional[RecommendationEngine], Optional[RecommendationUI]]:
    rec_frame = ttk.Frame(notebook)
    notebook.add(rec_frame, text="Discover")
    
    engine: Optional[RecommendationEngine] = None
    ui: Optional[RecommendationUI] = None

    if host_app_ref.music_library_db_ref: # Prerequisite
        engine = RecommendationEngine(host_app_ref=host_app_ref) # Pass host_app_ref
        ui = RecommendationUI(rec_frame, engine, host_app_ref, user_id="default_user_main_profile") # Example user_id
        ui.pack(fill=tk.BOTH, expand=True)
        host_app_ref.recommendation_engine_ref = engine # Store engine on host if needed by other services
    else:
        ttk.Label(rec_frame, text="AI Recommendations (Requires Music Library to be initialized)").pack(padx=20,pady=20)
        logger.warning("Cannot initialize RecommendationEngine: Music Library DB not available via host_app.")
            
    return engine, ui # Return engine and UI frame