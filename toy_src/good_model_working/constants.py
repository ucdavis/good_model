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

time_periods = list(range(0,24))

gen_to_remove = ['Fossil Waste', 
        # 'Municipal Solid Waste', 
        # 'Non-Fossil Waste', 
        'Pumped Storage',
        'Fuel Cell',
        'Landfill Gas', 
        # "Energy Storage", 
        # "Solar PV", 
        # "Onshore Wind", 
        # 'New Battery Storage', 
        # 'IMPORT', 
        # 'Tires',
        'Offshore Wind', 
        'Solar Thermal'
        ]
