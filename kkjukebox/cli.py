import asyncio
import datetime
from typing import TYPE_CHECKING, Literal, Optional

import click
from click import Choice, argument, group, option
from rich_click import RichCommand, RichGroup

from .game import Game
from .jukebox import Jukebox
from .weather import Weather

if TYPE_CHECKING:
    from click import Context, Parameter


def int_or_random(
    ctx: "Context", param: "Parameter", value: str
) -> int | Literal["random"]:
    if value.lower() == "random":
        return "random"
    try:
        return int(value)
    except ValueError:
        raise click.BadParameter('Value must be either an inteter or "random"')


def validate_hour(
    ctx: "Context", param: "Parameter", value: str
) -> int | Literal["now", "random"]:
    hour: Optional[int | str] = None
    if value.lower() == "random":
        return "random"
    elif value.lower() == "now":
        return "now"

    try:
        hour = int(value)
    except ValueError:
        pass
    else:
        if 23 < hour < 0:
            raise click.BadParameter("Hour value must be between 0 and 23")
        else:
            return hour

    try:
        return datetime.datetime.strptime(value, "%I%p").hour
    except ValueError:
        raise click.BadParameter("Could not parse hour value in AM/PM format")


@group(cls=RichGroup, context_settings={"auto_envvar_prefix": "KKJUKEBOX"})
@option("--force-cut", is_flag=True, help="Cut loop sample even if they already exist.")
@click.pass_context
def cli(ctx: "Context", force_cut: bool) -> None:
    """
    Play music from your favorite Animal Crossing games.
    """
    ctx.ensure_object(dict)
    ctx.obj["force_cut"] = force_cut


@cli.command(cls=RichCommand)
@option(
    "--loop-length",
    type=click.UNPROCESSED,
    callback=int_or_random,
    default=60,
    show_default=True,
    show_envvar=True,
    help='How long a looping song should play before transitioning to the next. Can be an integer or "random"',
)
@option(
    "--loop-length-upper-secs",
    "ll_upper",
    type=int,
    default=120,
    show_default=True,
    show_envvar=True,
    help="Upper bound in seconds for random selection of loop-length.",
)
@option(
    "--loop-length-lower-secs",
    "ll_lower",
    type=int,
    default=60,
    show_default=True,
    show_envvar=True,
    help="Lower bound in seconds for random selection of loop-length.",
)
@argument("version", type=Choice(["live", "aircheck", "musicbox"]))
@argument("song_name", type=str, required=False, default=None)
@click.pass_context
def kk(
    ctx: "Context",
    loop_length: int | Literal["random"],
    ll_upper: int,
    ll_lower: int,
    version: str,
    song_name: Optional[str],
) -> None:
    """
    Play music from KK Slider.
    """
    force_cut = ctx.obj["force_cut"]
    j = Jukebox(
        force_cut=force_cut,
        loop_length=loop_length,
        loop_upper_secs=ll_upper,
        loop_lower_secs=ll_lower,
    )
    try:
        asyncio.run(j.play_kk(version, song_name=song_name))
    except KeyboardInterrupt:
        asyncio.run(j.stop())


@cli.command(cls=RichCommand)
@option(
    "-g",
    "--game",
    type=Choice([g.value for g in Game] + ["random"]),
    default=Game.NEW_HORIZONS.value,
    show_default=True,
    show_envvar=True,
    help='Which AC game to source music from. Can be "random".',
)
@option(
    "-h",
    "--hour",
    type=click.UNPROCESSED,
    callback=validate_hour,
    default="now",
    help='The hour to play in either 24-hour or AM/PM format. Can also be "random" or "now".',
    show_default=True,
    show_envvar=True,
)
@option(
    "-w",
    "--weather",
    type=Choice([w.value for w in Weather] + ["location", "random"]),
    default="location",
    show_default=True,
    show_envvar=True,
    help='The weather type for sourcing music. Can also be "random" or "location" to use the value specified by the location option for real-time weather sourcing.',
)
@option(
    "-l",
    "--location",
    type=str,
    default="local",
    show_default=True,
    show_envvar=True,
    help='The location to use for sourcing real-time weather. Can be "local" to lookup (using IP geocoding) the current location.',
)
@click.pass_context
def hourly(
    ctx: "Context",
    game: str,
    hour: int | Literal["now", "random"],
    weather: str,
    location: str,
) -> None:
    """
    Play seamlessly-looping hourly music.
    """
    force_cut = ctx.obj["force_cut"]
    j = Jukebox(force_cut=force_cut)
    try:
        asyncio.run(j.play_hourly(hour, game, weather, location))
    except KeyboardInterrupt:
        asyncio.run(j.stop())


if __name__ == "__main__":
    cli()
