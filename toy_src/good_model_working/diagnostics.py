import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

## data inputs ##

# 2021 eGRID national fuel mix 
annual_mix_baseline = {
  "Coal": 0.219,
  "Oil": 0.006,
  "Gas": 0.384,
  "Other Fossil": 0.005,
  "Nuclear": 0.189,
  "Hydro": 0.06,
  "Biomass": 0.013,
  "Wind": 0.092,
  "Solar": 0.028,
  "Geothermal": 0.004,
  "Other unknown/purchased fuel": 0.001
}

annual_total_mwh_baseline = 4120144619

# total co2 emissions 2021: 1.6 billion metric tons
annual_emissions_baseline = 1.6 * 1e09


##

def get_hourly_gen_mix(results):

    nodes = results['nodes']

    fuel_mix = {}

    for region, obj_data in nodes.items():
        gen_dict = obj_data.get('generator', {})

        if gen_dict:
 
            capacity_dict = gen_dict.get('capacity', {})

            for gen_type, dispatch_profile in capacity_dict.items(): 

                if gen_type not in fuel_mix: 
                    fuel_mix[gen_type] = {} 

                for hour, capacity in dispatch_profile.items(): 
                    if hour not in fuel_mix[gen_type]:
                        fuel_mix[gen_type][hour] = 0
                
                    fuel_mix[gen_type][hour] += capacity
    
    return fuel_mix
#
# def get_annual_gen_mix(results):
#
#     nodes = results['nodes']
#
#     fuel_mix = {}
#
#     for region, obj_data in nodes.items():
#
#         gen_dict = obj_data.get('generator', {})
#         # solar_dict = obj_data.get('solar', {})
#         # wind_dict = obj_data.get('wind', {})
#
#         if gen_dict:
#
#             capacity_dict = gen_dict.get('capacity', {})
#
#             for gen_type, dispatch_profile in capacity_dict.items():
#
#                 if gen_type not in fuel_mix:
#                     fuel_mix[gen_type] = 0
#
#                     # Show each capacity value under the dispatch profile
#                 for time, capacity in dispatch_profile.items():
#
#                     fuel_mix[gen_type] += capacity


        # if solar_dict:
        #
        #     solar_capacity_dict = solar_dict.get('capacity', {})
        #
        #     total_solar_capacity = sum(solar_capacity_dict.values())
        #
        #     if 'Solar' not in fuel_mix:
        #         fuel_mix['Solar'] = 0
        #
        #     fuel_mix['Solar'] = total_solar_capacity
        #
        # if wind_dict:
        #
        #     wind_capacity_dict = wind_dict.get('capacity', {})
        #
        #     total_wind_capacity = sum(wind_capacity_dict.values())
        #
        #     if 'Wind' not in fuel_mix:
        #         fuel_mix['Wind'] = 0
        #
        #     fuel_mix['Wind'] = total_wind_capacity
        # if solar_dict:
        #     solar_profile_dict = solar_dict.get('profile', {})
        #     total_solar_gen = sum(solar_profile_dict.values())  # Summing generation, not capacity
        #
        #     if 'Solar' not in fuel_mix:
        #         fuel_mix['Solar'] = 0
        #     fuel_mix['Solar'] += total_solar_gen  # Summing over time
        #
        # if wind_dict:
        #     wind_profile_dict = wind_dict.get('profile', {})
        #     total_wind_gen = sum(wind_profile_dict.values())  # Same for wind
        #
        #     if 'Wind' not in fuel_mix:
        #         fuel_mix['Wind'] = 0
        #     fuel_mix['Wind'] += total_wind_gen
    # fuel_mix_sorted = dict(sorted(fuel_mix.items()))
    # return fuel_mix_sorted

def get_annual_gen_mix(results):

    nodes = results.get('nodes', {})
    fuel_mix = {}

    for region, obj_data in nodes.items():

        # Get the generator dictionary for the region
        gen_dict = obj_data.get('generator', {})

        if gen_dict:
            # Get the capacity dictionary for the generators
            capacity_dict = gen_dict.get('capacity', {})

            # Iterate over each generator type and its dispatch profile (time, capacity)
            for gen_type, dispatch_profile in capacity_dict.items():

                # Initialize the fuel mix for this generator type if it doesn't exist
                if gen_type not in fuel_mix:
                    fuel_mix[gen_type] = 0

                # Add up capacities for the same generator type across different regions
                for time, capacity in dispatch_profile.items():
                    fuel_mix[gen_type] += capacity  # Summing the capacity over the time periods
    fuel_mix_sorted = dict(sorted(fuel_mix.items()))
    # Calculate the total sum of the fuel mix capacities
    total_sum = sum(fuel_mix_sorted.values())

    # Print the total sum
    print(f"Total sum of fuel mix capacities: {total_sum}")
    return fuel_mix_sorted

