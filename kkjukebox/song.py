import datetime
import os
from pathlib import Path

from pydub import AudioSegment  # type: ignore

from .utils import load_json_resource

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
        self, path: Path, loop_timing: dict[str, str], recut: bool = False
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
            or recut
        ):
            print("Start and/or Loop files not found. Cutting now...")

            loop_start_ms = float(loop_timing["start"]) * 1000
            loop_end_ms = float(loop_timing["end"]) * 1000

            original = AudioSegment.from_file(path)

            print(f"Making start and loop tracks for {path}")
            print(f"Original track is {len(original)/1000}s")
            print(f"Cutting loop from {loop_start_ms/1000} to {loop_end_ms/1000}")
            start = original[:loop_end_ms]  # type: ignore
            loop = original[loop_start_ms:loop_end_ms]  # type: ignore
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
    game: str
    weather: str

    def __init__(self, hour: int, game: str, weather: str) -> None:
        if hour <= 0 or hour >= 23:
            raise ValueError(f"Hour must be between 0 and 23")
        self.hour = hour
        self.game = game
        self.weather = weather

        if self.game == "animal-crossing" and self.weather == "raining":
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

    def make_loop_files(self) -> tuple[str, str]:
        hours_filetype = "ogg"
        hour_path = self.filepath
        hour_str = self._hour_fill

        loop_times = load_json_resource("hour_loop_times.json")
        song_loop_time = loop_times[self.game][self.weather][hour_str]
        return self._make_loop_files(hour_path, song_loop_time)
