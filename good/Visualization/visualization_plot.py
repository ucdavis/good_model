import re
import matplotlib.pyplot as plt
import json
import pandas as pd

def plot_dispatch_fuel_mix(dataframe, json_path):
    with open(json_path, 'r') as f:
        cal_data = json.load(f)
    fuel_mapping = {}
    component_assets = set()
    load_assets = set()
    # First pass: collect all component asset IDs from combined assets
    for node in cal_data["nodes"]:
        if "assets" in node:
            for asset_id, asset_info in node["assets"].items():
                if "components" in asset_info:
                    component_assets.update(asset_info["components"])

    # Second pass: build fuel mapping, skip components that belong to combined assets
    for node in cal_data["nodes"]:
        if "assets" in node:
            for asset_id, asset_info in node["assets"].items():
                if asset_id in component_assets:
                    continue  # Skip component assets that are already in combined

                region = asset_info.get("region", "UNKNOWN")
                profile_prefix = asset_info.get("profile", f"{region}:").split(":")[0]
                key = f"{profile_prefix}:{asset_id}"

                # Identify base load assets and store separately
                if asset_id.startswith("base_load"):
                    load_assets.add(asset_id)
                    continue

                # Handle missing fuel
                if "fuel" not in asset_info:
                    if asset_id.startswith("optional_storage"):
                        fuel_mapping[key] = "Battery Storage"
                    else:
                        fuel_mapping[key] = "Unknown"
                else:
                    fuel_mapping[key] = asset_info["fuel"]

    # FILTER PRODUCTION COLUMNS
    production_cols = [
        c for c in dataframe.columns
        if ("::net" in c) and ("installed_" in c or "optional_" in c or "base_load_" in c)
    ]
    df_long = dataframe[production_cols].copy().melt(var_name="full_key", value_name="net")

    # EXTRACT REGION & ASSET ID
    def extract_asset_id(col):
        match = re.search(r'(installed_\d+_combined|optional_\d+_combined|base_load_\w+)', col)
        return match.group(1) if match else None

    df_long["region"] = df_long["full_key"].apply(lambda x: x.split(':')[0])
    df_long["asset_id"] = df_long["full_key"].apply(extract_asset_id)
    df_long["merge_key"] = df_long["region"] + ":" + df_long["asset_id"]

    # SPLIT LOAD vs GENERATION
    # Separate base load rows into df_load
    df_load = df_long[df_long["asset_id"].isin(load_assets)].copy()

    # Keep only generation (exclude base load)
    df_long = df_long[~df_long["asset_id"].isin(load_assets)].copy()

    # MAP FUEL TYPES AND STANDARDIZE
    fuel_category_map = {
        "natural gas": "Natural Gas",
        "coal": "Coal",
        "oil": "Oil",
        "nuclear": "Nuclear",
        "hydro": "Hydro",
        "pump hydro": "Hydro",
        "wind": "Wind",
        "solar": "Solar",
        "biomass": "Biomass",
        "geothermal": "Geothermal",
        "battery": "Battery Storage",
        "Battery Storage": "Battery Storage",
        "waste": "Waste",
        "import": "Import",
        "non-fossil": "Other Non-Fossil",
        "unknown": "Unknown"
    }

    # Apply mapping
    df_long["fuel"] = df_long["merge_key"].map(fuel_mapping)

    # Convert raw fuels to standardized names, preserve Battery Storage
    df_long["fuel"] = df_long["fuel"].apply(
        lambda f: fuel_category_map.get(f.lower(), f) if isinstance(f, str) else "Unknown"
    )

    # Separate truly Unknown assets into df_load as well
    df_load = pd.concat([df_load, df_long[df_long["fuel"] == "Unknown"]], ignore_index=True)
    df_long = df_long[df_long["fuel"] != "Unknown"]

    # AGGREGATE BY REGION AND FUEL
    df_grouped = df_long.groupby(["region", "fuel"], as_index=False)["net"].sum()
    df_grouped["total"] = df_grouped.groupby("region")["net"].transform("sum")
    df_grouped["share"] = df_grouped["net"] / df_grouped["total"]

    # ADD CALIFORNIA AGGREGATE
    df_total = df_grouped.groupby("fuel", as_index=False)["net"].sum()
    df_total["region"] = "California"
    df_total["total"] = df_total["net"].sum()
    df_total["share"] = df_total["net"] / df_total["total"]
    df_grouped_with_ca = pd.concat([df_grouped, df_total], ignore_index=True)

    # Pivot for stacked bar
    df_pivot = df_grouped_with_ca.pivot(index="region", columns="fuel", values="share").fillna(0)

    # COLOR MAPPING
    fuel_colors = {
        "Natural Gas": "orange", "Coal": "gray", "Oil": "pink", "Nuclear": "purple",
        "Hydro": "blue", "Wind": "green", "Solar": "red", "Biomass": "lightgreen",
        "Geothermal": "brown", "Battery Storage": "gold", "Waste": "darkred",
        "Import": "cyan", "Other Non-Fossil": "lightblue"
    }
    fuel_order = [f for f in fuel_colors.keys() if f in df_pivot.columns]
    colors = [fuel_colors[f] for f in fuel_order]

    # PLOT
    df_pivot[fuel_order].plot(kind="bar", stacked=True, figsize=(14, 7), color=colors)
    plt.ylabel("Generation Share")
    plt.xlabel("Region")
    plt.title("Fuel Mix by Region (Dispatch Model Output)")
    plt.legend(title="Fuel Type", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

    # CALCULATE TOTALS

    # Total generation for California
    ca_regions = ["WEC_BANC", "WEC_CALN", "WEC_LADW", "WEC_SDGE", "WECC_SCE", "WECC_IID"]
    df_ca_gen = df_long[df_long["region"].isin(ca_regions)].copy()
    total_generation = df_ca_gen["net"].sum()
    # Total load (sum of all base load + unknown assets)
    total_load = abs(df_load[df_load["region"].isin(ca_regions)]["net"].sum())

    # PLOT COMPARISON
    plt.figure(figsize=(6, 6))
    plt.bar(["Generation", "Load"], [total_generation, total_load], color=["steelblue", "orange"])
    plt.ylabel("Total Energy (MWh)")
    plt.title("California: Total Generation vs Load")
    for i, v in enumerate([total_generation, total_load]):
        plt.text(i, v * 1.02, f"{v:,.0f}", ha='center', fontsize=12)  # labels on bars
    plt.tight_layout()
    plt.show()


# json_path = 'C:\\Users\\ht9\\PycharmProjects\\good_model\\Examples\\California.json'
# dataframe = pd.read_csv("solution.csv")
# plot_dispatch_fuel_mix(dataframe, json_path)