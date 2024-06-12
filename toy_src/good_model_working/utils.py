import os
import pandas as pd 
import numpy as np
import pyomo.environ as pyomo
import networkx as nx
import json
from datetime import date
from .constants import time_periods

'''
    utils.py contains basic utility functions to support
    evaluation of model runs, including writing the model 
    to an .lp file to inspect, reporting the number of 
    variables in the model, or writing the model the results
    to a json or pickle file for storage

    the package will be updated will additional functions
    as requested by users or deemed useful by the 
    EV Research Center

'''

# variables used in the model:

gen_to_remove = [
        'Fossil Waste', 
        # 'Municipal Solid Waste', 
        'Non-Fossil Waste', 
        'Pumped Storage',
        'Fuel Cell',
        'Landfill Gas', 
        # "Energy Storage", 
        # "Solar PV", 
        # "Onshore Wind", 
        # 'New Battery Storage', 
        # 'IMPORT', 
        # 'Tires',
        'Offshore Wind', 
        'Solar Thermal'
        ]


def get_model_statistcs(model): 

    model.compute_statistics()

    statistics = {
        'total_variables': model.statistics.number_of_variables,
        'total_constraints': model.statistics.number_of_constraints}

    df = pd.DataFrame(statistics, index=[0])
    print(df.to_string(index=False))

def get_total_generator_count(model): 

    gen_count = 0 
    hours = len(time_periods)
    for component in model.component_objects(pyomo.Var, active=True): 
        component_name = component.local_name
        if '_generation' in component_name: 
            gen_count += len(component)

    print(f'Total generators: {gen_count/hours}')

def write_model(model, version): 
   
    today = date.today()

    file = f'lp_file_{today}_model_run_{version}.lp'
    path = '/Users/peterambiel/Desktop/good_model/output_logs'
    filename = os.path.join(path, file)
    model.write(filename, io_options = {'symbolic_solver_labels': True})


def create_graph(filepath): 

    with open(filepath, 'r') as file:
    # Load the JSON data into a Python dictionary
        model_objects = json.load(file)
    
    graph = nx.node_link_graph(model_objects, directed = True, multigraph = False)

    return graph


def get_sets(filepath): 

    with open(filepath, 'r') as file:
    # Load the JSON data into a Python dictionary
        model_sets = json.load(file)

    return model_sets


def filter_sets(model_sets, gen_to_remove): 
    
    sets = model_sets['gen_type']

    model_sets['gen_type'] = [gen for gen in sets if not any(substring in gen for substring in gen_to_remove)]

    return model_sets

def get_subgraph(user_input, graph): 

    selected_regions = user_input.split(',')

    sub_nodes = { 
    'ALL': ['FRCC', 'MIS_AMSO', 'MIS_AR', 'MIS_D_MS', 'MIS_IA', 'MIS_IL', 'MIS_INKY', 
    'MIS_LA', 'MIS_LMI', 'MIS_MAPP', 'MIS_MIDA', 'MIS_MNWI', 'MIS_MO', 'MIS_WOTA', 'MIS_WUMS',
    'NENGREST', 'NENG_CT', 'NENG_ME', 'NY_Z_A', 'NY_Z_B', 'NY_Z_C&E', 'NY_Z_D', 'NY_Z_F', 'NY_Z_G-I', 
    'NY_Z_J', 'NY_Z_K', 'PJM_AP', 'PJM_ATSI', 'PJM_COMD', 'PJM_Dom','PJM_EMAC', 'PJM_PENE', 
    'PJM_SMAC', 'PJM_WMAC', 'PJM_West', 'SPP_N', 'SPP_NEBR', 'SPP_SPS', 'SPP_WAUE', 'SPP_WEST',
    'S_C_KY', 'S_C_TVA', 'S_D_AECI', 'S_SOU', 'S_VACA', 'ERC_FRNT', 'ERC_GWAY', 'SPP_KIAM', 'ERC_PHDL', 
    'ERC_REST', 'ERC_WEST', 'WECC_AZ', 'WECC_CO', 'WECC_ID', 'WECC_IID', 'WECC_MT', 'WECC_NM', 
    'WECC_NNV', 'WECC_PNW', 'WECC_SCE', 'WECC_SNV', 'WECC_UT', 'WECC_WY', 'WEC_BANC', 'WEC_CALN', 
    'WEC_LADW', 'WEC_SDGE'],
    'Florida': ['FRCC'], 
    'MISO' : ['MIS_AMSO', 'MIS_AR', 'MIS_D_MS', 'MIS_IA', 'MIS_IL', 'MIS_INKY', 
    'MIS_LA', 'MIS_LMI', 'MIS_MAPP', 'MIS_MIDA', 'MIS_MNWI', 'MIS_MO', 'MIS_WOTA', 'MIS_WUMS'], 
    'NEW_ENGLAND': ['NENGREST', 'NENG_CT', 'NENG_ME'],
    'NYISO': ['NY_Z_A', 'NY_Z_B', 'NY_Z_C&E', 'NY_Z_D', 'NY_Z_F', 'NY_Z_G-I', 'NY_Z_J', 'NY_Z_K'],
    'PJM': ['PJM_AP', 'PJM_ATSI', 'PJM_COMD', 'PJM_Dom','PJM_EMAC', 'PJM_PENE', 'PJM_SMAC', 'PJM_WMAC', 'PJM_West'],
    'SSP': ['SPP_N', 'SPP_NEBR', 'SPP_SPS', 'SPP_WAUE', 'SPP_WEST', 'SPP_KIAM'],
    'SOUTHEAST': ['S_C_KY', 'S_C_TVA', 'S_D_AECI', 'S_SOU', 'S_VACA'],
    'ERCOT': ['ERC_FRNT', 'ERC_GWAY', 'ERC_PHDL', 'ERC_REST', 'ERC_WEST'],
    'WECC': ['WECC_AZ', 'WECC_CO', 'WECC_ID', 'WECC_IID', 'WECC_MT', 'WECC_NM', 'WECC_NNV', 'WECC_PNW', 'WECC_SCE', 
    'WECC_SNV', 'WECC_UT', 'WECC_WY', 'WEC_BANC', 'WEC_CALN', 'WEC_LADW', 'WEC_SDGE']
    }

    selected_nodes = []
    for region in selected_regions:
        region = region.strip().upper()
        if region in sub_nodes:
            selected_nodes.extend(sub_nodes[region])

    subgraph_nodes = graph.subgraph(selected_nodes)

    filtered_edges = [(u, v) for u, v, d in subgraph_nodes.edges(data=True) if d['capacity'] > 0.0]
    subgraph = subgraph_nodes.edge_subgraph(filtered_edges)

    return subgraph, selected_nodes
