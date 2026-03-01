import datetime
import logging
from enum import Enum
from typing import Optional
from dataclasses import dataclass

from logger import Logger


class PlayState(Enum):
    IDLE = 0
    PLAYING = 1
    STOPPED = 2
    UNKNOWN = 5


class StateData:
    pass


@dataclass(frozen=True)
class PlayingState(StateData):
    song_title: Optional[str] = None
    song_artist: Optional[str] = None


@dataclass(frozen=True)
class AppState:
    current: PlayState = PlayState.UNKNOWN
    data: Optional[StateData] = None


class StateManager:
    def __init__(self):
        self._logger: logging.Logger = Logger().get_logger()
        self._state: AppState = AppState()
        self._last_music_detected_time: Optional[datetime.datetime] = None

    def _set_state(self, new_state: PlayState, data: Optional[StateData]) -> None:
        old_state = self._state.current

        if old_state == new_state == PlayState.STOPPED and self._state.data == data:
            return

        self._state = AppState(
            current=new_state,
            data=data
        )
        self._logger.info(f"State changed from {old_state.name} to {new_state.name}.")

    def set_idle_state(self) -> None:
        self._set_state(PlayState.IDLE, None)

    def set_playing_state(self, song_title: str, song_artist: str) -> None:
        playing_state = PlayingState(song_title=song_title, song_artist=song_artist)
        self._set_state(PlayState.PLAYING, playing_state)

    def set_stopped_state(self) -> None:
        self._set_state(PlayState.STOPPED, None)

    def update_last_music_detected_time(self) -> None:
        self._last_music_detected_time = datetime.datetime.now()

    def no_music_detected_for_more_than_a_minute(self) -> bool:
        if self._last_music_detected_time is None:
            return True
        elapsed_time = datetime.datetime.now() - self._last_music_detected_time
        if elapsed_time >= datetime.timedelta(minutes=1):
            self._logger.info("No music detected for more than a minute.")
            return True
        return False

    def music_still_playing_but_different_song_identified(self, song_title: str):
        if self._state.current != PlayState.PLAYING:
            return False
        if self.get_playing_state().song_title != song_title:
            self._logger.info("Music still playing but new song identified.")
            return True
        self._logger.debug("Same song still playing.")
        return False

    def get_state(self) -> AppState:
        return self._state

    def get_playing_state(self) -> PlayingState:
        if self._state.current == PlayState.PLAYING and isinstance(self._state.data, PlayingState):
            return self._state.data
        raise RuntimeError("Attempted to access PlayingState while not in PLAYING state.")