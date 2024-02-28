import pyomo.environ as pyomo

class Solar:
    def __init__(self, region_id, *solar_data):
        self.region_id = region_id
        self.resource_id = []
        self.cost_class = []
        self.installed_capacity = {}
        self.cf = {}
        self.max_capacity = {}
        self.cost = {}

        for data in solar_data:
            resource_id = data.get('id', 0)
            self.resource_id.append(resource_id)

            # Assuming 'values' contains cost-related information
            values = data.get('values', {})
            self.cost_class += list(values.keys())

            # Installed capacity and capacity factor for each resource
            self.installed_capacity[resource_id] = data.get('capacity', 0)
            self.cf[resource_id] = data.get('capacity_factor', {})

            # Max capacity and cost for each cost class
            for cost_class, info in values.items():
                self.max_capacity[(resource_id, cost_class)] = info.get('max_capacity', 0)
                self.cost[(resource_id, cost_class)] = info.get('cost', 0)

        # Removing duplicate entries in cost_class list if any
        self.cost_class = list(set(self.cost_class))

    def sets(self, model):
        model.src = pyomo.Set(initialize=self.resource_id)
        model.cc = pyomo.Set(initialize=self.cost_class)

    def parameters(self, model):
        model.c_solarCap = pyomo.Param(model.src, initialize=self.installed_capacity)
        model.c_solarCF = pyomo.Param(model.src, model.t, initialize=self.cf)
        model.c_solarMax = pyomo.Param(model.src, model.cc, initialize=self.max_capacity)
        model.c_solarCost = pyomo.Param(model.src, model.cc, initialize=self.cost)

    def variables(self, model):
        model.x_solarnew = pyomo.Var(model.src, model.cc, within=pyomo.NonNegativeReals)
        # Removed unnecessary use of setattr; directly assign the variable

    def objective(self, model):
        # Simplify the construction of the objective function
        solar_cost_term = pyomo.summation(model.c_solarCost, model.x_solarnew)
        return solar_cost_term

    def constraints(self, model):
        model.solar_install_limits_rule = pyomo.ConstraintList()

        for s, c in self.max_capacity.keys():
            constraint_expr = model.c_solarMax[s, c] - model.x_solarnew[s, c] >= 0
            model.solar_install_limits_rule.add(constraint_expr)

        # Additional constraints for installed capacity if needed
