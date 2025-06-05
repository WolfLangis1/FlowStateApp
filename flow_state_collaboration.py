"""
Flow State: Real-time Collaboration Module
Multi-user listening sessions, collaborative playlists, and social features
"""

import asyncio
import websockets
import json
import sqlite3
import threading
import queue # Not directly used, but can be for message passing if needed
import time
from datetime import datetime, timezone # Added timezone
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog # Added simpledialog
from pathlib import Path # For DB path
import hashlib
import secrets
import logging
import concurrent.futures

logger = logging.getLogger(__name__)

# Using module-specific pool for its DB operations if not using aiosqlite
COLLAB_DB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="CollabDB")
COLLAB_DB_PATH = str(Path.home() / ".flowstate" / "data" / "collaboration_engine_data.db")


@dataclass
class User: # As defined before
    user_id: str; username: str; display_name: str
    avatar_url: Optional[str] = None
    status: str = "online"
    current_session_id: Optional[str] = None
    # followers/following removed for simplicity in this core server, could be separate social service
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class Session: # As defined before
    session_id: str; name: str; host_id: str
    participants: List[str] = field(default_factory=list)
    playlist: List[Dict[str, Any]] = field(default_factory=list) # Each dict is track info
    current_track_index: int = -1 # -1 if no track selected/playing
    current_position_sec: float = 0.0 # Renamed from current_position
    is_playing: bool = False
    is_public: bool = True
    max_participants: int = 50
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    chat_enabled: bool = True
    collaborative_queue: bool = True # Can users other than host add tracks?
    voting_enabled: bool = True # Can users vote to skip?

@dataclass
class ChatMessage: # As defined before
    message_id: str; session_id: str; user_id: str; username: str; message: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message_type: str = "text"


class CollaborationServer: # As refined before
    # ... (Full implementation of __init__, _db_execute (now uses COLLAB_DB_PATH), db_action,
    #      _init_database, start, handle_connection, handle_authenticate, handle_message,
    #      all specific message handlers like handle_join_session, handle_create_session,
    #      handle_play_pause (server reacts to host command and broadcasts), handle_seek,
    #      handle_next_track (server logic for next based on its playlist), handle_add_track,
    #      handle_remove_track, handle_chat, handle_vote_skip, handle_sync_request,
    #      handle_user_disconnect, broadcast_to_session, send_to_connection, send_to_user,
    #      get_user_id_by_connection, save_session (to DB), save_chat_message, get_chat_history)
    # Key aspects for this pass:
    #  - All DB operations use `await self.db_action(...)`.
    #  - `handle_play_pause`, `handle_seek`, `handle_next_track` are initiated by the *host* client.
    #    The server updates its `Session` state and then broadcasts the new state to all clients.
    #    Non-host clients react to these broadcasted states to sync their local players.
    pass


class CollaborationClient: # As refined before
    # ... (Full implementation of __init__, connect (sends auth), disconnect, listen_for_messages,
    #      send_message, register_handler, and specific command methods like create_session,
    #      join_session, leave_session, play_pause (sends command to server), seek (sends command),
    #      add_track (sends track info), send_chat, vote_skip, request_sync) ...
    pass


