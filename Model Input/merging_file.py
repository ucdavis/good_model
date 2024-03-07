import pandas as pd
import numpy as np


def merging_data(Plant, Parsed):
    Parsed1 = Parsed.copy()
    Parsed1.loc[:, "ORISCode"] = Parsed1["ORISCode"].copy()
    Parsed1["ORISPL"] = Parsed1["ORISCode"]
    merged = pd.merge(Parsed1, Plant, how="left", on="ORISPL")
    merged = merged.dropna(how='all')

    return merged


# Define a function to map fuel types
def map_fuel_type(row_input):
    plant_type = row_input["PlantType"]
    egrid_primaryfuel = row_input["PLPRMFL"]  # Replace this with the actual egrid_primaryfuel column
    if plant_type == 'Coal Steam':
        return 'Coal'
    elif plant_type == 'Nuclear':
        return 'Nuclear'
    elif plant_type == 'O/G Steam':
        return 'Oil'
    elif plant_type == 'Biomass':
        return 'Biomass'
    elif plant_type == 'IMPORT':
        return 'IMPORT'
    elif plant_type == 'IGCC' or (plant_type == 'Combined Cycle' or egrid_primaryfuel == 'NaturalGas'):
        return 'NaturalGas'
    elif plant_type == 'Combined Cycle' and egrid_primaryfuel == 'NaturalGas':
        return 'NaturalGas'
    elif plant_type == 'Geothermal':
        return 'Geothermal'
    elif (plant_type == 'Combustion Turbine') and (egrid_primaryfuel == 'NG'):
        return 'NaturalGas'
    elif (plant_type == 'Combustion Turbine') and (egrid_primaryfuel == 'DFO'):
        return 'Oil'
    elif (plant_type == 'Combustion Turbine') and (egrid_primaryfuel == 'WDS'):
        return 'Biomass'
    else:
        return row_input["FuelType"]


# Create a function to assign fuel costs
def assign_fuel_costs(input_df):
    merged_short = input_df[["RegionName", "StateName", "CountyName", "PlantType", "FuelType", "FossilUnit", "Capacity", "Firing", "Bottom", "EMFControls", "FuelCostTotal", "VOMCostTotal",
                           "UTLSRVNM", "NERC", "SUBRGN", "FIPSST", "FIPSCNTY", "LAT", "LON", "PLPRMFL", "PLNOXRTA", "PLSO2RTA", "PLCO2RTA", "PLCH4RTA", "PLN2ORTA", "HeatRate"]]

    # Apply the function to the DataFrame to create a new column 'MappedFuelType'
    merged_short.loc[:, "FuelType"] = merged_short.apply(map_fuel_type, axis=1).copy()
    merged_short = merged_short.loc[~((merged_short["FuelType"].isna()) & (merged_short["PlantType"] != "IMPORT"))].reset_index(drop=True)
    # Return the loaded dataframes

    for r in range(len(merged_short)):
        if (merged_short.loc[r, 'FossilUnit'] == 'Fossil') and (merged_short.loc[r, 'FuelCostTotal'] == 0):
            fuel_type_missing = merged_short.loc[r, 'FuelType']
            ipm_region = merged_short.loc[r, 'RegionName']
            mean_fuel_cost = merged_short[(merged_short['FuelType'] == fuel_type_missing) & (merged_short['RegionName'] == ipm_region)]['FuelCostTotal'].mean()
            merged_short.at[r, 'FuelCostTotal'] = mean_fuel_cost

            if (merged_short.loc[r, 'FossilUnit'] == 'Fossil') and (merged_short.loc[r, 'FuelCostTotal'] == 0):
                fuel_type_missing = merged_short.loc[r, 'FuelType']
                ipm_state = merged_short.loc[r, 'StateName']
                mean_fuel_cost = merged_short[(merged_short['FuelType'] == fuel_type_missing) & (merged_short['StateName'] == ipm_state)]['FuelCostTotal'].mean()
                merged_short.at[r, 'FuelCostTotal'] = mean_fuel_cost

    merged_short.loc[merged_short["FuelType"] == "Hydro", "FuelCostTotal"] = 0
    merged_short.loc[merged_short["FuelType"] == "Pumps", "FuelCostTotal"] = 0

    return merged_short


