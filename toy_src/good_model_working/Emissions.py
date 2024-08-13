import pickle
import pandas as pd
import folium
import geopandas as gpd

# %%
class EmissionHeatMap:
    def __init__(self, pickle_file_path1, pickle_file_path2, pickle_file_path3, shapefile):
        self.pickle_file_path1 = pickle_file_path1
        self.pickle_file_path2 = pickle_file_path2
        self.pickle_file_path3 = pickle_file_path3
        self.shapefile = shapefile
        self.state_fips_to_name = {
            '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas', '06': 'California',
            '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware', '11': 'District of Columbia',
            '12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho', '17': 'Illinois',
            '18': 'Indiana', '19': 'Iowa', '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana',
            '23': 'Maine', '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
            '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
            '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York', '37': 'North Carolina',
            '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania',
            '44': 'Rhode Island', '45': 'South Carolina', '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas',
            '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington', '54': 'West Virginia',
            '55': 'Wisconsin', '56': 'Wyoming'
        }
        self.links_dict = {}
        self.nodes_dict = {}
        self.Plants_group = None
        self.Plants_ungroup = None
        self.gdf = None
        self.emission_powerplant_grouped_mean = None

    def load_data(self):
        # Load the dictionaries from the pickle files
        with open(self.pickle_file_path1, 'rb') as f:
            loaded_results = pickle.load(f)
        self.links_dict = loaded_results.get('links', {})
        self.nodes_dict = loaded_results.get('nodes', {})

        with open(self.pickle_file_path2, 'rb') as f:
            self.Plants_group = pickle.load(f)

        with open(self.pickle_file_path3, 'rb') as f:
            self.Plants_ungroup = pickle.load(f)
        self.gdf = gpd.read_file(shapefile)

    def add_emissions_to_generators(self, nodes_dict, df_multipliers):
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

    def creating_emission_data(self, df):
        emission_data = df.copy()
        emission_data = emission_data.sort_values(by=["RegionName", "PlantType", "FuelType", "community"])
        emission_data.loc[:, 'gen_type'] = emission_data['PlantType'] + '_' + emission_data['FuelType'] + '_' + emission_data['community'].astype(str)
        return emission_data

    def emission_county(self, dict_input, all_power_plant):
        # Flatten the dictionary
        flattened_data = []

        for region, region_data in dict_input.items():
            if 'generator' in region_data and 'emissions' in region_data['generator']:
                for gen_type, emissions_data in region_data['generator']['emissions'].items():
                    for emission_criteria, time_emissions in emissions_data.items():
                        for time, emission in time_emissions.items():
                            flattened_data.append([region, gen_type, emission_criteria, time, emission])

        # Create DataFrame
        df = pd.DataFrame(flattened_data, columns=['RegionName', 'gen_type', 'Emission_Criteria', 'Time', 'Emission_Value'])

        # Pivot the DataFrame
        df_pivot = df.pivot(index=['RegionName', 'gen_type', 'Emission_Criteria'], columns='Time', values='Emission_Value').reset_index()

        # Flatten the MultiIndex in columns if needed
        df_pivot.columns.name = None
        df_pivot.columns = [str(col) if isinstance(col, int) else col for col in df_pivot.columns]

        df_pivot = df_pivot[~df_pivot["gen_type"].isin(["solar", "wind", "Tires_Tires_1"])]

        df_pivot1 = pd.merge(all_power_plant[["RegionName", "FuelType", "gen_type", "StateName", "CountyName", "NERC", "Capacity"]], df_pivot, how="left", on=["RegionName", "gen_type"])
        df_pivot1 = df_pivot1[~df_pivot1["FuelType"].isin(["Solar", "Wind", "Tires_Tires_1"])]

        # # Check for and remove duplicates
        # df_pivot1 = df_pivot1.drop_duplicates(subset=['RegionName', 'gen_type', 'Emission_Criteria'])
        #
        # Group by 'Region' and 'gen_type' to calculate the sum of 'Capacity'
        capacity_sum = df_pivot1.groupby(['RegionName', 'gen_type', "Emission_Criteria"])['Capacity'].sum().reset_index()
        capacity_sum.rename(columns={'Capacity': 'Total_Capacity'}, inplace=True)
        #
        # Merge the total capacity back into the original DataFrame
        df_pivot1 = pd.merge(df_pivot1, capacity_sum, on=['RegionName', 'gen_type', "Emission_Criteria"], how='left')
        df_pivot1 = df_pivot1.dropna(subset=['Emission_Criteria'])
        #
        # # Ensure no duplicates after merging
        # df_pivot1 = df_pivot1.drop_duplicates(subset=['RegionName', 'gen_type', 'Emission_Criteria'])
        #
        # Reorder columns to insert 'Total_Capacity' between the 8th and 9th columns
        cols = df_pivot1.columns.tolist()
        new_position = 8  # Position after the first 8 columns
        cols = cols[:new_position] + ['Total_Capacity'] + cols[new_position:-1]
        df_pivot1 = df_pivot1[cols]
        #
        df_pivot1['Capacity_Ratio'] = df_pivot1['Capacity'] / df_pivot1['Total_Capacity']
        cols = df_pivot1.columns.tolist()
        cols = cols[:new_position + 1] + ['Capacity_Ratio'] + cols[new_position + 1:-1]
        df_pivot1 = df_pivot1[cols]

        # Multiply the hour columns by the Capacity_Ratio
        hour_cols = cols[new_position + 2:]  # Get the hour columns dynamically based on their position
        df_pivot1[hour_cols] = df_pivot1[hour_cols].multiply(df_pivot1['Capacity_Ratio'], axis=0)

        return df_pivot1

    def process_data(self):
        emission_data1 = self.creating_emission_data(self.Plants_group)
        nodes_dict1 = self.add_emissions_to_generators(self.nodes_dict, emission_data1)
        emission_powerplant = self.emission_county(nodes_dict1, self.Plants_ungroup)
        emission_powerplant_grouped = emission_powerplant.groupby(["RegionName", "StateName", "CountyName", "Emission_Criteria"]).agg({col: 'sum' for col in emission_powerplant.columns[10:]}).reset_index()
        self.emission_powerplant_grouped_mean = emission_powerplant_grouped.groupby(["RegionName", 'StateName', 'CountyName', "Emission_Criteria"]).mean().reset_index()
        self.emission_powerplant_grouped_mean['Overall_Mean'] = self.emission_powerplant_grouped_mean.iloc[:, 4:].mean(axis=1)
        self.emission_powerplant_grouped_mean['StateName'] = self.emission_powerplant_grouped_mean['StateName'].str.lower()
        self.emission_powerplant_grouped_mean['StateName'] = self.emission_powerplant_grouped_mean['StateName'].str.capitalize()

        # Ensure the county names and state names match in both dataframes
        self.gdf['COUNTY_NAME'] = self.gdf['NAME'].str.lower()
        # Convert STATEFP to string and map to state names
        self.gdf['STATEFP'] = self.gdf['STATEFP'].apply(lambda x: str(x).zfill(2))
        self.gdf['STATE_NAME'] = self.gdf['STATEFP'].map(self.state_fips_to_name)
        # Merge the GeoDataFrame with the emissions data
        self.gdf = self.gdf.merge(self.emission_powerplant_grouped_mean, left_on=['STATE_NAME', 'NAME'], right_on=['StateName', 'CountyName'], how='left')

        # Select and reorder the required columns
        self.gdf = self.gdf[['STATEFP', 'COUNTYFP', 'COUNTYNS', 'AFFGEOID', 'GEOID', 'NAME', 'LSAD', 'ALAND', 'AWATER', 'geometry', 'COUNTY_NAME', 'STATE_NAME', 'RegionName', 'StateName', 'CountyName', 'Emission_Criteria', 'Overall_Mean']]
        self.gdf['Overall_Mean'] = self.gdf['Overall_Mean'].fillna(0)

    def create_heat_map(self, gdf, emission_column, output_file):
        m = folium.Map(location=[37.8, -96], zoom_start=4)
        folium.Choropleth(
            geo_data=gdf,
            name='choropleth',
            data=gdf,
            columns=['NAME', emission_column],
            key_on='feature.properties.NAME',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            nan_fill_color='white',
            nan_fill_opacity=0.4,
            legend_name=f'Overall Mean Emission ({emission_column})'
        ).add_to(m)
        folium.LayerControl().add_to(m)
        m.save(output_file)

    def generate_heatmaps(self):
        # List of emission criteria
        emission_criteria_list = self.emission_powerplant_grouped_mean['Emission_Criteria'].unique()

        # Loop through each emission criteria and create a heatmap
        for emission in emission_criteria_list:
            # Filter the GeoDataFrame for the current emission criteria
            gdf_filtered = self.gdf[self.gdf['Emission_Criteria'] == emission].copy()
            gdf_filtered['Overall_Mean'] = gdf_filtered['Overall_Mean'].fillna(0)

            # Generate the heatmap for the current emission criteria
            self.create_heat_map(gdf_filtered, 'Overall_Mean', f'./{emission}_heat_map.html')

