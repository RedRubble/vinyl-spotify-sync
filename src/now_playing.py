import logging
import sys
import numpy as np
import traceback
import signal
from typing import Tuple, Final, Optional

from logger import Logger
from config import Config
from state_manager import StateManager, PlayState

from service.song_identify_service import SongIdentifyService, SongInfo
from audio_processing_utils import AudioProcessingUtils
from service.audio_recording_service import AudioRecordingService
from service.music_detection_service import MusicDetectionService
from service.spotify_service import SpotifyService


class NowPlaying:
    AUDIO_DEVICE_SAMPLING_RATE: Final[int] = 44100
    AUDIO_DEVICE_NUMBER_OF_CHANNELS: Final[int] = 1
    AUDIO_RECORDING_DURATION_IN_SECONDS: Final[int] = 10
    SUPPORTED_SAMPLING_RATE_BY_MUSIC_DETECTION_MODEL: Final[int] = 16000
    NO_MUSIC_THRESHOLD: Final[int] = 4

    def __init__(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_exit)  # System or process termination
        signal.signal(signal.SIGINT, self._handle_exit)  # Ctrl+C termination

        self._config: dict = Config().get_config()
        self._logger: logging.Logger = Logger().get_logger()

        self._audio_recording_service: AudioRecordingService = AudioRecordingService(
            sampling_rate=NowPlaying.AUDIO_DEVICE_SAMPLING_RATE,
            channels=NowPlaying.AUDIO_DEVICE_NUMBER_OF_CHANNELS
        )
        self._music_detection_service: MusicDetectionService = MusicDetectionService(
            audio_duration_in_seconds=NowPlaying.AUDIO_RECORDING_DURATION_IN_SECONDS
        )
        self._song_identify_service: SongIdentifyService = SongIdentifyService()
        self._spotify_service: SpotifyService = SpotifyService()
        self._state_manager: StateManager = StateManager()

        self.set_idle_state()
        self._audio_buffer: Optional[np.ndarray] = None

        self._no_music_counter: int = 0

    def run(self) -> None:
        while True:
            try:
                audio, is_music_detected = self._record_audio_and_detect_music()

                if is_music_detected:
                    self._handle_music_detected(audio)
                else:
                    self._handle_no_music_detected()

            except Exception as e:
                self._logger.error(f"Error occurred: {e}")
                self._logger.error(traceback.format_exc())

    def _record_audio_and_detect_music(self) -> Tuple[np.ndarray, bool]:
        audio = self._audio_recording_service.record(
            duration=NowPlaying.AUDIO_RECORDING_DURATION_IN_SECONDS
        )
        resampled_audio = AudioProcessingUtils.resample(
            audio,
            source_sampling_rate=NowPlaying.AUDIO_DEVICE_SAMPLING_RATE,
            target_sampling_rate=NowPlaying.SUPPORTED_SAMPLING_RATE_BY_MUSIC_DETECTION_MODEL
        )
        is_music_detected = self._music_detection_service.is_music_detected(resampled_audio)

        # Build up a 10-second buffer by combining last two recordings
        if self._audio_buffer is None:
            self._audio_buffer = audio
        else:
            self._audio_buffer = np.concatenate((self._audio_buffer, audio))[
                                 -NowPlaying.AUDIO_DEVICE_SAMPLING_RATE * 10:]

        return audio, is_music_detected

    def _handle_music_detected(self, audio: np.ndarray) -> None:
        song_info = self._trigger_song_identify(audio)
        self._no_music_counter = 0
        self.stop_song_within_limit()

        if (self._state_manager.get_state().current != PlayState.PLAYING
                or self._state_manager.music_still_playing_but_different_song_identified(song_info.title)):
            self._state_manager.set_playing_state(song_info.title, song_info.artist)
            self.play_spotify()

    def stop_song_within_limit(self):
        if self._state_manager.get_state().current == PlayState.PLAYING:
            playback = self._spotify_service.get_current_playback()
            if playback and playback['is_playing'] and playback.get('item'):
                duration = playback['item']['duration_ms']
                progress = playback['progress_ms']
                # If song ends within 10 seconds, pause
                # We do this in order to not advance to the users queue that may or may not exist
                if duration - progress < 10000:
                    device_id = self._spotify_service.get_device_id(self._config['spotify']['device_name'])
                    self._spotify_service.pause_playback(device_id)
                    self._logger.debug(f"Song finishes within 10 seconds, pausing.")

    def _trigger_song_identify(self, audio: np.ndarray) -> SongInfo:
        int16_audio = AudioProcessingUtils.float32_to_int16(audio)
        wav_audio = AudioProcessingUtils.to_wav(
            int16_audio,
            sampling_rate=NowPlaying.AUDIO_DEVICE_SAMPLING_RATE
        )
        return self._song_identify_service.identify(wav_audio)

    def _handle_no_music_detected(self) -> None:
        self.stop_song_within_limit()
        if self._state_manager.get_state().current == PlayState.PLAYING:
            self._no_music_counter += 1

            if self._no_music_counter < (NowPlaying.NO_MUSIC_THRESHOLD + 1):
                self._logger.debug(
                    f"No music detected ({self._no_music_counter}/{NowPlaying.NO_MUSIC_THRESHOLD}), waiting before stopping.")
                return
            else:
                device_id = self._spotify_service.get_device_id(self._config['spotify']['device_name'])
                if device_id:
                    self._spotify_service.pause_playback(device_id)
                self._no_music_counter = 0
        self._audio_buffer = None

        if (self._state_manager.get_state().current == PlayState.STOPPED and
                self._state_manager.no_music_detected_for_more_than_a_minute()):
            self._state_manager.set_idle_state()
            self._spotify_service.restore_previous_session()

        if self._state_manager.get_state().current != PlayState.IDLE:
            self._state_manager.set_stopped_state()

    @staticmethod
    def _handle_exit(_sig, _frame):
        sys.exit(0)

    def set_idle_state(self) -> None:
        self._state_manager.set_idle_state()

    def play_spotify(self) -> None:
        try:
            if not self._state_manager.get_state().current == PlayState.PLAYING:
                return

            title = self._state_manager.get_playing_state().song_title
            artist = self._state_manager.get_playing_state().song_artist
            track = self._spotify_service.search_track(title, artist)
            device_id = self._spotify_service.get_device_id(self._config['spotify']['device_name'])

            if track:
                self._logger.debug(f"Sending track '{track.uri}' to Spotify on device '{device_id}'.")
                self._spotify_service.play_song(
                    uris=[track.uri],
                    device_id=device_id,
                    context_uri=track.context_uri,
                    offset=track.offset
                )

        except Exception as e:
            self._logger.error(f"Error occurred: {e}")
            self._logger.error(traceback.format_exc())


if __name__ == "__main__":
    service = NowPlaying()
    service.run()
