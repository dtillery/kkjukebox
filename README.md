# kkjukebox

Play your favorite Animal Crossing tunes from the comfort of your cli.

## Install
Install `ffmpeg` via Homebrew.

Install [pipx](https://pipx.pypa.io/stable/) via Homebrew according to their directions.

Then run:

```bash
pipx install git+ssh://git@github.com/dtillery/kkjukebox.git
```

**Currently incompatible with Python 3.13.0 and above.**

If you need to update, just use pipx's `reinstall` command.

Finally, add configuration environment variables (if desired) to your startup scripts.

## Music Files
You must provide your own music files for use by the app. The directory containing the music
files must be laid out as follows:

```
/Music/ac
- /animal-crossing
- /wild-world
- /new-leaf
- /new-horizons
    - /raining
    - /snowing
    - /sunny
        - 00.ogg
        - 23.ogg
        - ...
- /kk
    - /aircheck
    - /live
    - /musicbox
        - Agent K.K..mp3
        - K.K. Adventure.mp3
        - ...
```

All hourly files must be named with their 24-hour designation, e.g. 00.ogg, 13.ogg, etc.
KK files must be named with their full name, e.g. "Agent K.K..mp3" (note the period after
the 2nd K, separate from the `.mp3` extension). This is so that we can match songs to their
loop-time settings.

Currently, loop-music files will be cut and stored in the same directory as the originals,
in a `loops` subdirectory.

## Usage

### Base Configuration
`kkjukebox` by itself will not do anything, but there are a few configuration options that
can be given at this level. Configuration can be given to the command directly or through
environment variables.

#### `--force-cut, KKJUKEBOX_FORCE_CUT` (boolean)
Force the music files used for looping to be re-cut regardless of existing files found.

#### `--log-level, KKJUKEBOX_LOG_LEVEL` (text)
Set the logging level for the app when run. Can be "INFO", "DEBUG", or omitted entirely
for silent-running.

#### `--music-dir KKJUKEBOX_MUSIC_DIR` (text, required)
The path to the directory containing the music files. The subdirectories must be laid
out as detailed above.

### Hourly
Use the `hourly` subcommand to play hourly music. This can be configured based on desired
hour, game, weather and playing time. For example:

```bash
kkjukebox hourly -g new-horizons -h now -w raining
```

Will play the current-hour's music from New Horizons when it's raining. When using the `now`
option for hour, the music will change automatically at the top of the hour to what is
appropriate. If you specified random games, like so:

```bash
kkjukebox hourly -g random -h now -w location
```

This would play the appropriate hourly music for a random game with the weather based on
your current location for a while. After a set time (which can be configured, see below),
the music would change to another game's appropriate hourly music. If you wanted to get
completely random:

```bash
kkjukebox hourly -h random -g random -w random
```

Would play a random game's random hour's music for random weather.

**Configuration options include:**

#### `-g, --game, KKJUKEBOX_HOURLY_GAME` (text)
Which game to use for sourcing music. Can be any one of:

* animal-crossing
* wild-world
* new-leaf
* new-horizons
* random

Using `random` will allow music to change between games while running, based on
`--loop-length` and it's accompanying options.

#### `-h, --hour, KKJUKEBOX_HOURLY_HOUR` (text)
Which hour to use for sourcing music.. Can be any one of:

* 0-23
* 1-12 AM|PM
* now
* random

Using `now` will use music based on the current time hour.

Using `random` will allow music to change between different hours while running, based on
`--loop-length` and it's accompanying options.

#### `-w, --weather, KKJUKEBOX_HOURLY_WEATHER` (text)
Which weather to use for sourcing music. Can be any one of:

* sunny
* raining
* snowing
* location
* random

Using `location` will use whatever is passed for the `--location` option to attempt and
pull real-time weather information for a location from [wttr.in](https://wttr.in).

Using `random` will choose a random weather for use.

#### `-l, --location, KKJUKEBOX_HOURLY_LOCATION` (text)
A location to be used in conjunction with the `--weather` option to pull real-time weather
information for an area. Should be something like a city (e.g. Seattle). Other things might
work too but I haven't tested it extensively.

Alteratively, specify `local` to have the app attempt to look up your current location via
IP (which means it may be inaccurate if using a VPN).

#### `--loop-length, KKJUKEBOX_HOURLY_LOOP_LENGTH` (text)
How long in seconds an hourly song should play before transitioning to something new. This
is only relevant if `random` is specified for `--game` or `--hour`.

Using `random` will allow randomized lengths of time for music to play based on the bounds
specified by `--loop-length-upper-secs` and `--loop-length-lower-secs` (see below)

#### `--loop-length-upper-secs, KKJUKEBOX_HOURLY_LL_UPPER` (int)
The upper bound of seconds to be used when generating a random loop-length (as described above).

#### `--loop-length-lower-secs, KKJUKEBOX_HOURLY_LL_LOWER` (int)
The lower bound of seconds to be used when generating a random loop-length (as described above).

### KK Slider
This subcommand allows for playing KK Slider songs. These include the live, aircheck (radio)
and musicbox types. While live versions will play from start to end, the aircheck and musicbox
verions can be configured to loop as desired.

If a song name (fuzzily matched) is passed to the command, it will be played until finished
(in the case of live) or indefinitely (in the case of aircheck and musicbox):

```bash
kkjukebox kk -v live bubblegumkk
```

If no song name is passed, a randomized setlist will be created and played based on the passed
options. If multiple versions are included, they will all be included in the randomzied setlist:

```bash
kkjukebox kk -v aircheck -v musicbox
```

**Configuration options include:**

#### `SONG_NAME`
Optionally specify a song name after `kkjukebox kk` to play a single song until it ends (for `live` verion)
or indefinitely (for `aircheck` and `musicbox`). Uses a fuzzy-ish search to match song names.

If a song name is not supplied, a setlist will be generated based on the versions specified
and played indefinitely.

#### `-v, --version, KKJUKEBOX_KK_VERSIONS` (text)
Which version of a KK song to play. Can be any of the following:

* live
* aircheck
* musicbox

This may be specified multiple times on the command line (`-v live -v aircheck`) or env
var (`export KKJUKEBOX_KK_VERSIONS="aircheck musicbox"`). Multiple version specificiation
is only relevant when not supplying a specific SONG_NAME.

#### `--loop-length, KKJUKEBOX_KK_LOOP_LENGTH` (text)
How long in seconds a KK song should play before transitioning to something new. This is
only relevant for the `aircheck` and `musicbox` versions.

Using `random` will allow randomized lengths of time for music to play based on the bounds
specified by `--loop-length-upper-secs` and `--loop-length-lower-secs` (see below)

#### `--loop-length-upper-secs, KKJUKEBOX_KK_LL_UPPER` (int)
The upper bound of seconds to be used when generating a random loop-length (as described above).

#### `--loop-length-lower-secs, KKJUKEBOX_KK_LL_LOWER` (int)
The lower bound of seconds to be used when generating a random loop-length (as described above).


### Example Configuration
```bash
export KKJUKEBOX_FORCE_CUT=false
export KKJUKEBOX_LOG_LEVEL=INFO
export KKJUKEBOX_MUSIC_DIR=~/src/kkjukebox/music

export KKJUKEBOX_HOURLY_GAME=random
export KKJUKEBOX_HOURLY_HOUR=now
export KKJUKEBOX_HOURLY_WEATHER=location
export KKJUKEBOX_HOURLY_LOCATION=local
export KKJUKEBOX_HOURLY_LOOP_LENGTH=random
export KKJUKEBOX_HOURLY_LL_UPPER=1200
export KKJUKEBOX_HOURLY_LL_LOWER=600

export KKJUKEBOX_KK_VERSIONS="aircheck musicbox"
export KKJUKEBOX_KK_LOOP_LENGTH=random
export KKJUKEBOX_KK_LL_UPPER=120
export KKJUKEBOX_KK_LL_LOWER=60

```

## Thanks
Thank you Nintendo, please don't sue me.
