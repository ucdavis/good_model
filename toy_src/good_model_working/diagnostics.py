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

gen_emissions_inputs = {}



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

def get_annual_gen_mix(results): 

    nodes = results['nodes']

    fuel_mix = {}

    for region, obj_data in nodes.items():
        gen_dict = obj_data.get('generator', {})

        if gen_dict:
 
            capacity_dict = gen_dict.get('capacity', {})

            for gen_type, dispatch_profile in capacity_dict.items():

                if gen_type not in fuel_mix: 
                    fuel_mix[gen_type] = 0
            
                for capacity in dispatch_profile.values():

                    fuel_mix[gen_type] += capacity

    return fuel_mix

def plot_hourly_gen_mix(hourly_mix): 

    '''
        Purpose: Plots a stacked line chart of the hourly of US gen mix
        Inputs: Output from get_hourly_gen_mix
        Output: Stacked line chart
    '''

    hourly_df = pd.DataFrame.from_dict(hourly_mix, orient='index').T

    colors = sns.color_palette("Set2", len(hourly_df.columns))
    color_map = {col: color for col, color in zip(hourly_df.columns, colors)}

    # Prepare data for stackplot
    hours = hourly_df.index.values
    stack_data = [hourly_df[col].values for col in hourly_df.columns]

    # Plot stacked area chart using seaborn's stackplot
    plt.figure(figsize=(12, 6))
    plt.stackplot(hours, stack_data, labels=hourly_df.columns, colors=colors)
    plt.margins(x=0) 
    plt.margins(y=0)  

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

def compare_annual_mix_to_baseline(annual_mix):

    baseline_df = pd.DataFrame(annual_mix_baseline.items(), columns=['Resource','Value'])
    baseline_df['Value'] = baseline_df['Value'] * 100
    baseline_df['Percentage_Baseline'] = baseline_df['Value'].apply(lambda x: f'{x:.3f}%')

    annual_mix_baseline_keys = [annual_mix_baseline.keys()]
    annual_mix_keys = [annual_mix.keys()]

    grouped_data = {}
    for general_key in annual_mix_baseline:
        grouped_data[general_key] = []
        for specific_key in annual_mix:
            if general_key.lower() in specific_key.lower():
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

def get_annual_emissions(results): 

    nodes = results['nodes']

    fuel_mix = {}

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
