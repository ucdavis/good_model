import pyomo.environ as pyomo
from pyomo.opt import SolverFactory
from pyomo.common.timing import TicTocTimer
from pyomo.core.expr.numeric_expr import LinearExpression


class region_node():

    def __init__(self, region_id, **kwargs): 

        self.region_id = region_id
        self.params = kwargs.get('dependents', [])

        self.build_region_objects()

    def build_region_objects(self): 

        self.region_objects = []

        for param in self.params:
            
            if param['type'] == 'generator_cost' or param['type'] == 'generator_capacity':

                self.region_objects.append(Generators(param['id'], **param))

            elif param['type'] == 'solar':

                self.region_objects.append(Solar(param['id'], **param))

            elif param['type'] == 'wind':

                self.region_objects.append(Wind(param['id'], **param))

            elif param['type'] == 'storage':

                self.region_objects.append(Storage(param['id'], **param))

            elif param['type'] == 'load':

                self.region_objects.append(Load(**param))


    def balancing_constraints(self, model): 

        # constraint 1: generation-demand balancing
        self.model.gen_to_demand_rule = pyomo.ConstraintList()

        for gf in self.model.gf:
            for t in self.model.t:
                generation_term += region_objects.Generators.model.x_generation[gf, t]
        
        # generation_vars = []
        # for r in self.model.r:
        #     for gf in self.model.gf:
        #         for t in self.model.t:
        #             generation_vars.append(self.model.x_generation[r, gf, t])

        # generation_term = LinearExpression(constant=0.0, linear_vars=generation_vars)

        solar_term = pyomo.quicksum((region_objects.Solar.model.c_solarCap + region_objects.Solar.model.x_solarNew[s,c]) * region_objects.Solar.model.c_solarCF[s,t]
            for s in self.model.src 
            for t in self.model.t) 
        
        
        # solar_cap_indices = [(r,s,c) for r in self.model.r for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarMax]
        # solar_vars = []
        # solar_coefs = []
        # for (r, s, c) in solar_cap_indices:
        #     for t in self.model.t:
        #         if r in self.model.c_solarMax:
        #             solar_vars.append(self.model.c_solarCap[r] + self.model.x_solarNew[r, s, c])
        #             solar_coefs.append(self.model.c_solarCF[r, s, t])
        #         else: 
        #             solar_vars.append(self.model.x_solarNew[r, s, c])
        #             solar_coefs.append(self.model.c_solarCF[r, s, t])
                    
        # solar_term = LinearExpression(constant=0.0, linear_coefs=solar_coefs, linear_vars=solar_vars)


        wint_term = pyomo.quicksum((region_objects.Wind.model.c_windCap + region_objects.Solar.model.x_windNew[w,c]) * region_objects.Solar.model.c_windCF[w,t]
            + (region_objects.Wind.model.c_windTransCost[w,c] * region_objects.Wind.model.x_windNew[w,c]) 
            for w in self.model.wrc 
            for c in self.model.cc
            for t in self.model.t) 
        

        # wind_cap_indices = [(r,w,c) for r in self.model.r for w in self.model.wrc for c in self.model.cc if (r, w, c) in self.model.c_windCost or (r, w, c) in self.model.c_windTransCost]
        # wind_vars = []
        # wind_coefs = []
        # for (r, w, c) in wind_cap_indices:
        #     for t in self.model.t:
        #         if r in self.model.c_windMax:
        #             wind_vars.append(self.model.c_windCap[r] + self.model.x_windNew[r, w, c])
        #             wind_coefs.append(self.model.c_windCF[r, w, t])
        #         else:
        #             wind_vars.append(self.model.x_windNew[r, w, c])
        #             wind_coefs.append(self.model.c_windCF[r, w, t])
                    
        # wind_term = LinearExpression(constant=0.0, linear_coefs=wind_coefs, linear_vars=wind_vars)


        storage_term = pyomo.quicksum(region_objects.Storage.model.x_storOut[t] - region_objects.Storage.model.x_storIn[t] 
            for t in self.model.t)

        # stor_indices = [r for r in self.model.c_storCap]
        # stor_vars = []
        # for r in stor_indices: 
        #     for t in self.model.t: 
        #         stor_vars.append(self.model.x_storOut[r, t] - self.model.x_storIn[r, t])
        # storage_term = LinearExpression(constant=0.0,
        #                             linear_vars=stor_vars)
      

        # Unsure how to handle the generations objects wrt to region_node
        export_vars = []
        export_coefs = [] 
        for r in self.model.r:
            for o in self.model.o:
                for t in self.model.t: 
                    export_vars.append(self.model.x_trans[r, o, t])
                    export_coefs.append(self.model.c_transLoss)
        export_term = LinearExpression(constant=0.0, linear_coefs=export_coefs, linear_vars=export_vars)

        import_vars = [] 
        import_coefs = []
        for o in self.model.o:
            for r in self.model.r:
                for t in self.model.t:
                    import_vars.append(self.model.x_trans[o, r, t])
                    import_coefs.append(self.model.c_transLoss)
        import_term = LinearExpression(constant=0.0, linear_coefs=import_coefs, linear_vars=import_vars)
        

        for t in self.model.t: 
            demand_term += region_objects.Load.model.c_demandLoad[t]

        # demand_indices = [(r,t) for r in self.model.r for t in self.model.t if (r,t) in self.model.c_demandLoad]
        # demand_vars = []
        # for (r,t) in demand_indices: 
        #     demand_vars.append(self.model.c_demandLoad[r, t])
        # demand_term = LinearExpression(constant=0.0,
        #                            linear_vars=demand_vars)

        
        constraint_expr = (generation_term 
            + solar_term 
            + wind_term 
            + storage_term
            + export_term 
            -import_term
            - demand_term
            ) == 0
				
        self.model.gen_to_demand_rule.add(constraint_expr)		


