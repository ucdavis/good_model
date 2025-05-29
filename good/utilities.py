import os
import sys
import time
import json

import numpy as np

from scipy.stats import t
from shutil import get_terminal_size

class NpEncoder(json.JSONEncoder):
    '''
    Encoder to allow for numpy types to be converted to default types for
    JSON serialization. For use with json.dump(s)/load(s).
    '''
    def default(self, obj):

        if isinstance(obj, np.integer):

            return int(obj)

        if isinstance(obj, np.floating):

            return float(obj)

        if isinstance(obj, np.ndarray):

            return obj.tolist()

        return super(NpEncoder, self).default(obj)

def write_json(data, filename = 'output.json'):

    with open(filename, 'w') as file:

        json.dump(data, file, indent = 4, cls = NpEncoder)

def read_json(filename):

    with open(filename, 'r') as file:

        data = json.load(file)

    return data

def read_jsons(directory, output = 'list'):
    
    if output == 'list':

        data = []

        for filename in os.listdir(directory):

            with open(directory + filename, 'r') as file:

                data.append(json.load(file))

    elif output == 'dict':

        data = {}

        for filename in os.listdir(directory):

            with open(directory + filename, 'r') as file:

                key = filename.split('.')[0]

                data[key] = json.load(file)

    return data

def pythagorean(source_x, source_y, target_x, target_y):

    return np.sqrt((target_x - source_x) ** 2 + (target_y - source_y) ** 2)

def haversine(source_lon, source_lat, target_lon, target_lat, **kwargs):

    radius = kwargs.get('radius', 6372800) # [m]
    
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

def cprint(message, disp = True, **kwargs):

    if disp:

        print(message, **kwargs)