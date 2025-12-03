import logging

import geocoder  # type: ignore

log = logging.getLogger("kkjukebox")


def get_location() -> str | None:
    geo_data = geocoder.ip("me")
    if not geo_data:
        log.warning("Could not get current location via IP.")
        return None
    log.debug(f"Current Location: {geo_data.json['address']}")
    return geo_data.json["city"]
