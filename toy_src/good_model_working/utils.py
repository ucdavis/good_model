# from Generator import Generator
# from Solar import Solar
# from Wind import Wind
# from Storage import Storage
# from Load import Load
# from Transmission import Transmission

# class_dict_for_region = {
#     'generator_cost' : Generator,
#     'generator_capacity': Generator,
#     'solar_capex': Solar,
#     'solar_cf': Solar,
#     'solar_max_capacity': Solar,
#     'solar_installed_capacity': Solar,
#     'wind_capex': Wind,
#     'wind_capacity_factor': Wind,
#     'wind_max_capacity': Wind,
#     'wind_installed_capacity': Wind,
#     'wind_transmission_cost': Wind,
#     'storage': Storage,
#     'load': Load,
# }

# # _class_modules = {
# #     'Generator': 'Generator',
# #     'Solar': 'Solar',
# #     'Wind': 'Wind',
# #     'Storage': 'Storage',
# #     'Load': 'Load',
# #     'Transmission': 'Transmission'
# # }

# # def get_class_dict_for_region():
# #     class_dict_for_region = {}
# #     for class_name, module_name in _class_modules.items():
# #         module = __import__(f'good_model_working.{module_name}', fromlist=[''])
# #         class_dict_for_region[class_name.lower()] = getattr(module, class_name)
# #     return class_dict_for_region

# storage_efficiency = 0.7

# transmission_efficiency = 0.972

# storage_flow_limit = 0.85

# time_periods = list(range(0,8760))