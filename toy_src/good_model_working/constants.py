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

transmission_efficiency = 0.972

## Adjusting time frame for model run
min_hour = 0

# General time frames: 
# Annual: 8760
# 6-mos: 4380
max_hour = 8760

time_periods = list(range(min_hour,max_hour))