import traceback

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional
import logging

import sys
from time import sleep

sys.path.append("..")
from logger import Logger
from config import Config


class SpotifyService:
    def __init__(self):
        self._logger: logging.Logger = Logger().get_logger()
        self._config: dict = Config().get_config()
        self._saved_session = None
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self._config['spotify']['client_id'],
            client_secret=self._config['spotify']['client_secret'],
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="user-read-playback-state user-modify-playback-state user-read-currently-playing streaming user-read-playback-position",
            open_browser=False  # Important for headless mode
        ))

    def _save_session(self) -> None:
        playback = self.get_current_playback()
        if not playback or not playback.get('item'):
            return

        self._saved_session = {
            'device_id': playback['device']['id'],
            'shuffle_state': playback['shuffle_state'],
            'repeat_state': playback['repeat_state'],
        }
        self._logger.info(f"Saved session: {self._saved_session['device_id']}.")

    def restore_previous_session(self) -> None:
        if not self._saved_session:
            self._logger.debug("No previous session to restore.")
            return

        try:
            self.sp.shuffle(self._saved_session['shuffle_state'])
            self.sp.repeat(self._saved_session['repeat_state'])
            self.sp.next_track()
            self.sp.pause_playback()
            sleep(0.4)
            self.sp.transfer_playback(device_id=self._saved_session['device_id'],force_play=False)

            self._logger.info(f"Restored previous session to {self._saved_session['device_id']}")
            self._saved_session = None
        except Exception as e:
            self._logger.error(f"Failed to restore previous session: {e}")
            self._logger.error(traceback.format_exc())

    def search_track_uri(self, title: str, artist: str) -> Optional[str]:
        query = f"track:{title} artist:{artist}"
        self._logger.debug(f"Searching for track with query: {query}")

        try:
            results = self.sp.search(q=query, type="track", limit=1)
            tracks = results.get('tracks', {}).get('items', [])

            if tracks:
                track_uri = tracks[0]['uri']
                self._logger.info(f"Found track URI: {track_uri}")
                return track_uri

            self._logger.warning(f"No track found for '{title}' by '{artist}'.")
            return None
        except Exception as e:
            self._logger.error(f"Error searching for track '{title}' by '{artist}': {e}")
            return None

    def get_current_playback(self):
        return self.sp.current_playback()

    def play_song(self, uris, device_id) -> None:
        if device_id is None:
            self._logger.error("Cannot play track, given device name does not exist (device_id is None).")
            return

        playback = self.get_current_playback()
        position_ms = 1500

        if playback:
            current_device_id = playback['device']['id']
            is_playing = playback['is_playing']

            if is_playing and current_device_id != device_id:
                self._logger.error(
                    f"Failed to play track '{uris}' on device '{device_id}', another device '{playback['device']['name']}' is currently in use.")
                return

            if not is_playing and current_device_id != device_id:
                self._save_session()
                self.sp.transfer_playback(device_id, force_play=False)
                self._logger.info(f"Transferred playback from '{current_device_id}' to '{device_id}'.")
                sleep(0.4)

            # Resume from current position only if same track is loaded on the same device
            if playback.get('item') and playback['item']['uri'] in uris and current_device_id == device_id:
                position_ms = playback['progress_ms']

        try:
            self.sp.start_playback(device_id=device_id, uris=uris, position_ms=position_ms)
            self._logger.debug(f"Playing track '{uris}' on device '{device_id}' at position {position_ms}ms.")
        except Exception as e:
            self._logger.error(f"Failed to start playback: {e}")
            self._logger.error(traceback.format_exc())

    def get_devices(self):
        return self.sp.devices()

    def get_device_id(self, device_name):
        for device in self.get_devices()['devices']:
            if device['name'] == device_name:
                self._logger.debug(f"Found device called '{device_name}' with an ID of '{device['id']}'.")
                return device['id']
        self._logger.info(f"No devices were found with device name '{device_name}'.")
        return None

    def pause_playback(self, device_id):
        playback = self.get_current_playback()

        if playback['is_playing']:
            current_device_id = playback['device']['id']
            if current_device_id == device_id:
                self.sp.pause_playback(device_id)
                self._logger.info(f"Stopped playback on device: {device_id}.")
            else:
                self._logger.debug(f"Asked to pause playing on '{device_id}', however device is {current_device_id}.")
        else:
            self._logger.info(f"Asked to pause playback however nothing is playing.")
