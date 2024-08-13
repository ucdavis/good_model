import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# %%
def plotVOM(Price_test):

    # Assuming you already have the Price_test dataframe with the columns 'cost', 'capacity', 'gen_type', and '&/MWh'
    # Price_test["&/MWh"] = Price_test["cost"]
    Price_test["&/MWh"] = Price_test["Fuel_VOM_Cost"]
    # Price_test["&/MWh"] = Price_test["FuelCost[$/MWh]"]
    # Group the dataframe by 'PlantType'
    grouped = Price_test.groupby("PlantType")

    # Separate generator types with non-zero values and those with zeros
    non_zero_gen_types = []
    zero_gen_types = []
    for gen_type, group_data in grouped:
        if (group_data['&/MWh'] > 0).any():
            non_zero_gen_types.append(gen_type)
        else:
            zero_gen_types.append(gen_type)

    # Combine the lists such that non-zero gen types come first followed by zero gen types
    gen_types_ordered = non_zero_gen_types + zero_gen_types

    # Calculate the number of rows and columns for the grid
    num_rows = 8  # Number of rows
    num_cols = 3  # Number of columns

    # Calculate total number of subplots needed
    total_subplots = len(gen_types_ordered)

    # Adjust num_rows and num_cols if total_subplots exceed
    if total_subplots > num_rows * num_cols:
        num_rows = int(np.ceil(total_subplots / num_cols))

    # Create a grid of subplots
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(15, 20))

    # Flatten the axes array for easier indexing
    axes = np.array(axes).flatten()


    # Function to determine if a value is an outlier based on IQR
    def is_outlier(group_data, value):
        Q1 = group_data['&/MWh'].quantile(0.25)
        Q3 = group_data['&/MWh'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        return value < lower_bound or value > upper_bound


    # Plot histograms for each unique generator type
    for i, gen_type in enumerate(gen_types_ordered):
        ax = axes[i]  # Select the current subplot
        data = grouped.get_group(gen_type)

        # Exclude outliers based on IQR
        data_no_outliers = data[~data['&/MWh'].apply(lambda x: is_outlier(data, x))]
        bins = 30 if (data_no_outliers['&/MWh'] > 0).any() else np.linspace(0, 5, 11)  # Adjust number of bins based on non-zero values
        ax.hist(data_no_outliers['&/MWh'], bins=bins)
        ax.set_title(gen_type)
        ax.set_xlabel('Fuel & VOM Cost ($/MWh)')
        ax.set_ylabel('Frequency')

        # Set x-axis limits from 0 to 5 only for generator types with only zero values
        if gen_type in zero_gen_types and (data['&/MWh'] > 0).all():
            ax.set_xlim(0, 5)

    # Hide empty subplots
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    # Adjust layout
    plt.tight_layout()

    # Show plot
    plt.show()
    # Save the figure in PNG format
    # plt.savefig('subplot_grid3.png')

def plotfuel(Price_test):

    # Assuming you already have the Price_test dataframe with the columns 'cost', 'capacity', 'gen_type', and '&/MWh'
    # Price_test["&/MWh"] = Price_test["cost"]
    Price_test["&/MWh"] = Price_test["FuelCost[$/MWh]"]
    # Price_test["&/MWh"] = Price_test["FuelCost[$/MWh]"]
    # Group the dataframe by 'PlantType'
    grouped = Price_test.groupby("PlantType")

    # Separate generator types with non-zero values and those with zeros
    non_zero_gen_types = []
    zero_gen_types = []
    for gen_type, group_data in grouped:
        if (group_data['&/MWh'] > 0).any():
            non_zero_gen_types.append(gen_type)
        else:
            zero_gen_types.append(gen_type)

    # Combine the lists such that non-zero gen types come first followed by zero gen types
    gen_types_ordered = non_zero_gen_types + zero_gen_types

    # Calculate the number of rows and columns for the grid
    num_rows = 8  # Number of rows
    num_cols = 3  # Number of columns

    # Calculate total number of subplots needed
    total_subplots = len(gen_types_ordered)

    # Adjust num_rows and num_cols if total_subplots exceed
    if total_subplots > num_rows * num_cols:
        num_rows = int(np.ceil(total_subplots / num_cols))

    # Create a grid of subplots
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(15, 20))

    # Flatten the axes array for easier indexing
    axes = np.array(axes).flatten()

    # Function to determine if a value is an outlier based on IQR
    def is_outlier(group_data, value):
        Q1 = group_data['&/MWh'].quantile(0.25)
        Q3 = group_data['&/MWh'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        return value < lower_bound or value > upper_bound

    # Plot histograms for each unique generator type
    for i, gen_type in enumerate(gen_types_ordered):
        ax = axes[i]  # Select the current subplot
        data = grouped.get_group(gen_type)

        # Exclude outliers based on IQR
        data_no_outliers = data[~data['&/MWh'].apply(lambda x: is_outlier(data, x))]
        bins = 30 if (data_no_outliers['&/MWh'] > 0).any() else np.linspace(0, 5, 11)  # Adjust number of bins based on non-zero values
        ax.hist(data_no_outliers['&/MWh'], bins=bins)
        ax.set_title(gen_type)
        ax.set_xlabel('Fuel ($/MWh)')
        ax.set_ylabel('Frequency')

        # Set x-axis limits from 0 to 5 only for generator types with only zero values
        if gen_type in zero_gen_types and (data['&/MWh'] > 0).all():
            ax.set_xlim(0, 5)

    # Hide empty subplots
    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    # Adjust layout
    plt.tight_layout()

    # Show plot
    plt.show()
    # Save the figure in PNG format
    # plt.savefig('subplot_grid3.png')
# %%
plotVOM(Plants_group)
plotfuel(Plants_group)

plotVOM(Plant_short_fixed_Em)
plotfuel(Plant_short_fixed_Em)

plotVOM(Plant_short_fixed_fuelC)
# %%