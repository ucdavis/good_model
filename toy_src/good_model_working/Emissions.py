import pickle
import pandas as pd

# %%
# Specify the path to the pickle file
pickle_file_path1 = '/Users/haniftayarani/good_model/toy_src/results.pickle'
pickle_file_path2 = '/Users/haniftayarani/good_model/Model Input/Plants_group.pickle'
pickle_file_path3 = '/Users/haniftayarani/good_model/Model Input/Plants_ungroup.pickle'
# Load the dictionary from the pickle file
with open(pickle_file_path1, 'rb') as f:
    loaded_results = pickle.load(f)

# Load the dictionary from the pickle file
with open(pickle_file_path2, 'rb') as f:
    Plants_group = pickle.load(f)

with open(pickle_file_path3, 'rb') as f:
    Plants_ungroup = pickle.load(f)


# Extracting the 'links' and 'nodes' dictionaries
links_dict = loaded_results.get('links', {})
nodes_dict = loaded_results.get('nodes', {})


# Function to add emissions with multipliers from the DataFrame
def add_emissions_to_generators(nodes_dict, df_multipliers):
    for region, region_data in nodes_dict.items():
        if 'generator' in region_data:
            # Initialize the 'emissions' dictionary if it does not exist
            if 'emissions' not in region_data['generator']:
                region_data['generator']['emissions'] = {}

            for gen_type, capacity in region_data['generator']['capacity'].items():
                # Get the multipliers for the current region and generator type
                multipliers = df_multipliers[(df_multipliers['RegionName'] == region) & (df_multipliers['gen_type'] == gen_type)]
                if not multipliers.empty:
                    if gen_type not in region_data['generator']['emissions']:
                        region_data['generator']['emissions'][gen_type] = {}
                    for emission_type in ['PLPMTRO', 'PLNOXRTA', 'PLSO2RTA', 'PLCO2RTA', 'PLCH4RTA', 'PLN2ORTA']:
                        multiplier = multipliers[emission_type].values[0]
                        region_data['generator']['emissions'][gen_type][emission_type] = {
                            hour: cap * multiplier for hour, cap in capacity.items()
                        }
    return nodes_dict


def creating_emission_data(df):
    emission_data = df.copy()
    emission_data = emission_data.sort_values(by=["RegionName", "PlantType", "FuelType", "community"])
    emission_data.loc[:, 'gen_type'] = emission_data['PlantType'] + '_' + emission_data['FuelType'] + '_' + emission_data['community'].astype(str)
    return emission_data


emission_data1 = creating_emission_data(Plants_group)
# Add emissions data to the nodes dictionary
nodes_dict1 = add_emissions_to_generators(nodes_dict, emission_data1)
