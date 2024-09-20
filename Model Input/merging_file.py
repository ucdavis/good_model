import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import networkx as nx
import time
import math
# %%


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
    selected_columns = ["UniqueID", "ORISPL", "PLNGENAN",  "RegionName", "StateName", "CountyName", "NERC",  "PlantType", "FuelType", "FossilUnit", "Capacity", "Firing", "Bottom", "EMFControls", "FOMCost" , "FuelUseTotal", "FuelCostTotal", "VOMCostTotal",
                        "UTLSRVNM", "SUBRGN", "FIPSST", "FIPSCNTY", "LAT", "LON", "PLPRMFL", "PLNOXRTA", "PLSO2RTA", "PLCO2RTA", "PLCH4RTA", "PLN2ORTA", "HeatRate"]

    merged_short = input_df[selected_columns].copy()
    merged_short["FuelCost[$/MWh]"] = ((merged_short["FuelCostTotal"] / (merged_short["FuelUseTotal"] + 1)) * merged_short["HeatRate"]) / 1000
    # Define the plant types that should use VOMCostTotal directly
    plant_types_direct_vom = ["Solar", "Solar PV", "Wind", "Hydro", "Energy Storage", "Solar Thermal", "New Battery Storage", "Offshore Wind"]

    # Calculate VOMCost[$/MWh] with conditions
    merged_short["VOMCost[$/MWh]"] = np.where(
        merged_short["PlantType"].isin(plant_types_direct_vom),
        merged_short["VOMCostTotal"],
        ((merged_short["VOMCostTotal"] / (merged_short["FuelUseTotal"] + 1)) * merged_short["HeatRate"]) / 1000
    )

    # Calculate FOMCost[$/MWh] with conditions
    merged_short["FOMCost[$/MWh]"] = np.where(
        merged_short["PlantType"].isin(plant_types_direct_vom),
        merged_short["FOMCost"],
        (((merged_short["FOMCost"]*1e6)) / (merged_short["Capacity"]*8760))
    )

    # Add FOMCost[$/MWh] to VOMCost[$/MWh] if PlantType is Nuclear
    merged_short["VOMCost[$/MWh]"] = np.where(
        merged_short["PlantType"] == "Nuclear",
        merged_short["VOMCost[$/MWh]"] + merged_short["FOMCost[$/MWh]"],
        merged_short["VOMCost[$/MWh]"]
    )

    # Identify rows with NaN values in the "NERC" column
    nan_indices = merged_short[merged_short['NERC'].isna()].index

    # Fill NaN values in "NERC" column with mode of "NERC" for the same region
    for idx in nan_indices:
        region = merged_short.at[idx, 'RegionName']
        region_mode = merged_short[merged_short['RegionName'] == region]['NERC'].mode()
        if not region_mode.empty:
            merged_short.at[idx, 'NERC'] = region_mode.iloc[0]

    merged_short["FuelType"] = merged_short.apply(map_fuel_type, axis=1)
    merged_short = merged_short[~(merged_short["FuelType"].isna() & (merged_short["PlantType"] != "IMPORT"))].reset_index(drop=True)

    for idx, row in merged_short.iterrows():
        fuel_type = row['FuelType']
        fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['FuelCost[$/MWh]'] > 1)]['FuelCost[$/MWh]']
        mean_cost = fuel_costs.mean()
        std_cost = fuel_costs.std()
        threshold = mean_cost - (1/2) * std_cost
        if threshold < 0:
            threshold = 0
        if row['FuelCost[$/MWh]'] <= threshold:
            non_zero_costs = merged_short[(merged_short['FuelType'] == row['FuelType']) & (merged_short['RegionName'] == row['RegionName']) & (merged_short['FuelCost[$/MWh]'] > threshold)]['FuelCost[$/MWh]']
            if not non_zero_costs.empty:
                merged_short.at[idx, 'FuelCost[$/MWh]'] = np.random.choice(non_zero_costs)

            if merged_short.at[idx, 'FuelCost[$/MWh]'] <= threshold:
                state_fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['StateName'] == row['StateName']) & (merged_short['FuelCost[$/MWh]'] > threshold)]['FuelCost[$/MWh]']
                non_zero_costs = state_fuel_costs[state_fuel_costs > threshold]
                if not non_zero_costs.empty:
                    merged_short.at[idx, 'FuelCost[$/MWh]'] = np.random.choice(non_zero_costs)

                if merged_short.at[idx, 'FuelCost[$/MWh]'] <= threshold:
                    adj_fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['NERC'] == row['NERC']) & (merged_short['FuelCost[$/MWh]'] > threshold)]['FuelCost[$/MWh]']
                    non_zero_costs = adj_fuel_costs[adj_fuel_costs > threshold]
                    if not non_zero_costs.empty:
                        merged_short.at[idx, 'FuelCost[$/MWh]'] = np.random.choice(non_zero_costs)

                    if merged_short.at[idx, 'FuelCost[$/MWh]'] <= threshold:
                        all_fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['FuelCost[$/MWh]'] > threshold)]['FuelCost[$/MWh]']
                        non_zero_costs = all_fuel_costs[all_fuel_costs > threshold]
                        if not non_zero_costs.empty:
                            merged_short.at[idx, 'FuelCost[$/MWh]'] = np.random.choice(non_zero_costs)

    for idx, row in merged_short.iterrows():
        fuel_type = row['FuelType']
        fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['VOMCost[$/MWh]'] > 1)]['VOMCost[$/MWh]']
        mean_cost = fuel_costs.mean()
        std_cost = fuel_costs.std()
        threshold = mean_cost - (2) * std_cost
        if threshold < 0:
            threshold = 0
        if row['VOMCost[$/MWh]'] <= threshold:
            non_zero_costs = merged_short[(merged_short['FuelType'] == row['FuelType']) & (merged_short['RegionName'] == row['RegionName']) & (merged_short['VOMCost[$/MWh]'] > threshold)]['VOMCost[$/MWh]']
            if not non_zero_costs.empty:
                merged_short.at[idx, 'VOMCost[$/MWh]'] = np.random.choice(non_zero_costs)

            if merged_short.at[idx, 'VOMCost[$/MWh]'] <= threshold:
                state_fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['StateName'] == row['StateName']) & (merged_short['VOMCost[$/MWh]'] > threshold)]['VOMCost[$/MWh]']
                non_zero_costs = state_fuel_costs[state_fuel_costs > threshold]
                if not non_zero_costs.empty:
                    merged_short.at[idx, 'VOMCost[$/MWh]'] = np.random.choice(non_zero_costs)

                if merged_short.at[idx, 'VOMCost[$/MWh]'] <= threshold:
                    adj_fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['NERC'] == row['NERC']) & (merged_short['VOMCost[$/MWh]'] > threshold)]['VOMCost[$/MWh]']
                    non_zero_costs = adj_fuel_costs[adj_fuel_costs > threshold]
                    if not non_zero_costs.empty:
                        merged_short.at[idx, 'VOMCost[$/MWh]'] = np.random.choice(non_zero_costs)

                    if merged_short.at[idx, 'VOMCost[$/MWh]'] <= threshold:
                        all_fuel_costs = merged_short[(merged_short['FuelType'] == fuel_type) & (merged_short['VOMCost[$/MWh]'] > threshold)]['VOMCost[$/MWh]']
                        non_zero_costs = all_fuel_costs[all_fuel_costs > threshold]
                        if not non_zero_costs.empty:
                            merged_short.at[idx, 'VOMCost[$/MWh]'] = np.random.choice(non_zero_costs)
    merged_short["Fuel_VOM_Cost"] = merged_short["FuelCost[$/MWh]"] + merged_short["VOMCost[$/MWh]"]
    return merged_short


