import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import asyncio
import datetime
import random
from typing import TYPE_CHECKING, Optional

import click
import pygame
from click import Choice, argument, group, option
from rich_click import RichCommand, RichGroup

from .location import get_location
from .song import HourlySong, KKSong
from .utils import load_json_resource
from .weather import WeatherType, get_weather

GAME_OPTIONS = ["animal-crossing", "wild-world", "new-leaf", "new-horizons"]
HOUR_OPTIONS = [f"{i}{j}" for i in range(1, 13) for j in ["am", "pm"]]


async def play_kk(show_type: str, song_name: Optional[str]):
    pygame.mixer.init()
    if song_name:
        kk_song = KKSong.from_fuzzy_name(song_name, show_type)
    else:
        kk_song = KKSong.random(show_type)

    if not kk_song:
        raise ValueError(f'No song found that matches "{song_name}"')
    elif kk_song.is_loopable:
        song_start_filepath, song_loop_filepath = kk_song.make_loop_files()
        pygame.mixer.music.load(song_start_filepath)
        pygame.mixer.music.queue(song_loop_filepath, loops=-1)
        print(f"Now Playing: {kk_song.name} ({kk_song.play_type})!")
        pygame.mixer.music.play()
        while True:
            await asyncio.sleep(5)
    else:
        print(f"Now Playing: {kk_song.name} ({kk_song.play_type})!")
        pygame.mixer.music.load(kk_song.filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(5)


async def play_hour(
    game: str, hour: str, weather: WeatherType | str, location: str, force_cut: bool
):
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
            print(f"Playing {h.hour} ({h.game}/{h.weather.value})!")
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
@argument("song_name", type=str, required=False, default=None)
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
    "-w", "--weather", type=Choice(list(WeatherType) + ["location"]), default="location"
)
@option("-l", "--location", type=str, default="local")
@option("--force-cut", is_flag=True, help="Cut loop sample even if they already exist.")
def hourly(
    game: str,
    hour: str,
    weather: WeatherType | str,
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