def plot_hourly_gen_mix(hourly_mix):

    '''
        Purpose: Plots a stacked line chart of the hourly of US gen mix
        Inputs: Output from get_hourly_gen_mix
        Output: Stacked line chart
    '''

    # Convert the dictionary to DataFrame
    hourly_df = pd.DataFrame.from_dict(hourly_mix, orient='index').T

    # Extract the generation type
    hourly_df.columns = ['_'.join(col.split('_')[:2]) for col in hourly_df.columns]

    # Sum values with the same generation type
    hourly_df = hourly_df.groupby(level=0, axis=1).sum()

    colors = sns.color_palette("Set2", len(hourly_df.columns))
    color_map = {col: color for col, color in zip(hourly_df.columns, colors)}

    # Prepare data for stackplot
    hours = hourly_df.index.values
    stack_data = [hourly_df[col].values for col in hourly_df.columns]

    # Plot stacked area chart using seaborn's stackplot
    plt.figure(figsize=(12, 6))
    plt.stackplot(hours, stack_data, labels=hourly_df.columns, colors=colors)
    plt.margins(x=0, y=0)

    plt.title('Hourly Generation Mix')
    plt.xlabel('Hour')
    plt.ylabel('Capacity')
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.show()


def display_annual_gen_mix(annual_mix): 

    '''
        Purpose: Plots a pie chart of the total US gen mix
        Inputs: Output from get_annual_gen_mix
        Output: Piechart 
    '''

    annual_df = pd.DataFrame.from_dict(annual_mix, orient='index', columns=['Capacity'])
    total_capacity = annual_df['Capacity'].sum()
    annual_df['Percentage'] = (annual_df['Capacity'] / total_capacity) * 100

    # Format Capacity with two decimal places
    annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)

    # Format Percentage with percentage symbol
    annual_df['Percentage'] = annual_df['Percentage'].apply(lambda x: f'{x:.3f}%')
    print(annual_df.to_string())
#
# def compare_annual_mix_to_baseline(annual_mix):
#
#     baseline_df = pd.DataFrame(annual_mix_baseline.items(), columns=['Resource','Value'])
#     baseline_df['Value'] = baseline_df['Value'] * 100
#     baseline_df['Percentage_Baseline'] = baseline_df['Value'].apply(lambda x: f'{x:.3f}%')
#
#     annual_mix_baseline_keys = [annual_mix_baseline.keys()]
#     annual_mix_keys = [annual_mix.keys()]
#
#     grouped_data = {}
#     for general_key in annual_mix_baseline:
#         grouped_data[general_key] = []
#         for specific_key in annual_mix:
#             if general_key.lower() in specific_key.lower():
#                 grouped_data[general_key].append(specific_key)
#
#     data = []
#     for general_key, specific_keys in grouped_data.items():
#         total_value = sum(annual_mix[key] for key in specific_keys)
#         data.append({"Resource": general_key, "Capacity": total_value})
#
#     annual_df = pd.DataFrame(data)
#     total_capacity = annual_df['Capacity'].sum()
#     annual_df['Percentage_Model'] = (annual_df['Capacity'] / total_capacity) * 100
#
#     # Format Capacity with two decimal places
#     annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)
#
#     # Format Percentage with percentage symbol
#     annual_df['Percentage_Model'] = annual_df['Percentage_Model'].apply(lambda x: f'{x:.3f}%')
#
#     compared_df = pd.merge(baseline_df, annual_df, on='Resource', how='inner')
#     compared_df = compared_df.loc[:, ['Resource', 'Percentage_Baseline', 'Percentage_Model']]
#
#     print(compared_df.to_string())

