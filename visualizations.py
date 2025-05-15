import os
import sys
import time
import json
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

def plot_lmps(ax, solution):

    for source, node in solution._node.items():

        ax.plot(
            np.array(node['clearing_price']) * 3.6e9,
            label = source,
        )

    kw = {
        'facecolor': 'whitesmoke',
        'ylabel': 'Region Marginal Price [$ / MWh]',
    }

    ax.set(**kw)

    kw = {
        'ls': '--',
    }

    ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    ax.legend(**kw)

    return ax

def plot_base_loads(ax, solution):

    for source, node in solution._node.items():

        ax.plot(
            -np.array(node['assets'][f"base_load_{source}"]['net']) / 1e9,
            label = source,
        )
        
        # ax.set_title('Regional Base Load')

    kw = {
        'facecolor': 'whitesmoke',
        'ylabel': 'Regional Base Load [GW]',
        # 'ylabel': 'Power [GW]',
        'xlabel': 'Time [h]'
    }

    _ = ax.set(**kw)

    kw = {
        'ls': '--',
    }

    _ = ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    _ = ax.legend(**kw)

    return ax

def plot_total_generation(ax, solution):

    for source, node in solution._node.items():

        values = np.vstack(
            [v["net"] for k, v in node['assets'].items() if "base" not in k]
        )

        ax.plot(
            values.sum(axis = 0) / 1e9,
            label = source,
        )

    kw = {
        'facecolor': 'whitesmoke',
        'ylabel': 'Regional Total Generation [GW]',
        # 'ylabel': 'Power [GW]',
        'xlabel': 'Time [h]'
    }

    _ = ax.set(**kw)

    kw = {
        'ls': '--',
    }

    _ = ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    _ = ax.legend(**kw)

    return ax

def plot_net_generation(ax, solution):

    for source, node in solution._node.items():

        values = np.vstack(
            [v["net"] for k, v in node['assets'].items()]
        )

        ax.plot(
            values.sum(axis = 0) / 1e9,
            label = source,
        )

    kw = {
        'facecolor': 'whitesmoke',
        'ylabel': 'Regional Net Generation [GW]',
        # 'ylabel': 'Power [GW]',
        'xlabel': 'Time [h]'
    }

    _ = ax.set(**kw)

    kw = {
        'ls': '--',
    }

    _ = ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    _ = ax.legend(**kw)

    return ax

def plot_generation_by_type(ax, solution):

    gen_amounts = {'wastage': [], 'shortfall': []}

    for source, node in solution._node.items():

        gen_amounts['wastage'].append(node['wastage'])
        gen_amounts['shortfall'].append(node['shortfall'])

    for source, node in solution._node.items():

        for handle, asset in node['assets'].items():

            if asset['type'] not in gen_amounts:

                gen_amounts[asset['type']] = (
                    [node['assets'][handle]['net']]
                )

            else:

                gen_amounts[asset['type']].append(
                    [node['assets'][handle]['net']]
                )
                

    for key, val in gen_amounts.items():

        gen_amounts[key] = np.vstack(val).sum(axis = 0) / 1e9

    gen_amounts['load'] *= -1

    for key, val in gen_amounts.items():

        ax.plot(
            val,
            label = key,
            ls = '--' if key in ['wastage', 'shortfall'] else None,
        )

    kw = {
        'facecolor': 'whitesmoke',
        'ylabel': 'Power [GW]',
    }

    _ = ax.set(**kw)

    kw = {
        'ls': '--',
    }

    _ = ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    _ = ax.legend(**kw)

    return ax

def plot_generation_by_fuel(ax, solution):

    gen_amounts = {'wastage': [], 'shortfall': []}

    for source, node in solution._node.items():

        gen_amounts['wastage'].append(node['wastage'])
        gen_amounts['shortfall'].append(node['shortfall'])

    for source, node in solution._node.items():

        for handle, asset in node['assets'].items():

            if 'fuel' not in asset:

                continue

            if asset['fuel'] not in gen_amounts:

                gen_amounts[asset['fuel']] = (
                    [node['assets'][handle]['net']]
                )

            else:

                gen_amounts[asset['fuel']].append(
                    [node['assets'][handle]['net']]
                )

    for key, val in gen_amounts.items():

        gen_amounts[key] = np.vstack(val).sum(axis = 0) / 1e9

    for key, val in gen_amounts.items():

        ax.plot(
            val,
            label = key,
            ls = '--' if key in ['wastage', 'shortfall'] else None,
        )

    kw = {
        'facecolor': 'whitesmoke',
        'ylabel': 'Power [GW]',
    }

    _ = ax.set(**kw)

    kw = {
        'ls': '--',
    }

    _ = ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    _ = ax.legend(**kw)

    return ax

def plot_capex_by_fuel(ax, solution):

    capex_amounts = {}

    for source, node in solution._node.items():

        for handle, asset in node['assets'].items():

            if 'fuel' not in asset:

                continue

            if asset['fuel'] not in capex_amounts:

                capex_amounts[asset['fuel']] = (
                    [node['assets'][handle]['capex']]
                )

            else:

                capex_amounts[asset['fuel']].append(
                    [node['assets'][handle]['capex']]
                )

    for key, val in capex_amounts.items():

        capex_amounts[key] = np.vstack(val).sum(axis = 0)[0] / 1e9

    kw = {
        'color': 'xkcd:seafoam',
        'ec': 'k',
    }

    ax.barh(list(capex_amounts.keys()), list(capex_amounts.values()), **kw)

    kw = {
        'facecolor': 'whitesmoke',
        'xlabel': 'Capacity Expansion [GW]',
    }

    _ = ax.set(**kw)

    kw = {
        'ls': '--',
    }

    _ = ax.grid(**kw)

    kw = {
        'fontsize': 'x-small',
    }

    _ = ax.legend(**kw)

    return ax