def adjust_coal_generation_cost(df):
    # Filter only the rows with FuelType 'Coal'
    coal_data = df[df['FuelType'] == 'Coal'].copy()

    # Define the target mean
    target_mean = 23

    # Calculate the current mean
    current_mean = coal_data['Fuel_VOM_Cost'].mean()

    # Adjust the costs to have the target mean
    adjustment_factor = target_mean / current_mean
    coal_data['adjusted_cost'] = coal_data['Fuel_VOM_Cost'] * adjustment_factor

    # Replace the original Fuel_VOM_Cost with the adjusted values
    df.loc[df['FuelType'] == 'Coal', 'Fuel_VOM_Cost'] = coal_data['adjusted_cost']

    return df


def adjust_nuclear_generation_cost(df):
    # Filter only the rows with FuelType 'Nuclear'
    nuclear_data = df[df['FuelType'] == 'Nuclear'].copy()

    # Define the target mean
    target_mean = 21.2

    # Calculate the current mean
    current_mean = nuclear_data['Fuel_VOM_Cost'].mean()

    # Adjust the costs to have the target mean
    adjustment_factor = target_mean / current_mean
    nuclear_data['adjusted_cost'] = nuclear_data['Fuel_VOM_Cost'] * adjustment_factor

    # Replace the original Fuel_VOM_Cost with the adjusted values
    df.loc[df['FuelType'] == 'Nuclear', 'Fuel_VOM_Cost'] = nuclear_data['adjusted_cost']

    return df


