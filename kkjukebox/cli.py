import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import asyncio
import datetime
import json
import random
import re
import time
from importlib.resources import as_file, files
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import click
import geocoder  # type: ignore
import pygame
import python_weather as pw  # type: ignore
from click import Choice, argument, group, option
from pydub import AudioSegment  # type: ignore
from python_weather import Kind
from rich_click import RichCommand, RichGroup

from .song import HourlySong
from .utils import load_json_resource

if TYPE_CHECKING:
    from python_weather.forecast import Forecast  # type: ignore

GAME_OPTIONS = ["animal-crossing", "wild-world", "new-leaf", "new-horizons"]
HOUR_OPTIONS = [f"{i}{j}" for i in range(1, 13) for j in ["am", "pm"]]

WEATHER_SUNNY = "sunny"
WEATHER_RAINY = "raining"
WEATHER_SNOWY = "snowing"
WEATHER_OPTIONS = [WEATHER_SUNNY, WEATHER_RAINY, WEATHER_SNOWY]

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


async def get_weather(location: str) -> str:
    forecast: "Forecast" = None
    try:
        async with asyncio.timeout(5):
            async with pw.Client(unit=pw.IMPERIAL) as client:
                forecast = await client.get(location)
    except Exception as e:
        print(
            f"Error retrieving forecast ({type(e).__name__}); going with {WEATHER_SUNNY}"
        )
        return WEATHER_SUNNY

    print(
        f"{forecast.kind.emoji}  Weather in {forecast.location}, {forecast.region}: {forecast.kind}! {forecast.kind.emoji}"
    )
    if forecast.kind in KINDS_RAIN:
        return WEATHER_RAINY
    elif forecast.kind in KINDS_SNOW:
        return WEATHER_SNOWY
    else:
        return WEATHER_SUNNY


def make_loop(
    song_filepath: str, loop_timing: dict[str, str], force_cut: bool = False
) -> tuple[str, str]:
    p = Path(song_filepath)
    if not p.is_file():
        raise FileNotFoundError(f"No file at {song_filepath}")

    filetype = p.suffix.strip(".")
    loops_dir = f"{p.parent}/loops"
    start_filename = f"{p.stem}-start.{filetype}"
    loop_filename = f"{p.stem}-loop.{filetype}"
    start_filepath = f"{loops_dir}/{start_filename}"
    loop_filepath = f"{loops_dir}/{loop_filename}"

    if (
        not (Path(start_filepath).is_file() and Path(loop_filepath).is_file())
        or force_cut
    ):
        print("Start and/or Loop files not found. Cutting now...")

        loop_start_ms = float(loop_timing["start"]) * 1000
        loop_end_ms = float(loop_timing["end"]) * 1000

        original = AudioSegment.from_file(song_filepath)

        print(f"Making start and loop tracks for {song_filepath}")
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


def make_kk_loops(show_type: str, song_name: Optional[str]) -> tuple[str, str]:
    loop_times = load_json_resource("kk_loop_times.json")
    song_loop_time = loop_times[song_name][show_type]
    kk_song_filepath = f"{MUSIC_DIR}/kk/{show_type}/{song_name}.mp3"
    return make_loop(kk_song_filepath, song_loop_time)


def get_complete_song_name(song_name: str, all_song_names: list[str]) -> Optional[str]:
    pattern = re.compile("[^a-zA-Z]")
    given_stripped = pattern.sub("", song_name).lower()
    for s in all_song_names:
        if given_stripped in pattern.sub("", s).lower():
            return s
    return None


