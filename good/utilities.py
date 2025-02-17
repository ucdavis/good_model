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

'''
Calculates Gini coefficient (inequality)
'''
def gini(x):

    x = np.array(x)

    total = 0

    for i, xi in enumerate(x[:-1], 1):

        total += np.sum(np.abs(xi - x[i:]))

    return total / (len(x) ** 2 * np.mean(x))

def in_iterable(value):

    return hasattr(value, '__iter__')

def top_n_indices(array, n):

    return sorted(range(len(array)), key=lambda i: array[i])[-n:]

def bottom_n_indices(array, n):

    return sorted(range(len(array)), key=lambda i: array[i])[:n]

def full_factorial(levels):

    n = len(levels)  # number of factors

    nb_lines = np.prod(levels)  # number of trial conditions

    h = np.zeros((nb_lines, n))

    level_repeat = 1
    range_repeat = np.prod(levels).astype(int)

    for i in range(n):

        range_repeat /= levels[i]
        range_repeat = range_repeat.astype(int)

        lvl = []

        for j in range(levels[i]):

            lvl += [j] * level_repeat

        rng = lvl*range_repeat

        level_repeat *= levels[i]

        h[:, i] = rng

    return h.astype(int)

def two_way_t_test(x, y):

    x_n = len(x)
    y_n = len(y)

    x_mu = np.mean(x)
    y_mu = np.mean(y)

    x_sig = np.std(x)
    y_sig = np.std(y)

    x_se = x_sig / np.sqrt(x_n)
    y_se = y_sig / np.sqrt(y_n)

    x_y_se = np.sqrt(x_se ** 2 + y_se ** 2)

    t_value = (x_mu - y_mu) / x_y_se

    df = x_n + y_n

    p_value = (1 - t.cdf(np.abs(t_value), df)) * 2

    return p_value

def pythagorean(source_x, source_y, target_x, target_y):

    return np.sqrt((target_x - source_x) ** 2 + (target_y - source_y) ** 2)

def haversine(source_longitude, source_latitude, target_longitude, target_latitude, **kwargs):

    radius = kwargs.get('radius', 6372800) # [m]
    
    distance_longitude_radians = np.radians(target_longitude - source_longitude)
    distance_latitude_radians = np.radians(target_latitude - source_latitude)

    source_latitude_radians = np.radians(source_latitude)
    target_latitude_radians = np.radians(target_latitude)

    a_squared = (
        np.sin(distance_latitude_radians / 2) ** 2 +
        np.cos(source_latitude_radians) *
        np.cos(target_latitude_radians) *
        np.sin(distance_longitude_radians / 2) ** 2
        )

    c = 2 * np.arcsin(np.sqrt(a_squared))

    return c * radius

def root_mean_square_error(x, y):

    return np.sqrt(((x - y) ** 2).sum() / len(x))

def cprint(message, disp = True, **kwargs):

    if disp:

        print(message, **kwargs)