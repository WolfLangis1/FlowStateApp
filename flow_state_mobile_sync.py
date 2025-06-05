"""
Flow State: Mobile Sync & Remote Control
Control your music from any device with real-time synchronization
"""

import asyncio
import websockets # Used by aiohttp.web.WebSocketResponse implicitly
import aiohttp
from aiohttp import web
import qrcode
import socket
import json
import sqlite3 # SecurityManager might use it for persistent pairing tokens if not in memory
import secrets
import hashlib
from jose import jwt, JWTError # Using python-jose for JWT
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Any, Callable
import threading
# import queue # Not directly used in this version's MobileServer
import os
import base64
from dataclasses import dataclass, asdict, field
import netifaces # For getting local IP
import zeroconf # For service discovery
from cryptography.fernet import Fernet # For encrypting paired devices storage on disk
import logging
import concurrent.futures # For offloading blocking tasks if any
from pathlib import Path

logger = logging.getLogger(__name__)

# Module-specific thread pool if any blocking operations were needed by server logic
# For now, aiohttp is async, and DB ops for security are light.
# SYNC_MOBILE_DB_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="MobileSyncDB")

# Consistent path for app data
APP_DATA_BASE_PATH = Path.home() / ".flowstate"
MOBILE_SYNC_DATA_DIR = APP_DATA_BASE_PATH / "mobile_sync_data"
SECURITY_KEY_PATH = MOBILE_SYNC_DATA_DIR / "mobile_sync_encryption.key" # Specific name
PAIRED_DEVICES_PATH = MOBILE_SYNC_DATA_DIR / "paired_devices_mobile.json" # Specific name


@dataclass
class Device: # As defined before
    device_id: str; device_name: str; device_type: str; platform: str; app_version: str
    last_seen_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat()) # Renamed and UTC
    is_paired: bool = False
    capabilities: List[str] = field(default_factory=list)

@dataclass
class RemoteCommand: # As defined before
    command_id: str; device_id: str; command: str; params: Dict
    timestamp_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat()) # Renamed and UTC
    status: str = "pending"


class SecurityManager: # As refined before
    def __init__(self, app_name: str = "FlowStateMobileSync"):
        self.app_name = app_name
        MOBILE_SYNC_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self.jwt_secret = secrets.token_urlsafe(32)
        # Stores PIN -> (temp_server_id_for_pairing, expiry_utc_datetime)
        self.active_pairing_pins: Dict[str, Tuple[str, datetime]] = {}
        # Stores actual_device_id -> {name, paired_at_utc}
        self.paired_devices_info: Dict[str, Dict[str, str]] = self._load_paired_devices_info()

    def _get_or_create_encryption_key(self) -> bytes: # As before
        pass
    def _load_paired_devices_info(self) -> Dict[str, Dict[str,str]]: # As before
        pass
    def _save_paired_devices_info(self): # As before
        pass

    def generate_pin_for_desktop_display(self, temp_desktop_pairing_id: str) -> str:
        """Desktop calls this to get a PIN to show. Associates PIN with temp_desktop_id."""
        pin = "".join(secrets.choice("0123456") for _ in range(6)) # Avoid ambiguous chars like 8,9,0,I,O,1,l
        expiry = datetime.now(timezone.utc) + timedelta(minutes=5)
        self.active_pairing_pins[pin] = (temp_desktop_pairing_id, expiry)
        logger.info(f"SecurityManager: Generated PIN {pin} for temp_desktop_id {temp_desktop_pairing_id}, expires {expiry.isoformat()}")
        return pin

    def verify_pin_from_mobile(self, pin_entered_on_mobile: str, temp_desktop_id_from_mobile: str) -> bool:
        """Mobile client presents PIN and temp_desktop_id. Server verifies."""
        pin_info = self.active_pairing_pins.get(pin_entered_on_mobile)
        if pin_info:
            original_temp_desktop_id, expiry_utc = pin_info
            if datetime.now(timezone.utc) < expiry_utc:
                if original_temp_desktop_id == temp_desktop_id_from_mobile:
                    return True # PIN valid for this temp_desktop_id and not expired
                else: logger.warning(f"PIN {pin_entered_on_mobile} valid, but temp_desktop_id mismatch.")
            else: logger.warning(f"PIN {pin_entered_on_mobile} expired."); del self.active_pairing_pins[pin_entered_on_mobile]
        return False

    def confirm_device_pairing(self, actual_mobile_device_id: str, mobile_device_name: str, verified_pin: str) -> bool:
        # This is called after verify_pin_from_mobile returns True
        if verified_pin in self.active_pairing_pins: # Pin should still be active
            self.paired_devices_info[actual_mobile_device_id] = {
                'name': mobile_device_name,
                'paired_at_utc': datetime.now(timezone.utc).isoformat(),
            }
            self._save_paired_devices_info()
            del self.active_pairing_pins[verified_pin] # Clean up used PIN
            logger.info(f"SecurityManager: Device {actual_mobile_device_id} ('{mobile_device_name}') paired using PIN {verified_pin}.")
            return True
        logger.warning(f"SecurityManager: Attempted to confirm pairing for PIN {verified_pin} which is no longer active/valid.")
        return False

    def is_device_paired(self, device_id: str) -> bool: # As before
        return device_id in self.paired_devices_info
    def generate_auth_token(self, device_id: str) -> str: # As before
        pass
    def verify_auth_token(self, token: str) -> Optional[str]: # As before
        pass


