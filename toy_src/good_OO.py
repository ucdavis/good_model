import pyomo.environ as pyomo
from pyomo.opt import SolverFactory
from pyomo.common.timing import TicTocTimer
from pyomo.core.expr.numeric_expr import LinearExpression

class_dict_for_region = {
    'generator_cost' : Generators,
    'generator_capacity': Generators,
    'solar_capex': Solar,
    'solar_cf': Solar,
    'solar_max_capacity': Solar,
    'solar_installed_capacity': Solar,
    'wind_capex': Wind,
    'wind_capacity_factor': Wind,
    'wind_max_capacity': Wind,
    'wind_installed_capacity': Wind,
    'wind_transmission_cost': Wind,
    'storage': Storage,
    'load': Load,
}

class Region_node():

    def __init__(self, key, graph, node_data): 

        self.region_id = key
        self.region_data = node_data
        self.dependents = self.region_data.get('dependents', [])
        self.graph = graph
        #Nested dictionary {"generator": {"generator 1": generator class object, 
                            #             "generator 2": generator class object
                            #              }, 
                            # "wind": {
                            #     "wind 1": wind class object, 
                            #     "wind 2": wind class object
                            # }
                            # }
        self.region_objects = {}
        self.build_region_objects()

        self.build_region_model() 

        self.balancing_constraint()

    def build_region_objects(self): 

        self.region_objects = []

        for d in self.dependents:
            if d['data_type'] in class_dict_for_region:
                class_name = class_dict_for_region[d['data_type']]
                param = d['parameters']
                # will this append a new object for each data_type in dependents? 
                ## this loop should only create five objects and pass the appropriate data type to get each object
                self.region_objects.append(class_name(region_id, **param))

        self.transmission_objects = [] 

        for source, adjacency in self.graph._adj.items():
            for target, link in adjacency.items():
                
                self.transmission_objects

                # transmission['object'] = transmission(source, target, **link)

        # for param in self.params:
            
        #     if param['type'] == 'generator_cost' or param['type'] == 'generator_capacity':

        #         self.region_objects.append(Generators(param['id'], **param))

        #     elif param['type'] == 'solar':

        #         self.region_objects.append(Solar(param['id'], **param))

        #     elif param['type'] == 'wind':

        #         self.region_objects.append(Wind(param['id'], **param))

        #     elif param['type'] == 'storage':

        #         self.region_objects.append(Storage(param['id'], **param))

        #     elif param['type'] == 'load':

        #         self.region_objects.append(Load(**param))


    def build_region_model(self): 

        def sets(self, model): 

            for obj in region_objects: 

                model = obj.sets(model)

            return model

        def parameters(self, model): 

            for obj in self.region_objects: 

                model = obj.parameters(model)

            return model
        
        def variables(self, model): 

            for obj in self.region_objects: 

                model = obj.variables(model)

            return model

        def objective(self, model): 

            objective_function = 0

            for obj in self.region_objects: 

                objective_function += obj.objective(model)

            return objective_function

        def region_object_constraints(self, model):

            for obj in self.region_objects: 

                model = obj.constraints(model)

            return model

    # pass transmission to the balancing constraint?
    # or because the variable is created in the transmission class and added to the pyomo model, it should be accessible as model.x_trans...
    def balancing_constraint(self, model): 

        # constraint 1: generation-demand balancing
        self.model.gen_to_demand_rule = pyomo.ConstraintList()

        for gf in self.model.gf:
            for t in self.model.t:
                generation_term += self.model.x_generation[gf, t]
        
        solar_term = pyomo.quicksum((Solar.model.c_solarCap + self.region_objects.Solar.model.x_solarNew[s,c]) * self.region_objects.Solar.model.c_solarCF[s,t]
            for s in self.model.src 
            for t in self.model.t
            for c in self.model.cc) 
             
        wind_term = pyomo.quicksum((self.region_objects.Wind.model.c_windCap + self.region_objects.Wind.model.x_windNew[w,c]) * self.region_objects.Wind.model.c_windCF[w,t] 
            for w in self.model.wrc 
            for c in self.model.cc
            for t in self.model.t) 
        
        storage_term = pyomo.quicksum(self.region_objects.Storage.model.x_stordischarge[t] - self.region_objects.Storage.model.x_storcharge[t] 
            for t in self.model.t)

        # how to handle region sets in the region nodes 
        ## include some region_id check in the model.o, model.r, and model.p sets?
        export_term = pyomo.quicksum(Transmission.model.x_trans[o,r,t] * Transmission.model.c_transLoss 
            for o in model.o 
            for r in model.r 
            for t in model.t)

        for r in model.r: 
            for p in model.p: 
                for t in model.t:
                    import_term += Transmission.model.x_trans[r,p,t] 
        
        for t in self.model.t: 
            demand_term += self.region_objects.Load.model.c_demandLoad[t]
        
        constraint_expr = (generation_term 
            + solar_term 
            + wind_term 
            + storage_term
            + import_term
            - export_term
            - transmission_term
            - demand_term
            ) == 0
				
        self.model.gen_to_demand_rule.add(constraint_expr)

        return model		


