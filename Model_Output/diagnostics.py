import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle

class GenerationMixAnalyzer:
    def __init__(self):
        self.pickle_file_path = '/Users/haniftayarani/good_model/toy_src/results.pickle'
        self.annual_mix_baseline = {
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
        self.annual_total_mwh_baseline = 4120144619
        self.annual_emissions_baseline = 1.6 * 1e09
        self.loaded_results = None

    def load_data(self):
        with open(self.pickle_file_path, 'rb') as f:
            self.loaded_results = pickle.load(f)

    def get_hourly_gen_mix(self):
        if not self.loaded_results:
            raise ValueError("No data loaded. Please call 'load_data()' first.")

        nodes = self.loaded_results['nodes']
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

    def get_annual_gen_mix(self):
        if not self.loaded_results:
            raise ValueError("No data loaded. Please call 'load_data()' first.")

        nodes = self.loaded_results['nodes']
        fuel_mix = {}

        for region, obj_data in nodes.items():
            gen_dict = obj_data.get('generator', {})
            if gen_dict:
                capacity_dict = gen_dict.get('capacity', {})
                for gen_type, dispatch_profile in capacity_dict.items():
                    if gen_type not in fuel_mix:
                        fuel_mix[gen_type] = 0
                    for time, capacity in dispatch_profile.items():
                        fuel_mix[gen_type] += capacity

        fuel_mix_sorted = dict(sorted(fuel_mix.items()))
        total_sum = sum(fuel_mix_sorted.values())
        print(f"Total sum of fuel mix capacities: {total_sum}")
        return fuel_mix_sorted

    def get_annual_gen_mix_by_region(self):
        if not self.loaded_results:
            raise ValueError("No data loaded. Please call 'load_data()' first.")

        nodes = self.loaded_results['nodes']
        region_fuel_mix = {}

        for region, obj_data in nodes.items():
            fuel_mix = {}
            gen_dict = obj_data.get('generator', {})
            if gen_dict:
                capacity_dict = gen_dict.get('capacity', {})
                for gen_type, dispatch_profile in capacity_dict.items():
                    parts = gen_type.split('_')
                    fuel_type = parts[1] if len(parts) > 1 else gen_type
                    if fuel_type not in fuel_mix:
                        fuel_mix[fuel_type] = 0
                    for capacity in dispatch_profile.values():
                        fuel_mix[fuel_type] += capacity
            region_fuel_mix[region] = fuel_mix

        return region_fuel_mix

    def plot_hourly_gen_mix(self, hourly_mix):
        '''
        Purpose: Plots a stacked line chart of the hourly US generation mix.
        Inputs: hourly_mix: Dictionary output from get_hourly_gen_mix method
        Output: Stacked line chart and prints the legend as text.
        '''
        # Convert the dictionary to DataFrame
        hourly_df = pd.DataFrame.from_dict(hourly_mix, orient='index').T

        # Check if the DataFrame is non-empty
        if hourly_df.empty:
            print("No data available to plot.")
            return

        # Extract the generation type (modify here if gen_type structure differs)
        hourly_df.columns = [col.split('_')[0] for col in hourly_df.columns]

        # Sum values with the same generation type (in case multiple splits are involved)
        hourly_df = hourly_df.groupby(level=0, axis=1).sum()

        # Normalize the index to numeric values (i.e., hours)
        hourly_df.index = pd.to_numeric(hourly_df.index, errors='coerce')

        # Sort the index (hours) to ensure smooth plotting
        hourly_df = hourly_df.sort_index()

        # Define the order of generation types from bottom to top
        gen_type_order = [
            "Combined Cycle", "Nuclear", "Coal Steam", "Combustion Turbine", "Fossil Waste", "IGCC",
            "Municipal Solid Waste", "O/G Steam", "New Battery Storage", "Non-Fossil Waste", "Biomass",
            "Geothermal", "Hydro", "Wind", "Solar", "IMPORT", "Tires"
        ]

        # Reorder the columns according to the specified order
        # Keep only the generation types that exist in hourly_df
        gen_type_order = [gen_type for gen_type in gen_type_order if gen_type in hourly_df.columns]
        hourly_df = hourly_df[gen_type_order]

        # Generate distinct colors using a larger palette
        colors = sns.color_palette("tab20", len(hourly_df.columns))

        # Prepare data for stackplot
        hours = hourly_df.index.values
        stack_data = [hourly_df[col].values for col in hourly_df.columns]

        # Plot stacked area chart
        plt.figure(figsize=(12, 6))
        plt.stackplot(hours, stack_data, labels=hourly_df.columns, colors=colors)
        plt.margins(x=0, y=0)
        plt.title('Hourly Generation Mix')
        plt.xlabel('Hour')
        plt.ylabel('Capacity (MW)')
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
        plt.tight_layout()
        plt.show()

        # # Print the legend (generation types) as text below the plot
        # print("\nLegend (Generation Types):")
        # for col in hourly_df.columns:
        #     print(f"- {col}")

    def display_annual_gen_mix(self, annual_mix):
        annual_df = pd.DataFrame.from_dict(annual_mix, orient='index', columns=['Capacity'])
        total_capacity = annual_df['Capacity'].sum()
        annual_df['Percentage'] = (annual_df['Capacity'] / total_capacity) * 100
        annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)
        annual_df['Percentage'] = annual_df['Percentage'].apply(lambda x: f'{x:.3f}%')
        print(annual_df.to_string())

    def compare_annual_mix_to_baseline(self, annual_mix):
        baseline_df = pd.DataFrame(self.annual_mix_baseline.items(), columns=['Resource', 'Value'])
        baseline_df['Value'] = baseline_df['Value'] * 100
        baseline_df['Percentage_Baseline'] = baseline_df['Value'].apply(lambda x: f'{x:.3f}%')

        grouped_data = {}
        for general_key in self.annual_mix_baseline:
            grouped_data[general_key] = []
            for specific_key in annual_mix:
                if general_key.lower() == "solar" and "solar_current" in specific_key.lower():
                    grouped_data[general_key].append(specific_key)
                elif general_key.lower() == "wind" and "wind_current" in specific_key.lower():
                    grouped_data[general_key].append(specific_key)
                elif general_key.lower() in specific_key.lower():
                    grouped_data[general_key].append(specific_key)

        # Handle new solar and wind separately
        if 'Wind_New' in annual_mix:
            grouped_data['Wind_New'] = ['Wind_New']
        if 'Solar_New' in annual_mix:
            grouped_data['Solar_New'] = ['Solar_New']

        data = []
        for general_key, specific_keys in grouped_data.items():
            total_value = sum(annual_mix[key] for key in specific_keys)
            data.append({"Resource": general_key, "Capacity": total_value})

        annual_df = pd.DataFrame(data)
        total_capacity = annual_df['Capacity'].sum()
        annual_df['Percentage_Model'] = (annual_df['Capacity'] / total_capacity) * 100
        annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)
        annual_df['Percentage_Model'] = annual_df['Percentage_Model'].apply(lambda x: f'{x:.3f}%')

        # Add Wind_New and Solar_New with no baseline equivalent
        baseline_rows = ['Wind_New', 'Solar_New']
        for new_category in baseline_rows:
            if new_category in annual_df['Resource'].values:
                new_row = pd.DataFrame({'Resource': [new_category], 'Percentage_Baseline': ['N/A']})
                baseline_df = pd.concat([baseline_df, new_row], ignore_index=True)

        # Merge and format the output
        compared_df = pd.merge(baseline_df, annual_df, on='Resource', how='outer')
        compared_df = compared_df.loc[:, ['Resource', 'Percentage_Baseline', 'Percentage_Model']]

        print(compared_df.to_string())

    def plot_stacked_bar_chart(self, region_fuel_mix, percentage=False):
        regions = list(region_fuel_mix.keys())
        other_fuels = {'MSW', 'Fwaste', 'Tires', 'IMPORT', 'Non-Fossil'}

        new_region_fuel_mix = {}
        for region, fuel_mix in region_fuel_mix.items():
            new_fuel_mix = {'Others': 0}
            for fuel, value in fuel_mix.items():
                if fuel in other_fuels:
                    new_fuel_mix['Others'] += value
                else:
                    new_fuel_mix[fuel] = value
            new_region_fuel_mix[region] = new_fuel_mix

        fuel_types = list({fuel for mix in new_region_fuel_mix.values() for fuel in mix})

        data = {fuel: [new_region_fuel_mix[region].get(fuel, 0) for region in regions] for fuel in fuel_types}
        fig, ax = plt.subplots(figsize=(25, 10))

        bottom = np.zeros(len(regions))
        colors = plt.get_cmap('tab20').colors
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
        ax.legend(title='Fuel Types', loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=3)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
