import json
from importlib.resources import as_file, files


def load_json_resource(resource_filename) -> dict:
    with as_file(files("kkjukebox.resources").joinpath(resource_filename)) as path:
        with open(path, "rb") as f:
            return json.load(f)