class Generators():

    def __init__(self, handle, **kwargs): 

        self.region_id = region_id
        self.gen_cost = kwargs()
        self.gen_capacity = kwargs()
    
    def parameters(self, model):

        self.model.c_gencost = pyomo.Param(self.model.gf, initialize=self.gen_cost)
        self.model.c_genMax = pyomo.Param(self.model.gf, initialize=self.gen_capacity)

        return model 

    def variables(self, model):

        self.model.x_generation = pyomo.Var(self.model.gf, self.model.t, within = (pyomo.NonNegativeReals))

        setattr(model, self.handle, self.model.x_generation)

        return model

    def objective(self, model):

        gen_cost_indices = [gf for gf in model.gf if (gf) in self.model.c_gencost]

        gen_cost_term = pyomo.quicksum(self.model.x_generation[gf, t] * self.model.c_gencost[gf] 
            for gf in gen_cost_indices
            for t in self.model.t)

        return gen_cost_term

    def constraints(self, model):

        self.model.gen_limits_rule = pyomo.ConstraintList()
        
        constraint_expr = pyomo.quicksum(
            self.model.c_genMax[gf] - self.model.x_generation[gf, t]
            for gf in self.model.gf
            for t in self.model.t
        ) >= 0
                        
        self.model.gen_limits_rule.add(constraint_expr)

        return model
            
    
