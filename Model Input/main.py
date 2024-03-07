# %%
from reading_file import load_data
from merging_file import (merging_data, assign_fuel_costs, fill_missing_fuel_costs, assign_em_rates, long_wide, transmission_func,
                          ffill_ren_cost, ffill_ren_cap, cluster_and_aggregate, long_wide_load, load_dic, wind_cap_dic, wind_cost_dic, solar_cap_dic,
                          solar_cost_dic, storage_object, solar_object, wind_object, gen_object, load_object,trans_object, transmission_dic1, transmission_dic2, cp_dic, plant_dic, plant_capacity, trans_index, renewable_transmission_cost)
import json
import numpy as np
import gzip
import shutil
# %% Loading Input Data
(Plant, Transmission, Parsed, Input, NEEDS, Wind_generation_profile, Load, Wind_onshore_capacity,
 Wind_capital_cost, Solar_regional_capacity, Solar_generation_profile, Solar_capital_cost_photov, Solar_capacity_factor, Regional_Cost, Unit_Cost) = load_data()


Plant_short = merging_data(Plant, Parsed)

# Assigning fuel cost
Plant_short = assign_fuel_costs(Plant_short)
# Replacing missing fuel cost
Plant_short = fill_missing_fuel_costs(Plant_short, Transmission)
# Replacing missing fuel cost
Plant_short = assign_em_rates(Plant_short)
# Aggregating the power plants
Plants_ungroup,  Plants_group = cluster_and_aggregate(Plant_short, num_bins=20)
# Converting to data dictionary
Plants_Dic = plant_dic(Plants_group)


Wind_generation_profile_wide = long_wide(Wind_generation_profile)
Solar_generation_profile_wide = long_wide(Solar_generation_profile)

Transmission_Capacity, Transmission_Energy, Transmission_Cost = transmission_func(Transmission)

Wind_onshore_capacity, Solar_regional_capacity = ffill_ren_cap(Wind_onshore_capacity, Solar_regional_capacity)
Wind_capital_cost, Solar_capital_cost_photov = ffill_ren_cost(Wind_capital_cost, Solar_capital_cost_photov)

Load_wide = long_wide_load(Load)

load_final = load_dic(Load_wide)

Wind_onshore_capacity_final = wind_cap_dic(Wind_onshore_capacity)
Wind_capital_cost_final = wind_cost_dic(Wind_capital_cost)

Solar_regional_capacity_final = solar_cap_dic(Solar_regional_capacity)
Solar_capital_cost_photov_final = solar_cost_dic(Solar_capital_cost_photov)

Transmission_Capacity_final = transmission_dic1(Transmission_Capacity)
Transmission_Energy_final = transmission_dic1(Transmission_Energy)

Solar_capacity_factor_final = cp_dic(Solar_generation_profile_wide)
Wind_capacity_factor_final = cp_dic(Wind_generation_profile_wide)


Transmission_Capacity_dic = transmission_dic1(Transmission_Capacity)
Transmission_Energy_dic = transmission_dic1(Transmission_Energy)

Transmission_Cost_dic = transmission_dic2(Transmission_Cost)

Transmission_index = trans_index(Transmission_Capacity)

Plant_capacity_dic = plant_capacity(Plant_short)

Wind_trans_capital_cost_final, Solar_trans_capital_cost_photov_final, Wind_capital_cost_copy, Solar_capital_cost_photov_copy = renewable_transmission_cost(Unit_Cost, Regional_Cost, Wind_capital_cost, Solar_capital_cost_photov)

# %%
# Make a copy of the DataFrame
Region = Load['Region'].unique()
transmision_oo = trans_object(Transmission_Capacity, Transmission_Cost)
load_oo = load_object(Load_wide)
generator_oo = gen_object(Plants_group)
storage_oo = storage_object(Plants_group)
solar_oo = solar_object(Solar_generation_profile_wide, Solar_capital_cost_photov, Solar_regional_capacity, Solar_capital_cost_photov_copy, Plants_group, Region)
wind_oo = wind_object(Wind_generation_profile_wide, Wind_capital_cost, Wind_onshore_capacity, Wind_capital_cost_copy,  Plants_group, Region)

# %% Saving output as JSON file
# Define the file path for saving the JSON file
input_file = 'all_input_objects.json'
output_file = 'all_input_objects.json.gz'

# Define an empty list to hold all dictionaries
all_dicts = []

# Append each dictionary to the list
all_dicts.extend(load_oo)
all_dicts.extend(generator_oo)
all_dicts.extend(storage_oo)
all_dicts.extend(solar_oo)
all_dicts.extend(wind_oo)

# Create a dictionary to hold all objects
all_objects = {
    'nodal_object': all_dicts,
    'link_object': transmision_oo,
}


def convert_keys_to_string(obj):
    if isinstance(obj, dict):
        return {str(key) if not isinstance(key, np.int64) else str(int(key)): convert_keys_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_string(element) for element in obj]
    else:
        return obj


# Convert all nested keys to strings
all_objects_str_keys = convert_keys_to_string(all_objects)


# Save all objects as JSON
with open(input_file, 'w') as all_objects_file:
    json.dump(all_objects_str_keys, all_objects_file)

# Compress the JSON file using gzip
with open(input_file, 'rb') as f_in:
    with gzip.open(output_file, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)


# # Read the JSON file
# with open(input_file, 'r') as all_objects_file:
#     loaded_objects = json.load(all_objects_file)
#
#
# # Open the gzip-compressed file for reading
# with gzip.open(input_file, 'rb') as f:
#     # Read the contents of the file
#     compressed_data = f.read()
#
# # Decode the compressed data as JSON
# json_data = json.loads(compressed_data)

# final 