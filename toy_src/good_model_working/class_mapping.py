from .Generator import Generator
from .Solar import Solar
from .Wind import Wind
from .Storage import Storage
from .Load import Load

class_dict_for_region = {
    'generators' : Generator,
    'solar_cost': Solar,
    'solar_gen': Solar,
    'solar_max_capacity': Solar,
    'solar_installed_capacity': Solar,
    'solar_transmission_cost': Solar,
    'wind_cost': Wind,
    'wind_gen': Wind,
    'wind_max_capacity': Wind,
    'wind_installed_capacity': Wind,
    'wind_transmission_cost': Wind,
    'Energy Storage': Storage,
    'load': Load,
}