class Solar():

    def __init__(self, region_id, **kwargs): 

         self.region_id = region_id
         self.installed_capacity = kwargs()
         self.cf = kwargs()
         self.max_capacity = kwargs()
         self.cost = kwargs()


    def parameters(self, model): 

        self.model.c_solarCap = pyomo.Param(initialize=self.installed_capacity)
        self.model.c_solarCF = pyomo.Param(self.model.src, self.model.t, initialize=self.cf)
        self.model.c_solarMax = pyomo.Param(self.model.src, self.model.cc, initialize=self.max_capacity)
        self.model.c_solarCost = pyomo.Param(self.model.src, self.model.cc, initialize=self.cost)

        return model
        
    def variables(self, model):

        self.model.x_solarnew = pyomo.Var(self.model.src, self.model.cc, within=(pyomo.NonNegativeReals))

        setattr(model, self.handle, self.model.x_solarnew)

        return model

    def objective(self, model):

        solar_cost_indices = [(s,c) for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarCost]
        
        solar_cost_term = pyomo.quicksum(
            self.model.c_solarCost[s,c] * self.model.x_solarNew[s,c] 
            for (s,c) in solar_cost_indices
        )

        return solar_cost_term

    def constraints(self, model): 

        self.model.solar_install_limits_rule = pyomo.ConstraintList()

        solar_max_indices = [(s,c) for s in self.model.src for c in self.model.cc if (s,c) in self.model.c_solarMax]

        for s in self.model.src:
            for c in self.model.cc:
                if (s, c) in solar_max_indices:      
                    constraint_expr = pyomo.quicksum(
                        self.model.c_solarMax[r, s, c] - self.model.x_solarNew[r, s, c] + (self.model.c_solarCap[r] 
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

        setattr(model, self.handle, self.model.x_windnew)

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

        x_storsoc = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
        x_storcharge = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
        x_stordischarge = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
 
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

    return model


def Load(): 

    def __init__(self, region_id, **kwargs):

        self.region_id = region_id
        self.load = kwargs()

    def parameters(self, model): 

        self.model.c_demandLoad = pyomo.Param(self.model.t, initialize=load)

        return model

# need to update this class wrt to region_node 
class transmission():

    def __init__(self, source, target, **kwargs): 

        self.source = source
        self.target = target
        self.handle = f'{source}_{target}'
        self.capacity = kwargs.get('capacity', 1)
        self.cost = kwargs.get('cost', 1)
        self.efficiency = kwargs.get('efficiency', 1)


    def parameters(self, model): 

        self.model.c_transCost =  pyomo.Param(source, target, initialize = cost)
        self.model.c_transCap = pyomo.Param(source, target, initialize = cpacity)
        self.model.c_transLoss = pyomo.Param(initialize = efficiency)


    def variables(self, model): 

        self.model.x_trans = pyomo.Var(self.model.r, self.model.o, self.model.t, within=(pyomo.NonNegativeReals))

        return self.model.x_trans   

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


        self.model.trans_balance_rule = pyomo.ConstraintList()

        for r in self.model.r: 
            for o in self.model.o:
                if (r,o) in self.model.c_transCap:
                    for t in self.model.t:
                        constraint_expr = ( 
                        self.model.x_trans[r,o,t] - self.model.x_trans[o,r,t]
                        ) == 0
                    else: 
                        constraint_expr = (pyomo.Constraint.Skip)

                        self.model.trans_balance_rule.add(constraint_expr)


    return model

class model_opt(): 

    def __init__(self, graph, sets): 

        self.inputs = graph
        self.sets = sets

        self.build()

    def build(self, **kwargs): 

        self.build_grid()
        
        self.build_model()

        self.solve_model()

    def build_grid(self, **kwargs): 

        for handle, node in graph._node.items(): 

            node['object'] = region_node(handle, **node)
            
        for source, adjacency in self.graph._adj.items():

            for target, link in adjacency.items():

                transmission['object'] = transmission(source, target, **link)

    
    def build_model(self, *kwargs): 

        # create model instance
        self.model = pyomo.ConcreteModel()

        # add pyomo.timer method
        timer = TicTocTimer()

        # create model sets
        self.build_sets()

        self.build_variables()

        self.build_objective()

        self.build_constraints()

    def build_sets(self, **kwargs): 

        for handle, node in graph._node.items(): 

            for dependents, values in node.items(): 

                type = values.get('type', 0)
                
                if type == 'generator_capacity': 

                    gen_type = values.get('id', 0)

                self.model.g = pyomo.Set(initialize=gen_types)

        # set of generator types
        self.model.g = pyomo.Set(initialize=self.sets['gen_type']) 

        # set of generator fuel types
        self.model.gf = pyomo.Set(initialize=self.sets['gen_fuel_type']) 

        # set of solar resource classes
        self.model.src = pyomo.Set(initialize=self.sets['resource_class']) 

        # set of wind resource classes
        self.model.wrc = pyomo.Set(initialize=self.sets['resource_class']) 

        # set of cost classes for solar and wind resources 
        self.model.cc = pyomo.Set(initialize=self.sets['cost_class']) 
        
        # set of time periods expressed as hourly
        self.model.t = pyomo.Set(initialize=self.sets['hours']) # time period, hour

        # set of states (lower 48) to integrate state-specific policy constraints
        self.model.s = pyomo.Set(initialize=self.sets['states']) 

        # set of generator to region mapping
        self.model.gtor = pyomo.Set(within=self.model.g * self.model.r) 


    def build_variables(self, **kwargs): 

        for r in region_node(): 

            hold = ()

        for r in transmission(): 
        
            hold = ()

    def build_objective(self, **kwargs): 

        for r in region_node(): 

        for t in transmission(): 

    
    def build_constraint(self): 

        self.grid_object_constraints(): 

        self.balancing_constraints(): 

        self.transmission_constraints(): 


    def grid_object_constraints(self): 

        for r in region_node()

    def balancing_constraints(self): 

        for r in region_node()

    def transmission_constraints(self): 

        for t in transmission(): 


    def variables(self, model):

    def objective(self, model): 

        for r in region_node.items(): 

            objective_function = pyomo.Objective(generators + solar + wind + transmission)

    def constraints(self, model):

    def solve_model(self, solver_name, model): 

        self.solver = pyomo.SolverFactory(solver_name)

        self.solution = self.solver.solve(model) 




class model_opt():

    def __init__(self,set_inputs={}, param_inputs={}):

        self.set_inputs=set_inputs
        self.param_inputs=param_inputs

        if self.set_inputs and self.param_inputs:

            self.Build()

    def Solve(self,solver_name):

        self.solve=SolverFactory(solver_name).solve(self.model, tee = True)
       
    def Build(self):

        #Pulling the index values for the model sets from the data_inputs.py
        self.sets=self.set_inputs

		#Pulling the keys from the data_inputs.py
        self.params=self.param_inputs

		#Initializing the model as a concrete model (as in one that has fixed inputted values)
        self.model=pyomo.ConcreteModel()

        #add pyomo Timer
        timer = TicTocTimer()

        #Adding global sets
        self.GlobalSet()
        timer.toc('Global Set build complete')

        #Adding global parameters
        self.GlobalParam()
        timer.toc('Global Paramater build complete')

        #Adding regional blocks
        self.model.b = pyomo.Block(self.model.r, rule=self.RegionBlock)  # Create instances
        # Now call RegionBlock for each instance
        for r in self.model.r:  # Iterate over regions
            self.RegionBlock(self.model.b[r], r)  # Pass block instance and region index

        #Adding global constraints, linking blocks together
        self.GlobalConstraints()
        timer.toc('Global Constraints build complete')


    def GlobalSet(self): 
		
        self.model.t = pyomo.Set(initialize=self.sets['hours']) # time period, hour
        #self.model.y = pyomo.Set(initialize=self.keys[year_periods])
        self.model.d = pyomo.Set(initialize=self.sets['days']) # time period, day
        self.model.r = pyomo.Set(initialize=self.sets['regions']) # region, defaulting to IPM regions
        self.model.s = pyomo.Set(initialize=self.sets['states']) # pyomo.Set of regions used in the model corresponding to states (to account for policy constraints)
        #self.model.gtor = pyomo.Set(within=self.model.g * self.model.r) # generator to region mapping
        #self.model.ttod = pyomo.Set(within=self.model.t * self.model.d) # hour to day mapping

        # alias pyomo.Sets: when the model requires use of the same pyomo.Set within a single equation
        self.model.o = pyomo.Set(initialize=self.model.r)
	

    def GlobalParam(self): 
        # transmission pyomo.Parameters
        self.model.c_transCap = pyomo.Param(self.model.r, self.model.o, initialize=self.params['transmission_capacity'])
        self.model.c_transCost = pyomo.Param(self.model.r, self.model.o, initialize=self.params['transmission_cost'])
       
        # define model scalars
        self.model.c_transLoss = pyomo.Param(initialize=0.972)
        self.model.c_storEff = pyomo.Param(initialize=0.7) # efficiency is 2x one way efficiency (85%) because the model accounts for losses in only one direction 
        self.model.c_storCost = pyomo.Param(initialize=10000) 
        self.model.c_storFlowCap = pyomo.Param(initialize = 0.85)

    def RegionBlock(self, b, r):

        # define regional sets   
        b.g = pyomo.Set(initialize=self.sets['gen_type']) 
        b.gf = pyomo.Set(initialize=self.sets['gen_fuel_type']) 
        b.src = pyomo.Set(initialize=self.sets['resource_class']) 
        b.wrc = pyomo.Set(initialize=self.sets['resource_class']) 
        b.cc = pyomo.Set(initialize=self.sets['cost_class']) 
        
        # define regional parameters 
        # generation costs
        b.c_genCost = pyomo.Param(b.gf, initialize=lambda m, gf: self.params['generator_cost'][(r, gf)])
        b.c_solarCost = pyomo.Param(self.model.r, b.src, b.cc, initialize=self.params['solar_capex'])
        b.c_windCost = pyomo.Param(self.model.r, b.wrc, b.cc, initialize=self.params['wind_capex'][r])
        
        # demand
        b.c_demandLoad = pyomo.Param(self.model.t, initialize=self.params['load'][r])

        # generation pyomo.Parameters
        b.c_genMax = pyomo.Param(b.gf, initialize=self.params['generator_capacity'][r])

        # renewable generation pyomo.Parameters
        b.c_solarCap = pyomo.Param(initialize=self.params['solar_installed_capacity'][r])
        b.c_windCap = pyomo.Param(initialize=self.params['wind_installed_capacity'][r])
        b.c_solarCF = pyomo.Param(b.src, self.model.t, initialize=self.params['solar_CF'][r])
        b.c_windCF = pyomo.Param(b.wrc, self.model.t, initialize=self.params['wind_CF'])
        b.c_solarMax = pyomo.Param(b.wrc, b.cc, initialize=self.params['solar_max_capacity'][r])
        b.c_windMax = pyomo.Param(b.wrc, b.cc, initialize=self.params['wind_max_capacity'][r])
    
        b.c_windTransCost = pyomo.Param(b.wrc, b.cc, initialize=self.params['wind_transmission_cost'][r])

        # energy storage pyomo.Parameters
        b.c_storCap = pyomo.Param(initialize=self.params['enerstor_installed_capacity'][r])

        # policy pyomo.Parameters
        #self.model.c_rps = pyomo.Param(self.model.r, initialize=self.keys[rps])

        # define regional variables
        b.x_trans = pyomo.Var(self.model.o, self.model.t, within=(pyomo.NonNegativeReals),
                                bounds=lambda m, o, t: (1e-08, b.c_transCap[r, o] if (r, o) in b.c_transCap else None))
        b.x_generation = pyomo.Var(b.gf, self.model.t, 
                                   within=(pyomo.NonNegativeReals),
                                   bounds=lambda m, r, gf, t: (1e-08, b.c_genMax[r, gf] if (r, gf) in b.c_genMax else None))
        b.x_solarNew = pyomo.Var(b.src, b.cc, within=(pyomo.NonNegativeReals))
        b.x_windNew = pyomo.Var(b.wrc, b.cc, within=(pyomo.NonNegativeReals))
        b.x_storSOC = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
        b.x_storIn = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))
        b.x_storOut = pyomo.Var(self.model.t, within=(pyomo.NonNegativeReals))


        # Define objective function
        def obj_func_rule(model):
               
                gen_cost_indices = [(r, gf) for r in self.model.r for gf in b.gf if (r, gf) in model.b[r].c_gencost]
                gen_cost_vars = []
                gen_cost_coefs = []
                for (r,gf) in gen_cost_indices: 
                    for t in self.model.t: 
                        gen_cost_vars.append(self.model.x_generation[r, gf, t])
                        gen_cost_coefs.append(self.model.c_gencost[r, gf])
                gen_cost_term = LinearExpression(constant=0.0, linear_coefs=gen_cost_coefs, linear_vars=gen_cost_vars)

                trans_cost_indices = [(r,o) for r in self.model.r for o in self.model.o if (r,o) in b.c_transCost]
                trans_cost_vars = []
                trans_cost_coefs = []
                for (r,o) in trans_cost_indices:
                    for t in self.model.t: 
                        trans_cost_vars.append(self.model.x_trans[r, o, t])
                        trans_cost_coefs.append(self.model.c_transCost[r, o])
                trans_cost_term = LinearExpression(constant=0.0, linear_coefs=trans_cost_coefs, linear_vars=trans_cost_vars)
                
                solar_cost_indices = [(r,s,c) for r in self.model.r for s in b.src for c in b.cc if (r,s,c) in b.c_solarCost]
                solar_cost_vars = []
                solar_cost_coefs = []
                for (r,s,c) in solar_cost_indices:
                    solar_cost_vars.append(b.x_solarNew[r,s,c] )
                    solar_cost_coefs.append(b.c_solarCost[r,s,c])
                solar_cost_term = LinearExpression(constant=0.0, linear_coefs=solar_cost_coefs, linear_vars=solar_cost_vars)
                

                wind_cost_indices = [(r, w, c) for r in self.model.r for w in b.wrc for c in b.cc if (r, w, c) in b.c_windCost and (r, w) in self.model.c_windTransCost]
                wind_cost_vars = []
                wind_cost_coefs = []
                for (r,w,c) in wind_cost_indices:
                    wind_cost_vars.append(b.x_windNew[r, w, c])
                    wind_cost_coefs.append(b.c_windCost[r, w, c] + b.c_windTransCost[r, w])
                wind_cost_term = LinearExpression(constant=0.0, linear_coefs=wind_cost_coefs, linear_vars=wind_cost_vars)

                return (
                    gen_cost_term 
                    + trans_cost_term 
                    + solar_cost_term + wind_cost_term
                )

        b.obj_func = pyomo.Objective(rule=obj_func_rule, sense=pyomo.minimize)

        # constraint 1: generation-demand balancing
        b.gen_to_demand_rule = pyomo.ConstraintList()
        
        generation_vars = [(self.model.x_generation[r, gf, t]
                       for r in self.model.r
                       for gf in self.model.gf
                       for t in self.model.t)]
        generation_term = LinearExpression(constant=0.0, linear_vars=generation_vars)

        solar_cap_indices = [(r,s,c) for r in self.model.r for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarCap]
        solar_vars = []
        solar_coefs = []
        for (r, s, c) in solar_cap_indices:
            for t in self.model.t:
                solar_vars.append(self.model.c_solarCap[r, s, c] + self.model.x_solarNew[r, s, c])
                solar_coefs.append(self.model.c_solarCF[r, t, s, c])
        solar_term = LinearExpression(constant=0.0, linear_coefs=solar_coefs, linear_vars=solar_vars)


        wind_cap_indices = [(r,w,c) for r in self.model.r for w in self.model.wrc for c in self.model.cc if (r,w,c) in self.model.c_windCap]
        wind_vars = []
        wind_coefs = []
        for (r, w, c) in wind_cap_indices:
            for t in self.model.t:
                wind_vars.append(self.model.c_windCap[r, w, c] + self.model.x_windNew[r, w, c])
                wind_coefs.append(self.model.c_windCF[r, t, w, c])
        wind_term = LinearExpression(constant=0.0, linear_coefs=wind_coefs, linear_vars=wind_vars)

        storage_term = LinearExpression(constant=0.0,
                                    linear_vars=[(self.model.x_storOut[r, t] - self.model.x_storIn[r, t])
                                                for r in self.model.r
                                                for t in self.model.t])
      
        export_vars = []
        export_coefs = [] 
        for r in self.model.r:
            for o in self.model.o:
                for t in self.model.t: 
                    export_vars.append(self.model.x_trans[r, o, t])
                    export_coefs.append(self.model.c_transLoss)
        export_term = LinearExpression(constant=0.0, linear_coefs=export_coefs, linear_vars=export_vars)

        import_vars = [] 
        import_coefs = []
        for o in self.model.o:
            for r in self.model.r:
                for t in self.model.t:
                    import_vars.append(self.model.x_trans[o, r, t])
                    import_coefs.append(self.model.c_transLoss)
        import_term = LinearExpression(constant=0.0, linear_coefs=import_coefs, linear_vars=import_vars)
        
        demand_indices = [(r,t) for r in self.model.r for t in self.model.t if (r,t) in self.model.c_demandLoad]
        demand_term = LinearExpression(constant=0.0,
                                   linear_vars=[self.model.c_demandLoad[r, t]
                                                for (r, t) in demand_indices])

        constraint_expr = (generation_term + solar_term 
                        + wind_term + storage_term +
                        export_term - import_term - demand_term 
                ) == 0
				
        b.gen_to_demand_rule.add(constraint_expr)	
		 	
           
        #constraint 2: Generation Limits   
        b.gen_limits_rule = pyomo.ConstraintList() 
    
        gen_limts_indices = [(r,gf) for r in self.model.r for gf in b.gf if (r,gf) in b.c_genMax]	

        constraint_expr = (pyomo.quicksum(b.c_genMax[r,gf] - b.x_generation[r,gf,t] 
                        for (r,gf) in gen_limts_indices
                        for t in self.model.t)
                        ) >=0  
                        
        b.gen_limits_rule.add(constraint_expr)
            

        #constraint 4: storage limits (r,t)
        b.maxStorage_rule = pyomo.ConstraintList()

        stor_limit_indices = [r for r in self.model.r if r in b.c_storCap]

        constraint_expr = (pyomo.quicksum(
                b.c_storCap[r] - b.x_storSOC[r, t]
                for r in stor_limit_indices
                for t in self.model.t)
                ) >=0

        b.maxStorage_rule.add(constraint_expr)
        

        #constraint 5: storage state-of-charge (r,t)
        b.storageSOC_rule = pyomo.ConstraintList()

        for r in self.model.r:
            for t in self.model.t:
                if t == min(self.model.t):
                    # For the first time step, set storSOC to 0
                    b.storageSOC_rule.add(b.x_storSOC[r,t] == 0)
                else:
                    # For subsequent time steps, apply the constraint
                    constraint_expr = (
                        b.x_storSOC[r,t] - b.x_storSOC[r,t-1] - 
                        b.x_storIn[r,t-1] * b.c_storEff + b.x_storOut[r,t-1]  
                    ) == 0
                    
                    b.storageSOC_rule.add(constraint_expr)


        #constraint 6: storage flow-in limits (charging)
        b.stor_flowIN_rule = pyomo.ConstraintList() 
        
        stor_flowin_indices = [r for r in self.model.r if r in b.c_storCap]

        constraint_expr = (pyomo.quicksum(b.c_storCap[r] * b.c_storFlowCap - b.x_storIn[r,t] 
                        for r in stor_flowin_indices
                        for t in self.model.t) 
                        ) >= 0 

        b.stor_flowIN_rule.add(constraint_expr)


        #constaint 7: storage flow out limits (discharging)
        b.stor_flowOUT_rule = pyomo.ConstraintList()

        stor_flow_out_indices = [r for r in self.model.r if r in b.c_storCap]
        
        constraint_expr = pyomo.quicksum(
            b.c_storCap * b.c_storFlowCap - b.x_storOut[r, t]
            for r in stor_flow_out_indices
            for t in self.model.t
        ) >= 0
                
        b.stor_flowOUT_rule.add(constraint_expr)


        #constraint 8: solar resource capacity limits
        b.solar_install_limits_rule = pyomo.ConstraintList()

        if r in b.c_solarMax: 
            for s in b.src: 
                for c in b.cc:

                    constraint_expr = (pyomo.quicksum(
                                b.c_solarMax[r,s,c] - (b.x_solarNew[r,s,c] + b.c_solarCap[r])) 
                    ) >= 0
                    
                    b.solar_install_limits_rule.add(constraint_expr)  


        #constraint 9: wind resource capacity limts
        def windCapLimits(self):

            b.wind_cap_limits_rule = pyomo.ConstraintList()

            if r in b.c_windMax:
                for w in b.wrc: 
                    for c in b.cc:
                            
                        constraint_expr = (pyomo.quicksum(
                                    b.c_windMax[r,w,c] - (b.x_windNew[r,w,c] + b.c_windCap[r]))
                            )  >= 0
                            
                        b.wind_install_limits_rule.add(constraint_expr)  


    def GlobalConstraints(self):
        #constraint 3: transmission limits
        def transLimits(self):
        
            self.model.trans_limits_rule = pyomo.ConstraintList()

            for r in self.model.r: 
                for o in self.model.o: 
                    if (r,o) in self.model.c_transCap: 
                        for t in self.model.t: 
                            constraint_expr = (
                            self.model.c_transCap[r,o] - self.model.b[r].x_trans[r,o,t]
                            ) >=0
                        
                        self.model.trans_limits_rule.add(constraint_expr)
        
        # constraint 3a: transmission system balance - system level transmission balancing
        def transBalance(self): 

            self.model.trans_balance_rule = pyomo.ConstraintList()

            for r in self.model.r: 
                for o in self.model.o:
                    if (r,o) in self.model.c_transCap:
                        for t in self.model.t:
                            constraint_expr = ( 
                            self.model.b[r].x_trans[r,o,t] - self.model.b[r].x_trans[o,r,t]
                            ) == 0

                            self.model.trans_balance_rule.add(constraint_expr)


        '''
        #constraint 10: electricity import limits
        def importLimits(self):
        
            self.model.import_limit_rule = pyomo.ConstraintList()

            for r in self.model.r: 
                constraint_expr = (
                    self.model.c_importLimit[r] - sum(self.model.x_trans[r,o,t] for o in self.model.o for t in self.model.t)
                    ) == 0
                self.model.import_limit_rule.add(constraint_expr)
        '''