def compare_annual_mix_to_baseline(annual_mix):

    baseline_df = pd.DataFrame(annual_mix_baseline.items(), columns=['Resource', 'Value'])
    baseline_df['Value'] = baseline_df['Value'] * 100
    baseline_df['Percentage_Baseline'] = baseline_df['Value'].apply(lambda x: f'{x:.3f}%')

    annual_mix_baseline_keys = [annual_mix_baseline.keys()]
    annual_mix_keys = [annual_mix.keys()]

    grouped_data = {}
    for general_key in annual_mix_baseline:
        grouped_data[general_key] = []
        for specific_key in annual_mix:
            # Handle cases for Solar and Wind specifically
            if general_key.lower() == "solar" and "solar" in specific_key.lower():
                grouped_data[general_key].append(specific_key)
            elif general_key.lower() == "wind" and "wind" in specific_key.lower():
                grouped_data[general_key].append(specific_key)
            elif general_key.lower() in specific_key.lower():
                grouped_data[general_key].append(specific_key)

    data = []
    for general_key, specific_keys in grouped_data.items():
        total_value = sum(annual_mix[key] for key in specific_keys)
        data.append({"Resource": general_key, "Capacity": total_value})

    annual_df = pd.DataFrame(data)
    total_capacity = annual_df['Capacity'].sum()
    annual_df['Percentage_Model'] = (annual_df['Capacity'] / total_capacity) * 100

    # Format Capacity with two decimal places
    annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)

    # Format Percentage with percentage symbol
    annual_df['Percentage_Model'] = annual_df['Percentage_Model'].apply(lambda x: f'{x:.3f}%')

    compared_df = pd.merge(baseline_df, annual_df, on='Resource', how='inner')
    compared_df = compared_df.loc[:, ['Resource', 'Percentage_Baseline', 'Percentage_Model']]

    print(compared_df.to_string())

def compare_annual_mix_to_baseline_actual(annual_mix):

    # Convert baseline to DataFrame
    baseline_df = pd.DataFrame(annual_mix_baseline.items(), columns=['Resource', 'Value'])
    baseline_df['Value'] = baseline_df['Value'] * annual_total_mwh_baseline  # Assuming baseline values need to be scaled by 100

    # Extract keys
    annual_mix_baseline_keys = [annual_mix_baseline.keys()]
    annual_mix_keys = [annual_mix.keys()]

    # Group data
    grouped_data = {}
    for general_key in annual_mix_baseline:
        grouped_data[general_key] = []
        for specific_key in annual_mix:
            if general_key.lower() in specific_key.lower():
                grouped_data[general_key].append(specific_key)

    # Calculate capacities
    data = []
    for general_key, specific_keys in grouped_data.items():
        total_value = sum(annual_mix[key] for key in specific_keys)
        data.append({"Resource": general_key, "Capacity": total_value})

    annual_df = pd.DataFrame(data)

    # Format Capacity with two decimal places
    annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)

    # Merge DataFrames
    compared_df = pd.merge((baseline_df), annual_df, on='Resource', how='inner')
    compared_df = compared_df.loc[:, ['Resource', 'Value', 'Capacity']]

    # Rename columns for clarity
    compared_df.columns = ['Resource', 'Baseline_Capacity(8760)', 'Model_Capacity(Period of Study)']

    print(compared_df.to_string())

def get_annual_emissions(results): 

    nodes = results['nodes']

    emissions_total = {}

    for region, obj_data in nodes.items():
        gen_dict = obj_data.get('generator', {})

        if gen_dict:
 
            capacity_dict = gen_dict.get('capacity', {})

            for gen_type, dispatch_profile in capacity_dict.items():

                if gen_type not in fuel_mix: 
                    fuel_mix[gen_type] = 0
            
                for capacity in dispatch_profile.values():

                    fuel_mix[gen_type] += capacity

    return emissions_total
# %%

