import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Optional
import logging

import sys

sys.path.append("..")
from logger import Logger
from config import Config


class SpotifyService:
    def __init__(self):
        self._logger: logging.Logger = Logger().get_logger()
        self._config: dict = Config().get_config()
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=self._config['spotify']['client_id'],
            client_secret=self._config['spotify']['client_secret'],
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="user-read-playback-state user-modify-playback-state user-read-currently-playing streaming user-read-playback-position",
            open_browser=False  # Important for headless mode
        ))

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

    def add_to_playlist(self, track_uri: str) -> None:
        try:
            playlist_id = self._config['spotify']['playlist_id']
            self.sp.playlist_add_items(playlist_id, [track_uri])
            self._logger.info(f"Successfully added track '{track_uri}' to playlist '{playlist_id}'.")
        except Exception as e:
            self._logger.error(f"Failed to add track '{track_uri}' to playlist: {e}.")

    def get_current_playback(self):
        return self.sp.current_playback()

    def play_song(self, uris, device_id=None) -> None:
        playback = self.get_current_playback()
        if playback and playback['is_playing']:
            current_device_id = playback['device']['id']
            if current_device_id != device_id:
                self._logger.error(
                    f"Failed to play track '{uris}' to device '{playback['device']['name']} ({device_id})', another device is currently in use.")
                return
        # Don't restart song if already active song
        if playback and playback.get('item') and playback['item']['uri'] in uris:
            self.sp.start_playback(device_id=device_id, uris=uris, position_ms=playback['progress_ms'])
        else:
            self.sp.start_playback(device_id=device_id, uris=uris)

        self._logger.debug(f"Playing track '{uris}' on device '{device_id}'.")

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
            self._logger.debug(f"Asked to pause playback however nothing is playing.")