async def play_kk(show_type: str, song_name: Optional[str]):
    kk_music_dir = Path(f"{MUSIC_DIR}/kk/{show_type}")
    music_paths = [p for p in kk_music_dir.iterdir()]
    pygame.mixer.init()
    if show_type == "live":
        while True:
            if not pygame.mixer.music.get_busy():
                next_up = random.choice(music_paths)
                print(f"Now Playing: {next_up.name} ({show_type})!")
                pygame.mixer.music.load(str(next_up))
                pygame.mixer.music.play()
            await asyncio.sleep(1)
    else:
        song_names = [f.stem for f in music_paths]
        if song_name:
            full_song_name = get_complete_song_name(song_name, song_names)
            if not full_song_name:
                raise ValueError(f'No song found that matches "{song_name}')
        else:
            full_song_name = random.choice(song_names)
        song_start_filepath, song_loop_filepath = make_kk_loops(
            show_type, full_song_name
        )
        pygame.mixer.music.load(song_start_filepath)
        pygame.mixer.music.queue(song_loop_filepath, loops=-1)

        print(f"Now Playing: {full_song_name} ({show_type})!")
        pygame.mixer.music.play()
        while True:
            await asyncio.sleep(5)


async def play_hour(game: str, hour: str, weather: str, location: str, force_cut: bool):
    hour_12 = hour
    if hour == "now":
        hour_12 = datetime.datetime.now().strftime("%-I%p").lower()
    elif hour == "random":
        hour_12 = random.choice(HOUR_OPTIONS)

    hour_24 = datetime.datetime.strptime(hour_12, "%I%p").hour

    if location == "local":
        location = get_location()

    pygame.mixer.init()
    while True:
        now = datetime.datetime.now()
        one_hour = datetime.timedelta(hours=1)
        next_hour = now.replace(microsecond=0, second=0, minute=0) + one_hour
        # print(f"Time until next hour: {(next_hour - now).total_seconds()}")
        if (next_hour - now).total_seconds() < 10.0:
            hour_24 = next_hour.hour
            await end(10)
            await asyncio.sleep(1)

        if not pygame.mixer.music.get_busy():
            curr_game = game
            if game == "random":
                curr_game = random.choice(GAME_OPTIONS)

            curr_weather = weather
            if weather == "location":
                curr_weather = await get_weather(location)

            h = HourlySong(hour_24, curr_game, curr_weather)
            hour_start_filepath, hour_loop_filepath = h.make_loop_files()
            print(f"Playing {h.hour} ({h.game}/{h.weather})!")
            pygame.mixer.music.load(hour_start_filepath)
            pygame.mixer.music.queue(hour_loop_filepath, loops=-1)
            pygame.mixer.music.play()

        await asyncio.sleep(5)


async def end(fadeout_secs: int = 2) -> None:
    pygame.mixer.music.fadeout(fadeout_secs * 1000)
    await asyncio.sleep(fadeout_secs)


@group(cls=RichGroup, context_settings={"auto_envvar_prefix": "KKJUKEBOX"})
def cli() -> None:
    """
    Play music from your favorite Animal Crossing games.
    """
    pass


@cli.command(cls=RichCommand)
@argument("play_type", type=Choice(["live", "aircheck", "musicbox"]))
@argument("song_name", type=str, default=None)
def kk(play_type: str, song_name: Optional[str]):
    """
    Play music from KK Slider.
    """
    try:
        asyncio.run(play_kk(play_type, song_name))
    except KeyboardInterrupt:
        print("Bye!")
        asyncio.run(end())


@cli.command(cls=RichCommand)
@option("-g", "--game", type=Choice(GAME_OPTIONS + ["random"]), default="new-horizons")
@option("-h", "--hour", type=Choice(HOUR_OPTIONS + ["now", "random"]), default="now")
@option(
    "-w", "--weather", type=Choice(WEATHER_OPTIONS + ["location"]), default="location"
)
@option("-l", "--location", type=str, default="local")
@option("--force-cut", is_flag=True, help="Cut loop sample even if they already exist.")
def hourly(
    game: str,
    hour: str,
    weather: str,
    location: str,
    force_cut: bool,
):
    """
    Play seamlessly-looping hourly music.
    """
    try:
        asyncio.run(play_hour(game, hour, weather, location, force_cut))
    except KeyboardInterrupt:
        print("Bye!")
        asyncio.run(end())


if __name__ == "__main__":
    cli()