class Generators():

    def __init__(self, region_id, **kwargs): 

        #TODO: we need unique way to identify each generator in each region
        self.region_id = region_id
        self.gen_fuel_type = kwargs.get('type', 0)
        self.gen_cost = kwargs.get('cost', 0)
        self.gen_capacity = kwargs.get('capacity',0)

    #! Model shoould be either passed as the params to the constructor or should be available globally
    def sets(self, model): 

        model.gf = pyomo.Set(initialize=self.gen_fuel_type)

    def parameters(self, model):

        model.c_gencost = pyomo.Param(self.model.gf, initialize=self.gen_cost)

        model.c_genMax = pyomo.Param(self.model.gf, initialize=self.gen_capacity)

        return model 

    def variables(self, model):

        model.x_generation = pyomo.Var(model.gf, model.t, within = (pyomo.NonNegativeReals))

        return model

    def objective(self, model):

        gen_cost_indices = [gf for gf in model.gf if (gf) in model.c_gencost]

        gen_cost_term = 0

        gen_cost_term = pyomo.quicksum(model.x_generation[gf, t] * model.c_gencost[gf] 
            for gf in gen_cost_indices
            for t in model.t)

        return gen_cost_term

    def constraints(self, model):

        self.model.gen_limits_rule = pyomo.ConstraintList()
        
        constraint_expr = pyomo.quicksum(
            model.c_genMax[gf] - model.x_generation[gf, t]
            for gf in model.gf
            for t in model.t
        ) >= 0
                        
        self.model.gen_limits_rule.add(constraint_expr)

        return model
            
    
class Solar():

    def __init__(self, region_id, **kwargs): 

        # data needs to be collected properly from **kwargs
        self.region_id = region_id
        self.resource_id = kwargs.get('id', 0)
        self.cost_class = kwargs.get('values',{}).keys()
        self.installed_capacity = kwargs('capacity')
        self.cf = kwargs.get('values',{}).values()
        self.max_capacity = kwargs()
        self.cost = kwargs()

    def sets(self,model): 

        self.model.src = pyomo.Set(initialize=self.resource_id)
        self.model.cc = pyomo.Set(initialize=self.cost_class)

    def parameters(self, model): 

        model.c_solarCap = pyomo.Param(initialize=self.installed_capacity)
        model.c_solarCF = pyomo.Param(self.model.src, self.model.t, initialize=self.cf)
        model.c_solarMax = pyomo.Param(self.model.src, self.model.cc, initialize=self.max_capacity)
        model.c_solarCost = pyomo.Param(self.model.src, self.model.cc, initialize=self.cost)

        return model
        
    def variables(self, model):

        self.model.x_solarnew = pyomo.Var(self.model.src, self.model.cc, within=(pyomo.NonNegativeReals))

        setattr(model, self.region_id, self.model.x_solarnew)

        return model

    def objective(self, model):

        solar_cost_indices = [(s,c) for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarCost]
        
        solar_cost_term = pyomo.quicksum(
            self.model.c_solarCost[s,c] * self.model.x_solarNew[s,c] 
            for (s, c) in solar_cost_indices
        )

        return solar_cost_term

    def constraints(self, model): 

        self.model.solar_install_limits_rule = pyomo.ConstraintList()

        solar_max_indices = [(s,c) for s in self.model.src for c in self.model.cc if (s,c) in self.model.c_solarMax]

        for s in self.model.src:
            for c in self.model.cc:
                if (s, c) in solar_max_indices:      
                    constraint_expr = pyomo.quicksum(
                        self.model.c_solarMax[s, c] - self.model.x_solarNew[s, c] + (self.model.c_solarCap
                        if r in self.model.c_solarCap else 0)
                    ) >= 0
                    
                    self.model.solar_install_limits_rule.add(constraint_expr)
        
        return model 


