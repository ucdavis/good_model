# %%
import os
from reading_file import load_data
from merging_file import (merging_data, assign_fuel_costs, cluster_plants, adjust_coal_generation_cost, assign_em_rates, long_wide, transmission_func,
                          ffill_ren_cost, ffill_ren_cap, cluster_and_aggregate, long_wide_load, load_dic, wind_cap_dic, wind_cost_dic, solar_cap_dic,
                          solar_cost_dic, storage_object, solar_object, wind_object, gen_object, load_object, trans_object, transmission_dic1, cp_dic, plant_dic, plant_capacity, trans_index, renewable_transmission_cost)
import json
import numpy as np
# %% Loading Input Data
(Plant, Transmission, Parsed, Input, NEEDS, Wind_generation_profile, Load, Wind_onshore_capacity,
 Wind_capital_cost, Solar_regional_capacity, Solar_generation_profile, Solar_capital_cost_photov, Solar_capacity_factor, Regional_Cost, Unit_Cost) = load_data()

Plant_short = merging_data(Plant, Parsed)
# Assigning fuel cost
Plant_short_fixed_fuelC = assign_fuel_costs(Plant_short)
# Assuming merged_short is the DataFrame obtained from the assign_fuel_costs function
# Plant_short_fixed_allC = adjust_coal_generation_cost(Plant_short_fixed_fuelC)
# Replacing missing fuel cost
Plant_short_fixed_Em = assign_em_rates(Plant_short_fixed_fuelC)

# aggregation of power plants
Plants_community, all_regions_clusters = cluster_plants(Plant_short_fixed_Em, 2000, 2000, 10, 3, 1, 1, 1)
# Aggregating the power plants
Plants_ungroup,  Plants_group = cluster_and_aggregate(Plants_community)

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
Transmission_index = trans_index(Transmission_Capacity)
Plant_capacity_dic = plant_capacity(Plant_short)
Wind_trans_capital_cost_final, Solar_trans_capital_cost_photov_final, Wind_capital_cost_copy, Solar_capital_cost_photov_copy = renewable_transmission_cost(Unit_Cost, Regional_Cost, Wind_capital_cost, Solar_capital_cost_photov)
# %%
# Make a copy of the DataFrame
Region = Load['Region'].unique()
links = trans_object(Transmission_Capacity, Transmission_Cost)
load_oo = load_object(Load_wide)
generator_oo = gen_object(Plants_group)
storage_oo = storage_object(Plants_group)
solar_oo = solar_object(Solar_generation_profile_wide, Solar_capital_cost_photov, Solar_regional_capacity, Solar_capital_cost_photov_copy, Plants_group, Region)
wind_oo = wind_object(Wind_generation_profile_wide, Wind_capital_cost, Wind_onshore_capacity, Wind_capital_cost_copy,  Plants_group, Region)

# %% sets
sets = {
    'region': list(Transmission_Capacity.index.unique()),
    'gen_type': list(Plants_ungroup[~Plants_ungroup["gen_type"].isin(["Solar PV", "Onshore Wind", "Energy Storage"])]["gen_type"].unique()),
    'solar_rc': list(Solar_regional_capacity["New Resource Class"].unique()),
    'wind_rc': list(Wind_onshore_capacity["New Resource Class"].unique()),
    'cost_class': list([1, 2, 3, 4, 5, 6])
}
sorted_sets = {key: sorted(value) for key, value in sets.items()}
# %% Saving output as JSON file
# Define the file path for saving the JSON file
input_file = 'all_input_objects.json'
# Define an empty dictionary to hold merged dictionaries grouped by "id"
merged_dict = {}


# Define a list of all dictionaries
def merge_dictionaries_and_format(list_of_dicts):
    # Temporary dictionary to hold the merged data
    temp_merged_dict = {}

    # Final list to hold the formatted output
    formatted_list = []

    # Iterate over the list of dictionaries
    for single_dict in list_of_dicts:
        id = single_dict['id']
        dependents = single_dict['dependents']

        if id in temp_merged_dict:
            temp_merged_dict[id]['dependents'].extend(dependents)
        else:
            temp_merged_dict[id] = {'id': id, 'dependents': dependents}

    # Convert the merged dictionary into the desired list format
    for id, info in temp_merged_dict.items():
        formatted_list.append({'id': id, 'dependents': info['dependents']})

    return formatted_list

# Assuming load_oo, generator_oo, storage_oo, solar_oo, and wind_oo are defined with the same structure...


# Combine all the dictionaries into one list
all_dicts = load_oo + generator_oo + storage_oo + solar_oo + wind_oo
# all_dicts = load_oo + generator_oo + storage_oo

# Merge all dictionaries in the list
nodes = merge_dictionaries_and_format(all_dicts)

# Create a dictionary to hold all objects
all_objects = {
    'nodes': nodes,
    'links': links,
}


# Convert all nested keys to strings
def convert_keys_to_string(obj):
    if isinstance(obj, dict):
        return {str(key) if not isinstance(key, (np.int64, np.int32)) else int(key): convert_keys_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_string(element) for element in obj]
    else:
        return obj


all_objects_str_keys = convert_keys_to_string(all_objects)

# %%

# Save all objects as JSON
with open(input_file, 'w') as f:
    json.dump(all_objects_str_keys, f)

sorted_sets_str = {key: [str(item) for item in value] if isinstance(value, list) else int(value) if isinstance(value, (np.int64, int)) else str(value) for key, value in sorted_sets.items()}

input_sets_sorted = 'all_input_sets_sorted.json'

# Make sure to use sorted_sets_str for JSON serialization
with open(input_sets_sorted, 'w') as f:
    json.dump(sorted_sets_str, f)


# %%
