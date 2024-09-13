# %%
import os
import pandas as pd
from reading_file import load_data
from merging_file import (merging_data, assign_fuel_costs, cluster_plants, assign_em_rates, long_wide, transmission_func,
                          ffill_ren_cost, ffill_ren_cap, cluster_and_aggregate, long_wide_load, storage_object, solar_object,
                          wind_object, gen_object, load_object, trans_object, plant_capacity, trans_index, renewable_transmission_cost,adjust_coal_generation_cost,
                          convert_keys_to_string, merge_dictionaries_and_format, adjust_nuclear_generation_cost, concat_filtered_plants)
import json
import numpy as np
import pickle
import warnings
warnings.filterwarnings("ignore")
# %% Loading Input Data
(Plant, Transmission, Parsed, Input, NEEDS, Wind_generation_profile, Load, Wind_onshore_capacity,
 Wind_capital_cost, Solar_regional_capacity, Solar_generation_profile, Solar_capital_cost_photov,
 Solar_capacity_factor, Regional_Cost, Unit_Cost) = load_data()
# Merging power plants data
Plant_short = merging_data(Plant, Parsed)
# Assigning fuel cost
Plant_short_fixed_fuelC = assign_fuel_costs(Plant_short)
Plant_short_fixed_fuelC_coal = adjust_coal_generation_cost(Plant_short_fixed_fuelC)
Plant_short_fixed_fuelC_coal_Nuc = adjust_nuclear_generation_cost(Plant_short_fixed_fuelC)
# Replacing missing fuel cost
Plant_short_fixed_Em = assign_em_rates(Plant_short_fixed_fuelC_coal_Nuc)
# Aggregation of power plants
Plants_community, all_regions_clusters = cluster_plants(Plant_short_fixed_Em, 2000, 2000, 10, 4, 1, 1, 1)
# Aggregating the power plants
Plants_ungroup,  Plants_group = cluster_and_aggregate(Plants_community)
Plants_ungroup_extended = concat_filtered_plants(Plants_ungroup, Plant_short)

# Creat a wide version of the input datas
Wind_generation_profile_wide = long_wide(Wind_generation_profile)
Solar_generation_profile_wide = long_wide(Solar_generation_profile)
Transmission_Capacity, Transmission_Energy, Transmission_Cost = transmission_func(Transmission)
Wind_onshore_capacity, Solar_regional_capacity = ffill_ren_cap(Wind_onshore_capacity, Solar_regional_capacity)
Wind_capital_cost, Solar_capital_cost_photov = ffill_ren_cost(Wind_capital_cost, Solar_capital_cost_photov)
Load_wide = long_wide_load(Load)
Transmission_index = trans_index(Transmission_Capacity)
Plant_capacity_dic = plant_capacity(Plant_short)
Wind_trans_capital_cost_final, Solar_trans_capital_cost_photov_final, Wind_capital_cost_copy, Solar_capital_cost_photov_copy = renewable_transmission_cost(Unit_Cost, Regional_Cost, Wind_capital_cost, Solar_capital_cost_photov)
# %%
# Make object-oriented data dictionaries
Region = Load['Region'].unique()
links = trans_object(Transmission_Capacity, Transmission_Cost)
load_oo = load_object(Load_wide)
generator_oo = gen_object(Plants_group)
storage_oo = storage_object(Plants_group)
solar_oo = solar_object(Solar_generation_profile_wide, Solar_capital_cost_photov, Solar_regional_capacity, Solar_capital_cost_photov_copy, Plants_group, Region)
wind_oo = wind_object(Wind_generation_profile_wide, Wind_capital_cost, Wind_onshore_capacity, Wind_capital_cost_copy,  Plants_group, Region)
# %%
# Creating the sets
sets = {
    'region': list(Transmission_Capacity.index.unique()),
    'gen_type': list(Plants_ungroup[~Plants_ungroup["gen_type"].isin(["Solar PV", "Onshore Wind", "Energy Storage"])]["gen_type"].unique()),
    'solar_rc': list(Solar_regional_capacity["New Resource Class"].unique()),
    'wind_rc': list(Wind_onshore_capacity["New Resource Class"].unique()),
    'cost_class': list([1, 2, 3, 4, 5, 6])
}
sorted_sets = {key: sorted(value) for key, value in sets.items()}
# %%
# Creating nodes and links
# Combine all the dictionaries into one list
all_dicts = load_oo + generator_oo + storage_oo + solar_oo + wind_oo
# all_dicts = load_oo + generator_oo + storage_oo
# Merge all dictionaries in the list
nodes = merge_dictionaries_and_format(all_dicts)
# Create a dictionary to hold all objects
all_objects = {'nodes': nodes, 'links': links}
# Convert all nested keys to strings
all_objects_str_keys = convert_keys_to_string(all_objects)
# %%
# Saving output as JSON file
# Define the file path for saving the JSON file
input_file = 'all_input_objects.json'
# Save all objects as JSON
with open(input_file, 'w') as f:
    json.dump(all_objects_str_keys, f)

sorted_sets_str = {key: [str(item) for item in value] if isinstance(value, list) else int(value) if isinstance(value, (np.int64, int)) else str(value) for key, value in sorted_sets.items()}

input_sets_sorted = 'all_input_sets_sorted.json'

# Make sure to use sorted_sets_str for JSON serialization
with open(input_sets_sorted, 'w') as f:
    json.dump(sorted_sets_str, f)

# Specify the path to save the Power Plants pickle file
pickle_file_path1 = 'Plants_group.pickle'
pickle_file_path2 = 'Plants_ungroup_extended.pickle'

# Save the dictionary as a pickle file
with open(pickle_file_path1, 'wb') as f:
    pickle.dump(Plants_group, f)
with open(pickle_file_path2, 'wb') as f:
    pickle.dump(Plants_ungroup_extended, f)