def assign_em_rates(input_df, input_df_old):

    input_df.loc[input_df["FuelType"].isin(["Pumps", "Hydro", "Geothermal", "Non-Fossil", "EnerStor", "Nuclear", "Solar", "Wind"]), ["PLCO2RTA", "PLSO2RTA", "PLCH4RTA", "PLN2ORTA", "PLNOXRTA"]] = 0
    for r in range(input_df.shape[0]):
            if np.isnan(input_df.at[r, 'PLCO2RTA']):
                # Expand search to the same state if no similar plants found in the same state
                similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                        (input_df['StateName'] == input_df.at[r, 'StateName']) &
                                        (input_df['PlantType'] == input_df.at[r, 'PlantType']) &
                                        (input_df['Capacity'] > input_df.at[r, 'Capacity'] * 0.85) &
                                        (input_df['Capacity'] < input_df.at[r, 'Capacity'] * 1.15) &
                                        (input_df['HeatRate'] > input_df.at[r, 'HeatRate'] * 0.85) &
                                        (input_df['HeatRate'] < input_df.at[r, 'HeatRate'] * 1.15)]

                input_df.loc[r, ['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']] = similar_rows[['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']].mean()

            if np.isnan(input_df.at[r, 'PLCO2RTA']):
                # Expand search to the same NERC region if no similar plants found in the same NERC region
                similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                        (input_df['NERC'] == input_df.at[r, 'NERC']) &
                                        (input_df['PlantType'] == input_df.at[r, 'PlantType']) &
                                        (input_df['Capacity'] > input_df.at[r, 'Capacity'] * 0.85) &
                                        (input_df['Capacity'] < input_df.at[r, 'Capacity'] * 1.15) &
                                        (input_df['HeatRate'] > input_df.at[r, 'HeatRate'] * 0.85) &
                                        (input_df['HeatRate'] < input_df.at[r, 'HeatRate'] * 1.15)]

                input_df.loc[r, ['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']] = similar_rows[['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']].mean()

            if np.isnan(input_df.at[r, 'PLCO2RTA']):
                # Expand search to all similar plants if no similar plants found in entire state
                similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                        (input_df['PlantType'] == input_df.at[r, 'PlantType']) &
                                        (input_df['Capacity'] > input_df.at[r, 'Capacity'] * 0.85) &
                                        (input_df['Capacity'] < input_df.at[r, 'Capacity'] * 1.15) &
                                        (input_df['HeatRate'] > input_df.at[r, 'HeatRate'] * 0.85) &
                                        (input_df['HeatRate'] < input_df.at[r, 'HeatRate'] * 1.15)]

                input_df.loc[r, ['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']] = similar_rows[['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']].mean()


            if np.isnan(input_df.at[r, 'PLCO2RTA']):
                # Expand search to the same state if no similar plants found in the same state
                similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                        (input_df['StateName'] == input_df.at[r, 'StateName']) &
                                        (input_df['PlantType'] == input_df.at[r, 'PlantType'])]

                input_df.loc[r, ['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']] = similar_rows[['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']].mean()

            if np.isnan(input_df.at[r, 'PLCO2RTA']):
                # Expand search to the same NERC region if no similar plants found in the same NERC region
                similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                        (input_df['NERC'] == input_df.at[r, 'NERC']) &
                                        (input_df['PlantType'] == input_df.at[r, 'PlantType'])]

                input_df.loc[r, ['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']] = similar_rows[['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']].mean()

            if np.isnan(input_df.at[r, 'PLCO2RTA']):
                # Expand search to all similar plants if no similar plants found in entire state
                similar_rows = input_df[(input_df['FuelType'] == input_df.at[r, 'FuelType']) &
                                        (input_df['PlantType'] == input_df.at[r, 'PlantType'])]

                input_df.loc[r, ['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']] = similar_rows[['PLCO2RTA', 'PLNOXRTA', 'PLCH4RTA', 'PLN2ORTA', 'PLSO2RTA']].mean()

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

    # Adjust emissions for outliers based on conditions
    for r in range(input_df.shape[0]):
        if input_df.at[r, 'FuelType'] != 'Oil' and input_df.at[r, 'PLCO2RTA'] > 5000:
            if input_df.at[r, 'PLNGENAN'] > 1000:
                orispl = input_df.at[r, 'ORISPL']
                old_values = input_df_old[(input_df_old['ORISPL'] == orispl)]
                if not old_values.empty:
                    input_df.loc[r, ['PLCO2RTA', 'PLSO2RTA', 'PLCH4RTA', 'PLN2ORTA', 'PLNOXRTA']] = old_values[
                        ['PLCO2RTA', 'PLSO2RTA', 'PLCH4RTA', 'PLN2ORTA', 'PLNOXRTA']].values[0]

    return input_df


