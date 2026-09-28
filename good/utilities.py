import gzip
import json
import os

import numpy as np


class NpEncoder(json.JSONEncoder):
    '''
    Encoder that converts NumPy types to built-in types for json.dump(s).
    '''
    def default(self, obj):

        if isinstance(obj, np.integer):

            return int(obj)

        if isinstance(obj, np.floating):

            return float(obj)

        if isinstance(obj, np.bool_):

            return bool(obj)

        if isinstance(obj, np.ndarray):

            return obj.tolist()

        return super(NpEncoder, self).default(obj)


def _open(filename, mode):
    '''Open plain or gzip-compressed (".gz") text files.'''

    if str(filename).endswith(".gz"):

        return gzip.open(filename, mode + "t", encoding="utf-8")

    return open(filename, mode, encoding="utf-8")


def write_json(data, filename='output.json', indent=4):
    '''Write JSON; a ".gz" suffix compresses the file.'''

    with _open(filename, 'w') as file:

        json.dump(data, file, indent=indent, cls=NpEncoder)


def read_json(filename):
    '''Read JSON, compressed or not.'''

    with _open(filename, 'r') as file:

        return json.load(file)


def read_jsons(directory, output='list'):
    '''Read every JSON file in a directory into a list or a dict keyed by file stem.'''

    names = sorted(n for n in os.listdir(directory) if n.endswith((".json", ".json.gz")))
    paths = [os.path.join(directory, n) for n in names]

    if output == 'dict':

        return {n.split('.')[0]: read_json(p) for n, p in zip(names, paths)}

    return [read_json(p) for p in paths]


def pythagorean(source_x, source_y, target_x, target_y):

    return np.sqrt((target_x - source_x) ** 2 + (target_y - source_y) ** 2)


def haversine(source_lon, source_lat, target_lon, target_lat, **kwargs):
    '''Great-circle distance in meters.'''

    radius = kwargs.get('radius', 6372800)  # [m]

    distance_longitude_radians = np.radians(target_lon - source_lon)
    distance_latitude_radians = np.radians(target_lat - source_lat)

    source_latitude_radians = np.radians(source_lat)
    target_latitude_radians = np.radians(target_lat)

    a_squared = (
        np.sin(distance_latitude_radians / 2) ** 2 +
        np.cos(source_latitude_radians) *
        np.cos(target_latitude_radians) *
        np.sin(distance_longitude_radians / 2) ** 2
        )

    c = 2 * np.arcsin(np.sqrt(a_squared))

    return c * radius


def cprint(message, disp=True, **kwargs):

    if disp:

        print(message, **kwargs)