def get_annual_gen_mix_by_region(results):
    nodes = results['nodes']
    region_fuel_mix = {}

    for region, obj_data in nodes.items():
        fuel_mix = {}
        gen_dict = obj_data.get('generator', {})
        # solar_dict = obj_data.get('solar', {})
        # wind_dict = obj_data.get('wind', {})

        if gen_dict:
            capacity_dict = gen_dict.get('capacity', {})
            for gen_type, dispatch_profile in capacity_dict.items():
                # Check if the gen_type has at least two parts when split by '_'
                parts = gen_type.split('_')
                if len(parts) > 1:
                    fuel_type = parts[1]
                else:
                    fuel_type = gen_type  # Default to the full gen_type if splitting fails
                if fuel_type not in fuel_mix:
                    fuel_mix[fuel_type] = 0
                for capacity in dispatch_profile.values():
                    fuel_mix[fuel_type] += capacity

        # if solar_dict:
        #     solar_capacity_dict = solar_dict.get('capacity', {})
        #     total_solar_capacity = sum(solar_capacity_dict.values())
        #     fuel_mix['Solar'] = total_solar_capacity
        #
        # if wind_dict:
        #     wind_capacity_dict = wind_dict.get('capacity', {})
        #     total_wind_capacity = sum(wind_capacity_dict.values())
        #     fuel_mix['Wind'] = total_wind_capacity

        region_fuel_mix[region] = fuel_mix

    return region_fuel_mix

def get_annual_gen_mix_by_region(results):
    nodes = results['nodes']
    region_fuel_mix = {}

    for region, obj_data in nodes.items():
        fuel_mix = {}
        gen_dict = obj_data.get('generator', {})
        # solar_dict = obj_data.get('solar', {})
        # wind_dict = obj_data.get('wind', {})

        if gen_dict:
            capacity_dict = gen_dict.get('capacity', {})
            for gen_type, dispatch_profile in capacity_dict.items():
                # Check if the gen_type has at least two parts when split by '_'
                parts = gen_type.split('_')
                if len(parts) > 1:
                    fuel_type = parts[1]
                else:
                    fuel_type = gen_type  # Default to the full gen_type if splitting fails
                if fuel_type not in fuel_mix:
                    fuel_mix[fuel_type] = 0
                for capacity in dispatch_profile.values():
                    fuel_mix[fuel_type] += capacity

        # if solar_dict:
        #     solar_capacity_dict = solar_dict.get('capacity', {})
        #     total_solar_capacity = sum(solar_capacity_dict.values())
        #     fuel_mix['Solar'] = total_solar_capacity
        #
        # if wind_dict:
        #     wind_capacity_dict = wind_dict.get('capacity', {})
        #     total_wind_capacity = sum(wind_capacity_dict.values())
        #     fuel_mix['Wind'] = total_wind_capacity

        region_fuel_mix[region] = fuel_mix

    return region_fuel_mix

def plot_stacked_bar_chart(region_fuel_mix, percentage=False):
    regions = list(region_fuel_mix.keys())

    # Categories to be aggregated under "Others"
    other_fuels = {'MSW', 'Fwaste', 'Tires', 'IMPORT', 'Non-Fossil'}

    # Initialize new fuel mix with "Others" category
    new_region_fuel_mix = {}
    for region, fuel_mix in region_fuel_mix.items():
        new_fuel_mix = {'Others': 0}
        for fuel, value in fuel_mix.items():
            if fuel in other_fuels:
                new_fuel_mix['Others'] += value
            else:
                new_fuel_mix[fuel] = value
        new_region_fuel_mix[region] = new_fuel_mix

    # Updated fuel types for plotting
    fuel_types = list({fuel for mix in new_region_fuel_mix.values() for fuel in mix})

    data = {fuel: [new_region_fuel_mix[region].get(fuel, 0) for region in regions] for fuel in fuel_types}

    fig, ax = plt.subplots(figsize=(25, 10))  # Increased width for better readability

    bottom = np.zeros(len(regions))

    # Define a colormap
    colors = plt.get_cmap('tab20').colors

    # Create a color map dictionary for fuel types
    color_map = {fuel: colors[i % len(colors)] for i, fuel in enumerate(fuel_types)}

    for fuel in fuel_types:
        values = data[fuel]
        if percentage:
            total = np.sum([data[ft] for ft in fuel_types], axis=0, dtype=float)
            values = np.divide(values, total, out=np.zeros_like(values, dtype=float), where=total != 0) * 100
        ax.bar(regions, values, label=fuel, bottom=bottom, color=color_map[fuel])
        bottom += np.array(values)

    ax.set_xlabel('Regions')
    ax.set_ylabel('Capacity' if not percentage else 'Percentage')
    ax.set_title('Annual Generation Mix by Region' + (' (Percentage)' if percentage else ''))
    ax.legend(title='Fuel Types', loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3)  # Legend at the bottom in three rows
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()
