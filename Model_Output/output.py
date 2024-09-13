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
        output = pd.DataFrame(flattened_data, columns=["RegionName", "gen_type", "Time", "Capacity"])

        # Pivot the DataFrame
        output = output.pivot(index=['RegionName', 'gen_type'], columns='Time', values='Capacity').reset_index()

        # Merge with Plants_ungroup_extended for further analysis
        self.df_pivot1 = pd.merge(
            self.Plants_ungroup_extended[["UniqueIDN", "RegionName", "FuelType", "PlantType", "gen_type", "StateName", "CountyName", "NERC", "Capacity", "LAT", "LON"]],
            output,
            how="left",
            on=["RegionName", "gen_type"]
        )

        # Fill missing LAT and LON using county centroid first, then state centroid
        self.df_pivot1 = pd.merge(self.df_pivot1, self.gdf[['STATE_NAME', "NAME", 'county_centroid']],
                             left_on=['StateName', 'CountyName'],
                             right_on=["STATE_NAME", 'NAME'],
                             how='left')
        # #
        self.df_pivot1 = pd.merge(self.df_pivot1, self.gdf_state[['NAME', 'state_centroid']],
                             left_on='StateName',
                             right_on='NAME',
                             how='left')
        #
        # Update LAT and LON based on available centroids
        self.df_pivot1['LAT'] = self.df_pivot1['LAT'].fillna(self.df_pivot1['county_centroid'].apply(lambda x: x.y if x else None))
        self.df_pivot1['LON'] = self.df_pivot1['LON'].fillna(self.df_pivot1['county_centroid'].apply(lambda x: x.x if x else None))

        # If still missing, use state centroids
        self.df_pivot1['LAT'] = self.df_pivot1['LAT'].fillna(self.df_pivot1['state_centroid'].apply(lambda x: x.y if x else None))
        self.df_pivot1['LON'] = self.df_pivot1['LON'].fillna(self.df_pivot1['state_centroid'].apply(lambda x: x.x if x else None))
        #
        # Remove the extra columns used for merging
        self.df_pivot1 = self.df_pivot1.drop(columns=['STATE_NAME', 'NAME_x', 'NAME_y', 'county_centroid', 'state_centroid'])

        # Group by 'Region' and 'gen_type' to calculate the sum of 'Capacity'
        capacity_sum = self.df_pivot1.groupby(['RegionName', 'gen_type'])['Capacity'].sum().reset_index()
        capacity_sum.rename(columns={'Capacity': 'Total_Capacity_type_region'}, inplace=True)

        # Merge the total capacity back into the original DataFrame
        self.df_pivot1 = pd.merge(self.df_pivot1, capacity_sum, on=['RegionName', 'gen_type'], how='left')

        # Reorder columns to insert 'Total_Capacity' between the 7th and 8th columns
        cols = self.df_pivot1.columns.tolist()
        new_position = 8  # Position after the first 7 columns
        cols = cols[:new_position] + ['Total_Capacity_type_region'] + cols[new_position:-1]
        self.df_pivot1 = self.df_pivot1[cols]

        # Calculate the capacity ratio
        self.df_pivot1['Capacity_Ratio'] = self.df_pivot1['Capacity'] / self.df_pivot1['Total_Capacity_type_region']

        # Reorganize the columns again to include the new Capacity_Ratio column
        cols = self.df_pivot1.columns.tolist()
        cols = cols[:new_position + 1] + ['Capacity_Ratio'] + cols[new_position + 1:-1]
        self.df_pivot1 = self.df_pivot1[cols]

        # Multiply the hour columns by the Capacity_Ratio
        hour_cols = cols[new_position + 5:]  # Get the hour columns dynamically based on their position
        self.df_pivot1[hour_cols] = self.df_pivot1[hour_cols].multiply(self.df_pivot1['Capacity_Ratio'], axis=0).fillna(0)

        # Ensure hour_cols contains only numeric data for summation
        self.df_pivot1[hour_cols] = self.df_pivot1[hour_cols].apply(pd.to_numeric, errors='coerce')

        # Summing all the hour columns and adding the result as a new column
        self.df_pivot1['Total_generation_Sum'] = self.df_pivot1[hour_cols].sum(axis=1)

        # Calculate the length of non-zero values for each row and store it in a new column
        self.df_pivot1['Non_Zero_Hours_Count'] = (self.df_pivot1[hour_cols] != 0).sum(axis=1)

        # Create the new column by dividing the sum by the count of non-zero values
        self.df_pivot1['Average_generation_p_hour'] = self.df_pivot1.apply(
            lambda row: row['Total_generation_Sum'] / row['Non_Zero_Hours_Count'] if row['Non_Zero_Hours_Count'] > 0 else 0, axis=1
        )

        # Remove the hour columns from the DataFrame
        self.df_pivot1 = self.df_pivot1.drop(columns=hour_cols)

        # Merge with emissions data and compute total and hourly emissions
        self.df_pivot1 = pd.merge(self.df_pivot1, self.Plants_ungroup_extended[["UniqueIDN", 'PLPMTRO', 'PLNOXRTA', 'PLSO2RTA', 'PLCO2RTA', 'PLCH4RTA', 'PLN2ORTA']], on="UniqueIDN", how="left")

        # List of emissions criteria
        emission_criteria = ['PLPMTRO', 'PLNOXRTA', 'PLSO2RTA', 'PLCO2RTA', 'PLCH4RTA', 'PLN2ORTA']

        # Create new columns by multiplying each emission by Total_generation_sum and Average_generation_p_hour
        for emission in emission_criteria:
            # Multiply by Total_generation_sum and create a new column with 'total' in the name
            self.df_pivot1[f'{emission}_total'] = self.df_pivot1[emission] * self.df_pivot1['Total_generation_Sum']

            # Multiply by Average_generation_p_hour and create a new column with 'hourly' in the name
            self.df_pivot1[f'{emission}_hourly'] = self.df_pivot1[emission] * self.df_pivot1['Average_generation_p_hour']


    def create_map(self, emission_criteria='PLCO2RTA', plant_type='All', save_as_html=False, html_filename='map.html', export_filename='plant_emissions_export.csv'):
        """Creates an interactive map based on the emission criteria and plant type."""

        # Filter by plant type if selected
        if plant_type != 'All':
            df = self.df_pivot1[self.df_pivot1['PlantType'] == plant_type]
        else:
            df = self.df_pivot1

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
                popup=f'Plant: {row["UniqueIDN"]}<br>'
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

        # Update filenames to include plant type and emission criteria
        export_filename = f'{plant_type}_{emission_criteria}_emissions_export.csv'
        html_filename = f'{plant_type}_{emission_criteria}_emissions_map.html'

        # Save the map as an HTML file if requested
        if save_as_html:
            m.save(html_filename)

        # Export DataFrame to CSV with plant name and emissions
        df[['UniqueIDN', 'LAT', 'LON', 'PlantType', "FuelType", "Capacity", "Total_generation_Sum", "Non_Zero_Hours_Count", "Average_generation_p_hour", emission_criteria]].to_csv(export_filename, index=False)
        print(f"Exported data to {export_filename}")

        # return m

    def ask_emission_criteria(self):
        # Prompts the user to input whether they want total or hourly emissions, then generates the map.

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
        plant_types = self.df_pivot1['PlantType'].unique().tolist()
        # print(f"Available Plant Types: {', '.join(plant_types)} or enter 'All' to include all plants.")

        plant_type = input("Enter the plant type (or type 'All' for all plant types): "
                           "\n'Combined Cycle'\n'Biomass'\n 'Coal Steam'\n'Combustion Turbine'\n"
                           "'Landfill Gas'\n'Non-Fossil Waste'\n'Nuclear'\n'O/G Steam'\n 'IGCC'\n"
                           "'Municipal Solid Waste'\n'Fossil Waste'\n'Pumped Storage'\n'Fuel Cell'\n"
                           "'Tires'\n'IMPORT'\n'Hydro'\n'Geothermal'\n'Onshore Wind'\n'Offshore Wind'"
                           "\n'Solar PV'\n'Solar Thermal'\n'Energy Storage'\n'New Battery Storage'")


        if plant_type not in plant_types and plant_type != 'All':
            print("Invalid plant type. Please enter a valid option or 'All'.")
            return

        # Create and save the map and export the data to CSV
        self.create_map(emission_criteria=emission_criteria, plant_type=plant_type, save_as_html=True, html_filename='plant_emissions_map.html', export_filename='plant_emissions_export.csv')
        print(f"Map saved as '{plant_type}_{emission_choice}_{emission_type_choice}_emissions_map.html'.")
        print(f"Data has been exported to '{plant_type}_{emission_choice}_{emission_type_choice}_emissions_export.csv'.")

    def create_capacity_map(self, save_as_html=False, html_filename='capacity_map.html'):
        # Creates a static map showing installed capacity with plant type as color and size based on capacity.

        # Remove rows where Latitude or Longitude is NaN
        df = self.df_pivot1.dropna(subset=['LAT', 'LON'])

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


    # def emission_county(self, nodes_dict1):
    #     # Flatten the dictionary
    #     flattened_data = []
    #
    #     for region, region_data in nodes_dict1.items():
    #         if 'generator' in region_data and 'emissions' in region_data['generator']:
    #             for gen_type, emissions_data in region_data['generator']['emissions'].items():
    #                 for emission_criteria, time_emissions in emissions_data.items():
    #                     for time, emission in time_emissions.items():
    #                         flattened_data.append([region, gen_type, emission_criteria, time, emission])
    #
    #     # Create DataFrame
    #     df = pd.DataFrame(flattened_data, columns=['RegionName', 'gen_type', 'Emission_Criteria', 'Time', 'Emission_Value'])
    #
    #     # Pivot the DataFrame
    #     df_pivot = df.pivot(index=['RegionName', 'gen_type', 'Emission_Criteria'], columns='Time', values='Emission_Value').reset_index()
    #
    #     # Flatten the MultiIndex in columns if needed
    #     df_pivot.columns.name = None
    #     df_pivot.columns = [str(col) if isinstance(col, int) else col for col in df_pivot.columns]
    #
    #     df_pivot = df_pivot[~df_pivot["gen_type"].isin(['Hydro', 'Solar', 'Wind', 'Geothermal'])]
    #
    #     df_pivot1 = pd.merge(self.Plants_ungroup_extended[["RegionName", "FuelType", "gen_type", "StateName", "CountyName", "NERC", "Capacity", "LAT", "LON"]], df_pivot, how="left", on=["RegionName", "gen_type"])
    #     df_pivot1 = df_pivot1[~df_pivot1["FuelType"].isin(['Hydro', 'Solar', 'Wind', 'Geothermal'])]
    #
    #     # Group by 'Region' and 'gen_type' to calculate the sum of 'Capacity'
    #     capacity_sum = df_pivot1.groupby(['RegionName', 'gen_type', "Emission_Criteria"])['Capacity'].sum().reset_index()
    #     capacity_sum.rename(columns={'Capacity': 'Total_Capacity'}, inplace=True)
    #     #
    #     # Merge the total capacity back into the original DataFrame
    #     df_pivot1 = pd.merge(df_pivot1, capacity_sum, on=['RegionName', 'gen_type', "Emission_Criteria"], how='left')
    #     df_pivot1 = df_pivot1.dropna(subset=['Emission_Criteria'])
    #     #
    #     # # Ensure no duplicates after merging
    #     # df_pivot1 = df_pivot1.drop_duplicates(subset=['RegionName', 'gen_type', 'Emission_Criteria'])
    #     #
    #     # Reorder columns to insert 'Total_Capacity' between the 8th and 9th columns
    #     cols = df_pivot1.columns.tolist()
    #     new_position = 11  # Position after the first 8 columns
    #     cols = cols[:new_position] + ['Total_Capacity'] + cols[new_position:-1]
    #     df_pivot1 = df_pivot1[cols]
    #     #
    #     df_pivot1['Capacity_Ratio'] = df_pivot1['Capacity'] / df_pivot1['Total_Capacity']
    #     cols = df_pivot1.columns.tolist()
    #     cols = cols[:new_position + 1] + ['Capacity_Ratio'] + cols[new_position + 1:-1]
    #     df_pivot1 = df_pivot1[cols]
    #
    #     # Multiply the hour columns by the Capacity_Ratio
    #     hour_cols = cols[new_position + 2:]  # Get the hour columns dynamically based on their position
    #     df_pivot1[hour_cols] = df_pivot1[hour_cols].multiply(df_pivot1['Capacity_Ratio'], axis=0)
    #
    #     return df_pivot1
    #
    # def process_data(self):
    #     self.emission_data = self.creating_emission_data(self.Plants_group)
    #     nodes_dict1 = self.add_emissions_to_generators(self.emission_data)
    #     self.emission_powerplant = self.emission_county(nodes_dict1)
    #
    #     self.emission_powerplant_grouped = self.emission_powerplant.groupby(
    #         ["RegionName", "StateName", "CountyName", "Emission_Criteria"]
    #     ).agg({col: 'sum' for col in self.emission_powerplant.columns[10:]}).reset_index()
    #
    #     self.emission_powerplant_grouped_mean = self.emission_powerplant_grouped.groupby(
    #         ["RegionName", 'StateName', 'CountyName', "Emission_Criteria"]
    #     ).mean().reset_index()
    #
    #     self.emission_powerplant_grouped_mean['Overall_Mean'] = self.emission_powerplant_grouped_mean.iloc[:, 4:].mean(axis=1)
    #
    #     # Ensure all state names are properly capitalized
    #     self.emission_powerplant_grouped_mean['StateName'] = self.emission_powerplant_grouped_mean['StateName'].str.lower()
    #     self.emission_powerplant_grouped_mean['StateName'] = self.emission_powerplant_grouped_mean['StateName'].str.title()
    #
    #     # Ensure the county names and state names match in both dataframes
    #     self.gdf['COUNTY_NAME'] = self.gdf['NAME'].str.lower()
    #     self.gdf['STATEFP'] = self.gdf['STATEFP'].apply(lambda x: str(x).zfill(2))
    #     self.gdf['STATE_NAME'] = self.gdf['STATEFP'].map(self.state_fips_to_name)
    #
    #     # Merge the GeoDataFrame with the emissions data
    #     self.gdf = self.gdf.merge(self.emission_powerplant_grouped_mean,
    #                               left_on=['STATE_NAME', 'NAME'],
    #                               right_on=['StateName', 'CountyName'],
    #                               how='left')
    #
    #     # Select and reorder the required columns
    #     self.gdf = self.gdf[['STATEFP', 'COUNTYFP', 'COUNTYNS', 'AFFGEOID', 'GEOID', 'NAME', 'LSAD',
    #                          'ALAND', 'AWATER', 'geometry', 'COUNTY_NAME', 'STATE_NAME', 'RegionName',
    #                          'StateName', 'CountyName', 'Emission_Criteria', 'Overall_Mean']]
    #
    #     self.gdf['Overall_Mean'] = self.gdf['Overall_Mean'].fillna(0)
    #
    # def create_heat_map(self, gdf, emission_column, output_file):
    #     m = folium.Map(location=[37.8, -96], zoom_start=4)
    #     folium.Choropleth(
    #         geo_data=gdf,
    #         name='choropleth',
    #         data=gdf,
    #         columns=['NAME', emission_column],
    #         key_on='feature.properties.NAME',
    #         fill_color='YlOrRd',
    #         fill_opacity=0.7,
    #         line_opacity=0.2,
    #         nan_fill_color='white',
    #         nan_fill_opacity=0.4,
    #         legend_name=f'Overall Mean Emission ({emission_column})'
    #     ).add_to(m)
    #     folium.LayerControl().add_to(m)
    #     m.save(output_file)
    #
    #
    # def generate_heatmaps(self):
    #     # List of emission criteria
    #     emission_criteria_list = self.emission_powerplant_grouped_mean['Emission_Criteria'].unique()
    #
    #     # Loop through each emission criteria and create a heatmap
    #     for emission in emission_criteria_list:
    #         # Filter the GeoDataFrame for the current emission criteria
    #         gdf_filtered = self.gdf[self.gdf['Emission_Criteria'] == emission].copy()
    #         gdf_filtered['Overall_Mean'] = gdf_filtered['Overall_Mean'].fillna(0)
    #
    #         # Generate the heatmap for the current emission criteria
    #         self.create_heat_map(gdf_filtered, 'Overall_Mean', f'./{emission}_heat_map.html')
    #
    # def calculate_region_emissions(self):
    #     emissions_by_region = {}
    #     total_power_by_region = {}
    #
    #     for region, region_data in self.nodes_dict.items():
    #         if 'generator' in region_data:
    #             for gen_type, emissions in region_data['generator']['emissions'].items():
    #                 # Exclude certain types from total power calculation
    #                 if any(x in gen_type.lower() for x in ['Hydro', 'Solar', 'Wind', 'Geothermal']):
    #                     continue
    #
    #                 if region not in emissions_by_region:
    #                     emissions_by_region[region] = {}
    #                     total_power_by_region[region] = 0
    #
    #                 for emission_type, emission_values in emissions.items():
    #                     if emission_type not in emissions_by_region[region]:
    #                         emissions_by_region[region][emission_type] = 0
    #
    #                     emissions_by_region[region][emission_type] += sum(emission_values.values())
    #
    #                 # Sum total power for this generator type
    #                 total_power_by_region[region] += sum(region_data['generator']['capacity'][gen_type].values())
    #
    #     # Calculate emissions per MWh
    #     emissions_per_mwh = {}
    #     for region, emissions in emissions_by_region.items():
    #         emissions_per_mwh[region] = {}
    #         for emission_type, total_emission_1 in emissions.items():
    #             emissions_per_mwh[region][emission_type] = total_emission_1 / total_power_by_region[region]
    #
    #     return emissions_per_mwh
    #
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
        valid_data = self.df_pivot1[self.df_pivot1[generation_column] > 0]

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
    #
    # def generate_heatmap_emissions_per_mwh(self):
    #     # Step 1: Call generation_county to get the total generation per county
    #     self.df_generation = self.generation_county()
    #     self.emission_powerplant_grouped_mean = self.emission_powerplant_grouped_mean[self.emission_powerplant_grouped_mean["Emission_Criteria"] == "PLCO2RTA"]
    #     self.emission_powerplant_grouped_mean['Total_emission'] = self.emission_powerplant_grouped_mean.iloc[:, 4:-1].sum(axis=1)
    #
    #     # Ensure the county names and state names match in both dataframes
    #     self.gdf_map['COUNTY_NAME'] = self.gdf_map['NAME'].str.lower()
    #     self.gdf_map['STATEFP'] = self.gdf_map['STATEFP'].apply(lambda x: str(x).zfill(2))
    #     self.gdf_map['STATE_NAME'] = self.gdf_map['STATEFP'].map(self.state_fips_to_name)
    #
    #     # Merge the GeoDataFrame with the emissions data
    #     self.gdf_map = self.gdf_map.merge(self.emission_powerplant_grouped_mean,
    #                               left_on=['STATE_NAME', 'NAME'],
    #                               right_on=['StateName', 'CountyName'],
    #                               how='left')
    #
    #     # Select and reorder the required columns
    #     self.gdf_map = self.gdf_map[['STATEFP', 'COUNTYFP', 'COUNTYNS', 'AFFGEOID', 'GEOID', 'NAME', 'LSAD',
    #                          'ALAND', 'AWATER', 'geometry', 'COUNTY_NAME', 'STATE_NAME', 'RegionName',
    #                          'StateName', 'CountyName', 'Emission_Criteria', 'Overall_Mean']]
    #
    #     # Step 2: List of emission criteria
    #     emission_criteria_list = self.emission_powerplant_grouped_mean['Emission_Criteria'].unique()
    #     self.gdf_map = self.gdf_map.merge(self.emission_powerplant_grouped_mean[["RegionName", "CountyName", "Emission_Criteria", "Total_emission"]], how='left', on=["RegionName", "CountyName", "Emission_Criteria"])
    #     # Step 3: Loop through each emission criteria and create a heatmap
    #     for emission in emission_criteria_list:
    #         # Filter the GeoDataFrame for the current emission criteria
    #         self.gdf_map_filtered = self.gdf_map[self.gdf_map['Emission_Criteria'] == emission].copy()
    #         self.gdf_map_filtered['Total_emission'] = self.gdf_map_filtered['Total_emission'].fillna(0)
    #
    #         # Step 4: Merge the generation data with the GeoDataFrame
    #         self.gdf_map_filtered = pd.merge(self.gdf_map_filtered, self.df_generation, on=['RegionName', 'StateName', 'CountyName'], how='left')
    #
    #         # Step 5: Calculate Emissions per MWh (Total_emission / Total_Gen_Sum)
    #         self.gdf_map_filtered['Emissions_per_MWh'] = self.gdf_map_filtered.apply(
    #             lambda row: row['Total_emission'] / row['Total_Gen_Sum'] if row['Total_Gen_Sum'] > 0 else 0, axis=1
    #         )
    #         # Step 6: Create the heatmap for the current emission criteria
    #         m = folium.Map(location=[37.8, -96], zoom_start=4)
    #
    #         # Step 7: Add choropleth layer
    #         folium.Choropleth(
    #             geo_data=self.gdf_map_filtered,
    #             name='choropleth',
    #             data=self.gdf_map_filtered,
    #             columns=['CountyName', 'Emissions_per_MWh'],
    #             key_on='feature.properties.CountyName',
    #             fill_color='YlOrRd',
    #             fill_opacity=0.7,
    #             line_opacity=0.2,
    #             nan_fill_color='white',
    #             nan_fill_opacity=0.4,
    #             legend_name=f'{emission} (kg) / MWh'
    #         ).add_to(m)
    #
    #         # Step 8: Add tooltips with county and state names
    #         folium.GeoJson(
    #             self.gdf_map_filtered,
    #             name="County",
    #             tooltip=folium.features.GeoJsonTooltip(
    #                 fields=['CountyName', 'StateName'],
    #                 aliases=['County: ', 'State: '],
    #                 localize=True
    #             )
    #         ).add_to(m)
    #
    #         # Step 9: Add layer control and save the map
    #         folium.LayerControl().add_to(m)
    #         self.create_heat_map(self.gdf_map_filtered, 'Emissions_per_MWh', f'./{emission}_emissions_per_mwh_heatmap.html')


# %%
# emission_heat_map = ModelOutput()
# emission_heat_map.load_data()
# emission_heat_map.generation_county()
# emission_heat_map.plot_emissions()
# emission_heat_map.process_data()
# emission_heat_map.generate_heatmap_emissions_per_mwh()
# emission_heat_map.plot_emissions('PLCO2RTA')
# emission_heat_map.plot_emissions('PLSO2RTA')
# emission_heat_map.plot_emissions('PLNOXRTA')