class MobileServer: # As refined before
    def __init__(self, host_address: str = "0.0.0.0", port_number: int = 8888,
                 host_app_interface: Optional[Any] = None): # Takes HostAppInterface
        self.host = host_address
        self.port = port_number
        self.host_app = host_app_interface # Store HostAppInterface
        self.app = web.Application(middlewares=[self._auth_middleware]) # Add middleware at app creation
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self.security = SecurityManager()
        self.authed_websockets: Dict[str, web.WebSocketResponse] = {}
        self.player_state: Dict[str, Any] = { 'is_playing': False, 'current_track': None, 'volume': 0.7, 'is_muted': False, 'duration':0, 'position':0, 'playlist':[], 'current_index':-1 }
        self.setup_routes()
        self.zeroconf_handler: Optional[zeroconf.Zeroconf] = None # Correct type hint
        self.service_info: Optional[zeroconf.ServiceInfo] = None
        # UI Callbacks (set by RemoteControlUI instance)
        self.ui_pair_success_callback: Optional[Callable[[str,str],None]] = None
        self.ui_display_pin_for_pairing_callback : Optional[Callable[[str,str],None]] = None # pin, temp_desktop_id

    # ... (_db_execute_sync, db_action if server has its own DB, now less likely) ...

    def setup_routes(self): # As before, ensure paths are correct
        # Static files for web interface (if any)
        # web_interface_path = Path(__file__).parent / "web_interface_mobile"
        # if web_interface_path.is_dir():
        #     self.app.router.add_static('/ui/', path=str(web_interface_path), name='mobile_ui')
        #     self.app.router.add_get('/', lambda r: web.HTTPFound('/ui/index.html')) # Redirect root to index

        self.app.router.add_get('/api/info', self.handle_info)
        self.app.router.add_post('/api/request-pairing-pin', self.handle_request_pairing_pin_from_desktop_ui) # Desktop UI calls this
        self.app.router.add_post('/api/submit-pin-for-pairing', self.handle_submit_pin_from_mobile) # Mobile client calls this
        self.app.router.add_get('/api/state', self.handle_get_state) # Needs auth
        self.app.router.add_post('/api/command', self.handle_command) # Needs auth
        self.app.router.add_get('/api/library/browse', self.handle_library_browse) # Needs auth, placeholder
        # self.app.router.add_get('/api/artwork/{track_id}', self.handle_artwork) # Needs auth
        self.app.router.add_get('/ws', self.handle_websocket) # WS connection also needs auth via first message
        self.app.router.add_get('/api/qr-code-info', self.handle_qr_code_info_for_mobile) # Provides info for mobile to connect

    async def _auth_middleware(self, app, handler): # As refined before
        async def middleware(request: web.Request):
            # Bypass auth for pairing initiation by desktop, PIN submission by mobile, info, QR
            if request.path in ['/api/request-pairing-pin', '/api/submit-pin-for-pairing', '/api/info', '/api/qr-code-info'] or \
               request.path.startswith('/ui/'): # Allow access to static UI files
                return await handler(request)
            # WebSocket auth is handled in its own handler after connection
            if request.path == '/ws': return await handler(request)

            auth_header = request.headers.get('Authorization')
            # ... (token verification as before, sets request['device_id']) ...
            if not auth_header or not auth_header.startswith('Bearer '): return web.json_response({'error': 'Unauthorized: Missing token'}, status=401)
            token = auth_header.split(" ", 1)[1]
            device_id = self.security.verify_auth_token(token)
            if not device_id: return web.json_response({'error': 'Unauthorized: Invalid or expired token'}, status=401)
            request['device_id'] = device_id
            return await handler(request)
        return middleware


    async def handle_request_pairing_pin_from_desktop_ui(self, request: web.Request) -> web.Response:
        """Desktop UI calls this to get a new PIN to display."""
        temp_desktop_pairing_id = secrets.token_hex(8) # Desktop generates a temp ID for this pairing attempt
        pin = self.security.generate_pin_for_desktop_display(temp_desktop_pairing_id)
        logger.info(f"MobileServer: Generated PIN {pin} for Desktop UI (temp_id: {temp_desktop_pairing_id})")
        # This PIN and temp_desktop_pairing_id are for the QR code / manual entry.
        # The desktop UI will display this PIN.
        # No need to call self.ui_display_pin_for_pairing_callback here as this IS the desktop UI's request.
        # It returns the PIN and temp_id for the desktop UI to use.
        return web.json_response({'pin': pin, 'temp_server_id': temp_desktop_pairing_id, 'expires_in_seconds': 300})


    async def handle_submit_pin_from_mobile(self, request: web.Request) -> web.Response:
        """Mobile client submits PIN (it got from desktop display/QR) and its own device details."""
        data = await request.json()
        pin_from_mobile = data.get('pin')
        temp_desktop_id_from_mobile = data.get('temp_server_id') # The temp ID desktop generated
        actual_mobile_device_id = data.get('mobile_device_id') # Mobile's persistent ID
        mobile_device_name = data.get('mobile_device_name')

        if not all([pin_from_mobile, temp_desktop_id_from_mobile, actual_mobile_device_id, mobile_device_name]):
            return web.json_response({'error': 'Missing required pairing fields'}, status=400)

        if self.security.verify_pin_from_mobile(pin_from_mobile, temp_desktop_id_from_mobile):
            if self.security.confirm_device_pairing(actual_mobile_device_id, mobile_device_name, pin_from_mobile):
                auth_token = self.security.generate_auth_token(actual_mobile_device_id)
                if self.ui_pair_success_callback: # Notify desktop UI
                    self._schedule_on_main_thread(self.ui_pair_success_callback, actual_mobile_device_id, mobile_device_name)
                return web.json_response({'status': 'paired', 'device_id': actual_mobile_device_id, 'auth_token': auth_token})
            else: return web.json_response({'error': 'Pairing confirmation failed'}, status=500)
        else: return web.json_response({'error': 'Invalid or expired PIN/ID'}, status=403)

    async def handle_qr_code_info_for_mobile(self, request: web.Request) -> web.Response:
        """Provides info for a QR code to be displayed on desktop, for mobile to scan."""
        # This is similar to handle_request_pairing_pin_from_desktop_ui, but called via GET if QR displayed constantly.
        # It should generate a new pairing session (PIN + temp_desktop_id).
        temp_desktop_pairing_id = secrets.token_hex(8)
        pin = self.security.generate_pin_for_desktop_display(temp_desktop_pairing_id)
        ip_addr = self.get_local_ip()
        url_base = f"http://{ip_addr}:{self.port}" # Server's base URL
        
        qr_data_content = {
            "server_url_base": url_base, # Mobile connects to this
            "api_pair_submit_endpoint": "/api/submit-pin-for-pairing", # Endpoint mobile calls
            "temp_server_id": temp_desktop_pairing_id, # Desktop's temp ID for this attempt
            "pin_to_enter_on_mobile": pin # The PIN mobile needs to include in its submission
        }
        # The QR code itself would typically encode a URL that contains some of this, or just this JSON.
        # For example, a custom URL scheme: flowstate-pair://<base64_encoded_json_qr_data_content>
        # Or just display the JSON for the mobile app to parse after scanning a generic QR of this JSON.
        return web.json_response(qr_data_content)


    def _schedule_on_main_thread(self, callable_to_run: Callable, *args):
        """Helper to schedule a function call on the main Tkinter thread if host_app has root."""
        if self.host_app and hasattr(self.host_app, 'root') and self.host_app.root:
            self.host_app.root.after(0, callable_to_run, *args)
        else: # Fallback if no root access, run directly (might be risky if callable updates UI)
            try: callable_to_run(*args)
            except Exception as e: logger.error(f"Error in _schedule_on_main_thread fallback: {e}")

    # ... (start, service discovery, get_local_ip, handle_info, handle_get_state,
    #      handle_websocket (auth via first message), handle_command (uses self.host_app.request_playback_action),
    #      broadcast_state_update, update_player_state_from_host as refined before) ...

    async def handle_library_browse(self, request: web.Request) -> web.Response: # Placeholder
        device_id = request['device_id'] # Authenticated
        path_param = request.query.get('path', '/') # e.g., /artists, /artists/SomeArtist, /albums
        logger.info(f"Device {device_id} requested library browse at path: {path_param}")

        if not self.host_app or not self.host_app.music_library_db_ref:
            return web.json_response({'error': 'Library service not available'}, status=503)

        # This needs to be an async call to host_app.request_library_action
        # loop = asyncio.get_running_loop()
        # library_data = await loop.run_in_executor(SYNC_DB_EXECUTOR, # Example if it were sync
        #     self.host_app.music_library_db_ref.browse_path, path_param)
        
        # Correct way: use HostAppInterface's async request method
        # This requires request_library_action in HostApp to be awaitable or use a callback
        # Let's assume request_library_action is a normal function that internally uses a thread pool
        # and we can make this handler await its completion if needed, or return a "processing" response.
        # For a simple REST API, it's better if the host_app action is awaitable itself.
        # For now, let's mock a direct (potentially blocking) call for simplicity in this handler.
        # THIS IS A SIMPLIFICATION - a real app would use await with an async host_app method.
        browse_result = []
        if path_param == "/artists":
            # artists_list = self.host_app.request_library_action("get_all_artists") # This is sync
            # browse_result = [{'id': art_obj.id, 'name': art_obj.name, 'type': 'artist'} for art_obj in artists_list or []]
            browse_result = [{'id':'art1', 'name':'Artist One', 'type':'artist'}, {'id':'art2', 'name':'Artist Two', 'type':'artist'}] # Mock
        elif path_param == "/albums":
            browse_result = [{'id':'alb1', 'name':'Album X', 'artist':'Artist One', 'type':'album'}] # Mock
        else:
            browse_result = {'error': 'Path not implemented for browse'}
            return web.json_response(browse_result, status=404)

        return web.json_response({'path': path_param, 'items': browse_result})


