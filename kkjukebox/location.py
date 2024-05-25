import geocoder  # type: ignore


def get_location() -> str:
    geo_data = geocoder.ip("me")
    print(f"Location: {geo_data.json['address']}")
    return geo_data.json["city"]
