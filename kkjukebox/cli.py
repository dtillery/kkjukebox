import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import datetime
import json
import random
import time
from importlib.resources import as_file, files
from pathlib import Path

import click
import pygame
from pydub import AudioSegment  # type: ignore

GAME_CHOICES = ["animal-crossing", "wild-world", "new-leaf", "new-horizons"]
HOUR_CHOICES = [f"{i}{j}" for i in range(1, 13) for j in ["am", "pm"]] + ["now"]
WEATHER_CHOICES = ["sunny", "raining", "snowing"]

MUSIC_DIR = "music"


def load_loop_times() -> dict:
    filename = "loop_times.json"
    with as_file(files("kkjukebox.resources").joinpath(filename)) as path:
        with open(path, "rb") as f:
            return json.load(f)


@click.command(context_settings={"auto_envvar_prefix": "KKJUKEBOX"})
@click.option("-g", "--game", type=click.Choice(GAME_CHOICES), default="new-horizons")
@click.option("-h", "--hour", type=click.Choice(HOUR_CHOICES), default="now")
@click.option("-w", "--weather", type=click.Choice(WEATHER_CHOICES), default="sunny")
@click.option("--force-cut", is_flag=True)
@click.option("-p", "--play", is_flag=True)
def cli(game: str, hour: str, weather: str, force_cut: bool, play: bool):
    hour_12 = hour
    if hour == "now":
        hour_12 = datetime.datetime.now().strftime("%-I%p").lower()
    hour_24 = str(datetime.datetime.strptime(hour_12, "%I%p").hour).zfill(2)

    if game == "random":
        game = random.choice(GAME_CHOICES)

    if game == "animal-crossing" and weather == "raining":
        weather = "sunny"

    game_weather_dir = f"{MUSIC_DIR}/{game}/{weather}"
    hour_track_files = [
        f for f in os.listdir(game_weather_dir) if f.startswith(hour_12)
    ]
    if len(hour_track_files) > 1:
        raise Exception(f"More than one hour track file found: {hour_track_files}")
    hour_track_uri = f"{game_weather_dir}/{hour_track_files[0]}"

    loops_dir = f"{MUSIC_DIR}/{game}/{weather}/loops"
    hour_start_filename = f"{hour_12}-start.ogg"
    hour_loop_filename = f"{hour_12}-loop.ogg"
    hour_start_uri = f"{loops_dir}/{hour_start_filename}"
    hour_loop_uri = f"{loops_dir}/{hour_loop_filename}"

    if (
        not (Path(hour_start_uri).is_file() and Path(hour_loop_uri).is_file())
        or force_cut
    ):
        print("Start and/or Loop files not found. Cutting now...")
        loop_times = load_loop_times()

        hour_loop_timings = loop_times[game][weather][hour_24]
        loop_start_ms = float(hour_loop_timings["start"]) * 1000
        loop_end_ms = float(hour_loop_timings["end"]) * 1000

        hour_original = AudioSegment.from_file(hour_track_uri)

        print(f"Making start and loop tracks for Hour {hour_12} ({game}/{weather})")
        print(f"Original track is {len(hour_original)/1000}s")
        print(f"Cutting loop from {loop_start_ms/1000} to {loop_end_ms/1000}")
        hour_start = hour_original[:loop_end_ms]  # type: ignore
        hour_loop = hour_original[loop_start_ms:loop_end_ms]  # type: ignore
        print(f"Hour-Start is {len(hour_start)/1000}s")
        print(f"Hour-Loops is {len(hour_loop)/1000}s")

        try:
            os.mkdir(loops_dir)
        except FileExistsError:
            pass

        hour_start.export(
            hour_start_uri, format="ogg", codec="libvorbis", bitrate="320k"
        )
        hour_loop.export(hour_loop_uri, format="ogg", codec="libvorbis", bitrate="320k")

    if play:
        print(f"Playing {hour_12} ({game}/{weather})...")
        pygame.mixer.init()
        pygame.mixer.music.load(hour_start_uri)
        pygame.mixer.music.queue(hour_loop_uri, loops=-1)

        try:
            pygame.mixer.music.play(fade_ms=5000)
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            print("Bye!")
            pygame.mixer.music.fadeout(2000)
            time.sleep(2)


if __name__ == "__main__":
    cli()
