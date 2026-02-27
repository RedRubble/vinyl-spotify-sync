import logging
import sys
import numpy as np
import traceback
import signal
from typing import Tuple, Final

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
    AUDIO_RECORDING_DURATION_IN_SECONDS: Final[int] = 5
    SUPPORTED_SAMPLING_RATE_BY_MUSIC_DETECTION_MODEL: Final[int] = 16000

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

        self.set_clean_state()

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
        return audio, is_music_detected

    def _handle_music_detected(self, audio: np.ndarray) -> None:
        song_info = self._trigger_song_identify(audio)
        if (
                song_info
                and (self._state_manager.get_state().current != PlayState.PLAYING
                     or self._state_manager.music_still_playing_but_different_song_identified(song_info.title))
        ):
            self._set_playing_state(song_info)

        self._state_manager.update_last_music_detected_time()

    def _trigger_song_identify(self, audio: np.ndarray) -> SongInfo:
        int16_audio = AudioProcessingUtils.float32_to_int16(audio)
        wav_audio = AudioProcessingUtils.to_wav(
            int16_audio,
            sampling_rate=NowPlaying.AUDIO_DEVICE_SAMPLING_RATE
        )
        return self._song_identify_service.identify(wav_audio)

    def _set_playing_state(self, song_info: SongInfo) -> None:
        self._state_manager.set_playing_state(song_info.title, song_info.artist)

    def _handle_no_music_detected(self) -> None:
        if (
                self._state_manager.get_state().current != PlayState.SCREENSAVER and self._state_manager.no_music_detected_for_more_than_a_minute()
        ):
            #TODO: Something with Spotify
            print("TODO")

    @staticmethod
    def _handle_exit(_sig, _frame):
        sys.exit(0)

    def set_clean_state(self) -> None:
        self._state_manager.set_clean_state()


if __name__ == "__main__":
    service = NowPlaying()
    service.run()
