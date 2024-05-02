import pandas as pd 
import numpy as np
from datetime import date
import os

def write_model(model, version): 
    today = date.today()

    file = f'lp_file_{today}_model_run_{version}.lp'
    path = '/Users/peterambiel/Desktop/good_model/output_logs'
    filename = os.path.join(path, file)
    model.write(filename, io_options = {'symbolic_solver_labels': True})