def fill_missing_fuel_costs(input_df, transmission_df):
    merged_short1 = input_df.loc[(input_df["FossilUnit"] == "Fossil") & (input_df["FuelType"] != "Fwaste") & (input_df["FuelCostTotal"] == 0)]
    df_matrix = transmission_df[["From", "To"]]
    regions_with_missing_fuel_cost = input_df.loc[(input_df["FossilUnit"] == "Fossil") & (input_df["FuelType"] != "Fwaste") & (input_df["FuelCostTotal"] == 0)]["RegionName"].tolist()

    neighbors = {}
    for index, row in df_matrix.iterrows():
        from_region = row['From']
        to_region = row['To']

        if from_region not in neighbors:
            neighbors[from_region] = []
        neighbors[from_region].append(to_region)

        if to_region not in neighbors:
            neighbors[to_region] = []
        neighbors[to_region].append(from_region)

    for region in regions_with_missing_fuel_cost:
        fuel_type = merged_short1.loc[merged_short1["RegionName"] == region, "FuelType"].values[0]

        region_neighbors = neighbors.get(region, [])
        matching_rows = input_df[(input_df['RegionName'].isin(region_neighbors)) & (input_df['FuelType'] == fuel_type)]
        avg_fuel_cost = matching_rows['FuelCostTotal'].mean()

        condition = (merged_short1['RegionName'] == region) & (merged_short1['FuelType'] == fuel_type)
        if not matching_rows.empty:
            merged_short1.loc[condition, 'FuelCostTotal'] = avg_fuel_cost
        else:
            merged_short1.loc[condition, 'FuelCostTotal'] = 0

    for index in merged_short1.index:
        input_df.loc[index] = merged_short1.loc[index]

    return input_df


def assign_em_rates(input_df):
    input_df.loc[(input_df["FuelType"].isin(["Pumps", "Hydro", "Geothermal", "Non-Fossil", "EnerStor", "Nuclear", "Solar", "Wind"])), "PLCO2RTA"] = 0
    input_df.loc[(input_df["FuelType"].isin(["Pumps", "Hydro", "Geothermal", "Non-Fossil", "EnerStor", "Nuclear", "Solar", "Wind"])), "PLSO2RTA"] = 0
    input_df.loc[(input_df["FuelType"].isin(["Pumps", "Hydro", "Geothermal", "Non-Fossil", "EnerStor", "Nuclear", "Solar", "Wind"])), "PLCH4RTA"] = 0
    input_df.loc[(input_df["FuelType"].isin(["Pumps", "Hydro", "Geothermal", "Non-Fossil", "EnerStor", "Nuclear", "Solar", "Wind"])), "PLN2ORTA"] = 0
    input_df.loc[(input_df["FuelType"].isin(["Pumps", "Hydro", "Geothermal", "Non-Fossil", "EnerStor", "Nuclear", "Solar", "Wind"])), "PLNOXRTA"] = 0
    for r in range(input_df.shape[0]):
        if np.isnan(input_df.at[r, 'PLCO2RTA']):
            similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                    (input_df['Capacity'] > input_df.at[r, 'Capacity'] * 0.85) &
                                    (input_df['Capacity'] < input_df.at[r, 'Capacity'] * 1.15) &
                                    (input_df['HeatRate'] > input_df.at[r, 'HeatRate'] * 0.85) &
                                    (input_df['HeatRate'] < input_df.at[r, 'HeatRate'] * 1.15)]

            input_df.at[r, 'PLCO2RTA'] = similar_rows['PLCO2RTA'].mean()
            input_df.at[r, 'PLNOXRTA'] = similar_rows['PLNOXRTA'].mean()
            input_df.at[r, 'PLCH4RTA'] = similar_rows['PLCH4RTA'].mean()
            input_df.at[r, 'PLN2ORTA'] = similar_rows['PLN2ORTA'].mean()
            input_df.at[r, 'PLSO2RTA'] = similar_rows['PLSO2RTA'].mean()

        if pd.isna(input_df.at[r, 'PLCO2RTA']) and input_df.at[r, 'Capacity'] < 50:
            input_df.at[r, 'PLCO2RTA'] = 0
            input_df.at[r, 'PLNOXRTA'] = 0
            input_df.at[r, 'PLCH4RTA'] = 0
            input_df.at[r, 'PLN2ORTA'] = 0
            input_df.at[r, 'PLSO2RTA'] = 0
    # PM emissions
    input_df['PLPMTRO'] = np.select(
        [(input_df['FuelType'] == 'Coal') & (input_df['PLPRMFL'] == 'RC'),
         (input_df['FuelType'] == 'Coal') & (input_df['PLPRMFL'] != 'RC'),
         (input_df['FuelType'] == 'Oil') & (input_df['PLPRMFL'] != 'WO'),
         (input_df['FuelType'] == 'NaturalGas'),
         (input_df['FuelType'] == 'LF Gas'),
         (input_df['FuelType'] == 'Biomass') & (input_df['PLPRMFL'].isin(['WDL', 'WDS'])),
         (input_df['FuelType'] == 'Oil') & (input_df['PLPRMFL'] == 'WO')],
        [0.08, 0.04, 1.4 / 145, 5.7 / 1020, 0.55 / 96.75, 0.017, 65 / 145],
        default=0)

    input_df['PLPMTRO'] = input_df['PLPMTRO'] * input_df['HeatRate'] / 1000

    return input_df


