from .utils import class_dict_for_region

class RegionNode():

    def __init__(self, key, graph, node_data): 

        self.region_id = key
        self.region_data = node_data
        self.dependents = self.region_data.get('dependents', [])
        self.graph = graph
        self.region_objects = {}
        self.build_region_objects()

    def build_region_objects(self): 
        self.region_objects = []

        for d in self.dependents:
            if d['data_type'] in class_dict_for_region:
                class_name = class_dict_for_region[d['data_type']]
                param = d['parameters']
                if str(class_name) not in  class_dict_for_region:
                    self.region_objects[str(class_name)] = []
                self.region_objects[str(class_name)].append(class_name(self.region_id, **param))


    def sets(self, model): 

        for obj in self.region_objects: 
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


