import pandas as pd
import numpy as np
def load_data():
    import pandas as pd
    # Define the paths to your files
    xlsx_file_path1 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/eGRID2021_data.xlsx"
    xlsx_file_path2 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/needs_v6_transmission.csv"
    xlsx_file_path3 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/needs_v617_parsed.csv"
    xlsx_file_path4 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/needs_v621_inputs.csv"
    xlsx_file_path5 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/NEEDS v621_06-21-2022.xlsx"

    xlsx_file_path6 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table 4-39 Wind Generation Profiles in EPA Platform v6.xlsx"
    xlsx_file_path7 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_2-2_load_duration_curves_used_in_epa_platform_v6.xlsx"
    xlsx_file_path8 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_4-38_onshore_regional_potential_wind_capacity_mw_by_trg_and_cost_class_in_epa_platform_v6.xlsx"
    xlsx_file_path9 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_4-40_capital_cost_adder_for_new_onshore_wind_plants_in_epa_platform_v6.xlsx"
    xlsx_file_path10 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_4-41_solar_photovoltaic_regional_potential_capacity_mw_by_resource_and_cost_class_in_epa_platform_v6.xlsx"
    xlsx_file_path11 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_4-43_solar_photovoltaic_generation_profiles_in_epa_platform_v6.xlsx"
    xlsx_file_path12 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_4-44_capital_cost_adder_for_new_solar_pv_plants_in_epa_platform_v6.xlsx"
    xlsx_file_path13 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/table_4-46_solar_photovoltaic_capacity_factor_by_resource_class_in_epa_platform_v6.xlsx"
    xlsx_file_path14 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/Table 4-15.xlsx"
    xlsx_file_path15 = "/Users/haniftayarani/Library/CloudStorage/Box-Box/GOOD Model/Table 4-16.xlsx"

    # Specify the sheet name for the XLSX file
    sheet_name1 = "PLNT21"
    sheet_name5 = "NEEDS v621_active"
    sheet_name6 = "Onshore"
    sheet_name7 = "Table 2-2"
    sheet_name8 = "Table 4-38"
    sheet_name9 = "Table 4-40"
    sheet_name10 = "Table 4-41"
    sheet_name11 = "Table 4-43"
    sheet_name12 = "Table 4-44"
    sheet_name13 = "Table 4-46"
    sheet_name14 = "Table 4-15"
    sheet_name15 = "Table 4-16"

    # Read XLSX files
    Plant = pd.read_excel(xlsx_file_path1, sheet_name=sheet_name1, header=1)
    NEEDS = pd.read_excel(xlsx_file_path5, sheet_name=sheet_name5, header=0)
    Wind_generation_profile = pd.read_excel(xlsx_file_path6, sheet_name=sheet_name6, header=0)
    Load = pd.read_excel(xlsx_file_path7, sheet_name=sheet_name7, header=0)
    Wind_onshore_capacity = pd.read_excel(xlsx_file_path8, sheet_name=sheet_name8, header=0)
    Wind_capital_cost = pd.read_excel(xlsx_file_path9, sheet_name=sheet_name9, header=0)
    Solar_regional_capacity = pd.read_excel(xlsx_file_path10, sheet_name=sheet_name10, header=0)
    Solar_generation_profile = pd.read_excel(xlsx_file_path11, sheet_name=sheet_name11, header=0)
    Solar_capital_cost_photo = pd.read_excel(xlsx_file_path12, sheet_name=sheet_name12, header=0)
    Solar_capacity_factor = pd.read_excel(xlsx_file_path13, sheet_name=sheet_name13, header=0)
    Regional_Cost = pd.read_excel(xlsx_file_path14, sheet_name=sheet_name14, header=0)
    Unit_Cost = pd.read_excel(xlsx_file_path15, sheet_name=sheet_name15, header=0)

    # Read CSV files
    Transmission = pd.read_csv(xlsx_file_path2)
    Parsed = pd.read_csv(xlsx_file_path3)
    Input = pd.read_csv(xlsx_file_path4, encoding="latin1")
    # Return the loaded dataframes
    return (Plant, Transmission, Parsed, Input, NEEDS, Wind_generation_profile, Load, Wind_onshore_capacity, Wind_capital_cost,
            Solar_regional_capacity, Solar_generation_profile, Solar_capital_cost_photo, Solar_capacity_factor, Regional_Cost, Unit_Cost)