# Create a MultiIndex for the columns with month and day
def long_wide(input_df):
    df = input_df.copy()
    # Define the columns to keep (first four columns)
    columns_to_keep = ['Region Name', 'State Name', 'Resource Class']

    # Group by the first four columns and concatenate columns 6 to 26, and convert the kwh/MW to MWh/MW
    result_df = df.groupby(columns_to_keep).apply(lambda x: (x.iloc[:, 6:] / 1000).values.flatten()).reset_index()

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
    return Wind_onshore_capacity_df, Solar_regional_capacity_df


def ffill_ren_cost(Wind_onshore_cost_df, Solar_regional_cost_df):
    Wind_onshore_cost_df['IPM Region'].ffill(inplace=True)
    Wind_onshore_cost_df['State'].ffill(inplace=True)
    Solar_regional_cost_df['IPM Region'].ffill(inplace=True)
    Solar_regional_cost_df['State'].ffill(inplace=True)

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


def cluster_and_aggregate(df):
    # Merging identical plants in a region from the group perspective
    # Sort the DataFrame to ensure proper ordering within groups
    df = df.sort_values(by=["RegionName", "PlantType", "FuelType", "community"])
    df.loc[:, 'gen_type'] = df['PlantType'] + '_' + df['FuelType'] + '_' + df['community'].astype(str)
    # Define a function to compute the weighted average
    def weighted_avg(df, value_col, weight_col):
        return (df[value_col] * df[weight_col]).sum() / df[weight_col].sum()

    # Assuming df is your DataFrame
    result = df.groupby(["RegionName", "PlantType", "FuelType", "community"]).apply(
        lambda x: pd.Series({
            "Capacity": x["Capacity"].sum(),
            "FuelCost[$/MWh]": weighted_avg(x, "FuelCost[$/MWh]", "Capacity"),
            "VOMCost[$/MWh]": weighted_avg(x, "VOMCost[$/MWh]", "Capacity"),
            "FuelCostTotal": weighted_avg(x, "FuelCostTotal", "Capacity"),
            "VOMCostTotal": weighted_avg(x, "VOMCostTotal", "Capacity"),
            "Fuel_VOM_Cost": weighted_avg(x, "Fuel_VOM_Cost", "Capacity"),
            "PLNOXRTA": weighted_avg(x, "PLNOXRTA", "Capacity"),
            "PLSO2RTA": weighted_avg(x, "PLSO2RTA", "Capacity"),
            "PLCO2RTA": weighted_avg(x, "PLCO2RTA", "Capacity"),
            "PLCH4RTA": weighted_avg(x, "PLCH4RTA", "Capacity"),
            "PLN2ORTA": weighted_avg(x, "PLN2ORTA", "Capacity"),
            "PLPMTRO": weighted_avg(x, "PLPMTRO", "Capacity"),
        })
    ).reset_index()

    return df, result


# Create a MultiIndex for the columns with month and day