# %%


# Example usage
pickle_file_path1 = '/Users/haniftayarani/good_model/toy_src/results.pickle'
pickle_file_path2 = '/Users/haniftayarani/good_model/Model Input/Plants_group.pickle'
pickle_file_path3 = '/Users/haniftayarani/good_model/Model Input/Plants_ungroup.pickle'
shapefile = '/Users/haniftayarani/good_model/Model Input/cb_2018_us_county_5m'

emission_heat_map = EmissionHeatMap(pickle_file_path1, pickle_file_path2, pickle_file_path3, shapefile)
emission_heat_map.load_data()
emission_heat_map.process_data()
emission_heat_map.generate_heatmaps()
# %%
from bokeh.io import output_file, show
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, Slider, CustomJS, GeoJSONDataSource, HoverTool
from bokeh.layouts import column
from bokeh.palettes import Viridis6 as palette
from bokeh.transform import linear_cmap
import json

# Sample data
data = {
    'ERC_REST_ERC_WEST': {
        'type': 'transmission',
        'cost': 0.0,
        'capacity': {5000: 0.0, 5001: 0.0, 5002: 0.0, 5003: 0.0, 5004: 400, 5005: 0.0}
    },
    'ERC_WEST_ERC_REST': {
        'type': 'transmission',
        'cost': 0.0,
        'capacity': {5000: 0.0, 5001: 0.0, 5002: 200, 5003: 0.0, 5004: 0.0, 5005: 0.0}
    },
    # Add more regions...
}
regions = ['ERC_FRNT', 'ERC_GWAY', 'ERC_PHDL', 'ERC_REST', 'ERC_WEST', 'FRCC',
           'MIS_AMSO', 'MIS_AR', 'MIS_D_MS', 'MIS_IA', 'MIS_IL', 'MIS_INKY',
           'MIS_LA', 'MIS_LMI', 'MIS_MAPP', 'MIS_MIDA', 'MIS_MNWI', 'MIS_MO',
           'MIS_WOTA', 'MIS_WUMS', 'NENGREST', 'NENG_CT', 'NENG_ME', 'NY_Z_A',
           'NY_Z_B', 'NY_Z_C&E', 'NY_Z_D', 'NY_Z_F', 'NY_Z_G-I', 'NY_Z_J',
           'NY_Z_K', 'PJM_AP', 'PJM_ATSI', 'PJM_COMD', 'PJM_Dom', 'PJM_EMAC',
           'PJM_PENE', 'PJM_SMAC', 'PJM_WMAC', 'PJM_West', 'SPP_KIAM',
           'SPP_N', 'SPP_NEBR', 'SPP_SPS', 'SPP_WAUE', 'SPP_WEST', 'S_C_KY',
           'S_C_TVA', 'S_D_AECI', 'S_SOU', 'S_VACA', 'WECC_AZ', 'WECC_CO',
           'WECC_ID', 'WECC_IID', 'WECC_MT', 'WECC_NM', 'WECC_NNV',
           'WECC_PNW', 'WECC_SCE', 'WECC_SNV', 'WECC_UT', 'WECC_WY',
           'WEC_BANC', 'WEC_CALN', 'WEC_LADW', 'WEC_SDGE']
