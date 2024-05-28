import datetime
import os
import random
import re
from pathlib import Path
from typing import Optional

from pydub import AudioSegment, effects  # type: ignore

from .game import Game
from .utils import load_json_resource
from .weather import Weather

try:
    MUSIC_DIR = os.environ["KKJUKEBOX_MUSIC_DIR"]
except KeyError:
    raise RuntimeError(f"KKJUKEBOX_MUSIC_DIR must be set")


class Song:

    filepath: Path

    def __init__(self, filepath: str | Path) -> None:
        self.filepath = Path(filepath)
        if not self.filepath.is_file():
            raise FileNotFoundError(f'Song file not found at "{self.filepath}"')

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.filename})"

    @property
    def filename(self) -> str:
        return self.filepath.name

    def _make_loop_files(
        self, path: Path, loop_timing: dict[str, str], force_cut: bool = False
    ) -> tuple[str, str]:
        if not path.is_file():
            raise FileNotFoundError(f"No file at {path}")

        filetype = path.suffix.strip(".")
        loops_dir = f"{path.parent}/loops"
        start_filename = f"{path.stem}-start.{filetype}"
        loop_filename = f"{path.stem}-loop.{filetype}"
        start_filepath = f"{loops_dir}/{start_filename}"
        loop_filepath = f"{loops_dir}/{loop_filename}"

        if (
            not (Path(start_filepath).is_file() and Path(loop_filepath).is_file())
            or force_cut
        ):
            print("Start and/or Loop files not found. Cutting now...")

            loop_start_ms = float(loop_timing["start"]) * 1000
            loop_end_ms = float(loop_timing["end"]) * 1000

            original = AudioSegment.from_file(path)

            print(f"Making start and loop tracks for {path}")
            print(f"Original track is {len(original)/1000}s")
            print(f"Cutting loop from {loop_start_ms/1000} to {loop_end_ms/1000}")
            start = effects.normalize(original[:loop_end_ms])  # type: ignore
            loop = effects.normalize(original[loop_start_ms:loop_end_ms])  # type: ignore
            print(f"Start file is {len(start)/1000}s")
            print(f"Loop file is {len(loop)/1000}s")

            try:
                os.mkdir(loops_dir)
            except FileExistsError:
                pass

            start.export(start_filepath, format=filetype, parameters=["-aq", "3"])
            loop.export(loop_filepath, format=filetype, parameters=["-aq", "3"])
        return start_filepath, loop_filepath


class HourlySong(Song):

    hour: int
    game: Game
    weather: Weather

    def __init__(self, hour: int, game: Game, weather: Weather) -> None:
        if hour < 0 or hour > 23:
            raise ValueError(f"Hour must be between 0 and 23")
        self.hour = hour
        self.game = Game(game)
        self.weather = Weather(weather)

        if self.game is Game.ANIMAL_CROSSING and self.weather is Weather.RAINING:
            # dumb hack for single raining track in AC, don't want to dupe files
            self.hour = 0

        song_dir = Path(os.path.join(MUSIC_DIR, game, weather))
        if not song_dir.is_dir():
            raise OSError(f'Directory "{song_dir}" not found.')

        hour_match = str(self.hour).zfill(2)
        matching_songs = [f for f in song_dir.iterdir() if hour_match in f.name]
        if not matching_songs:
            raise OSError(f'No file found containing "{self.hour}"')
        elif len(matching_songs) > 1:
            raise OSError(f'Multiple files found for "{self.hour}"')

        super().__init__(matching_songs[0])

    @property
    def _hour_fill(self) -> str:
        return str(self.hour).zfill(2)

    def make_loop_files(self, force_cut: bool = False) -> tuple[str, str]:
        hour_path = self.filepath
        hour_str = self._hour_fill

        loop_times = load_json_resource("hour_loop_times.json")
        song_loop_time = loop_times[self.game][self.weather][hour_str]
        return self._make_loop_files(hour_path, song_loop_time, force_cut)


class KKSong(Song):

    base_music_dir: Path = Path(f"{MUSIC_DIR}/kk")
    name: str
    version: str

    @classmethod
    def from_fuzzy_name(cls, song_name: str, version: str) -> Optional["KKSong"]:
        all_song_names = cls.all_song_names(version)
        pattern = re.compile("[^a-zA-Z]")
        name_squished = pattern.sub("", song_name).lower()
        for s in all_song_names:
            if name_squished in pattern.sub("", s).lower():
                return cls(s, version)
        return None

    @classmethod
    def all_song_names(cls, version: str, shuffle: bool = False) -> list[str]:
        all_song_names: list[str] = []
        song_dir = Path(cls.base_music_dir, version)
        if song_dir.is_dir():
            all_song_names = [f.stem for f in song_dir.iterdir()]
        if shuffle:
            random.shuffle(all_song_names)
        else:
            all_song_names.sort()
        return all_song_names

    @classmethod
    def random(cls, version: str) -> Optional["KKSong"]:
        all_song_names = cls.all_song_names(version, shuffle=True)
        if all_song_names:
            return cls(all_song_names[0], version)
        return None

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

        song_dir = Path(os.path.join(MUSIC_DIR, "kk", version))
        if not song_dir.is_dir():
            raise OSError(f'Directory "{song_dir}" not found.')

        matching_songs = [f for f in song_dir.iterdir() if self.name in f.name]
        if not matching_songs:
            raise OSError(f'No file found containing "{self.name}"')
        elif len(matching_songs) > 1:
            raise OSError(f'Multiple files found for "{self.name}"')

        super().__init__(matching_songs[0])

    @property
    def is_loopable(self):
        return self.version in ["aircheck", "musicbox"]

    def make_loop_files(self, force_cut: bool = False) -> tuple[str, str]:
        loop_times = load_json_resource("kk_loop_times.json")
        song_loop_time = loop_times[self.name][self.version]
        return self._make_loop_files(self.filepath, song_loop_time, force_cut)