# Create a MultiIndex for the columns with month and day
def long_wide(input_df):
    df = input_df.copy()
    # Define the columns to keep (first four columns)
    columns_to_keep = ['Region Name', 'State Name', 'Resource Class']

    # Group by the first four columns and concatenate columns 6 to 26
    result_df = df.groupby(columns_to_keep).apply(lambda x: x.iloc[:, 6:].values.flatten()).reset_index()
    result_df = result_df.rename(columns={result_df.columns[3]: "Profile"})

    # Convert the Profile column to a list of lists
    result_df['Profile'] = result_df['Profile'].tolist()

    # Create a new DataFrame from the list of lists in the Profile column
    result_df_profile = pd.DataFrame.from_records(result_df['Profile'])

    # Remove the original Profile column
    result_df = result_df.drop(columns=['Profile'])

    result_df = pd.concat([result_df, result_df_profile], axis=1)
    return result_df


# Forward fill missing values in each column
def ffill_ren_cap(Wind_onshore_capacity_df, Solar_regional_capacity_df):
    Wind_onshore_capacity_df['IPM Region'].ffill(inplace=True)
    Wind_onshore_capacity_df['State'].ffill(inplace=True)
    Solar_regional_capacity_df['IPM Region'].ffill(inplace=True)
    Solar_regional_capacity_df['State'].ffill(inplace=True)
    # Wind_onshore_capacity_df.fillna(0, inplace=True)
    # Solar_regional_capacity_df.fillna(0, inplace=True)
    # Wind_onshore_capacity_df.fillna(0, inplace=True)
    # Solar_regional_capacity_df.fillna(0, inplace=True)
    return Wind_onshore_capacity_df, Solar_regional_capacity_df


def ffill_ren_cost(Wind_onshore_cost_df, Solar_regional_cost_df):
    Wind_onshore_cost_df['IPM Region'].ffill(inplace=True)
    Wind_onshore_cost_df['State'].ffill(inplace=True)
    Solar_regional_cost_df['IPM Region'].ffill(inplace=True)
    Solar_regional_cost_df['State'].ffill(inplace=True)
    # Wind_onshore_cost_df.fillna(10**9, inplace=True)
    # Solar_regional_cost_df.fillna(10**9, inplace=True)
    return Wind_onshore_cost_df, Solar_regional_cost_df


