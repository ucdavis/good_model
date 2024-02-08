import pyomo.environ as pyomo
from pyomo.opt import SolverFactory
from pyomo.common.timing import TicTocTimer
from pyomo.core.expr.numeric_expr import LinearExpression

# add solar transmission cost
# self.model.T=pyomo.Set(initialize=[idx for idx in range(self.inputs['n_t'])])
# self.model.R=pyomo.Set(initialize=[idx for idx in range(self.inputs['n_r'])])

class model_opt():

    def __init__(self,set_inputs={}, param_inputs={}):

        self.set_inputs=set_inputs
        self.param_inputs=param_inputs

        if self.set_inputs and self.param_inputs:

            self.Build()

    def Solve(self,solver_name):

        self.solve=SolverFactory(solver_name).solve(self.model, options={"threads": 6}, tee = True)
       
    def Build(self):

        #Pulling the index values for the model sets from the data_inputs.py
        self.sets=self.set_inputs

		#Pulling the keys from the data_inputs.py
        self.params=self.param_inputs

		#Initializing the model as a concrete model (as in one that has fixed inputted values)
        self.model=pyomo.ConcreteModel()

        #add pyomo Timer
        timer = TicTocTimer()

        #Adding sets
        self.Set()
        timer.toc('Set build complete')

        #Adding parameters
        self.Param()
        timer.toc('Paramater build complete')

		#Adding variables
        self.Variables()
        timer.toc('Variable build complete')

		#Adding the objective function
        self.Objective()
        timer.toc('Objective function build complete')
	
        #constraint 1: genToDemand(t, r) with evload constraint
        self.genToDemand()
        timer.toc('Generation-Demand Balancing constraint build complete')

        #constraint 2: Generation Limits
        self.genLimits()
        timer.toc('Generation limits constraint complete')
        
        #constraint 3: transmission limits
        self.transLimits()
        timer.toc('Transmission limits constraint complete')

        #constraint 3a: transission balance
        self.transBalance()
        timer.toc('System-level transmission balance constraint complete')

        #constraint 4: storage limits (r,t)
        self.storLimits()
        timer.toc('Storage limits constraint build complete')

        #constraint 5: storage state-of-charge (r,t)
        self.storSOC()
        timer.toc('Storage SOC constraint build complete')

        #constraint 6: storage flow-in limits (charging)
        self.storFlowIn()
        timer.toc('Storage charging constraint build complete')

        #constaint 7: storage flow out limits (discharging)
        self.storFlowOut()
        timer.toc('Storage discharging constraint complete')

        #constraint 8: solar resource capacity limits
        self.solarCapLimits()
        timer.toc('Solar resource capacity constraint build complete')

        #constraint 9: wind resource capacity limts
        self.windCapLimits()
        timer.toc('Wind resource capacity constraint build complete')

        #constraint 10: electricity import limits
        #self.importLimits()


    def Set(self): 
		
        self.model.g = pyomo.Set(initialize=self.sets['gen_type']) 
        self.model.gf = pyomo.Set(initialize=self.sets['gen_fuel_type']) 
        self.model.src = pyomo.Set(initialize=self.sets['resource_class']) 
        self.model.wrc = pyomo.Set(initialize=self.sets['resource_class']) 
        self.model.cc = pyomo.Set(initialize=self.sets['cost_class']) 
        self.model.t = pyomo.Set(initialize=self.sets['hours']) # time period, hour
        #self.model.y = pyomo.Set(initialize=self.keys[year_periods])
        self.model.d = pyomo.Set(initialize=self.sets['days']) # time period, day
        self.model.r = pyomo.Set(initialize=self.sets['regions']) # region, defaulting to IPM regions
        self.model.s = pyomo.Set(initialize=self.sets['states']) # pyomo.Set of regions used in the model corresponding to states (to account for policy constraints)
        self.model.gtor = pyomo.Set(within=self.model.g * self.model.r) # generator to region mapping
        self.model.ttod = pyomo.Set(within=self.model.t * self.model.d) # hour to day mapping

        # alias pyomo.Sets: when the model requires use of the same pyomo.Set within a single equation
        self.model.o = pyomo.Set(initialize=self.model.r)
	
    def Param(self):
	
        self.model.c_gencost = pyomo.Param(self.model.r, self.model.gf, initialize=self.params['generator_cost'])
        self.model.c_solarCost = pyomo.Param(self.model.r, self.model.src, self.model.cc, initialize=self.params['solar_capex'])
        self.model.c_windCost = pyomo.Param(self.model.r, self.model.wrc, self.model.cc, initialize=self.params['wind_capex'])

        # demand pyomo.Parameters
        self.model.c_demandLoad = pyomo.Param(self.model.r, self.model.t, initialize=self.params['load'])
        #self.model.c_evLoad = pyomo.Param(self.model.r, self.model.t, initialize=self.keys[evLoad])
        #self.model.c_fixedevLoad = pyomo.Param(self.model.r, self.model.d, initialize=self.keys[fixedevLoad])

        # generation pyomo.Parameters
        self.model.c_genMax = pyomo.Param(self.model.r, self.model.gf, initialize=self.params['generator_capacity'])

        # renewable generation pyomo.Parameters
        self.model.c_solarCap = pyomo.Param(self.model.r, initialize=self.params['solar_installed_capacity'])
        self.model.c_windCap = pyomo.Param(self.model.r, initialize=self.params['wind_installed_capacity'])
        self.model.c_solarCF = pyomo.Param(self.model.r, self.model.src, self.model.t, initialize=self.params['solar_CF'])
        self.model.c_windCF = pyomo.Param(self.model.r, self.model.wrc, self.model.t, initialize=self.params['wind_CF'])
        self.model.c_solarMax = pyomo.Param(self.model.r, self.model.src, self.model.cc, initialize=self.params['solar_max_capacity'])
        self.model.c_windMax = pyomo.Param(self.model.r, self.model.wrc, self.model.cc, initialize=self.params['wind_max_capacity'])

        # transmission pyomo.Parameters
        self.model.c_transCap = pyomo.Param(self.model.r, self.model.o, initialize=self.params['transmission_capacity'])
        self.model.c_transCost = pyomo.Param(self.model.r, self.model.o, initialize=self.params['transmission_cost'])
        self.model.c_windTransCost = pyomo.Param(self.model.r, self.model.wrc, self.model.cc, initialize=self.params['wind_transmission_cost'])

        # energy storage pyomo.Parameters
        self.model.c_storCap = pyomo.Param(self.model.r, initialize=self.params['enerstor_installed_capacity'])

        # policy pyomo.Parameters
        #self.model.c_rps = pyomo.Param(self.model.r, initialize=self.keys[rps])

        # define model scalars
        self.model.c_transLoss = pyomo.Param(initialize=0.972)
        self.model.c_storEff = pyomo.Param(initialize=0.7) # efficiency is 2x one way efficiency (85%) because the model accounts for losses in only one direction 
        self.model.c_storCost = pyomo.Param(initialize=10000) 
        #self.model.c_importLimit = pyomo.Param(self.model.r, initialize=800000000)
        self.model.c_storFlowCap = pyomo.Param(initialize = 0.85)

    def Variables(self):
		
        self.model.x_generation = pyomo.Var(self.model.r, self.model.gf, self.model.t, within =(pyomo.NonNegativeReals))
        self.model.x_trans = pyomo.Var(self.model.r, self.model.o, self.model.t, within=(pyomo.NonNegativeReals))     
        self.model.x_solarNew = pyomo.Var(self.model.r, self.model.src, self.model.cc, within=(pyomo.NonNegativeReals))
        self.model.x_windNew = pyomo.Var(self.model.r, self.model.wrc, self.model.cc, within=(pyomo.NonNegativeReals))
        self.model.x_storSOC = pyomo.Var(self.model.r, self.model.t, within=(pyomo.NonNegativeReals))
        self.model.x_storIn = pyomo.Var(self.model.r, self.model.t, within=(pyomo.NonNegativeReals))
        self.model.x_storOut = pyomo.Var(self.model.r, self.model.t, within=(pyomo.NonNegativeReals))

    def Objective(self):

        def obj_func_rule(model):
            
            gen_cost_indices = [(r, gf) for r in model.r for gf in model.gf if (r, gf) in model.c_gencost]
            gen_cost_term = pyomo.quicksum(model.x_generation[r, gf, t] * model.c_gencost[r, gf] 
                            for (r,gf) in gen_cost_indices
                            for t in self.model.t
                            )
            
            trans_cost_indices = [(r,o) for r in self.model.r for o in self.model.o if (r,o) in self.model.c_transCost]
            trans_cost_term = pyomo.quicksum(self.model.x_trans[r, o, t] * self.model.c_transCost[r, o]
                            for (r, o) in trans_cost_indices
                            for t in self.model.t
                            )
            
            solar_cost_indices = [(r,s,c) for r in self.model.r for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarCost]
            solar_cost_term = pyomo.quicksum(self.model.c_solarCost[r,s,c] * self.model.x_solarNew[r,s,c] 
                            for (r,s,c) in solar_cost_indices
                            )
            
            wind_cost_indices = [(r, w, c) for r in self.model.r for w in self.model.wrc for c in self.model.cc if (r, w, c) in self.model.c_windCost]
            wind_cost_term = pyomo.quicksum(
                            (self.model.c_windCost[r, w, c] + self.model.c_windTransCost[r, w, c]) * self.model.x_windNew[r, w, c]
                            for (r, w, c) in wind_cost_indices
                            )

            return (
                gen_cost_term 
                + trans_cost_term 
                + solar_cost_term + wind_cost_term
            )

        self.model.obj_func = pyomo.Objective(rule=obj_func_rule, sense=pyomo.minimize)

    #constraint 1: generation-demand balancing
    def genToDemand(self):

        self.model.gen_to_demand_rule = pyomo.ConstraintList()
        
        generation_vars = []
        for r in self.model.r:
            for gf in self.model.gf:
                for t in self.model.t:
                    generation_vars.append(self.model.x_generation[r, gf, t])

        generation_term = LinearExpression(constant=0.0, linear_vars=generation_vars)

        solar_cap_indices = [(r,s,c) for r in self.model.r for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarMax]
        solar_vars = []
        solar_coefs = []
        for (r, s, c) in solar_cap_indices:
            for t in self.model.t:
                if r in self.model.c_solarMax:
                    solar_vars.append(self.model.c_solarCap[r] + self.model.x_solarNew[r, s, c])
                    solar_coefs.append(self.model.c_solarCF[r, s, t])
                else: 
                    solar_vars.append(self.model.x_solarNew[r, s, c])
                    solar_coefs.append(self.model.c_solarCF[r, s, t])
                    
        solar_term = LinearExpression(constant=0.0, linear_coefs=solar_coefs, linear_vars=solar_vars)


        wind_cap_indices = [(r,w,c) for r in self.model.r for w in self.model.wrc for c in self.model.cc if (r, w, c) in self.model.c_windCost or (r, w, c) in self.model.c_windTransCost]
        wind_vars = []
        wind_coefs = []
        for (r, w, c) in wind_cap_indices:
            for t in self.model.t:
                if r in self.model.c_windMax:
                    wind_vars.append(self.model.c_windCap[r] + self.model.x_windNew[r, w, c])
                    wind_coefs.append(self.model.c_windCF[r, w, t])
                else:
                    wind_vars.append(self.model.x_windNew[r, w, c])
                    wind_coefs.append(self.model.c_windCF[r, w, t])
                    
        wind_term = LinearExpression(constant=0.0, linear_coefs=wind_coefs, linear_vars=wind_vars)

        stor_indices = [r for r in self.model.c_storCap]
        stor_vars = []
        for r in stor_indices: 
            for t in self.model.t: 
                stor_vars.append(self.model.x_storOut[r, t] - self.model.x_storIn[r, t])
        storage_term = LinearExpression(constant=0.0,
                                    linear_vars=stor_vars)
      
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
        demand_vars = []
        for (r,t) in demand_indices: 
            demand_vars.append(self.model.c_demandLoad[r, t])
        demand_term = LinearExpression(constant=0.0,
                                   linear_vars=demand_vars)

        constraint_expr = LinearExpression(constant = 0.0, linear_vars=[generation_term, solar_term, 
                        wind_term,storage_term,export_term,-import_term, -demand_term]
                ) == 0
				
        self.model.gen_to_demand_rule.add(constraint_expr)		
		 	
    #constraint 2: Generation Limits   
    def genLimits(self):
	
        self.model.gen_limits_rule = pyomo.ConstraintList() 
       
        gen_limts_indices = [(r,gf) for (r,gf) in self.model.c_genMax]	

        constraint_expr = pyomo.quicksum(self.model.c_genMax[r, gf] - self.model.x_generation[r, gf, t]
            for (r, gf) in gen_limts_indices
            for t in self.model.t) >= 0
                        
        self.model.gen_limits_rule.add(constraint_expr)
        
    
    #constraint 3: transmission limits
    def transLimits(self):
	
        self.model.trans_limits_rule = pyomo.ConstraintList()

        trans_cap_indices = [(r,o) for r in self.model.r for o in self.model.o if (r,o) in self.model.c_transCap]
        
        constraint_expr = pyomo.quicksum(
            self.model.c_transCap[r,o] - self.model.x_trans[r,o,t]
            for (r,o) in trans_cap_indices
            for t in self.model.t) >=0
                  
        self.model.trans_limits_rule.add(constraint_expr)


    # constraint 3a: transmission system balance - system level transmission balancing
    def transBalance(self): 

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

    
    #constraint 4: storage limits (r,t)
    def storLimits(self):

        self.model.maxStorage_rule = pyomo.ConstraintList()

        stor_limit_indices = [r for r in self.model.r if r in self.model.c_storCap]

        constraint_expr = (pyomo.quicksum(
                self.model.c_storCap[r] - self.model.x_storSOC[r, t]
                for r in stor_limit_indices
                for t in self.model.t)
                ) >=0

        self.model.maxStorage_rule.add(constraint_expr)
	

    #constraint 5: storage state-of-charge (r,t)
    def storSOC(self):
    
        self.model.storageSOC_rule = pyomo.ConstraintList()

        for r in self.model.r:
            for t in self.model.t:
                if t == min(self.model.t):
                    # For the first time step, set storSOC to 0
                    self.model.storageSOC_rule.add(self.model.x_storSOC[r,t] == 0)
                else:
                    # For subsequent time steps, apply the constraint
                    constraint_expr = (
                        self.model.x_storSOC[r,t] - self.model.x_storSOC[r,t-1] - self.model.x_storIn[r,t-1] * self.model.c_storEff + self.model.x_storOut[r,t-1]  
                    ) == 0
                    
                    self.model.storageSOC_rule.add(constraint_expr)


    #constraint 6: storage flow-in limits (charging)
    def storFlowIn(self): 
    
        self.model.stor_flowIN_rule = pyomo.ConstraintList() 
        
        stor_flowin_indices = [r for r in self.model.r if r in self.model.c_storCap]

        constraint_expr = (pyomo.quicksum(self.model.c_storCap[r] * self.model.c_storFlowCap - self.model.x_storIn[r,t] 
                        for r in stor_flowin_indices
                        for t in self.model.t) 
                        ) >= 0 

        self.model.stor_flowIN_rule.add(constraint_expr)

    #constaint 7: storage flow out limits (discharging)
    def storFlowOut(self):

        self.model.stor_flowOUT_rule = pyomo.ConstraintList()

        stor_flow_out_indices = [r for r in self.model.r if r in self.model.c_storCap]
        
        constraint_expr = pyomo.quicksum(
            self.model.c_storCap[r] * self.model.c_storFlowCap - self.model.x_storOut[r, t]
            for r in stor_flow_out_indices
            for t in self.model.t
        ) >= 0
                
        self.model.stor_flowOUT_rule.add(constraint_expr)

    #constraint 8: solar resource capacity limits
    def solarCapLimits(self):
    
        self.model.solar_install_limits_rule = pyomo.ConstraintList()

        solar_max_indices = [(r,s,c) for r in self.model.r for s in self.model.src for c in self.model.cc if (r,s,c) in self.model.c_solarMax]

        for r in self.model.r:
            for s in self.model.src:
                for c in self.model.cc:
                    if (r, s, c) in solar_max_indices:
                        
                        constraint_expr = (
                            self.model.c_solarMax[r, s, c] - self.model.x_solarNew[r, s, c] + (self.model.c_solarCap[r] 
                            if r in self.model.c_solarCap else 0)
                            ) >= 0
                        
                        self.model.solar_install_limits_rule.add(constraint_expr)


    #constraint 9: wind resource capacity limts
    def windCapLimits(self):

        self.model.wind_install_limits_rule = pyomo.ConstraintList()

        wind_max_indices = [(r,w,c) for r in self.model.r for w in self.model.wrc for c in self.model.cc if (r,w,c) in self.model.c_windMax]
                        
        for r in self.model.r:
            for w in self.model.src:
                for c in self.model.cc:
                    if (r, w, c) in wind_max_indices:
                        
                        constraint_expr = (
                            self.model.c_windMax[r, w, c] - self.model.x_windNew[r, w, c] + (self.model.c_windCap[r] 
                            if r in self.model.c_windCap else 0)
                            ) >= 0
                        
                        self.model.wind_install_limits_rule.add(constraint_expr)

    
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



