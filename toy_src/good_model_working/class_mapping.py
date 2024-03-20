from .Generator import Generator
from .Solar import Solar
from .Wind import Wind
from .Storage import Storage
from .Load import Load

class_dict_for_region = {
    'generator' : Generator,
    'solar': Solar, 
    'wind': Wind, 
    'storage': Storage,
    'load': Load,
}