def transmission_func(Input_df):
    Transmission_Capacity_df = pd.DataFrame(Input_df, columns=["From", "To", "Capacity TTC (MW)"])
    Transmission_Energy_df = pd.DataFrame(Input_df, columns=["From", "To", "Energy TTC (MW)"])
    Transmission_Cost_df = pd.DataFrame(Input_df, columns=["From", "To", "Transmission Tariff (2016 mills/kWh)"])
    # Create a pivot table to convert the DataFrame into a matrix
    Transmission_Capacity_df = Transmission_Capacity_df.pivot(index="From", columns="To", values="Capacity TTC (MW)")
    Transmission_Energy_df = Transmission_Energy_df.pivot(index="From", columns="To", values="Energy TTC (MW)")
    Transmission_Cost_df = Transmission_Cost_df.pivot(index="From", columns="To", values="Transmission Tariff (2016 mills/kWh)")
    # If there are missing values (NaN) in the matrix, you can fill them with 0
    Transmission_Capacity_df = Transmission_Capacity_df.fillna(0)
    Transmission_Energy_df = Transmission_Energy_df.fillna(0)
    Transmission_Cost_df = Transmission_Cost_df.fillna(0)

    return Transmission_Capacity_df, Transmission_Energy_df, Transmission_Cost_df


def cluster_and_aggregate(df, num_bins=20):
    # Define custom heat rate ranges
    bin_width = (df['HeatRate'].max() - df['HeatRate'].min()) / num_bins
    # Assign cluster numbers to each data point
    df['HeatRate_Cluster'] = np.digitize(df['HeatRate'], np.arange(df['HeatRate'].min(), df['HeatRate'].max(), bin_width))

    df['GroupID'] = df.groupby(["RegionName", "PlantType", "FuelType", "HeatRate_Cluster"]).ngroup()

    result = df.groupby(["RegionName", "PlantType", "FuelType", "HeatRate_Cluster"])[
        ["FossilUnit", "Capacity", "FuelCostTotal", "NERC", "PLNOXRTA", "PLSO2RTA", "PLCO2RTA", "PLCH4RTA", "PLN2ORTA", "PLPMTRO", "GroupID"]
    ].agg({
        "Capacity": 'sum',
        "FuelCostTotal": 'mean',
        "PLNOXRTA": 'mean',
        "PLSO2RTA": 'mean',
        "PLCO2RTA": 'mean',
        "PLCH4RTA": 'mean',
        "PLN2ORTA": 'mean',
        "PLPMTRO": 'mean',
        "GroupID": 'mean'
    }).reset_index()

    return df, result


# Create a MultiIndex for the columns with month and day


def long_wide_load(input_df):
    df = input_df.copy()
    # Define the columns to keep (first four columns)
    columns_to_keep = ['Region']
    # Group by the first four columns and concatenate columns 6 to 26
    result_df = df.groupby(columns_to_keep).apply(lambda x: x.iloc[:, 3:].values.flatten()).reset_index()
    result_df = result_df.rename(columns={result_df.columns[1]: "Profile"})
    # Convert the Profile column to a list of lists
    result_df['Profile'] = result_df['Profile'].tolist()
    # Create a new DataFrame from the list of lists in the Profile column
    result_df_profile = pd.DataFrame.from_records(result_df['Profile'])
    # Remove the original Profile column
    result_df = result_df.drop(columns=['Profile'])
    result_df = pd.concat([result_df, result_df_profile], axis=1)

    return result_df


def load_dic(df):
    df = df.set_index(df.columns[0])
    data_dict = df.to_dict(orient='index')
    result_dict = {(row_index, col_index): value for row_index, row_data in data_dict.items()
                   for col_index, value in row_data.items()}
    return result_dict


def plant_dic(df):
    df = df.set_index([df.columns[0], df.columns[1], df.columns[2], df.columns[3]])
    data_dict = df.to_dict(orient='index')
    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        key = row_index
        value = list(row_data.values())  # Assuming there's only one value in row_data
        result_dict[key] = value
    return result_dict


