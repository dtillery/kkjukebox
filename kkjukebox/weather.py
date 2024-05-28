import asyncio
from enum import Enum
from typing import TYPE_CHECKING

import python_weather as pw  # type: ignore

if TYPE_CHECKING:
    from python_weather import Forecast

KINDS_RAIN = [
    pw.Kind.HEAVY_RAIN,
    pw.Kind.HEAVY_SHOWERS,
    pw.Kind.LIGHT_RAIN,
    pw.Kind.LIGHT_SHOWERS,
    pw.Kind.LIGHT_SLEET,
    pw.Kind.LIGHT_SLEET_SHOWERS,
    pw.Kind.THUNDERY_HEAVY_RAIN,
    pw.Kind.THUNDERY_SHOWERS,
]

KINDS_SNOW = [
    pw.Kind.HEAVY_SNOW,
    pw.Kind.HEAVY_SNOW_SHOWERS,
    pw.Kind.LIGHT_SNOW,
    pw.Kind.LIGHT_SNOW_SHOWERS,
    pw.Kind.THUNDERY_SNOW_SHOWERS,
]


class Weather(str, Enum):
    SUNNY = "sunny"
    RAINING = "raining"
    SNOWING = "snowing"

    @classmethod
    def all_values(cls) -> list[str]:
        return [w.value for w in cls]


async def get_weather(location: str) -> "Weather":
    forecast: "Forecast" = None
    try:
        async with asyncio.timeout(5):
            async with pw.Client(unit=pw.IMPERIAL) as client:
                forecast = await client.get(location)
    except Exception as e:
        print(
            f"Error retrieving forecast ({type(e).__name__}); going with {Weather.SUNNY.value}"
        )
        return Weather.SUNNY

    print(
        f"{forecast.kind.emoji}  Weather in {forecast.location}, {forecast.region}: {forecast.kind}! {forecast.kind.emoji}"
    )
    if forecast.kind in KINDS_RAIN:
        return Weather.RAINING
    elif forecast.kind in KINDS_SNOW:
        return Weather.SNOWING
    else:
        return Weather.SUNNY
