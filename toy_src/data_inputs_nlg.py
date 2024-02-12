import pickle as pickle
import networkx as nx


def create_sets(data): 

     def gen_fuel_type_extraction(data): 
        unique_keys = {'region': [], 'gen_type': [], 'gen_fuel': [], 'emissions_code':[]}  # Initialize unique_keys dictionary

        for tuples in data['Plants_Dic']:
            for idx_val, idx_name in enumerate(tuples):
                if idx_val == 0:
                    if idx_name not in unique_keys['region']:
                        unique_keys['region'].append(idx_name)  # Assign idx_name to 'region' key in unique_keys
                elif idx_val == 1:
                    if idx_name not in unique_keys['gen_type']:
                        unique_keys['gen_type'].append(idx_name)  # Assign idx_name to 'generator' key in unique_keys
                elif idx_val == 2: 
                    if idx_name not in unique_keys['gen_fuel']:
                        unique_keys['gen_fuel'].append(idx_name)
                elif idx_val == 3: 
                    if idx_name not in unique_keys['emissions_code']:
                        unique_keys['emissions_code'].append(idx_name)

        return unique_keys


def create_graph(data): 

    input_dict = data

    hold_params = {'generator_cost': {(i[0], i[2]): d[1] for i, d in input_dict['Plants_Dic'].items()},
                    'generator_capacity': input_dict['Plant_capacity_dic'],
                    'solar_capex': input_dict['Solar_capital_cost_photov_final'], 
                    'solar_CF': {(i[0], i[2], i[3]): d for i,d in input_dict['Solar_capacity_factor_final'].items()}, 
                    'solar_max_capacity': input_dict['Solar_regional_capacity_final'],
                    'solar_installed_capacity': {i[0]: d for i, d in input_dict['Plant_capacity_dic'].items() if i[1] == 'Solar'},
                    'wind_capex': input_dict['Wind_capital_cost_final'], 
                    'wind_CF': input_dict['Wind_capacity_factor_final'], 
                    'wind_max_capacity': input_dict['Wind_onshore_capacity_final'],
                    'wind_installed_capacity': {i: d for i, d in input_dict['Plant_capacity_dic'].items() if i[1] == 'Wind'},
                    'wind_transmission_cost': input_dict['Wind_trans_capital_cost_final'],
                    'transmission_cost':input_dict['Transmission_Cost_dic'], 
                    'transmission_capacity':input_dict['Transmission_Capacity_dic'],
                    'enerstor_installed_capacity': {i[0]: d for i, d in input_dict['Plant_capacity_dic'].items() if i[1] == 'EnerStor'},
                    'load': input_dict['load_final']}

    def recursive_store(d, key, value):
        if len(key) == 1:
            d[key[0]] = value
        else:
            if key[0] not in d:
                d[key[0]] = {}
            recursive_store(d[key[0]], key[1:], value)

    def process_dict(input_dict, target_key):
        output_dict = {}
        for key, value in input_dict[target_key].items():
            recursive_store(output_dict, key, value)
        
        return output_dict


    # reindex dictionary
    output = {}
    keys_to_remove = ['solar_installed_capacity', 'enerstor_installed_capacity']

    hold = [key for key in hold_params.keys()]
    for key in hold:
        if key in keys_to_remove:
            output[key] = hold_params[key]
        else: 
            output[key] = process_dict(hold_params, key) 

    # create hold dictionaries for nodes and links

    dicts_remove = ['transmission_cost', 'transmission_capacity']
    hold_links = {}
    hold_nodes = {} 

    for key, value in output.items(): 
        if key in dicts_remove: 
            hold_links[key] = value
        else: 
            hold_nodes[key] = value


    # create nodes
    nodes_dict = {} 
    for key, dict in hold_nodes.items():
        for next_key, next_dict in dict.items():
            # Check if next_key exists in test dictionary
            if next_key not in nodes_dict :
                nodes_dict[next_key] = {}
            
            # Assign the value as the dictionary itself, not a set
            nodes_dict[next_key][key] = next_dict

    nodes = []
    for key, dict in nodes_dict.items(): 
        # key = region 
        # dict = data type
        dependents = []
        for sub_key, sub_dict in dict.items(): 
            parameters = []
            if sub_key == 'generator_cost': 
                for next_key, value in sub_dict.items():
                    hold = [{'id': next_key, 'cost': value}]
                    parameters.append(hold)
                dependents.append({ 'type': 'generation_cost', 'parameters': parameters})    
            elif sub_key == 'generator_capacity':
                for next_key, value in sub_dict.items():
                    hold = [{'id': next_key, 'capacity': value}]
                    parameters.append(hold)    
                dependents.append({'type': 'generation_capacity', 'parameters': parameters})     
            elif sub_key == 'solar_capex': 
                for next_key, next_dict in sub_dict.items():
                    # next key = state
                    # sub dict = resource class
                    for n_key, n_dict in next_dict.items(): 
                        # n key = resource class
                        # n dict = cost class
                        for last_key, last_value in n_dict.items():
                            # last key = cost calss
                            # last value = value
                            hold = {'resource_class': n_key, 'cost_class': last_key, 'value': value}
                            parameters.append(hold)
                dependents.append({'type': 'solar_capex', 'parameters': parameters})
            elif sub_key == 'solar_CF': 
                for next_key, next_dict in sub_dict.items():
                    # next key = resource class
                    # next dict = hours 
                    for n_key, value in next_dict.items(): 
                        # n key = hour 
                        # value = value 
                        hold = {'resource_class': next_key, 'hour': n_key, 'value': value}
                        parameters.append(hold)
                dependents.append({'type': 'solar_cf', 'parameters': parameters})
            elif sub_key == 'solar_installed_capacity': 
                hold = {'value': dict[sub_key]}
                parameters.append(hold)
                dependents.append({'type': 'solar_installed_capacity', 'parameters': parameters})
            elif sub_key == 'solar_max_capacity': 
                for next_key, next_dict in sub_dict.items():
                    # next key = state
                    # sub dict = resource class
                    for n_key, n_dict in next_dict.items(): 
                        # n key = resource class
                        # n dict = cost class
                        for last_key, last_value in n_dict.items():
                            # last key = cost calss
                            # last value = value
                            hold = {'resource_class': n_key, 'cost_class': last_key, 'value': value}
                            parameters.append(hold)
                dependents.append({'type': 'solar_max_capacity', 'parameters': parameters})
            elif sub_key == 'wind_capex': 
                for next_key, next_dict in sub_dict.items():
                    # next key = state
                    # sub dict = resource class
                    for n_key, n_dict in next_dict.items(): 
                        # n key = resource class
                        # n dict = cost class
                        for last_key, last_value in n_dict.items():
                            # last key = cost calss
                            # last value = value
                            hold = {'resource_class': n_key, 'cost_class': last_key, 'value': value}
                            parameters.append(hold)
                dependents.append({'type': 'wind_capex', 'parameters': parameters})
            elif sub_key == 'wind_CF': 
                for next_key, next_dict in sub_dict.items():
                    # next key = resource class
                    # next dict = hours 
                    for n_key, value in next_dict.items(): 
                        # n key = hour 
                        # value = value 
                        hold = {'resource_class': next_key, 'hour': n_key, 'value': value}
                        parameters.append(hold)
                dependents.append({'type': 'wind_cf', 'parameters': parameters})
            elif sub_key == 'wind_max_capacity': 
                for next_key, next_dict in sub_dict.items():
                        # next key = state
                        # sub dict = resource class
                    for n_key, n_dict in next_dict.items(): 
                            # n key = resource class
                            # n dict = cost class
                        for last_key, last_value in n_dict.items():
                                # last key = cost calss
                                # last value = value
                                hold = {'resource_class': n_key, 'cost_class': last_key, 'value': value}
                                parameters.append(hold)
                dependents.append({'type': 'wind_max_capacity', 'parameters': parameters})
            elif sub_key == 'wind_installed_capacity': 
                hold = {'value': dict[sub_key]}
                parameters.append(hold)
                dependents.append({'type': 'wind_installed_capacity', 'parameters': parameters})
            elif sub_key == 'wind_transmission_cost': 
                for next_key, next_dict in sub_dict.items():
                        # next key = state
                        # sub dict = resource class
                    for n_key, n_dict in next_dict.items(): 
                            # n key = resource class
                            # n dict = cost class
                        for last_key, last_value in n_dict.items():
                                # last key = cost calss
                                # last value = value
                                hold = {'resource_class': n_key, 'cost_class': last_key, 'value': value}
                                parameters.append(hold)
                dependents.append({'type': 'wind_trans_cost', 'parameters': parameters})
            elif sub_key == 'enerstor_installed_capacity': 
                hold = {'value': dict[sub_key]}
                parameters.append(hold)
                dependents.append({'type': 'storage_capacity', 'parameters': parameters})
            elif sub_key == 'load': 
                for next_key, value in sub_dict.items():
                    hold = {'hour': next_key, 'value': value}
                    parameters.append(hold)
                dependents.append({'type': 'load', 'parameters': parameters}) 
            nodes.append({'id': key, 'dependents': dependents})


    # create links 
    links_dict = {}
    for key, dict in hold_links.items():
        for next_key, next_dict in dict.items():
            # Check if next_key exists in test dictionary
            if next_key not in links_dict:
                links_dict[next_key] = {}
            
            # Assign the value as the dictionary itself, not a set
            links_dict[next_key][key] = next_dict

    data = output['transmission_capacity']
    cost = output['transmission_cost']

    links = []

    for source, targets in data.items():
        for target, capacity in targets.items():
            item = {
                "source": source,
                "target": target,
                "capacity": capacity
            }
            if target in cost[source]:  # Check if cost exists for the relationship
                item["cost"] = cost[source][target]
            links.append(item)


    # create graph

    nlg = {'nodes': nodes, 'links': links}

    graph = nx.node_link_graph(nlg, directed = True, multigraph = False)

    return graph