def wind_cap_dic(df):
    df = df.set_index([df.columns[0], df.columns[1], df.columns[2]])
    data_dict = df.to_dict(orient='index')
    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        for col_index, value in row_data.items():
            if not pd.isna(value):  # Check if the value is not NaN
                key = (*row_index, col_index)
                result_dict[key] = value
    return result_dict


def wind_cost_dic(df):
    df = df.set_index([df.columns[0], df.columns[1], df.columns[2]])
    data_dict = df.to_dict(orient='index')
    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        for col_index, value in row_data.items():
            if not pd.isna(value):  # Check if the value is not NaN
                key = (*row_index, col_index)
                result_dict[key] = value
    return result_dict


def plant_capacity(input_df):
    Plant_capacity = input_df.groupby(["RegionName", "FuelType"])["Capacity"].sum().reset_index()
    Plant_capacity = Plant_capacity.set_index([Plant_capacity.columns[0], Plant_capacity.columns[1]])
    data_dict = Plant_capacity.to_dict(orient='index')
    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        key = row_index
        value = next(iter(row_data.values()))  # Get the first (and presumably only) value
        result_dict[key] = value

    return result_dict


def solar_cap_dic(df):
    df = df.set_index([df.columns[0], df.columns[1], df.columns[2]])
    data_dict = df.to_dict(orient='index')

    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        for col_index, value in row_data.items():
            if not pd.isna(value):  # Check if the value is not NaN
                key = (*row_index, col_index)
                result_dict[key] = value
    return result_dict


def solar_cost_dic(df):
    df = df.set_index([df.columns[0], df.columns[1], df.columns[2]])
    data_dict = df.to_dict(orient='index')

    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        for col_index, value in row_data.items():
            if not pd.isna(value):  # Check if the value is not NaN
                key = (*row_index, col_index)
                result_dict[key] = value
    return result_dict


def cp_dic(df):
    df = df.set_index([df.columns[0], df.columns[1], df.columns[2]])
    data_dict = df.to_dict(orient='index')

    # Process the nested dictionary
    result_dict = {}
    for row_index, row_data in data_dict.items():
        for col_index, value in row_data.items():
            if not pd.isna(value):  # Check if the value is not NaN
                key = (*row_index, col_index)
                result_dict[key] = value
    return result_dict


def transmission_dic1(df):
    data_dict = {(row, col): value for (row, col), value in df.stack().items() if value != 0}
    return data_dict


def transmission_dic2(df):
    data_dict = {(row, col): value for (row, col), value in df.stack().items()}
    return data_dict


def trans_index(df):
    # Create a dictionary to store row names and corresponding column names where values are not zero
    result_dict = {}

    # Iterate over each row in the DataFrame
    for i, row in df.iterrows():
        # Find the column names where the value is not zero or NaN
        non_zero_column_names = list(row.index[(row != 0) & ~pd.isna(row)])

        # Store the non-zero column names in the dictionary
        result_dict[f"{row.name}"] = non_zero_column_names

    return result_dict


