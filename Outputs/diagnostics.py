import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
# %%

class GenerationMixAnalyzer:
    # Initializes the GenerationMixAnalyzer with file paths, baseline data, and placeholders for loaded data.
    def __init__(self):
        # Path to the pickle file containing generation data results
        self.pickle_file_path = '/Users/haniftayarani/good_model/Model_Main/results.pickle'

        # Baseline generation mix percentages by fuel type for comparison
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

        # Baseline for total annual generation (MWh) and emissions (tons CO2)
        self.annual_total_mwh_baseline = 4120144619
        self.annual_emissions_baseline = 1.6 * 1e09

        # Placeholder to store loaded results after calling load_data()
        self.loaded_results = None

    # load_data: Loads generation data from a pickle file into the loaded_results attribute.
    def load_data(self):
        with open(self.pickle_file_path, 'rb') as f:
            self.loaded_results = pickle.load(f)

    # get_hourly_gen_mix: Calculates the hourly generation mix by fuel type.
    # Raises an error if data is not loaded, so load_data() must be called first.
    # Returns: A dictionary with fuel types as keys and dictionaries of hourly capacities as values.
    def get_hourly_gen_mix(self):
        if not self.loaded_results:
            raise ValueError("No data loaded. Please call 'load_data()' first.")

        # Retrieve node data containing generation information
        nodes = self.loaded_results['nodes']
        fuel_mix = {}

        # Iterate through each region, extracting generation capacity data by fuel type and hour
        for region, obj_data in nodes.items():
            gen_dict = obj_data.get('generator', {})
            if gen_dict:
                capacity_dict = gen_dict.get('capacity', {})
                for gen_type, dispatch_profile in capacity_dict.items():
                    # Initialize fuel type in fuel_mix if it doesn't exist
                    if gen_type not in fuel_mix:
                        fuel_mix[gen_type] = {}
                    # Add capacity data for each hour to the fuel_mix dictionary
                    for hour, capacity in dispatch_profile.items():
                        if hour not in fuel_mix[gen_type]:
                            fuel_mix[gen_type][hour] = 0
                        fuel_mix[gen_type][hour] += capacity
        return fuel_mix

    # get_annual_gen_mix: Calculates the total annual generation mix across all regions.
    # Raises an error if data is not loaded, so load_data() must be called first.
    # Returns: A dictionary with fuel types as keys and total annual capacities as values.
    def get_annual_gen_mix(self):
        if not self.loaded_results:
            raise ValueError("No data loaded. Please call 'load_data()' first.")

        # Retrieve node data containing generation information
        nodes = self.loaded_results['nodes']
        fuel_mix = {}

        # Iterate over each region to aggregate capacity data by fuel type
        for region, obj_data in nodes.items():
            gen_dict = obj_data.get('generator', {})
            if gen_dict:
                capacity_dict = gen_dict.get('capacity', {})
                for gen_type, dispatch_profile in capacity_dict.items():
                    # Initialize fuel type in fuel_mix if it doesn't exist
                    if gen_type not in fuel_mix:
                        fuel_mix[gen_type] = 0
                    # Accumulate total capacity for each time period
                    for time, capacity in dispatch_profile.items():
                        fuel_mix[gen_type] += capacity

        # Sort the dictionary by fuel type and calculate the total capacity sum
        fuel_mix_sorted = dict(sorted(fuel_mix.items()))
        total_sum = sum(fuel_mix_sorted.values())
        print(f"Total sum of fuel mix capacities: {total_sum}")
        return fuel_mix_sorted

    # get_annual_gen_mix_by_region: Calculates the annual generation mix for each region,\
    # tracking both current and new capacities by fuel type.
    # Raises an error if data is not loaded, so load_data() must be called first.
    # Returns: A dictionary with regions as keys, each containing a sub-dictionary with fuel types\
    # and their total annual capacities.
    def get_annual_gen_mix_by_region(self):
        if not self.loaded_results:
            raise ValueError("No data loaded. Please call 'load_data()' first.")

        # Retrieve node data containing generation information
        nodes = self.loaded_results['nodes']
        region_fuel_mix = {}

        # Iterate over each region to aggregate capacity data by fuel type and status (Current or New)
        for region, obj_data in nodes.items():
            fuel_mix = {}
            gen_dict = obj_data.get('generator', {})
            if gen_dict:
                capacity_dict = gen_dict.get('capacity', {})
                for gen_type, dispatch_profile in capacity_dict.items():
                    # Split gen_type to differentiate between 'current' and 'new' generation capacities
                    parts = gen_type.split('_')
                    base_fuel_type = parts[0]  # Primary fuel type (e.g., Solar, Wind)
                    # Defaults to 'Current' if no status is specified
                    status = parts[1] if len(parts) > 1 else 'Current'

                    # Create a unique fuel key to track both new and current capacities for each fuel type
                    fuel_key = f"{base_fuel_type}_{status}"

                    # Initialize fuel type in fuel_mix if it doesn't exist
                    if fuel_key not in fuel_mix:
                        fuel_mix[fuel_key] = 0

                    # Accumulate total capacity across all time periods
                    for capacity in dispatch_profile.values():
                        fuel_mix[fuel_key] += capacity

            # Assign the fuel mix dictionary to the region in region_fuel_mix
            region_fuel_mix[region] = fuel_mix

        return region_fuel_mix

    # plot_hourly_gen_mix: Plots a stacked area chart showing the hourly generation mix by fuel type.
    # Parameters:
    # - hourly_mix: Dictionary of hourly generation data, output from get_hourly_gen_mix method.
    # Output: Displays a stacked area chart of generation mix and prints the legend as text.
    def plot_hourly_gen_mix(self, hourly_mix):
        # Purpose: Plots a stacked line chart of the hourly US generation mix.
        # Inputs: hourly_mix: Dictionary output from get_hourly_gen_mix method
        # Output: Stacked line chart and prints the legend as text.
        #
        # Convert the dictionary to a DataFrame, with hours as the index and fuel types as columns
        hourly_df = pd.DataFrame.from_dict(hourly_mix, orient='index').T

        # Check if the DataFrame is non-empty; print a message and exit if it is empty
        if hourly_df.empty:
            print("No data available to plot.")
            return

        # Extract generation type from column names (e.g., removing any suffixes from gen_type)
        hourly_df.columns = [col.split('_')[0] for col in hourly_df.columns]

        # Sum values with the same generation type (e.g., if multiple entries for 'Coal')
        hourly_df = hourly_df.groupby(level=0, axis=1).sum()

        # Convert index (hours) to numeric values to ensure correct plotting
        hourly_df.index = pd.to_numeric(hourly_df.index, errors='coerce')

        # Sort the index to ensure the data is in chronological order for smooth plotting
        hourly_df = hourly_df.sort_index()

        # Define the order in which generation types will appear on the plot, from bottom to top
        gen_type_order = [
            "Combined Cycle", "Nuclear", "Coal Steam", "Combustion Turbine", "Fossil Waste", "IGCC",
            "Municipal Solid Waste", "O/G Steam", "New Battery Storage", "Non-Fossil Waste", "Biomass",
            "Geothermal", "Hydro", "Wind", "Solar", "IMPORT", "Tires"
        ]

        # Reorder columns in the DataFrame according to gen_type_order and keep only those that exist in the data
        gen_type_order = [gen_type for gen_type in gen_type_order if gen_type in hourly_df.columns]
        hourly_df = hourly_df[gen_type_order]

        # Generate a distinct color palette for each generation type
        colors = sns.color_palette("tab20", len(hourly_df.columns))

        # Prepare data for the stacked area plot
        hours = hourly_df.index.values  # X-axis (hours)
        stack_data = [hourly_df[col].values for col in hourly_df.columns]  # Y-axis (generation capacity)

        # Plot a stacked area chart
        plt.figure(figsize=(12, 6))
        plt.stackplot(hours, stack_data, labels=hourly_df.columns, colors=colors)
        plt.margins(x=0, y=0)  # Remove margins for a tighter fit
        plt.title('Hourly Generation Mix')  # Set the title of the plot
        plt.xlabel('Hour')  # Label for the X-axis
        plt.ylabel('Capacity (MW)')  # Label for the Y-axis
        plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')  # Position the legend outside the plot
        plt.tight_layout()  # Adjust the layout to ensure all elements fit well
        plt.show()  # Display the plot

    # display_annual_gen_mix: Displays the annual generation mix as a table, showing both capacity\
    # and percentage for each fuel type.
    # Parameters:
    # - annual_mix: Dictionary with fuel types as keys and annual capacities as values.
    # Output: Prints a formatted DataFrame of annual generation mix, including percentage share of each fuel type.
    def display_annual_gen_mix(self, annual_mix):
        # Convert annual_mix dictionary to a DataFrame, setting the fuel type as the index\
        # and capacity as the column
        annual_df = pd.DataFrame.from_dict(annual_mix, orient='index', columns=['Capacity'])
        # Calculate the total capacity to determine each fuel type's percentage share
        total_capacity = annual_df['Capacity'].sum()
        # Calculate the percentage of total capacity for each fuel type
        annual_df['Percentage'] = (annual_df['Capacity'] / total_capacity) * 100
        # Format the capacity values to two decimal places for display
        annual_df['Capacity'] = annual_df['Capacity'].apply('{:.2f}'.format)
        # Format the percentage values to three decimal places and add a percentage sign
        annual_df['Percentage'] = annual_df['Percentage'].apply(lambda x: f'{x:.3f}%')
        # Print the DataFrame as a string to display the table format in the console
        print(annual_df.to_string())

    # compare_annual_mix_to_baseline: Compares the annual generation mix from the model with\
    # a baseline generation mix.
    # Parameters:
    # - annual_mix: Dictionary with fuel types as keys and annual capacities as values.
    # Output: Prints a DataFrame showing model vs. baseline percentages for each fuel type.
    def compare_annual_mix_to_baseline(self, annual_mix):
        # Convert the baseline mix to a DataFrame with resources as rows and baseline values as percentages
        baseline_df = pd.DataFrame(self.annual_mix_baseline.items(), columns=['Resource', 'Value'])
        baseline_df['Value_Percent'] = baseline_df['Value'] * 100
        baseline_df['Percentage_Baseline'] = baseline_df['Value_Percent'].apply(lambda x: f'{x:.3f}%')

        # Initialize a dictionary to group similar resource types from the model to the baseline categories
        grouped_data = {}
        for general_key in self.annual_mix_baseline:
            grouped_data[general_key] = []
            for specific_key in annual_mix:
                # Group 'Solar' and 'Wind' specifically by 'Current' status in the key
                if general_key == "Solar" and "Solar_Current" in specific_key:
                    grouped_data[general_key].append(specific_key)
                elif general_key == "Wind" and "Wind_Current" in specific_key:
                    grouped_data[general_key].append(specific_key)
                elif general_key.lower() in specific_key.lower():
                    grouped_data[general_key].append(specific_key)

        # Handle new capacities for Solar and Wind, not included in the baseline, separately
        grouped_data['Wind_New'] = ['Wind_New'] if 'Wind_New' in annual_mix else []
        grouped_data['Solar_New'] = ['Solar_New'] if 'Solar_New' in annual_mix else []

        # Create a list of dictionaries to store each resource's total capacity for the model's annual mix
        data = []
        for general_key, specific_keys in grouped_data.items():
            # Exclude 'Solar' and 'Wind' new capacities from the sum
            if general_key not in ["Solar", "Wind"]:
                total_value = sum(annual_mix[key] for key in specific_keys)
            else:
                # Sum only 'Current' values for Solar and Wind when calculating their total capacity
                total_value = sum(annual_mix[key] for key in specific_keys if key == f"{general_key}_Current")
            data.append({"Resource": general_key, "Capacity": total_value})

        # Convert the model's grouped data into a DataFrame and calculate capacity percentages
        annual_df = pd.DataFrame(data)
        total_capacity = annual_df['Capacity'].sum()
        annual_df['Percentage_Model'] = (annual_df['Capacity'] / total_capacity) * 100
        annual_df['Percentage_Model'] = annual_df['Percentage_Model'].apply(lambda x: f'{x:.3f}%')

        # Add entries for Wind_New and Solar_New in the baseline with no baseline equivalent
        baseline_rows = ['Wind_New', 'Solar_New']
        for new_category in baseline_rows:
            if new_category in annual_df['Resource'].values:
                new_row = pd.DataFrame({
                    'Resource': [new_category],
                    'Value': [None],
                    'Value_Percent': [None],
                    'Percentage_Baseline': ['N/A']  # Mark these entries as not applicable in baseline
                })
                baseline_df = pd.concat([baseline_df, new_row], ignore_index=True)

        # Convert baseline values to absolute MWh using the total MWh baseline
        baseline_df["Value"] = baseline_df["Value"] * self.annual_total_mwh_baseline

        # Merge the baseline and model data on 'Resource' for side-by-side comparison of percentages
        compared_df = pd.merge(baseline_df, annual_df, on='Resource', how='outer')
        compared_df = compared_df[['Resource', 'Percentage_Baseline', 'Percentage_Model']]

        # Print the comparison DataFrame as a formatted string to the console
        print(compared_df.to_string())

    # plot_stacked_bar_chart: Plots a stacked bar chart of the annual generation mix by region.
    # Parameters:
    # - region_fuel_mix: Dictionary with regions as keys and dictionaries of fuel types and capacities as values.
    # - percentage: Boolean flag to plot values as percentages if True, or as absolute MWh if False.
    # Output: Displays a stacked bar chart of the generation mix by region,\
    # with an option to show values in percentages.
    def plot_stacked_bar_chart(self, region_fuel_mix, percentage=False):
        # Extract the list of regions from the region_fuel_mix keys
        regions = list(region_fuel_mix.keys())

        # Define fuel types to be grouped under 'Others'
        other_fuels = {'MSW', 'Fwaste', 'Tires', 'IMPORT', 'Non-Fossil'}

        # Create a new dictionary to store adjusted fuel mix data, grouping certain fuel types as 'Others'
        new_region_fuel_mix = {}
        for region, fuel_mix in region_fuel_mix.items():
            new_fuel_mix = {'Others': 0}
            for fuel, value in fuel_mix.items():
                # Sum values of 'other' fuel types under 'Others'
                if fuel in other_fuels:
                    new_fuel_mix['Others'] += value
                else:
                    new_fuel_mix[fuel] = value
            new_region_fuel_mix[region] = new_fuel_mix

        # Get a list of unique fuel types across all regions, including 'Others'
        fuel_types = list({fuel for mix in new_region_fuel_mix.values() for fuel in mix})

        # Organize data for plotting: fuel type as keys, and values are lists of capacities per region
        data = {fuel: [new_region_fuel_mix[region].get(fuel, 0) for region in regions] for fuel in fuel_types}
        fig, ax = plt.subplots(figsize=(25, 10))

        # Initialize the bottom of each bar at zero for stacking purposes
        bottom = np.zeros(len(regions))

        # Generate distinct colors for each fuel type using a color map
        colors = plt.get_cmap('tab20').colors
        color_map = {fuel: colors[i % len(colors)] for i, fuel in enumerate(fuel_types)}

        # Plot each fuel type as a segment in the stacked bar chart
        for fuel in fuel_types:
            values = data[fuel]
            if percentage:
                # Calculate total capacity for each region and convert values to percentages
                total = np.sum([data[ft] for ft in fuel_types], axis=0, dtype=float)
                values = np.divide(values, total, out=np.zeros_like(values, dtype=float), where=total != 0) * 100
            ax.bar(regions, values, label=fuel, bottom=bottom, color=color_map[fuel])
            # Update bottom position for the next fuel type to stack on top
            bottom += np.array(values)

        # Label the X and Y axes
        ax.set_xlabel('Regions', fontsize=16)
        ax.set_ylabel('Capacity (MWh)' if not percentage else 'Percentage (%)', fontsize=16)

        # Set the title, appending '(Percentage)' if the values are shown as percentages
        ax.set_title('Annual Generation Mix by Region' + (' (Percentage)' if percentage else ''), fontsize=16)

        # Configure legend for fuel types with multiple columns below the plot
        ax.legend(title='Plant & Fuel Types', loc='upper center',
                  bbox_to_anchor=(0.5, -0.4), ncol=6, fontsize=14, title_fontsize=16)

        # Rotate the X-axis labels for readability
        plt.xticks(rotation=45, ha='right', fontsize=14)
        plt.yticks(fontsize=16)

        # Adjust layout to fit all components without overlap
        plt.tight_layout()

        # Display the stacked bar chart
        plt.show()

    # get_total_solar_wind_capacity: Calculates and prints the total installed\
    # capacity for solar and wind energy across all regions.
    # Output: Prints the total capacities for solar and wind power in MW.
    def get_total_solar_wind_capacity(self):
        # Initialize total capacity counters for solar and wind
        total_solar_capacity = 0
        total_wind_capacity = 0

        # Loop through each region (node) in the loaded results
        for region, region_data in self.loaded_results["nodes"].items():
            # Check if the region contains generator capacity data
            if "generator" in region_data and "capacity" in region_data["generator"]:
                capacities = region_data["generator"]["capacity"]

                # Add up solar capacity for all available time periods, if it exists in the data
                if "Solar_Current" in capacities:
                    total_solar_capacity += sum(capacities["Solar_New"].values())

                # Add up wind capacity for all available time periods, if it exists in the data
                if "Wind_Current" in capacities:
                    total_wind_capacity += sum(capacities["Wind_New"].values())

        # Print the calculated total capacities for solar and wind
        print(f"Total Solar Capacity: {total_solar_capacity}")
        print(f"Total Wind Capacity: {total_wind_capacity}")
