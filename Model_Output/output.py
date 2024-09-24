import pickle
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import matplotlib.pyplot as plt
# %%


class ModelOutput:
    def __init__(self):


        self.pickle_file_path1 = '/Users/haniftayarani/good_model/toy_src/results.pickle'
        self.pickle_file_path2 = '/Users/haniftayarani/good_model/Model Input/Plants_group.pickle'
        self.pickle_file_path3 = '/Users/haniftayarani/good_model/Model Input/Plants_ungroup_extended.pickle'
        self.shapefile = '/Users/haniftayarani/good_model/Model Input/cb_2018_us_county_5m'
        self.shapefile_state = '/Users/haniftayarani/good_model/Model Input/cb_2018_us_state_5m'

        self.state_fips_to_name = {
            '01': 'Alabama',
            '02': 'Alaska',
            '04': 'Arizona',
            '05': 'Arkansas',
            '06': 'California',
            '08': 'Colorado',
            '09': 'Connecticut',
            '10': 'Delaware',
            '11': 'DISTRICT OF COLUMBIA',
            '12': 'Florida',
            '13': 'Georgia',
            '15': 'Hawaii',
            '16': 'Idaho',
            '17': 'Illinois',
            '18': 'Indiana',
            '19': 'Iowa',
            '20': 'Kansas',
            '21': 'Kentucky',
            '22': 'Louisiana',
            '23': 'Maine',
            '24': 'Maryland',
            '25': 'Massachusetts',
            '26': 'Michigan',
            '27': 'Minnesota',
            '28': 'Mississippi',
            '29': 'Missouri',
            '30': 'Montana',
            '31': 'Nebraska',
            '32': 'Nevada',
            '33': 'New Hampshire',
            '34': 'New Jersey',
            '35': 'New Mexico',
            '36': 'New York',
            '37': 'North Carolina',
            '38': 'North Dakota',
            '39': 'Ohio',
            '40': 'Oklahoma',
            '41': 'Oregon',
            '42': 'Pennsylvania',
            '44': 'Rhode Island',
            '45': 'South Carolina',
            '46': 'South Dakota',
            '47': 'Tennessee',
            '48': 'Texas',
            '49': 'Utah',
            '50': 'Vermont',
            '51': 'Virginia',
            '53': 'Washington',
            '54': 'West Virginia',
            '55': 'Wisconsin',
            '56': 'Wyoming'
        }

        self.links_dict = {}
        self.nodes_dict = {}
        self.Plants_group = None
        self.emission_powerplant = None
        self.Plants_ungroup_extended = None
        self.gdf = None
        self.gdf_state = None
        self.emission_powerplant_grouped_mean = None
        self.emission_powerplant_grouped = None
        self.df_pivot1 = None
        self.output = None

    def load_data(self):
        # Load the dictionaries from the pickle files
        with open(self.pickle_file_path1, 'rb') as f:
            loaded_results = pickle.load(f)
        self.links_dict = loaded_results.get('links', {})
        self.nodes_dict = loaded_results.get('nodes', {})

        with open(self.pickle_file_path2, 'rb') as f:
            self.Plants_group = pickle.load(f)

        with open(self.pickle_file_path3, 'rb') as f:
            self.Plants_ungroup_extended = pickle.load(f)

        self.gdf = gpd.read_file(self.shapefile)
        self.gdf_state = gpd.read_file(self.shapefile_state)
        self.gdf_map = gpd.read_file(self.shapefile)


    def creating_emission_data(self, df):
        self.emission_data = df.copy()
        self.emission_data = self.emission_data.sort_values(by=["RegionName", "PlantType", "FuelType", "community"])
        self.emission_data.loc[:, 'gen_type'] = self.emission_data['PlantType'] + '_' + self.emission_data['FuelType'] + '_' + self.emission_data['community'].astype(str)
        return self.emission_data

    def add_emissions_to_generators(self, df_multipliers):
        for region, region_data in self.nodes_dict.items():
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
        return self.nodes_dict

    def generation_county(self):
        # Load the state and county shapefiles using GeoPandas

        self.gdf['STATE_NAME'] = self.gdf['STATEFP'].map(self.state_fips_to_name)
        self.gdf_state['STATE_NAME'] = self.gdf_state['STATEFP'].map(self.state_fips_to_name)

        self.gdf = self.gdf.to_crs(epsg=4326)
        self.gdf_state = self.gdf_state.to_crs(epsg=4326)

        # Compute centroids for both states and counties
        self.gdf['county_centroid'] = self.gdf.geometry.centroid
        self.gdf_state['state_centroid'] = self.gdf_state.geometry.centroid

        flattened_data = []

        for region, region_data in self.nodes_dict.items():
            if "generator" in region_data and 'capacity' in region_data['generator']:
                for gen_type, capacity_data in region_data['generator']['capacity'].items():
                    # If capacity_data is a dictionary of time periods, you'll need to flatten it
                    for time_period, capacity in capacity_data.items():
                        flattened_data.append([region, gen_type, time_period, capacity])

        # Create DataFrame with appropriate column names
        self.output = pd.DataFrame(flattened_data, columns=["RegionName", "gen_type", "Time", "Capacity"])

        # Pivot the DataFrame
        self.output = self.output.pivot(index=['RegionName', 'gen_type'], columns='Time', values='Capacity').reset_index()

        # Separate the solar and wind types
        solar_df = self.output[self.output['gen_type'].isin(['Solar_Current', 'Solar_New'])]
        wind_df = self.output[self.output['gen_type'].isin(['Wind_Current', 'Wind_New'])]

        # Group by RegionName and sum capacities for Solar and Wind separately
        solar_aggregated = solar_df.groupby('RegionName').sum().reset_index()
        wind_aggregated = wind_df.groupby('RegionName').sum().reset_index()

        # Add a column 'gen_type' to distinguish Solar and Wind
        solar_aggregated['gen_type'] = 'Solar'
        wind_aggregated['gen_type'] = 'Wind'

        # Combine the solar and wind data back into the output DataFrame
        self.output1 = pd.concat([solar_aggregated, wind_aggregated], ignore_index=True)

        # Reorder the columns so 'gen_type' is in the correct place
        cols = self.output1.columns.tolist()
        cols.insert(1, cols.pop(cols.index('gen_type')))  # Move gen_type to the 2nd column
        self.output1 = self.output1[cols]

        # Step 1: Update 'gen_type' in Plants_ungroup_extended if the FuelType is "EnerStor", "Hydro", or "Geothermal"
        self.Plants_ungroup_extended = self.Plants_ungroup_extended.reset_index(drop=True)

        fuel_types_update = ["EnerStor", "Hydro", "Geothermal"]
        self.Plants_ungroup_extended.loc[self.Plants_ungroup_extended['FuelType'].isin(fuel_types_update), 'gen_type'] = self.Plants_ungroup_extended['FuelType']

        # Step 2: Update 'gen_type' in output if it contains any of the words "EnerStor", "Hydro", or "Geothermal"
        for fuel in fuel_types_update:
            self.output['gen_type'] = self.output['gen_type'].replace(to_replace=r'.*' + fuel + '.*', value=fuel, regex=True)

        # Update 'gen_type' only where 'FuelType' is in the specified list
        fuel_types = ["Solar", "Wind", "EnerStor", "Hydro", "Geothermal"]
        self.Plants_ungroup_extended.loc[self.Plants_ungroup_extended['FuelType'].isin(fuel_types), 'gen_type'] = self.Plants_ungroup_extended['FuelType']



        # Merge with Plants_ungroup_extended for further analysis
        self.df_pivot1 = pd.merge(
            self.Plants_ungroup_extended[["UniqueIDN", "RegionName", "FuelType", "PlantType", "gen_type", "StateName", "CountyName", "NERC", "Capacity", "LAT", "LON"]],
            self.output,
            how="left",
            on=["RegionName", "gen_type"]
        )

        # Filter the DataFrame for the second merge based on 'gen_type' condition
        fuel_types1 = ["Solar", "Wind"]
        df_filtered = self.df_pivot1[self.df_pivot1['gen_type'].isin(fuel_types1)]

        # Perform the second merge only for filtered rows
        self.df_pivot2 = pd.merge(
            df_filtered[["UniqueIDN", "RegionName", "FuelType", "PlantType", "gen_type", "StateName", "CountyName", "NERC", "Capacity", "LAT", "LON"]],
            self.output1,
            how="left",
            on=["RegionName", "gen_type"]
        )

        # Optionally, you may want to append the non-matching rows back if you want to retain them
        non_filtered = self.df_pivot1[~self.df_pivot1['gen_type'].isin(fuel_types)]
        self.df_pivot3 = pd.concat([self.df_pivot2, non_filtered], ignore_index=True)
    #
        # Fill missing LAT and LON using county centroid first, then state centroid
        self.df_pivot3 = pd.merge(self.df_pivot3, self.gdf[['STATE_NAME', "NAME", 'county_centroid']],
                             left_on=['StateName', 'CountyName'],
                             right_on=["STATE_NAME", 'NAME'],
                             how='left')
        # #
        self.df_pivot3 = pd.merge(self.df_pivot3, self.gdf_state[['NAME', 'state_centroid']],
                             left_on='StateName',
                             right_on='NAME',
                             how='left')
        #
        # Update LAT and LON based on available centroids
        self.df_pivot3['LAT'] = self.df_pivot3['LAT'].fillna(self.df_pivot3['county_centroid'].apply(lambda x: x.y if x else None))
        self.df_pivot3['LON'] = self.df_pivot3['LON'].fillna(self.df_pivot3['county_centroid'].apply(lambda x: x.x if x else None))

        # If still missing, use state centroids
        self.df_pivot3['LAT'] = self.df_pivot3['LAT'].fillna(self.df_pivot3['state_centroid'].apply(lambda x: x.y if x else None))
        self.df_pivot3['LON'] = self.df_pivot3['LON'].fillna(self.df_pivot3['state_centroid'].apply(lambda x: x.x if x else None))
        #
        # Remove the extra columns used for merging
        self.df_pivot3 = self.df_pivot3.drop(columns=['STATE_NAME', 'NAME_x', 'NAME_y', 'county_centroid', 'state_centroid'])

        # Group by 'Region' and 'gen_type' to calculate the sum of 'Capacity'
        capacity_sum = self.df_pivot3.groupby(['RegionName', 'gen_type'])['Capacity'].sum().reset_index()
        capacity_sum.rename(columns={'Capacity': 'Total_Capacity_type_region'}, inplace=True)

        # Merge the total capacity back into the original DataFrame
        self.df_pivot3 = pd.merge(self.df_pivot3, capacity_sum, on=['RegionName', 'gen_type'], how='left')

        # Reorder columns to insert 'Total_Capacity' between the 7th and 8th columns
        cols = self.df_pivot3.columns.tolist()
        new_position = 8  # Position after the first 7 columns
        cols = cols[:new_position] + ['Total_Capacity_type_region'] + cols[new_position:-1]
        self.df_pivot3 = self.df_pivot3[cols]

        # Calculate the capacity ratio
        self.df_pivot3['Capacity_Ratio'] = self.df_pivot3['Capacity'] / self.df_pivot3['Total_Capacity_type_region']

        # Reorganize the columns again to include the new Capacity_Ratio column
        cols = self.df_pivot3.columns.tolist()
        cols = cols[:new_position + 1] + ['Capacity_Ratio'] + cols[new_position + 1:-1]
        self.df_pivot3 = self.df_pivot3[cols]

        # Multiply the hour columns by the Capacity_Ratio
        hour_cols = cols[new_position + 5:]  # Get the hour columns dynamically based on their position
        self.df_pivot3[hour_cols] = self.df_pivot3[hour_cols].multiply(self.df_pivot3['Capacity_Ratio'], axis=0).fillna(0)

        # Ensure hour_cols contains only numeric data for summation
        self.df_pivot3[hour_cols] = self.df_pivot3[hour_cols].apply(pd.to_numeric, errors='coerce')

        # Summing all the hour columns and adding the result as a new column
        self.df_pivot3['Total_generation_Sum'] = self.df_pivot3[hour_cols].sum(axis=1)

        # Calculate the length of non-zero values for each row and store it in a new column
        self.df_pivot3['Non_Zero_Hours_Count'] = (self.df_pivot3[hour_cols] != 0).sum(axis=1)

        # Create the new column by dividing the sum by the count of non-zero values
        self.df_pivot3['Average_generation_p_hour'] = self.df_pivot3.apply(
            lambda row: row['Total_generation_Sum'] / row['Non_Zero_Hours_Count'] if row['Non_Zero_Hours_Count'] > 0 else 0, axis=1
        )

        # Remove the hour columns from the DataFrame
        self.df_pivot3 = self.df_pivot3.drop(columns=hour_cols)

        # Merge with emissions data and compute total and hourly emissions
        self.df_pivot3 = pd.merge(self.df_pivot3, self.Plants_ungroup_extended[["UniqueIDN", 'PLPMTRO', 'PLNOXRTA', 'PLSO2RTA', 'PLCO2RTA', 'PLCH4RTA', 'PLN2ORTA']], on="UniqueIDN", how="left")

        # List of emissions criteria
        emission_criteria = ['PLPMTRO', 'PLNOXRTA', 'PLSO2RTA', 'PLCO2RTA', 'PLCH4RTA', 'PLN2ORTA']

        # Create new columns by multiplying each emission by Total_generation_sum and Average_generation_p_hour
        for emission in emission_criteria:
            # Multiply by Total_generation_sum and create a new column with 'total' in the name
            self.df_pivot3[f'{emission}_total'] = self.df_pivot3[emission] * self.df_pivot3['Total_generation_Sum']

            # Multiply by Average_generation_p_hour and create a new column with 'hourly' in the name
            self.df_pivot3[f'{emission}_hourly'] = self.df_pivot3[emission] * self.df_pivot3['Average_generation_p_hour']

    def create_map(self, emission_criteria='PLCO2RTA', plant_type='All', level_choice='unit', save_as_html=False, html_filename='map.html', export_filename='plant_emissions_export.csv'):
        """Creates an interactive map based on the emission criteria and plant type."""

        # Filter by plant type if selected
        if plant_type != 'All':
            df = self.df_pivot3[self.df_pivot3['PlantType'] == plant_type]
        else:
            df = self.df_pivot3

        # Remove rows where Latitude or Longitude is NaN
        df = df.dropna(subset=['LAT', 'LON'])

        # Define a dictionary to map emission criteria to their readable names and units
        emission_units = {
            'PLCO2RTA_total': 'kg CO2 (Total)',
            'PLNOXRTA_total': 'kg NOx (Total)',
            'PLSO2RTA_total': 'kg SO2 (Total)',
            'PLPMTRO_total': 'kg PM (Total)',
            'PLCH4RTA_total': 'kg CH4 (Total)',
            'PLN2ORTA_total': 'kg N2O (Total)',
            'PLCO2RTA_hourly': 'kg CO2 (Hourly)',
            'PLNOXRTA_hourly': 'kg NOx (Hourly)',
            'PLSO2RTA_hourly': 'kg SO2 (Hourly)',
            'PLPMTRO_hourly': 'kg PM (Hourly)',
            'PLCH4RTA_hourly': 'kg CH4 (Hourly)',
            'PLN2ORTA_hourly': 'kg N2O (Hourly)'
        }

        # Clean up the emission name (removing 'PL', 'RTA', and adding 'Total' or 'Hourly')
        clean_emission_name = emission_units.get(emission_criteria, 'Unknown Emission')

        # If level_choice is 'plant', aggregate the data by LAT, LON, and PlantType
        if level_choice == 'plant':
            # Aggregate emissions and other data at the power plant level
            agg_columns = ['LAT', 'LON', 'PlantType']
            df = df.groupby(agg_columns).agg({
                emission_criteria: 'sum',
                'Capacity': 'sum',
                'Total_generation_Sum': 'sum',
                'Non_Zero_Hours_Count': 'sum',
                'Average_generation_p_hour': 'mean'
            }).reset_index()

        # Initialize map centered in the US
        m = folium.Map(location=[37.8, -96], zoom_start=4)

        # Set a fixed circle size (e.g., radius 10)
        fixed_radius = 10

        # Use MarkerCluster to add markers
        marker_cluster = MarkerCluster().add_to(m)

        # Loop through the DataFrame and plot points
        for idx, row in df.iterrows():
            folium.CircleMarker(
                location=[row['LAT'], row['LON']],
                radius=fixed_radius,  # Set constant circle size
                popup=f'Plant: {row["PlantType"]}<br>'
                      f'Emission: {clean_emission_name}<br>'
                      f'Value: {row[emission_criteria]}',
                tooltip=f'{row["PlantType"]}',  # Show plant type as tooltip
                color='crimson',
                fill=True,
                fill_color='crimson'
            ).add_to(marker_cluster)

        # Add a custom legend to the map
        legend_html = f'''
         <div style="position: fixed;
         bottom: 50px; left: 50px; width: 200px; height: 120px;
         background-color: white; z-index:9999; font-size:14px;">
         &nbsp;<b>Emission Info</b><br>
         &nbsp;Criteria: {clean_emission_name}<br>
         &nbsp;Plant Type: {plant_type} <br>
         </div>
         '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Update filenames to include plant type, emission criteria, and level choice
        export_filename = f'{plant_type}_{emission_criteria}_{level_choice}_emissions_export.csv'
        html_filename = f'{plant_type}_{emission_criteria}_{level_choice}_emissions_map.html'

        # Save the map as an HTML file if requested
        if save_as_html:
            m.save(html_filename)

        # Export DataFrame to CSV with plant name and emissions
        df.to_csv(export_filename, index=False)
        print(f"Exported data to {export_filename}")

    def ask_emission_criteria(self):
        """Prompts the user to input whether they want total or hourly emissions, then generates the map."""

        # Step 1: Ask for total or hourly
        emission_type_choice = input("Do you want to map 'Total' or 'Hourly' emissions? (Enter 'Total' or 'Hourly'): ").strip().lower()

        if emission_type_choice == 'total':
            suffix = '_total'
        elif emission_type_choice == 'hourly':
            suffix = '_hourly'
        else:
            print("Invalid choice. Please enter 'Total' or 'Hourly'.")
            return

        # Step 2: Ask for emission criteria
        emission_options = {
            'CO2': f'PLCO2RTA{suffix}',
            'NOx': f'PLNOXRTA{suffix}',
            'SO2': f'PLSO2RTA{suffix}',
            'PM': f'PLPMTRO{suffix}',
            'CH4': f'PLCH4RTA{suffix}',
            'N2O': f'PLN2ORTA{suffix}'
        }

        emission_choice = input("Enter the emission criteria you'd like to map \n CO2\n NOx\n SO2\n PM\n CH4\n N2O\n").strip()

        if emission_choice not in emission_options:
            print("Invalid emission criteria. Please enter a valid option (e.g.\n CO2\n NOx\n SO2\n PM\n CH4\n N2O\n).")
            return

        emission_criteria = emission_options[emission_choice]

        # Step 3: Ask for plant type
        plant_types = self.df_pivot3['PlantType'].unique().tolist()

        plant_type = input("Enter the plant type (or type 'All' for all plant types): \n"
                           "'Combined Cycle'\n'Biomass'\n 'Coal Steam'\n'Combustion Turbine'\n"
                           "'Landfill Gas'\n'Non-Fossil Waste'\n'Nuclear'\n'O/G Steam'\n 'IGCC'\n"
                           "'Municipal Solid Waste'\n'Fossil Waste'\n'Pumped Storage'\n'Fuel Cell'\n"
                           "'Tires'\n'IMPORT'\n'Hydro'\n'Geothermal'\n'Onshore Wind'\n'Offshore Wind'\n"
                           "'Solar PV'\n'Solar Thermal'\n'Energy Storage'\n'New Battery Storage'")

        if plant_type not in plant_types and plant_type != 'All':
            print("Invalid plant type. Please enter a valid option or 'All'.")
            return

        # Step 4: Ask if they want unit-level or power plant-level data
        level_choice = input("Do you want the information on 'Unit' or 'Power Plant' level? (Enter 'Unit' or 'Plant'): ").strip().lower()

        if level_choice not in ['unit', 'plant']:
            print("Invalid choice. Please enter 'Unit' or 'Plant'.")
            return

        # Create and save the map and export the data to CSV
        self.create_map(emission_criteria=emission_criteria, plant_type=plant_type, level_choice=level_choice,
                        save_as_html=True, html_filename='plant_emissions_map.html', export_filename='plant_emissions_export.csv')

        print(f"Map saved as '{plant_type}_{emission_choice}_{emission_type_choice}_emissions_map.html'.")
        print(f"Data has been exported to '{plant_type}_{emission_choice}_{emission_type_choice}_emissions_export.csv'.")

    def create_capacity_map(self, save_as_html=False, html_filename='capacity_map.html'):
        # Creates a static map showing installed capacity with plant type as color and size based on capacity.

        # Remove rows where Latitude or Longitude is NaN
        df = self.df_pivot3.dropna(subset=['LAT', 'LON'])

        # Define a color palette for each PlantType
        plant_type_colors = {
            'Combined Cycle': 'blue',  # Often gas-powered
            'Biomass': 'green',  # Eco-friendly type of energy
            'Coal Steam': 'black',  # Coal-based
            'Combustion Turbine': 'lightblue',  # Similar to gas turbines
            'Landfill Gas': 'olive',  # Waste-based
            'Non-Fossil Waste': 'lime',  # Eco-friendly, waste-based
            'Nuclear': 'darkgreen',  # Nuclear plants
            'O/G Steam': 'navy',  # Oil/Gas steam turbines
            'IGCC': 'teal',  # Integrated Gasification Combined Cycle (gas-based)
            'Municipal Solid Waste': 'darkorange',  # Waste-based
            'Fossil Waste': 'brown',  # Fossil fuel-based waste
            'Pumped Storage': 'aqua',  # Water storage plants
            'Fuel Cell': 'pink',  # Eco-friendly, new tech
            'Tires': 'purple',  # Less common, waste-to-energy
            'IMPORT': 'gray',  # Power imported from outside sources
            'Hydro': 'aqua',  # Hydropower
            'Geothermal': 'brown',  # Geothermal power
            'Onshore Wind': 'purple',  # Wind turbines onshore
            'Offshore Wind': 'darkpurple',  # Offshore wind turbines
            'Solar PV': 'orange',  # Solar photovoltaic
            'Solar Thermal': 'gold',  # Solar thermal plants
            'Energy Storage': 'cyan',  # Battery energy storage
            'New Battery Storage': 'magenta'  # New types of battery storage
        }

        # Initialize the map
        m = folium.Map(location=[37.8, -96], zoom_start=4)

        # Use MarkerCluster to add markers
        marker_cluster = MarkerCluster().add_to(m)

        # Normalize capacity to a reasonable scale for circle sizes
        max_capacity = df['Capacity'].max()
        min_radius, max_radius = 10, 200  # Min and max radius for circles
        scale_factor = (max_radius - min_radius) / max_capacity

        # Loop through the DataFrame and plot points
        for idx, row in df.iterrows():
            # Set a default color in case the plant type is not in the dictionary
            plant_color = plant_type_colors.get(row['PlantType'], 'gray')

            # Scale the circle size based on capacity
            scaled_radius = row['Capacity'] * scale_factor + min_radius

            folium.CircleMarker(
                location=[row['LAT'], row['LON']],
                radius=scaled_radius,  # Adjust the circle size based on Capacity
                popup=f'Plant: {row["UniqueIDN"]}<br>Capacity: {row["Capacity"]} MW<br>Type: {row["PlantType"]}',
                color=plant_color,
                fill=True,
                fill_color=plant_color,
                fill_opacity=0.7,
                line_opacity=0.7
            ).add_to(marker_cluster)

        # Create a dynamic legend based on the plant_type_colors
        legend_html = '''
        <div style="position: fixed;
        bottom: 50px; left: 50px; width: 250px; height: auto;
        background-color: white; z-index:9999; font-size:14px;
        border:2px solid grey; padding: 10px;">
        <b>Plant Type Legend</b><br>
        '''

        for plant_type, color in plant_type_colors.items():
            legend_html += f'<i style="background:{color}; width: 18px; height: 18px; display:inline-block;"></i> {plant_type}<br>'

        legend_html += '</div>'

        m.get_root().html.add_child(folium.Element(legend_html))

        # Save the map as an HTML file if requested
        if save_as_html:
            m.save(html_filename)

        # return m


    def plot_emissions(self, y_limit=None):
        """Plots emissions per MWh for selected regions and criteria."""

        # Step 1: Ask for total or hourly emissions
        emission_type_choice = input("Do you want to plot 'Total' or 'Hourly' emissions? (Enter 'Total' or 'Hourly'): ").strip().lower()

        if emission_type_choice == 'total':
            emission_suffix = '_total'
            generation_column = 'Total_generation_Sum'
        elif emission_type_choice == 'hourly':
            emission_suffix = '_hourly'
            generation_column = 'Average_generation_p_hour'
        else:
            print("Invalid choice. Please enter 'Total' or 'Hourly'.")
            return

        # Step 2: Ask for emission criteria
        emission_options = {
            'CO2': f'PLCO2RTA{emission_suffix}',
            'NOx': f'PLNOXRTA{emission_suffix}',
            'SO2': f'PLSO2RTA{emission_suffix}',
            'PM': f'PLPMTRO{emission_suffix}',
            'CH4': f'PLCH4RTA{emission_suffix}',
            'N2O': f'PLN2ORTA{emission_suffix}'
        }

        emission_choice = input("Enter the emission criteria you'd like to plot\n CO2\n NOx\n SO2\n PM\n CH4\n N2O\n ").strip()

        if emission_choice not in emission_options:
            print("Invalid emission criteria. Please enter a valid option\n CO2\n NOx\n SO2\n PM\n CH4\n N2O\n")
            return

        emission_criteria = emission_options[emission_choice]

        # Step 3: Ask for region type (NERC or IPM)
        region_type_choice = input("Do you want to use 'NERC' or 'IPM' regions? (Enter 'NERC' or 'IPM'): ").strip().upper()

        if region_type_choice == 'NERC':
            region_column = 'NERC'
        elif region_type_choice == 'IPM':
            region_column = 'RegionName'
        else:
            print("Invalid region choice. Please enter 'NERC' or 'IPM'.")
            return

        # Step 4: Group data by the chosen region and calculate mean emissions per MWh
        # Ensure that the generation column does not include zero or NaN values to avoid division errors
        valid_data = self.df_pivot3[self.df_pivot3[generation_column] > 0]

        valid_data['Emissions_per_MWh'] = valid_data[emission_criteria] / valid_data[generation_column]

        # Calculate mean emissions per region
        region_emissions = valid_data.groupby(region_column)['Emissions_per_MWh'].mean().reset_index()

        # Clean up the emission name for plotting
        emission_label = emission_choice

        # Step 5: Plotting
        fig, ax = plt.subplots(figsize=(14, 8))

        bars = ax.bar(region_emissions[region_column], region_emissions['Emissions_per_MWh'], color='red')

        ax.set_xlabel(f'{region_type_choice} Regions', fontsize=18)
        ax.set_ylabel(f'{emission_label} Emissions (lbs/MWh)', fontsize=18)
        ax.set_title(f'{emission_label} Emissions per MWh by {region_type_choice} Region', fontsize=20)

        # Set a constant Y-axis limit if provided
        if y_limit is not None:
            ax.set_ylim(0, y_limit)

        # Add Y-axis grid
        ax.grid(True, axis='y')

        # Rotate region labels for better readability
        plt.xticks(rotation=45, ha='right', fontsize=10)

        plt.tight_layout()
        plt.show()