def renewable_transmission_cost(Unit_Cost_df, Regional_Cost_df, Wind_capital_cost_df, Solar_capital_cost_photov_df):
    user_input = input("Please enter a year(2021): ")

    # Selecting relevant rows based on user input
    selected_rows = Unit_Cost_df[Unit_Cost_df['year'].str.contains(user_input)]
    selected_rows = selected_rows[selected_rows["cost"] == 'Capital(2016$/kW)']
    selected_rows = selected_rows[["SolarPhotovoltaic", "OnshoreWind"]]
    # Creating a new DataFrame for regional costs
    Regional_Cost_selected = Regional_Cost_df[['ModelRegion', 'OnshoreWind', 'SolarPV']].copy()
    Regional_Cost_selected['OnshoreWind'] = Regional_Cost_selected['OnshoreWind'] * selected_rows['OnshoreWind'].iloc[0]
    Regional_Cost_selected['SolarPV'] = Regional_Cost_selected['SolarPV'] * selected_rows['SolarPhotovoltaic'].iloc[0]
    Regional_Cost_selected = Regional_Cost_selected.rename(columns={"ModelRegion": "IPM Region"})
    # Copying DataFrames for wind and solar capital costs
    Wind_capital_cost_copy = Wind_capital_cost_df.copy()
    Solar_capital_cost_photov_copy = Solar_capital_cost_photov_df.copy()
    # Merging regional cost information with wind and solar capital cost DataFrames
    Wind_capital_cost_copy = pd.merge(Wind_capital_cost_copy, Regional_Cost_selected[["IPM Region", "OnshoreWind"]], how="left", on="IPM Region")
    Solar_capital_cost_photov_copy = pd.merge(Solar_capital_cost_photov_copy, Regional_Cost_selected[["IPM Region", "SolarPV"]], how="left", on="IPM Region")
    # Summing values and removing redundant columns for wind and solar capital costs
    Wind_capital_cost_copy.iloc[:, 3:9] = Wind_capital_cost_copy.iloc[:, 3:9].add(Wind_capital_cost_copy.iloc[:, -1], axis=0)
    Solar_capital_cost_photov_copy.iloc[:, 3:9] = Solar_capital_cost_photov_copy.iloc[:, 3:9].add(Solar_capital_cost_photov_copy.iloc[:, -1], axis=0)
    Wind_capital_cost_copy = Wind_capital_cost_copy.iloc[:, :-1]
    Solar_capital_cost_photov_copy = Solar_capital_cost_photov_copy.iloc[:, :-1]

    # Creating dictionaries for wind and solar capital costs
    Wind_trans_capital_cost_final = wind_cost_dic(Wind_capital_cost_copy)
    Solar_trans_capital_cost_photov_final = solar_cost_dic(Solar_capital_cost_photov_copy)

    return Wind_trans_capital_cost_final, Solar_trans_capital_cost_photov_final, Wind_capital_cost_copy, Solar_capital_cost_photov_copy


def trans_object(df1, df2):
    link_example = []

    # Iterate through each row and column to extract data
    for origin, row in df1.iterrows():
        for destination, capacity in row.items():  # Using items() instead of iteritems()
            # Print values for debugging
            # print("Origin:", origin)
            # print("Destination:", destination)

            # Check if the cost dataframe has the same row and column indices
            if origin in df2.index and destination in df2.columns:
                cost = df2.loc[origin, destination]
                # print("Cost:", cost)
            else:
                print("Error: No cost found for this transmission line")
                continue  # Skip to the next iteration if cost is not available

            # print("Capacity:", capacity)

            # Append data to link_example list
            link_example.append({'origin': origin, 'destination': destination, 'cost': cost, 'capacity': capacity})
    return link_example


def load_object(df):
    load_example = []  # List to store load data in the desired format

    # Iterate through each row of the dataframe
    for index, row in df.iterrows():
        region_name = row.iloc[0]  # First column contains the region name
        load_data = row.iloc[1:]  # Load data starts from the second column onwards

        dependents = []  # List to store load data for each hour

        # Iterate through each hour and load data
        for hour, load in load_data.items():
            load_hour = {hour: load}
            dependents.append(load_hour)

        # Append data to load_example list
        load_example.append({'id': region_name, 'dependents': [{'data_type': 'load', 'parameters': {'load': dependents}}]})
    return load_example


def gen_object(df):
    gen_example = []  # List to store load data in the desired format
    df = df[df["PlantType"] != "Energy Storage"]
    df = df[df["PlantType"] != "Solar PV"]
    df = df[df["PlantType"] != "Onshore Wind"]
    # Iterate through each row of the dataframe
    for index, row in df.iterrows():
        region_name = row.iloc[0]  # First column contains the region name
        plant_type = row.iloc[1]
        fuel_type = row.iloc[2]
        cost = row.iloc[5]
        capacity = row.iloc[4]
        group_id = row.iloc[12]
        # Append data to load_example list
        gen_example.append({'id': region_name, 'dependents': [{'data_type': "generators", 'parameters': [{'plant_type': plant_type, 'parameters': [{'fuel_type': fuel_type, 'values':{"cost": cost, "capacity": capacity, "group_id": group_id}}]}]}]})
    return gen_example


