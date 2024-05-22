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
from click import Choice, argument, group, option
from pydub import AudioSegment  # type: ignore
from python_weather import Kind
from rich_click import RichCommand

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


def load_json_resource(resource_filename) -> dict:
    with as_file(files("kkjukebox.resources").joinpath(resource_filename)) as path:
        with open(path, "rb") as f:
            return json.load(f)


def make_kk_loops(show_type: str, song_name: Optional[str]) -> tuple[str, str]:
    loop_times = load_json_resource("kk_loop_times.json")
    song_loop_time = loop_times[song_name][show_type]
    kk_song_filepath = f"{MUSIC_DIR}/kk/{show_type}/{song_name}.mp3"
    return make_loop(kk_song_filepath, song_loop_time)


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
        song_start_filepath, song_loop_filepath = make_kk_loops(show_type, song_name)
        pygame.mixer.music.load(song_start_filepath)
        pygame.mixer.music.queue(song_loop_filepath, loops=-1)

        print(f"Now Playing: {song_name} ({show_type})!")
        pygame.mixer.music.play(fade_ms=2000)
        while True:
            await asyncio.sleep(5)


def make_hour_loops(game: str, weather: str, hour_12: str) -> tuple[str, str]:
    hour_24 = str(datetime.datetime.strptime(hour_12, "%I%p").hour).zfill(2)
    loop_times = load_json_resource("hour_loop_times.json")
    song_loop_time = loop_times[game][weather][hour_24]
    hour_song_filepath = f"{MUSIC_DIR}/{game}/{weather}/{hour_12}.ogg"
    return make_loop(hour_song_filepath, song_loop_time)


async def play_hour(game: str, hour: str, weather: str, location: str, force_cut: bool):
    hour_12 = hour
    if hour == "now":
        hour_12 = datetime.datetime.now().strftime("%-I%p").lower()
    elif hour == "random":
        hour_12 = random.choice(HOUR_OPTIONS)

    if game == "random":
        game = random.choice(GAME_OPTIONS)

    if location == "local":
        location = get_location()

    if weather == "location":
        weather = await get_weather(location)

    if game == "animal-crossing" and weather == WEATHER_RAINY:
        # single rain song, saved as 12am
        hour_12 = "12am"

    hour_start_filepath, hour_loop_filepath = make_hour_loops(game, weather, hour_12)

    print(hour_start_filepath)
    print(hour_loop_filepath)
    print(f"Playing {hour_12} ({game}/{weather})!")
    pygame.mixer.init()
    pygame.mixer.music.load(hour_start_filepath)
    pygame.mixer.music.queue(hour_loop_filepath, loops=-1)

    pygame.mixer.music.play(fade_ms=2000)
    while True:
        await asyncio.sleep(5)


async def end() -> None:
    pygame.mixer.music.fadeout(2000)
    await asyncio.sleep(2)


@group(context_settings={"auto_envvar_prefix": "KKJUKEBOX"})
def cli() -> None:
    pass


@cli.command(cls=RichCommand)
@argument("play_type", type=Choice(["live", "aircheck", "musicbox"]))
@argument("song_name", type=str, default=None)
def kk(play_type: str, song_name: Optional[str]):

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
@option("--force-cut", is_flag=True)
def hourly(
    game: str,
    hour: str,
    weather: str,
    location: str,
    force_cut: bool,
):
    try:
        asyncio.run(play_hour(game, hour, weather, location, force_cut))
    except KeyboardInterrupt:
        print("Bye!")
        asyncio.run(end())


if __name__ == "__main__":
    cli()
