from .user_inputs import time_periods
'''
Description: stores all constant values used within the model

Depedent Modules: 

        Storage.py
        Load.py
        Generator.py
        Wind.py
        Solar.py
        Transmission.py

Notes: 

    time_periods variable can be manipulated to adjust the time frame
    for the model run. 
    
'''

storage_efficiency = 0.7
storage_flow_limit = 0.85
transmission_efficiency = 0.985
time_periods = time_periods
hydro_capacity_limit = 0.45  # the capacity factor for conventional hydropower resources across the US has remained relatively consistent through the years, between 35 and 45% (US DOE)