def storage_object(df):
    df = df[df["PlantType"] == "Energy Storage"]
    stor_example = []  # List to store load data in the desired format

    # Iterate through each row of the dataframe
    for index, row in df.iterrows():
        region_name = row.iloc[0]  # First column contains the region name
        plant_type = row.iloc[1]
        cost = row.iloc[5]
        capacity = row.iloc[4]
        group_id = row.iloc[12]
        # Append data to load_example list
        stor_example.append({'id': region_name, 'dependents': [{'data_type': plant_type, 'parameters':  [{"cost": cost, "capacity": capacity}]}]})
    return stor_example


def solar_object(df1, df2, df3, df4, Plants_group, Region):
    max_cap = Plants_group.groupby(["RegionName", "PlantType"])["Capacity"].sum().reset_index(drop=False)
    max_cap = max_cap[max_cap["PlantType"] == "Solar PV"].reset_index(drop=True)
    # Rename the first two columns in df1
    df1 = df1.rename(columns={'Region Name': 'IPM Region', 'State Name': 'State'})

    # Create 'New Resource Class' column and populate it in df2, df3, and df4
    for df in [df2, df3, df4]:
        df.sort_values(by=['IPM Region', 'State', 'Resource Class'], inplace=True)
        df['New Resource Class'] = df.groupby('IPM Region').cumcount() + 1

    # Merge df1 with df2 on 'IPM Region', 'State', and 'Resource Class' columns
    df1 = pd.merge(df1, df2[['IPM Region', 'State', 'Resource Class', 'New Resource Class']], how="left", on=["IPM Region", "State", "Resource Class"])
    # Initialize an empty list to hold solar examples
    solar_examples = []

    # Iterate over each region name
    for region_name in Region:
        # Initialize a dictionary for the current region
        region_data = {'id': region_name, 'dependents': []}

        # Filter DataFrames for the current region
        gen_profile_df = df1[df1['IPM Region'] == region_name]
        solar_cost_df = df2[df2['IPM Region'] == region_name]
        max_capacity_df = df3[df3['IPM Region'] == region_name]
        installed_capacity_df = max_cap[max_cap['RegionName'] == region_name]
        trans_cost_df = df4[df4['IPM Region'] == region_name]

        # Add solar generation profile data
        solar_gen_params = {'data_type': 'solar_gen', 'parameters': []}
        for index, row in gen_profile_df.iterrows():
            gen_profile = row.drop(['IPM Region', 'Resource Class', 'State', "New Resource Class"]).dropna().to_dict()
            solar_gen_params['parameters'].append({'Resource Class': row['New Resource Class'], 'generation_profile': gen_profile})
        region_data['dependents'].append(solar_gen_params)

        # Add solar cost data
        solar_cost_params = {'data_type': 'solar_cost', 'parameters': []}
        for index, row in solar_cost_df.iterrows():
            cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_cost_params['parameters'].append({'Resource Class': row['New Resource Class'], 'cost': cost_profile})
        region_data['dependents'].append(solar_cost_params)

        # Add solar max capacity data
        solar_max_capacity_params = {'data_type': 'solar_max_capacity', 'parameters': []}
        for index, row in max_capacity_df.iterrows():
            max_capacity_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_max_capacity_params['parameters'].append({'Resource Class ': row['New Resource Class'], 'max_capacity': max_capacity_profile})
        region_data['dependents'].append(solar_max_capacity_params)

        # Add solar installed capacity data
        solar_installed_capacity_params = {'data_type': 'solar_installed_capacity', 'parameters': []}
        for index, row in installed_capacity_df.iterrows():
            solar_installed_capacity_params['parameters'].append({'capacity': row['Capacity']})
        region_data['dependents'].append(solar_installed_capacity_params)

        # Add solar transmission cost data
        solar_transmission_cost_params = {'data_type': 'solar_transmission_cost', 'parameters': []}
        for index, row in trans_cost_df.iterrows():
            trans_cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_transmission_cost_params['parameters'].append({'Resource Class': row['New Resource Class'], 'transmission_cost': trans_cost_profile})
        region_data['dependents'].append(solar_transmission_cost_params)

        # Append region data to solar examples
        solar_examples.append(region_data)

    return solar_examples


