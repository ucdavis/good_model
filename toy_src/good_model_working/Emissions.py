import pickle
import pandas as pd

# %%
# Specify the path to the pickle file
pickle_file_path1 = '/Users/haniftayarani/good_model/toy_src/results.pickle'
pickle_file_path2 = '/Users/haniftayarani/good_model/Model Input/Plants_group.pickle'
pickle_file_path3 = '/Users/haniftayarani/good_model/Model Input/Plants_community.pickle'
# Load the dictionary from the pickle file
with open(pickle_file_path1, 'rb') as f:
    loaded_results = pickle.load(f)

# Load the dictionary from the pickle file
with open(pickle_file_path2, 'rb') as f:
    Plants_group = pickle.load(f)

with open(pickle_file_path3, 'rb') as f:
    Plants_community = pickle.load(f)


# Extracting the 'links' and 'nodes' dictionaries
links_dict = loaded_results.get('links', {})
nodes_dict = loaded_results.get('nodes', {})


# Function to add 'emissions' key to the same level as 'capacity' and 'cost'
# Define multipliers for each emission type
multipliers = {
    'PLPRMFL': 0.1,
    'PLNOXRTA': 0.2,
    'PLSO2RTA': 0.3,
    'PLCO2RTA': 0.4,
    'PLCH4RTA': 0.5,
    'PLN2ORTA': 0.6
}


# Function to add emissions with multipliers
def add_emissions_to_generators(nodes_dict, multipliers):
    for region, region_data in nodes_dict.items():
        if 'generator' in region_data:
            # Initialize the 'emissions' dictionary if it does not exist
            if 'emissions' not in region_data['generator']:
                region_data['generator']['emissions'] = {}

            for emission_type, multiplier in multipliers.items():
                region_data['generator']['emissions'][emission_type] = {
                    gen_type: {hour: cap * multiplier for hour, cap in capacity.items()}
                    for gen_type, capacity in region_data['generator']['capacity'].items()
                }


# Add emissions data to the nodes dictionary
add_emissions_to_generators(nodes_dict, multipliers)


emission_data = Plants_community.copy()
emission_data = emission_data.sort_values(by=["RegionName", "PlantType", "FuelType", "community"])
emission_data['community_number'] = emission_data.groupby(["RegionName", "PlantType", "FuelType", "community"]).cumcount() + 1
emission_data.loc[:, 'gen_type'] = emission_data['PlantType'] + '_' + emission_data['FuelType'] + '_' + emission_data['community_number'].astype(str)
emission_data.columns
