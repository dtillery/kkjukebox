import asyncio
import datetime
import random
from typing import TYPE_CHECKING, Literal, Optional

import pygame

from .game import Game
from .location import get_location
from .song import HourlySong, KKSong
from .weather import Weather, get_weather


class Jukebox:

    force_cut: bool
    randomize_hour: bool
    randomize_game: bool
    randomize_weather: bool
    localized_weather: bool

    def __init__(self, force_cut: bool = False) -> None:
        self.force_cut = force_cut
        self.randomized_hour = False
        self.randomized_game = False
        self.randomized_weather = False
        self.localized_weather = False
        pygame.mixer.init()

    def _get_curr_location(self) -> str:
        return get_location()

    async def _get_curr_weather(self, location: str) -> "Weather":
        return await get_weather(location)

    async def stop(self, fadeout_secs: int = 2) -> None:
        pygame.mixer.music.fadeout(fadeout_secs * 1000)
        await asyncio.sleep(fadeout_secs)

    async def play_hourly(
        self,
        hour: int | Literal["now", "random"],
        game: str,
        weather: str,
        location: str,
    ) -> None:
        if hour == "now":
            hour_24 = datetime.datetime.now().hour
        elif hour == "random":
            self.randomized_hour = True
            hour_24 = random.randint(0, 23)
        elif type(hour) == int:
            if 23 < hour < 0:
                raise ValueError("Hour must be integer between 0 and 23")
            else:
                hour_24 = hour
        else:
            raise ValueError(f'"{hour}" is not a valid value for hour')

        if game == "random":
            self.randomized_game = True
        else:
            curr_game = Game(game)

        if weather == "random":
            self.randomized_weather = True
        elif weather == "location":
            self.localized_weather = True
        else:
            curr_weather = Weather(weather)

        if self.localized_weather and location == "local":
            location = self._get_curr_location()

        while True:
            now = datetime.datetime.now()
            one_hour = datetime.timedelta(hours=1)
            next_hour = now.replace(microsecond=0, second=0, minute=0) + one_hour
            # print(f"Time until next hour: {(next_hour - now).total_seconds()}")
            if (next_hour - now).total_seconds() < 10.0:
                hour_24 = next_hour.hour
                await self.stop(10)
                await asyncio.sleep(1)

            if not pygame.mixer.music.get_busy():
                if self.randomized_game:
                    curr_game = random.choice(list(Game))
                    print(f"Random game is {curr_game}")

                if self.localized_weather:
                    curr_weather = await self._get_curr_weather(location)
                elif self.randomized_weather:
                    curr_weather = random.choice(list(Weather))
                    print(f"Random weather is {curr_weather}")

                h = HourlySong(hour_24, curr_game, curr_weather)
                hour_start_filepath, hour_loop_filepath = h.make_loop_files(
                    self.force_cut
                )
                print(f"Playing {h.hour} ({h.game.value}/{h.weather.value})!")
                pygame.mixer.music.load(hour_start_filepath)
                pygame.mixer.music.queue(hour_loop_filepath, loops=-1)
                pygame.mixer.music.play()

            await asyncio.sleep(5)

    async def play_kk(self, version: str, song_name: Optional[str]):
        if song_name:
            kk_song = KKSong.from_fuzzy_name(song_name, version)
        else:
            kk_song = KKSong.random(version)

        if not kk_song:
            raise ValueError(f'No song found that matches "{song_name}"')
        elif kk_song.is_loopable:
            song_start_filepath, song_loop_filepath = kk_song.make_loop_files(
                self.force_cut
            )
            pygame.mixer.music.load(song_start_filepath)
            pygame.mixer.music.queue(song_loop_filepath, loops=-1)
            print(f"Now Playing: {kk_song.name} ({kk_song.version})!")
            pygame.mixer.music.play()
            while True:
                await asyncio.sleep(5)
        else:
            print(f"Now Playing: {kk_song.name} ({kk_song.version})!")
            pygame.mixer.music.load(kk_song.filepath)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(5)