# Initialize a DataFrame to store the transmission matrix
df_matrix = pd.DataFrame(0.0, index=regions, columns=regions)

# Initialize a dictionary to store the hourly transmission data
hourly_data = {hour: df_matrix.copy() for hour in range(5000, 5006)}

# Fill the hourly transmission data
for key, value in data.items():
    parts = key.split('_')
    origin = '_'.join(parts[:-1])  # All parts except the last one
    destination = parts[-1]        # The last part
    for hour, capacity in value['capacity'].items():
        hourly_data[hour].at[origin, destination] = capacity

# Sample coordinates for regions (replace with actual coordinates)
region_coords = {
    'ERC_REST': [37.8, -96],
    'ERC_WEST': [38.8, -97],
    # Add more coordinates for other regions...
}

# Load US counties shapefile
shapefile = '/Users/haniftayarani/good_model/Model Input/cb_2018_us_county_5m'  # Replace with the path to your shapefile
gdf = gpd.read_file(shapefile)


# Prepare geodata by adding transmission capacity for a specific hour
def prepare_geodata(hour):
    gdf['capacity'] = gdf['NAME'].apply(lambda x: sum(hourly_data[hour].loc[x, :]) + sum(hourly_data[hour].loc[:, x]) if x in hourly_data[hour].index else 0)
    return gdf


# Function to create the transmission map for a given hour
def create_transmission_map(hour):
    gdf_hour = prepare_geodata(hour)
    gdf_json = json.loads(gdf_hour.to_json())
    geosource = GeoJSONDataSource(geojson=json.dumps(gdf_json))

    p = figure(title=f"Power Transmission at Hour {hour}",
               x_axis_label='Longitude', y_axis_label='Latitude',
               width=12000, height=8000,
               x_range=(-130, -65), y_range=(24, 50),  # Focus on the US region
               tools="pan,wheel_zoom,box_zoom,reset,hover,save",
               sizing_mode='stretch_both')
    p.grid.grid_line_color = None

    mapper = linear_cmap(field_name='capacity', palette=palette, low=gdf_hour['capacity'].min(), high=gdf_hour['capacity'].max())
    p.patches('xs', 'ys', source=geosource, fill_color=mapper, line_color="black", line_width=0.25, fill_alpha=1)

    hover = p.select_one(HoverTool)
    hover.point_policy = "follow_mouse"
    hover.tooltips = [("County", "@NAME"), ("Capacity", "@capacity")]

    return p


# Create initial plot
hour = 5000
p = create_transmission_map(hour)

# Slider to select hour
hour_slider = Slider(start=5000, end=5005, value=5000, step=1, title="Hour")


# Update function for the slider
def update(attr, old, new):
    hour = hour_slider.value
    layout.children[1] = create_transmission_map(hour)


hour_slider.on_change('value', update)

# Layout and show
layout = column(hour_slider, p)

# Save the output to an HTML file
output_file("transmission_map.html")
show(layout)
