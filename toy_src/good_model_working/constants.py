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

time_periods = list(range(0, 168))

hydro_capacity_limit = 0.05