class Wind():

    def __init__(self, region_id, **kwargs):

        self.region_id = region_id
        self.installed_capacity = kwargs()
        self.cf = kwargs()
        self.max_capacity = kwargs()
        self.cost = kwargs()
        self.trans_cost = kwargs()

    def parameters(self, model): 

        self.model.c_windCap = pyomo.Param(initialize=self.installed_capacity)
        self.model.c_windCF = pyomo.Param(self.model.wrc, self.model.t, initialize=self.cf)
        self.model.c_windMax = pyomo.Param(self.model.wrc, self.model.cc, initialize=self.max_capacity)
        self.model.c_windCost = pyomo.Param(self.model.wrc, self.model.cc, initialize=self.cost)
        self.model.c_windTransCost = pyomo.Param(self.model.wrc, self.model.cc, initialize=self.trans_cost)

    def variables(self, model): 

        self.model.x_windnew = pyomo.Var(self.model.wrc, self.model.cc, within=(pyomo.NonNegativeReals))

        setattr(model, self.region_id, self.model.x_windnew)

        return model

    def objective(self, model):

        wind_cost_indices = [(w, c) for w in self.model.wrc for c in self.model.cc if (w, c) in self.model.c_windCost]
        wind_cost_term = pyomo.quicksum(
            (self.model.c_windCost[w, c] + self.model.c_windTransCost[w, c]) * self.model.x_windNew[w, c]
            for (w, c) in wind_cost_indices
        )

        return wind_cost_term

    def constraints(self, model): 

        self.model.wind_install_limits_rule = pyomo.ConstraintList()

        wind_max_indices = [(w,c) for w in self.model.wrc for c in self.model.cc if (w,c) in self.model.c_windMax]
                        

        for w in self.model.src:
            for c in self.model.cc:
                if (w, c) in wind_max_indices:
                    
                    constraint_expr = (
                        self.model.c_windMax[w, c] - self.model.x_windNew[w, c] + (self.model.c_windCap[r])
                    ) >= 0
                    
                    self.model.wind_install_limits_rule.add(constraint_expr)

        return model


class Storage():

    def __init__(self, region_id, **kwargs):

        self.region_id = region_id
        self.params = kwargs.get('dependents',0)
        self.storage_capacity = kwargs()
        self.efficiency = kwargs()
        self.cost = kwargs()
        self.storage_flow_limit = kwargs

    def parameters(self, model): 

        self.model.c_storCap = pyomo.Param(initialize=self.storage_capacity)
        self.model.c_storEff = pyomo.Param(initialize=efficiency)
        self.model.c_storCost = pyomo.Param(initialize=cost) 
        self.model.c_storFlowCap = pyomo.Param(initialize = storage_flow_limit)

    def variables(self): 

        self.model.x_storsoc = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
        self.model.x_storcharge = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
        self.model.x_stordischarge = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))

        setattr(model, self.region_id, self.model.model.x_storsoc)
        setattr(model, self.region_id, self.model.x_storcharge)
        setattr(model, self.region_id, self.model.x_stordischarge)

        return model
 
    def constraints(self): 

        #constraint 4: storage limits (r,t)
        self.model.maxStorage_rule = pyomo.ConstraintList()

        constraint_expr = (pyomo.quicksum(
            self.model.c_storCap - self.model.x_storSOC[t]
            for t in self.model.t)
        ) >=0

        self.model.maxStorage_rule.add(constraint_expr)
        
        #constraint 5: storage state-of-charge (r,t)
        self.model.storageSOC_rule = pyomo.ConstraintList()


        for t in self.model.t:
            if t == min(self.model.t):
                # For the first time step, set storSOC to 0
                self.model.storageSOC_rule.add(self.model.x_storSOC[t] == 0)
            else:
                # For subsequent time steps, apply the constraint
                constraint_expr = (
                    self.model.x_storSOC[t] - self.model.x_storSOC[t-1] - self.model.x_storIn[t-1] * self.model.c_storEff + self.model.x_storOut[t-1]  
                ) == 0
                
                self.model.storageSOC_rule.add(constraint_expr)


        #constraint 6: storage flow-in limits (charging)
        self.model.stor_flowIN_rule = pyomo.ConstraintList() 
        

        constraint_expr = (pyomo.quicksum(self.model.c_storCap * self.model.c_storFlowCap - self.model.x_storIn[t] 
            for t in self.model.t) 
        ) >= 0 

        self.model.stor_flowIN_rule.add(constraint_expr)


        #constaint 7: storage flow out limits (discharging)
        self.model.stor_flowOUT_rule = pyomo.ConstraintList()
        
        constraint_expr = pyomo.quicksum(
            self.model.c_storCap * self.model.c_storFlowCap - self.model.x_storOut[t]
            for t in self.model.t
        ) >= 0
                
        self.model.stor_flowOUT_rule.add(constraint_expr)

        return self.model


class Load():

    def __init__(self, region_id, **kwargs):

        self.region_id = region_id
        self.load = kwargs()

    def parameters(self, model): 

        self.model.c_demandLoad = pyomo.Param(self.model.t, initialize=load)

        return model