def wind_object(df1, df2, df3, df4, Plants_group, Region):
    max_cap = Plants_group.groupby(["RegionName", "PlantType"])["Capacity"].sum().reset_index(drop=False)
    max_cap = max_cap[max_cap["PlantType"] == "Onshore Wind"].reset_index(drop=True)

    # Rename the first two columns in df1
    df1 = df1.rename(columns={'Region Name': 'IPM Region', 'State Name': 'State'})

    # Create 'New Resource Class' column and populate it in df2, df3, and df4
    for df in [df2, df3, df4]:
        df.sort_values(by=['IPM Region', 'State', 'Resource Class'], inplace=True)
        df['New Resource Class'] = df.groupby('IPM Region').cumcount() + 1

    # Merge df1 with df2 on 'IPM Region', 'State', and 'Resource Class' columns
    df1 = pd.merge(df1, df2[['IPM Region', 'State', 'Resource Class', 'New Resource Class']], how="left", on=["IPM Region", "State", "Resource Class"])

    # Initialize an empty list to hold solar examples
    wind_examples = []

    # Iterate over each region name
    for region_name in Region:
        # Initialize a dictionary for the current region
        region_data = {'id': region_name, 'dependents': []}

        # Filter DataFrames for the current region
        gen_profile_df = df1[df1['IPM Region'] == region_name]
        wind_cost_df = df2[df2['IPM Region'] == region_name]
        max_capacity_df = df3[df3['IPM Region'] == region_name]
        installed_capacity_df = max_cap[max_cap['RegionName'] == region_name]
        trans_cost_df = df4[df4['IPM Region'] == region_name]

        # Add solar generation profile data
        solar_gen_params = {'data_type': 'wind_gen', 'parameters': []}
        for index, row in gen_profile_df.iterrows():
            gen_profile = row.drop(['IPM Region', 'Resource Class', 'State', "New Resource Class"]).dropna().to_dict()
            solar_gen_params['parameters'].append({'Resource Class': row['New Resource Class'], 'generation_profile': gen_profile})
        region_data['dependents'].append(solar_gen_params)

        # Add solar cost data
        solar_cost_params = {'data_type': 'wind_cost', 'parameters': []}
        for index, row in wind_cost_df.iterrows():
            cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_cost_params['parameters'].append({'Resource Class': row["New Resource Class"], 'cost': cost_profile})
        region_data['dependents'].append(solar_cost_params)

        # Add solar max capacity data
        solar_max_capacity_params = {'data_type': 'wind_max_capacity', 'parameters': []}
        for index, row in max_capacity_df.iterrows():
            max_capacity_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_max_capacity_params['parameters'].append({'Resource Class ': row["New Resource Class"], 'max_capacity': max_capacity_profile})
        region_data['dependents'].append(solar_max_capacity_params)

        # Add solar installed capacity data
        solar_installed_capacity_params = {'data_type': 'wind_installed_capacity', 'parameters': []}
        for index, row in installed_capacity_df.iterrows():
            solar_installed_capacity_params['parameters'].append({'capacity': row['Capacity']})
        region_data['dependents'].append(solar_installed_capacity_params)

        # Add solar transmission cost data
        solar_transmission_cost_params = {'data_type': 'wind_transmission_cost', 'parameters': []}
        for index, row in trans_cost_df.iterrows():
            trans_cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_transmission_cost_params['parameters'].append({'Resource Class': row["New Resource Class"], 'transmission_cost': trans_cost_profile})
        region_data['dependents'].append(solar_transmission_cost_params)

        # Append region data to solar examples
        wind_examples.append(region_data)

    return wind_examples

