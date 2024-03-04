from Generator import Generator
from Solar import Solar
from Wind import Wind
from Storage import Storage
from Load import Load

class_dict_for_region = {
    'generator_cost' : Generator,
    'generator_capacity': Generator,
    'solar_capex': Solar,
    'solar_cf': Solar,
    'solar_max_capacity': Solar,
    'solar_installed_capacity': Solar,
    'wind_capex': Wind,
    'wind_capacity_factor': Wind,
    'wind_max_capacity': Wind,
    'wind_installed_capacity': Wind,
    'wind_transmission_cost': Wind,
    'storage': Storage,
    'load': Load,
}

storage_efficiency = 0.7

transmission_efficiency = 0.972

time_periods = list(range(0,8760))