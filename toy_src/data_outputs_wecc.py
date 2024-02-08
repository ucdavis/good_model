import pandas as pd 
import numpy as np
import pyomo.environ as pyomo

def Solution(self):
    '''
    From StackOverflow
    https://stackoverflow.com/questions/67491499/
    how-to-extract-indexed-variable-information-in-pyomo-model-and-build-pandas-data
    '''
    model_vars=self.model.component_map(ctype=pyomo.Var)

    serieses=[]   # collection to hold the converted "serieses"
    for k in model_vars.keys():   # this is a map of {name:pyo.Var}
        v=model_vars[k]

        # make a pd.Series from each    
        s=pd.Series(v.extract_values(),index=v.extract_values().keys())

        # if the series is multi-indexed we need to unstack it...
        if type(s.index[0])==tuple:# it is multi-indexed
            s=s.unstack(level=1)
        else:
            s=pd.DataFrame(s) # force transition from Series -> df

        # multi-index the columns
        s.columns=pd.MultiIndex.from_tuples([(k,t) for t in s.columns])

        serieses.append(s)

    self.solution=pd.concat(serieses,axis=1)