class RemoteControlUI(ttk.Frame): # As refined before
    # ... (__init__(parent, host_app_ref)
    #      create_ui (with desktop_pin_var display)
    #      handle_remote_command (calls host_app.request_playback_action)
    #      start_server (creates MobileServer, passes callbacks)
    #      _run_server_in_thread
    #      stop_server
    #      update_server_display_info (CALLS server_instance.security.generate_pin_for_desktop_display)
    #      generate_qr_code_image (gets data from server_instance.handle_qr_code_info_for_mobile - needs server method)
    #      update_paired_devices_list (uses server_instance.security.paired_devices_info)
    #      on_device_paired_ui_update (callback from MobileServer)
    #      _subscribe_to_host_events_for_remote, on_host_playback_state_changed, on_host_volume_changed
    #      on_app_exit (calls self.stop_server)
    # )
    # Ensure MobileServer instance created in start_server gets ui_pair_success_callback correctly set.
    def __init__(self, parent: ttk.Widget, host_app_ref: Any):
        super().__init__(parent)
        self.host_app = host_app_ref
        self.server_instance: Optional[MobileServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.server_loop: Optional[asyncio.AbstractEventLoop] = None
        
        self.desktop_pin_var = tk.StringVar(value="----") # PIN displayed on this Desktop UI
        # ... other vars ...
        self.create_ui() # This will create self.ip_label etc.
        self.update_ip_address_display() # Initial IP display
        self._subscribe_to_host_events_for_remote()

    def start_server(self):
        if self.server_thread and self.server_thread.is_alive(): return
        self.server_loop = asyncio.new_event_loop()
        self.server_instance = MobileServer(
            host_app_interface=self.host_app # Pass host_app to server
        )
        # Set UI callbacks on the server instance
        self.server_instance.ui_pair_success_callback = self.on_device_paired_ui_update
        # self.server_instance.ui_display_pin_for_pairing_callback = self.display_desktop_pin_for_pairing # Not needed if desktop requests PIN from server
        
        self.server_thread = threading.Thread(target=self._run_server_in_thread, daemon=True)
        self.server_thread.start()
        # ... (update UI buttons, status as before) ...
        self.after(1000, self.refresh_pairing_info_from_server) # Get initial PIN/QR info

    def refresh_pairing_info_from_server(self):
        """Requests a new PIN from the server and updates QR code."""
        if not self.server_instance or not self.server_instance._loop or not self.server_instance._loop.is_running():
            self.desktop_pin_var.set("SERVER OFF")
            self.qr_label.config(image='', text="Server not running to get QR info.")
            return

        async def _get_qr_info_and_update_ui():
            try:
                # This is an HTTP request to our own server, but from the UI thread's perspective.
                # It should be non-blocking for UI.
                # For simplicity, we are calling an async method that will run in server's loop.
                # This needs to be structured carefully.
                # The QR info endpoint on server is simple GET, so direct request is okay.
                # A better way for desktop UI to get PIN: Call a direct method on self.server_instance
                # that generates it internally, if UI and server are in same process.
                # Here, QR info endpoint provides PIN + temp_server_id.

                # This is tricky: Desktop UI asking its own server for pairing info.
                # Let's make server's SecurityManager generate PIN and temp_id on demand from UI.
                temp_desktop_id = secrets.token_hex(8)
                pin = self.server_instance.security.generate_pin_for_desktop_display(temp_desktop_id)
                
                self.after(0, self.desktop_pin_var.set, pin) # Update UI var
                
                ip_addr = self.server_instance.get_local_ip()
                url_base = f"http://{ip_addr}:{self.server_instance.port}"
                qr_data_content = {
                    "server_url_base": url_base,
                    "api_pair_submit_endpoint": "/api/submit-pin-for-pairing",
                    "temp_server_id": temp_desktop_id,
                    "pin_to_enter_on_mobile": pin
                }
                self.after(0, self.generate_qr_code_image, qr_data_content)
            except Exception as e:
                logger.error(f"Error refreshing pairing info from server: {e}")
                self.after(0, self.desktop_pin_var.set, "ERROR")

        # Schedule this async task on the server's loop if possible, or run sync if method is safe
        # For now, direct call to security manager and then UI update.
        # This is safe because this method (refresh_pairing_info...) is called via self.after from UI thread.
        if self.server_instance and self.server_instance.security:
            temp_desktop_id = secrets.token_hex(8)
            pin = self.server_instance.security.generate_pin_for_desktop_display(temp_desktop_id)
            self.desktop_pin_var.set(pin)
            
            ip_addr = self.server_instance.get_local_ip()
            url_base = f"http://{ip_addr}:{self.server_instance.port}"
            qr_data_content = {"server_url_base": url_base, "api_pair_submit_endpoint": "/api/submit-pin-for-pairing",
                               "temp_server_id": temp_desktop_id, "pin_to_enter_on_mobile": pin}
            self.generate_qr_code_image(qr_data_content)
        self.update_paired_devices_list() # Refresh list of already paired devices


    # ... (rest of RemoteControlUI as refined previously) ...


# create_remote_control_tab as before