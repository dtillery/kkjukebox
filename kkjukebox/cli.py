import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import asyncio
import datetime
import json
import random
import time
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import click
import geocoder  # type: ignore
import pygame
import python_weather as pw  # type: ignore
from click import Choice
from pydub import AudioSegment  # type: ignore
from python_weather import Kind
from rich_click import RichCommand

if TYPE_CHECKING:
    from python_weather.forecast import Forecast  # type: ignore

GAME_OPTIONS = ["animal-crossing", "wild-world", "new-leaf", "new-horizons"]
HOUR_OPTIONS = [f"{i}{j}" for i in range(1, 13) for j in ["am", "pm"]]
WEATHER_OPTIONS = ["sunny", "raining", "snowing"]

MUSIC_DIR = "music"

KINDS_RAIN = [
    Kind.HEAVY_RAIN,
    Kind.HEAVY_SHOWERS,
    Kind.LIGHT_RAIN,
    Kind.LIGHT_SHOWERS,
    Kind.LIGHT_SLEET,
    Kind.LIGHT_SLEET_SHOWERS,
    Kind.THUNDERY_HEAVY_RAIN,
    Kind.THUNDERY_SHOWERS,
]

KINDS_SNOW = [
    Kind.HEAVY_SNOW,
    Kind.HEAVY_SNOW_SHOWERS,
    Kind.LIGHT_SNOW,
    Kind.LIGHT_SNOW_SHOWERS,
    Kind.THUNDERY_SNOW_SHOWERS,
]


def get_location() -> str:
    geo_data = geocoder.ip("me")
    print(f"Location: {geo_data.json['address']}")
    return geo_data.json["city"]


async def _get_weather_async(location: str) -> "Forecast":
    async with pw.Client(unit=pw.IMPERIAL) as client:
        return await client.get(location)


def get_weather(location: str) -> str:
    forecast = asyncio.run(_get_weather_async(location))
    print(f"Weather in {forecast.location}, {forecast.region}: {forecast.kind}")
    if forecast.kind in KINDS_RAIN:
        return "raining"
    elif forecast.kind in KINDS_SNOW:
        return "snowing"
    else:
        return "sunny"


def load_loop_times() -> dict:
    filename = "loop_times.json"
    with as_file(files("kkjukebox.resources").joinpath(filename)) as path:
        with open(path, "rb") as f:
            return json.load(f)


def play_kk(show_type: str):
    kk_music_dir = Path(f"{MUSIC_DIR}/kk/{show_type}")
    music_paths = [p for p in kk_music_dir.iterdir() if p.name.endswith("ogg")]
    pygame.mixer.init()
    try:
        while True:
            if not pygame.mixer.music.get_busy():
                next_up = random.choice(music_paths)
                print(f"Now Playing: {next_up.name}")
                pygame.mixer.music.load(str(next_up))
                pygame.mixer.music.play()
            time.sleep(1)
    except KeyboardInterrupt:
        print("See ya!")
        pygame.mixer.music.fadeout(2000)
        time.sleep(2)


def play_hour(game: str, hour: str, weather: str, location: str, force_cut: bool):
    hour_12 = hour
    if hour == "now":
        hour_12 = datetime.datetime.now().strftime("%-I%p").lower()
    elif hour == "random":
        hour_12 = random.choice(HOUR_OPTIONS)

    hour_24 = str(datetime.datetime.strptime(hour_12, "%I%p").hour).zfill(2)

    if game == "random":
        game = random.choice(GAME_OPTIONS)

    if location == "local":
        location = get_location()

    if weather == "location":
        weather = get_weather(location)

    if game == "animal-crossing" and weather == "raining":
        # todo: add support for singlular raining music.
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


@click.command(cls=RichCommand, context_settings={"auto_envvar_prefix": "KKJUKEBOX"})
@click.option(
    "-g", "--game", type=Choice(GAME_OPTIONS + ["random"]), default="new-horizons"
)
@click.option(
    "-h", "--hour", type=Choice(HOUR_OPTIONS + ["now", "random"]), default="now"
)
@click.option(
    "-w", "--weather", type=Choice(WEATHER_OPTIONS + ["location"]), default="location"
)
@click.option("-l", "--location", type=str, default="local")
@click.option("--force-cut", is_flag=True)
@click.option("-kk", "kk_type", type=Choice(["live", "aircheck"]), default=None)
def cli(
    game: str,
    hour: str,
    weather: str,
    location: str,
    force_cut: bool,
    kk_type: Optional[str],
):
    if kk_type:
        play_kk(kk_type)
    else:
        play_hour(game, hour, weather, location, force_cut)


if __name__ == "__main__":
    cli()