def haversine_distance_miles(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    # Earth's radius in miles (mean radius)
    r = 3959.0

    # Distance in miles
    distance = c * r
    return distance


def cluster_plants(df, heat_rate_distance, emission_rate_distance, cost_rate_distance, resolution, heatrate_weight, emission_weight, cost_weight):
    # df = Plant_short_fixed_Em.copy()
    a = ["Solar", "Wind", "EnerStor", "Hydro", "Geothermal"]
    dispatch_df = df[~df["FuelType"].isin(a)].copy()
    nondispatch_df = df[df["FuelType"].isin(a)].copy()

    def weighted_avg(df, value_col, weight_col):
        return (df[value_col] * df[weight_col]).sum() / df[weight_col].sum()

    nondispatch_df = nondispatch_df.groupby(["RegionName", "PlantType", "FuelType"]).apply(
        lambda x: pd.Series({
            "Capacity": x["Capacity"].sum(),
            "FuelCost[$/MWh]": weighted_avg(x, "FuelCost[$/MWh]", "Capacity"),
            "VOMCost[$/MWh]": weighted_avg(x, "VOMCost[$/MWh]", "Capacity"),
            "FuelCostTotal": weighted_avg(x, "FuelCostTotal", "Capacity"),
            "VOMCostTotal": weighted_avg(x, "VOMCostTotal", "Capacity"),
            "Fuel_VOM_Cost": weighted_avg(x, "Fuel_VOM_Cost", "Capacity"),
            "PLNOXRTA": weighted_avg(x, "PLNOXRTA", "Capacity"),
            "PLSO2RTA": weighted_avg(x, "PLSO2RTA", "Capacity"),
            "PLCO2RTA": weighted_avg(x, "PLCO2RTA", "Capacity"),
            "PLCH4RTA": weighted_avg(x, "PLCH4RTA", "Capacity"),
            "PLN2ORTA": weighted_avg(x, "PLN2ORTA", "Capacity"),
            "PLPMTRO": weighted_avg(x, "PLPMTRO", "Capacity"),
             "StateName": 'first',
        })
      ).reset_index(drop=False)
    nondispatch_df["community"] = 0

    unique_regions = dispatch_df['RegionName'].unique()

    all_regions_clusters = {}
    dispatch_df.loc[:, 'community'] = 0   # Initialize a new column for community numbers

    for region_name in unique_regions:

        start_time = time.time()
        # Filter the dataframe to include only plants from the current region
        dispatch_df_region = dispatch_df[dispatch_df['RegionName'] == region_name].copy()

        nodes = []
        for idx in range(len(dispatch_df_region)):
            nodes.append({
                'id': f'plant_{idx}',
                'heat_rate': dispatch_df_region["HeatRate"].iloc[idx],
                'emission_rate': dispatch_df_region["PLCO2RTA"].iloc[idx],
                'cost_rate': dispatch_df_region['FuelCost[$/MWh]'].iloc[idx],
            })

        links = []

        weighted_distance_function = lambda link: math.e**-(
                heatrate_weight * (link['heat_rate_distance'] / heat_rate_distance) +
                emission_weight * (link['emission_rate_distance'] / emission_rate_distance) +
                cost_weight * (link['cost_rate_distance'] / cost_rate_distance)
        )

        for idx_source in range(len(dispatch_df_region)):
            for idx_target in range(idx_source + 1, len(dispatch_df_region)):
                source = f'plant_{idx_source}'
                target = f'plant_{idx_target}'

                links.append({
                    'source': source,
                    'target': target,
                    'heat_rate_distance': np.abs(nodes[idx_target]['heat_rate'] - nodes[idx_source]['heat_rate']),
                    'emission_rate_distance': np.abs(nodes[idx_target]['emission_rate'] - nodes[idx_source]['emission_rate']),
                    'cost_rate_distance': np.abs(nodes[idx_target]['cost_rate'] - nodes[idx_source]['cost_rate']),
                })

                links[-1]['weighted_distance'] = weighted_distance_function(links[-1])

        limits = {
            'heat_rate_distance': heat_rate_distance,
            'emission_rate_distance': emission_rate_distance,
            'cost_rate_distance': cost_rate_distance,
        }

        links_filtered = [link for link in links if all(link[field] <= value for field, value in limits.items())]
        graph = nx.node_link_graph({'nodes': nodes, 'links': links_filtered})

        communities = list(nx.community.greedy_modularity_communities(graph, weight='weighted_distance', resolution=resolution))

        community_map = {}
        for community_number, community in enumerate(communities):
            for node in community:
                community_map[node] = community_number

        for node_index, row_index in enumerate(dispatch_df_region.index):
            node_id = f'plant_{node_index}'
            if node_id in community_map:
                dispatch_df.loc[row_index, 'community'] = community_map[node_id]

        all_regions_clusters[region_name] = {
            'nodes': graph.number_of_nodes(),
            'links': graph.number_of_edges()
        }

        end_time = time.time()
        print(f"Time taken to cluster plants in {region_name}: {end_time - start_time} seconds")

    nondispatch_df_cn = dispatch_df["community"].max()
    nondispatch_df_cn_solar = nondispatch_df_cn + 1
    nondispatch_df_cn_wind = nondispatch_df_cn + 2
    nondispatch_df_cn_storage = nondispatch_df_cn + 3
    nondispatch_df_cn_geo = nondispatch_df_cn + 4

    nondispatch_df.loc[nondispatch_df["FuelType"] == "Wind", "community"] = nondispatch_df_cn_wind
    nondispatch_df.loc[nondispatch_df["FuelType"] == "Solar", "community"] = nondispatch_df_cn_solar
    nondispatch_df.loc[nondispatch_df["FuelType"] == "EnerStor", "community"] = nondispatch_df_cn_storage
    nondispatch_df.loc[nondispatch_df["FuelType"] == "Geothermal", "community"] = nondispatch_df_cn_geo

    df = pd.concat([dispatch_df, nondispatch_df], axis=0)
    return df, all_regions_clusters

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
            link_example.append({'source': origin, 'target': destination, 'cost': cost, 'capacity': capacity})
    return link_example


def load_object(df):
    load_example = []  # List to store load data in the desired format

    # Iterate through each row of the dataframe
    for index, row in df.iterrows():
        region_name = row.iloc[0]  # First column contains the region name
        load_data = row.iloc[1:]  # Load data starts from the second column onwards

        parameters = {}  # Dictionary to store load data for each hour

        # Iterate through each hour and load data
        for hour, load in load_data.items():
            # Directly add hour:load pair to the parameters dictionary
            parameters[hour] = load

        # Append data to load_example list
        load_example.append({'id': region_name, 'dependents': [{'data_class': 'load', 'parameters': [{'data_type': 'load', 'parameters': [{"value": parameters}]}]}]})
    return load_example


def gen_object(df):
    gen_example = []  # List to store generator data in the desired format
    df = df[~df["PlantType"].isin(["Energy Storage", "Solar PV", "Onshore Wind"])]  # Remove unwanted plant types

    for index, row in df.iterrows():
        region_name = row.iloc[0]  # First column contains the region name
        plant_type = row.iloc[1]  # Second column contains the Plant Type
        fuel_type = row.iloc[2]  # Third column contains the Fuel Type
        community = row.iloc[3]  # Fourth column contains the community number
        cost = row.iloc[9]  # Tenth column contains the Fuel and VOM Cost
        capacity = row.iloc[4]  # Seventh column contains the generator capacity
        # group_id = row.iloc[15]  # Seventeenth column contains the group ID
        gen_type = f'{plant_type}_{fuel_type}_{community}'

        # Check if the region already exists in gen_example
        region_exists = False
        for region_data in gen_example:
            if region_data['id'] == region_name:
                # Find the index of the existing generator type if it exists
                generator_exists = False
                for data_class in region_data['dependents']:
                    if data_class['data_class'] == 'generator':
                        for parameter in data_class['parameters']:
                            if parameter['data_type'] == 'generators':
                                for gen_param in parameter['parameters']:
                                    if gen_param['gen_type'] == gen_type:
                                        gen_param['values'].append({
                                            'cost': cost,
                                            'capacity': capacity,
                                            'group_id': community
                                        })
                                        generator_exists = True
                                        break
                                if not generator_exists:
                                    parameter['parameters'].append({
                                        'gen_type': gen_type,
                                        'values': [{
                                            'cost': cost,
                                            'capacity': capacity,
                                            'group_id': community
                                        }]
                                    })
                                region_exists = True
                                break

        # If the region doesn't exist, create a new entry
        if not region_exists:
            gen_example.append({
                'id': region_name,
                'dependents': [{
                    'data_class': 'generator',
                    'parameters': [{
                        'data_type': "generators",
                        'parameters': [{
                            'gen_type': gen_type,
                            'values': [{
                                'cost': cost,
                                'capacity': capacity,
                                'group_id': community
                            }]
                        }]
                    }]
                }]
            })

    return gen_example
#
# def gen_object(df):
#     gen_example = []  # List to store generator data in the desired format
#     df = df[~df["PlantType"].isin(["Energy Storage", "Solar PV", "Onshore Wind"])]  # Remove unwanted plant types
#
#     for index, row in df.iterrows():
#         region_name = row.iloc[0]  # First column contains the region name
#         plant_type = row.iloc[1]  # Second column contains the Plant Type
#         fuel_type = row.iloc[2]  # Third column contains the Fuel Type
#         community = row.iloc[3]  # Fourth column contains the community number
#         cost = row.iloc[5]  # Tenth column contains the Fuel and VOM Cost
#         capacity = row.iloc[4]  # Seventh column contains the generator capacity
#         group_id = row.iloc[15]  # Seventeenth column contains the group ID
#         gen_type = f'{plant_type}_{fuel_type}_{community}'
#
#         # Check if the region already exists in gen_example
#         region_exists = False
#         for region_data in gen_example:
#             if region_data['id'] == region_name:
#                 # Find the index of the existing generator type if it exists
#                 generator_exists = False
#                 for data_class in region_data['dependents']:
#                     if data_class['data_class'] == 'generator':
#                         for parameter in data_class['parameters']:
#                             if parameter['data_type'] == 'generators':
#                                 for gen_param in parameter['parameters']:
#                                     if gen_param['gen_type'] == gen_type:
#                                         gen_param['values'].append({
#                                             'cost': cost,
#                                             'capacity': capacity,
#                                             'group_id': group_id
#                                         })
#                                         generator_exists = True
#                                         break
#                                 if not generator_exists:
#                                     parameter['parameters'].append({
#                                         'gen_type': gen_type,
#                                         'values': {
#                                             'cost': cost,
#                                             'capacity': capacity,
#                                             'group_id': group_id
#                                         }
#                                     })
#                                 region_exists = True
#                                 break
#
#         # If the region doesn't exist, create a new entry
#         if not region_exists:
#             gen_example.append({
#                 'id': region_name,
#                 'dependents': [{
#                     'data_class': 'generator',
#                     'parameters': [{
#                         'data_type': "generators",
#                         'parameters': [{
#                             'gen_type': gen_type,
#                             'values': {
#                                 'cost': cost,
#                                 'capacity': capacity,
#                                 'group_id': group_id
#                             }
#                         }]
#                     }]
#                 }]
#             })
#
#     return gen_example


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
        stor_example.append({'id': region_name, 'dependents': [{'data_class': 'storage', 'parameters': [{'data_type': plant_type, 'parameters':  [{"cost": cost, "capacity": capacity}]}]}]})
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
        region_dict = {'id': region_name, 'dependents': []}

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
            solar_gen_params['parameters'].append({'resource_class': row['New Resource Class'], 'generation_profile': gen_profile})

        # Add solar cost data
        solar_cost_params = {'data_type': 'solar_cost', 'parameters': []}
        for index, row in solar_cost_df.iterrows():
            cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_cost_params['parameters'].append({'resource_class': row['New Resource Class'], 'cost': cost_profile})

        # Add solar max capacity data
        solar_max_capacity_params = {'data_type': 'solar_max_capacity', 'parameters': []}
        for index, row in max_capacity_df.iterrows():
            max_capacity_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_max_capacity_params['parameters'].append({'resource_class': row['New Resource Class'], 'max_capacity': max_capacity_profile})

        # Add solar installed capacity data
        solar_installed_capacity_params = {'data_type': 'solar_installed_capacity', 'parameters': []}
        for index, row in installed_capacity_df.iterrows():
            solar_installed_capacity_params['parameters'].append({'capacity': row['Capacity']})

        # Add solar transmission cost data
        solar_transmission_cost_params = {'data_type': 'solar_transmission_cost', 'parameters': []}
        for index, row in trans_cost_df.iterrows():
            trans_cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            solar_transmission_cost_params['parameters'].append({'resource_class': row['New Resource Class'], 'transmission_cost': trans_cost_profile})

        region_dict['dependents'].append({'data_class': 'solar', 'parameters': [
            solar_gen_params,
            solar_cost_params,
            solar_max_capacity_params,
            solar_installed_capacity_params,
            solar_transmission_cost_params
        ]})

        # Append region data to solar examples
        solar_examples.append(region_dict)

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

    # Initialize an empty list to hold wind examples
    wind_examples = []

    # Iterate over each region name
    for region_name in Region:
        # Initialize a dictionary for the current region
        region_dict = {'id': region_name, 'dependents': []}

        # Filter DataFrames for the current region
        gen_profile_df = df1[df1['IPM Region'] == region_name]
        wind_cost_df = df2[df2['IPM Region'] == region_name]
        max_capacity_df = df3[df3['IPM Region'] == region_name]
        installed_capacity_df = max_cap[max_cap['RegionName'] == region_name]
        trans_cost_df = df4[df4['IPM Region'] == region_name]

        # Add wind generation profile data
        gen_profile_df['New Resource Class'] = gen_profile_df['New Resource Class'].fillna('1')
        wind_gen_params = {'data_type': 'wind_gen', 'parameters': []}
        for index, row in gen_profile_df.iterrows():
            gen_profile = row.drop(['IPM Region', 'Resource Class', 'State', "New Resource Class"]).dropna().to_dict()
            wind_gen_params['parameters'].append({'resource_class': row['New Resource Class'], 'generation_profile': gen_profile})

        # Add wind cost data
        wind_cost_params = {'data_type': 'wind_cost', 'parameters': []}
        for index, row in wind_cost_df.iterrows():
            cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            wind_cost_params['parameters'].append({'resource_class': row["New Resource Class"], 'cost': cost_profile})

        # Add wind max capacity data
        wind_max_capacity_params = {'data_type': 'wind_max_capacity', 'parameters': []}
        for index, row in max_capacity_df.iterrows():
            max_capacity_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            wind_max_capacity_params['parameters'].append({'resource_class': row["New Resource Class"], 'max_capacity': max_capacity_profile})

        # Add wind installed capacity data
        wind_installed_capacity_params = {'data_type': 'wind_installed_capacity', 'parameters': []}
        for index, row in installed_capacity_df.iterrows():
            wind_installed_capacity_params['parameters'].append({'capacity': row['Capacity']})

        # Add wind transmission cost data
        wind_transmission_cost_params = {'data_type': 'wind_transmission_cost', 'parameters': []}
        for index, row in trans_cost_df.iterrows():
            trans_cost_profile = row.drop(['IPM Region', 'State', 'Resource Class', "New Resource Class"]).dropna().to_dict()
            wind_transmission_cost_params['parameters'].append({'resource_class': row["New Resource Class"], 'transmission_cost': trans_cost_profile})

        region_dict['dependents'].append({'data_class': 'wind', 'parameters': [
            wind_gen_params,
            wind_cost_params,
            wind_max_capacity_params,
            wind_installed_capacity_params,
            wind_transmission_cost_params
        ]})

        # Append region data to wind examples
        wind_examples.append(region_dict)

    return wind_examples


def merge_dictionaries_and_format(list_of_dicts):
    # Define an empty dictionary to hold merged dictionaries grouped by "id"
    merged_dict = {}
    # Temporary dictionary to hold the merged data
    temp_merged_dict = {}

    # Final list to hold the formatted output
    formatted_list = []

    # Iterate over the list of dictionaries
    for single_dict in list_of_dicts:
        id = single_dict['id']
        dependents = single_dict['dependents']

        if id in temp_merged_dict:
            temp_merged_dict[id]['dependents'].extend(dependents)
        else:
            temp_merged_dict[id] = {'id': id, 'dependents': dependents}

    # Convert the merged dictionary into the desired list format
    for id, info in temp_merged_dict.items():
        formatted_list.append({'id': id, 'dependents': info['dependents']})

    return formatted_list


def convert_keys_to_string(obj):
    if isinstance(obj, dict):
        return {str(key) if not isinstance(key, (np.int64, np.int32)) else int(key): convert_keys_to_string(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_keys_to_string(element) for element in obj]
    else:
        return obj


def concat_filtered_plants(Plants_ungroup, Plant_short):
    # Filter rows for non-renewable fuel types in Plants_ungroup_extended
    Plants_ungroup_extended = Plants_ungroup[~Plants_ungroup["FuelType"].isin(["Solar", "Wind", "EnerStor", "Hydro", "Geothermal"])]

    # Filter rows for renewable fuel types in Plant_short
    Plant_short_filtered = Plant_short[Plant_short["FuelType"].isin(["Solar", "Wind", "EnerStor", "Hydro", "Geothermal"])]

    # Select only the columns that exist in Plants_ungroup_extended from Plant_short_filtered
    Plant_short_filtered = Plant_short_filtered[Plants_ungroup_extended.columns.intersection(Plant_short_filtered.columns)]

    # Concatenate the two DataFrames along axis=0 (i.e., row-wise concatenation)
    result_df = pd.concat([Plants_ungroup_extended, Plant_short_filtered], axis=0)

    # Create a new column 'UniqueIDN' that copies existing 'UniqueID'
    result_df['UniqueIDN'] = result_df['UniqueID']

    # Identify rows with NaN in 'UniqueID' and assign unique values in the format '999_G_x'
    nan_rows = result_df['UniqueID'].isna()

    # Assign unique values to the NaNs in the format '999_G_1', '999_G_2', etc.
    result_df.loc[nan_rows, 'UniqueIDN'] = ['999_G_nan_' + str(i) for i in range(nan_rows.sum())]

    return result_df

