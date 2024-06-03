import logging as log

import geocoder  # type: ignore


def get_location() -> str:
    geo_data = geocoder.ip("me")
    log.debug(f"Current Location: {geo_data.json['address']}")
    return geo_data.json["city"]