class CollaborationUI(ttk.Frame):
    def __init__(self, parent: ttk.Widget, host_app_ref: Any):
        super().__init__(parent)
        self.host_app = host_app_ref
        self.root_app_tk = parent.winfo_toplevel() # Get root for dialog parenting

        # User identity from host_app (launcher should ensure these are set if collab is enabled)
        self.user_id = getattr(self.host_app, 'user_id_for_services', secrets.token_hex(8))
        self.username = getattr(self.host_app, 'username_for_services', f"User_{self.user_id[:4]}")
        
        self.client = CollaborationClient(server_url="ws://localhost:8765") # Configurable
        self._setup_client_event_handlers() # Renamed
        
        self.current_session_data: Optional[Dict] = None # Stores session dict from server
        self.participants_map: Dict[str, Dict] = {} # user_id -> user_dict
        self.is_host_of_session = False
        
        self.async_loop = asyncio.new_event_loop()
        self.async_thread = threading.Thread(target=self._run_async_loop_in_thread, daemon=True)
        self.async_thread.start()
        
        self._create_ui_widgets() # Renamed
        self.run_async(self._connect_and_log_status())


    async def _connect_and_log_status(self): # New helper for connect sequence
        logger.info(f"CollabUI: Attempting to connect as {self.username} ({self.user_id})")
        success = await self.client.connect(self.user_id, self.username)
        if success:
            self.after(0, lambda: self.host_app.update_status_bar(f"Collaboration: Connected as {self.username}."))
            # Optionally, fetch public session list here
        else:
            self.after(0, lambda: messagebox.showerror("Connection Error", "Failed to connect to collaboration server.", parent=self.host_app.root))
            self.after(0, lambda: self.host_app.update_status_bar("Collaboration: Connection failed."))


    def _run_async_loop_in_thread(self): # As before
        pass
    def run_async(self, coro): # As before
        pass # Assume previous robust implementation using self.async_loop

    def _setup_client_event_handlers(self): # Renamed
        self.client.register_handler('auth_success', self.on_auth_success)
        self.client.register_handler('auth_failed', self.on_auth_failed)
        self.client.register_handler('session_created', self.on_session_joined) # Server sends full session on create
        self.client.register_handler('session_joined', self.on_session_joined)
        self.client.register_handler('user_joined', self.on_user_joined)
        self.client.register_handler('user_left', self.on_user_left)
        self.client.register_handler('chat_message', self.on_chat_message_received) # Renamed
        self.client.register_handler('track_added', self.on_track_added_to_session) # Renamed
        self.client.register_handler('track_removed', self.on_track_removed_from_session)
        self.client.register_handler('playback_state', self.on_session_playback_state_changed) # Renamed
        self.client.register_handler('track_changed', self.on_session_track_changed) # Server tells new track
        self.client.register_handler('seek', self.on_session_seek) # Server confirms seek
        self.client.register_handler('skip_vote_update', self.on_skip_vote_update)
        self.client.register_handler('host_changed', self.on_host_changed)
        self.client.register_handler('error', self.on_server_error) # Generic error from server

    def _create_ui_widgets(self): # Renamed
        # ... (Full UI layout as in "UI Polish" pass: main_paned, left_panel with session controls,
        #      self.host_controls_frame (initially not packed), session_info label, participants_list,
        #      center_panel with queue_frame, queue_controls (Add Track, Vote Skip), queue_tree,
        #      right_panel with chat_frame, chat_display, chat_input) ...
        # Ensure host_controls_frame buttons call new methods:
        # self.host_play_button.config(command=self.host_ui_action_play_pause)
        # Add self.host_next_button, self.host_prev_button
        pass

    # --- UI Action Handlers ---
    def create_session_dialog(self): # As before, calls self.run_async(self.client.create_session(...))
        pass
    def join_session_dialog(self): # As before, calls self.run_async(self.client.join_session(...))
        pass
    def leave_session(self): # As before, calls self.run_async(self.client.leave_session()), resets UI state
        if self.current_session_data:
            self.run_async(self.client.leave_session())
            self.current_session_data = None # Clear local state immediately
            self.participants_map.clear()
            self.is_host_of_session = False
            self.after(0, self._update_session_ui_display) # Use renamed method
            self.host_app.update_status_bar("Left collaboration session.")

    def add_track_to_session_dialog(self): # Renamed from add_track_dialog
        # ... (as refined in "UI Polish" pass, using host_app.request_library_action to get track info,
        #      then self.run_async(self.client.add_track(collab_track_info))) ...
        pass
    
    def vote_to_skip_track(self): # Renamed
        if self.current_session_data: self.run_async(self.client.vote_skip())

    def send_chat_message_from_ui(self): # Renamed
        # ... (gets message from self.chat_input, then self.run_async(self.client.send_chat(message))) ...
        pass

    # --- Host-Specific UI Action Handlers ---
    def host_ui_action_play_pause(self):
        if not self.is_host_of_session or not self.current_session_data or not self.host_app.audio_engine_ref:
            return
        
        # The host's action dictates the session's state.
        # Get the current state of the *session's track* from the host's local player if it's playing that track.
        # This is complex if host is listening to something else locally.
        # Simplification: Assume if host controls session, their local player *should* be playing the session track.
        
        # Let's assume the server's current_session_data.is_playing is the source of truth to toggle.
        new_target_play_state = not self.current_session_data.get('is_playing', False)
        
        # Position should be what the host's local player is currently at for *this session's track*
        # If host's player is playing a *different* track, this logic is flawed.
        # For now, use the session's last known position for the command to server.
        # The server will broadcast, and host's player will also sync to that if needed.
        session_pos = self.current_session_data.get('current_position_sec', 0.0)

        logger.info(f"CollabUI (Host): UI action play/pause. New session target: {'Play' if new_target_play_state else 'Pause'} at {session_pos:.2f}s")
        self.run_async(self.client.play_pause(new_target_play_state, session_pos))
        # UI button text updates will happen when on_session_playback_state_changed is received from server.

    def host_ui_action_next_track(self):
        if not self.is_host_of_session or not self.current_session_data: return
        logger.info("CollabUI (Host): UI action next track for session.")
        self.run_async(self.client.next_track()) # Server finds next track and broadcasts

    def host_ui_action_seek_session(self, new_position_sec: float): # Called by a seek bar/slider for host
        if not self.is_host_of_session or not self.current_session_data: return
        logger.info(f"CollabUI (Host): UI action seek session to {new_position_sec:.2f}s")
        self.run_async(self.client.seek(new_position_sec))


    # --- Client Event Handlers (from CollaborationClient, called via self.after(0,...)) ---
    def on_auth_success(self, data: Dict): self.after(0, lambda d=data: self._handle_auth_success(d))
    def _handle_auth_success(self, data: Dict): logger.info(f"CollabUI: Auth success: {data}"); # Optionally fetch public sessions
    
    def on_auth_failed(self, data: Dict): self.after(0, lambda d=data: self._handle_auth_failed(d))
    def _handle_auth_failed(self, data: Dict): logger.error(f"CollabUI: Auth failed: {data.get('reason')}"); messagebox.showerror("Auth Failed", data.get('reason','Unknown error'), parent=self.host_app.root)

    def on_session_joined(self, data: Dict): self.after(0, lambda d=data: self._handle_session_joined(d))
    def _handle_session_joined(self, data: Dict): # Handles both session_created and session_joined
        self.current_session_data = data['session']
        self.participants_map = {p['user_id']: p for p in data.get('participants', []) if 'user_id' in p}
        self.is_host_of_session = (self.user_id == self.current_session_data.get('host_id'))
        self._update_session_ui_display()
        self._add_chat_message_to_display({'username': 'System', 'message': f"Joined session: {self.current_session_data['name']}", 'message_type': 'system'})
        self.host_app.update_status_bar(f"Joined session: {self.current_session_data['name']}")
        # Initial sync request after joining might be good
        self.run_async(self.client.request_sync())


    def on_user_joined(self, data: Dict): self.after(0, lambda d=data: self._handle_user_joined(d))
    def _handle_user_joined(self, data: Dict): # ... (update participants_map, UI, chat message) ...
        pass
    def on_user_left(self, data: Dict): self.after(0, lambda d=data: self._handle_user_left(d))
    def _handle_user_left(self, data: Dict): # ... (update participants_map, UI, chat message) ...
        pass
        
    def on_chat_message_received(self, data: Dict): self.after(0, lambda d=data: self._add_chat_message_to_display(d['message']))
    def _add_chat_message_to_display(self, message_dict: Dict): # As before
        pass

    def on_track_added_to_session(self, data: Dict): self.after(0, lambda d=data: self._handle_track_added(d))
    def _handle_track_added(self, data: Dict): # ... (update self.current_session_data['playlist'], UI queue, chat) ...
        pass
    def on_track_removed_from_session(self, data: Dict): self.after(0, lambda d=data: self._handle_track_removed(d))
    def _handle_track_removed(self, data: Dict): # ... (update self.current_session_data['playlist'], UI queue, chat) ...
        pass

    def on_session_playback_state_changed(self, data: Dict): self.after(0, lambda d=data: self._handle_session_playback_state_changed(d))
    def _handle_session_playback_state_changed(self, data: Dict): # Renamed from on_playback_state
        # ... (Logic as in previous "Host Controls & Client Sync" pass:
        #      - Update self.current_session_data with new play state, position, track_index.
        #      - If self.is_host_of_session, update host play/pause button text.
        #      - If NOT host, call self.host_app.request_playback_action("force_sync_playback", ...)
        #        to make local player mirror this new session master state.
        #        This requires "force_sync_playback" to be robustly implemented in FlowStateApp/AudioEngine.
        # )
        pass

    def on_session_track_changed(self, data: Dict): self.after(0, lambda d=data: self._handle_session_track_changed(d))
    def _handle_session_track_changed(self, data: Dict):
        # Server indicates the session's current track has changed.
        # data should contain 'track_index' and 'track' (info of new track).
        # Update self.current_session_data['current_track_index'] and ['current_position_sec'] = 0.0
        # Update UI queue to highlight new track.
        # Non-hosts will then sync to this new track via on_session_playback_state_changed if it also includes play state.
        # Or, this event itself can trigger the sync.
        logger.info(f"CollabUI: Session track changed to index {data.get('track_index')}")
        # ... (update UI queue highlight) ...
        # If this client is NOT host, immediately try to sync to the new track (paused at 0)
        # The subsequent 'playback_state' event will handle actual play/pause and position.
        # This pre-loads the track for non-hosts.
        # if self.host_app and self.current_session_data and self.user_id != self.current_session_data.get('host_id'):
        #     new_track_info = data.get('track')
        #     if new_track_info and 'track_id_lib' in new_track_info:
        #         self.host_app.request_playback_action("force_sync_playback", {
        #             'library_track_id': int(new_track_info['track_id_lib']),
        #             'position_seconds': 0.0,
        #             'is_playing_target': False # Load paused, wait for play state msg
        #         })
        pass

    def on_session_seek(self, data: Dict): self.after(0, lambda d=data: self._handle_session_seek(d))
    def _handle_session_seek(self, data: Dict): # Server confirms/broadcasts a seek
        # ... (Similar to on_session_playback_state_changed, focuses on position update)
        # Update self.current_session_data['current_position_sec'].
        # Non-hosts sync their local player to this new position.
        pass

    def on_skip_vote_update(self, data: Dict): self.after(0, lambda d=data: self._update_skip_vote_button(d))
    def _update_skip_vote_button(self, data: Dict): # ... (updates self.skip_button text) ...
        pass
    def on_host_changed(self, data: Dict): self.after(0, lambda d=data: self._handle_host_changed(d))
    def _handle_host_changed(self, data: Dict): # ... (update self.is_host_of_session, UI, chat) ...
        pass
    def on_server_error(self, data: Dict): self.after(0, lambda d=data: self._handle_server_error(d))
    def _handle_server_error(self, data: Dict): # ... (show messagebox) ...
        pass

    def _update_session_ui_display(self): # Renamed from update_session_display
        # ... (Full UI update logic based on self.current_session_data, self.participants_map, self.is_host_of_session)
        # This includes packing/unpacking self.host_controls_frame.
        pass

    def on_app_exit(self): # As refined before
        pass

# create_collaboration_tab as refined before, ensures host_app_ref passed to CollaborationUI