# need to update this class wrt to region_node 
class Transmission():

    def __init__(self, source, target, **kwargs): 

        self.source = source
        self.target = target
        self.link_id = f'{source}_{target}'
        self.capacity = kwargs.get('capacity', 1)
        self.cost = kwargs.get('cost', 1)
        self.efficiency = kwargs.get('efficiency', 1)


    def parameters(self, model): 

        self.model.c_transCost =  pyomo.Param(source, target, initialize = cost)
        self.model.c_transCap = pyomo.Param(source, target, initialize = cpacity)
        self.model.c_transLoss = pyomo.Param(initialize = efficiency)


    def variables(self, model): 

        self.model.x_trans = pyomo.Var(self.model.r, self.model.o, self.model.t, within=(pyomo.NonNegativeReals))

        setattr(model, self.source, self.target, self.model.x_trans)

        return model

    def objective(self, model): 

        trans_cost_indices = [(r,o) for r in self.model.r for o in self.model.o if (r,o) in self.model.c_transCost]
        transmission_cost_term = pyomo.quicksum(self.model.x_trans[r, o, t] * self.model.c_transCost[r, o]
                        for (r, o) in trans_cost_indices
                        for t in self.model.t
                        )

        return transmission_cost_term

    def constraints(self, model): 

        self.model.trans_limits_rule = pyomo.ConstraintList()

        trans_cap_indices = [(r,o) for r in self.model.r for o in self.model.o if (r,o) in self.model.c_transCap]
        
        constraint_expr = pyomo.quicksum(
            self.model.c_transCap[r,o] - self.model.x_trans[r,o,t]
            for (r,o) in trans_cap_indices
            for t in self.model.t) >=0
                
        self.model.trans_limits_rule.add(constraint_expr)

        return model


class model_opt(): 

    def __init__(self, graph, periods): 

        self.graph = graph
        self.time_periods = periods.get('hours',[])
        self.region_list = graph.node.keys()

        if self.graph and self.periods: 

            self.build()

    def build(self, **kwargs): 

        #! we are building nodes and transmission objects in build_grid. THese classes uses "pynomo model" but if you see
        #! the pynomo model is initialised after building_grid it will through error
        self.build_grid()
        
        self.build_model()

        self.solve_model()

    def build_grid(self, **kwargs): 

        for key in self.graph._node.keys(): 

            graph = self.graph            
            region_data = self.graph._node[key]

            #TODO: Make a node dict in class model_opt
            node['object'] = region_node(key, graph, region_data)

        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():
            #TODO: Make a transmission dict with key as object of node class for source and value as object of node class for target
                transmission['object'] = transmission(source, target, **link)

    def build_model(self, *kwargs): 

        # create model instance
        self.model = pyomo.ConcreteModel()

        # add pyomo.timer method
        timer = TicTocTimer()

        # create model sets
        self.build_sets()

        self.build_variables()
        timer.toc('Variables built: complete')

        self.build_objective()
        timer.toc('Objective function built: complete')

        self.build_constraints()
        timer.toc('Constraints built: complete')

    def build_sets(self, **kwargs): 

        self.global_sets()

    def global_sets(self, model): 

        self.model.t = pyomo.Set(initialize=self.time_periods)
        self.model.r = pyomo.Set(initialize=self.region_list)
        self.model.o = pyomo.Set(initialize=self.model.r)
        self.model.p = pyomo.set(initialize=self.model.r)

    # add all variables cretaed in each node and link to the model
    def build_variables(self, **kwargs): 

        for r in region_node(): 

            hold = ()

        for r in transmission(): 
        
            hold = ()

    # add all objective terms created in each node and link to the model
    def build_objective(self, **kwargs): 

        objective_function = 0

        for region in region_node(): 

             objective_function += region['object'].variables(self.model, self.model.t)
             (Generators.objective + Solar.objective + Wind.objective)

        for link in transmission():

            objective_function += link['object'].objective(self.model, source, target) 

        return pyomo.Objective(expr=objective_function)

    # add all region object constraints for each each node and link to the model
    def build_constraints(self, model): 

        self.region_object_constraints()

        self.region_balancing_constraints()

        self.transmission_constraints()

    def region_object_constraints(self, model): 

        for node in self.graph._node.values():
            
            for t in self.model.t: 

                self.model = node['object'].constraints(self.model, t)

    # add region energy balancing constratint for each node to the model
    def region_balancing_constraints(self, model): 

        for r in region_node(): 
            constraint_expr = region_node.balancing_constraints()

        return model

    # all constraints for each link to the model
    def transmission_constraints(self, model): 

        for t in transmission(): 

            constraint_expr = Transmission.constraints()

        return model
            
    # solve the model and return the solution
    def solve_model(self, solver_name, model): 

        self.solver = pyomo.SolverFactory(solver_name)

        self.solution = self.solver.solve(model) 
    
        return self.solution
