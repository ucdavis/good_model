from ..base.node import Node
import pyomo.environ as pyomo

class Jurisdiction(Node):
    """
    Jurisdictions enforce renewable energy mix requirements across plants in a political unit.
    Requirements are enforced at a daily granularity.
    """

    def __init__(self, handle, political_unit, renewable_portion=0.0):

        self.handle = handle
        self.political_unit = political_unit
        self.renewable_portion = renewable_portion  # e.g. 0.3 for 30% renewable requirement
        self.plants = []

    def add_plant(self, plant):
        """
        Add a plant that falls under this policy's jurisdiction
        """

        self.plants.append(plant)

    def parameters(self, model):

        # Renewable portion requirement
        setattr(
            model, f"{self.handle}::renewable_portion",
            pyomo.Param(initialize=self.renewable_portion, mutable=True)
        )

        return model

    def constraints(self, model):

        portion = getattr(model, f"{self.handle}::renewable_portion")
        steps_per_day = 24  # Assuming hourly timesteps
        
        # Calculate number of full days
        num_days = len(model.steps) // steps_per_day
        
        # For each day, enforce renewable portion
        for day in range(num_days):
            
            start_step = day * steps_per_day
            end_step = (day + 1) * steps_per_day
            day_steps = range(start_step, end_step)
            
            # Sum up renewable energy for the day
            renewable_energy = sum(
                sum(plant.energy(model, step) for step in day_steps)
                for plant in self.plants 
                if plant.renewable
            )
            
            # Sum up non-renewable energy for the day
            non_renewable_energy = sum(
                sum(plant.energy(model, step) for step in day_steps)
                for plant in self.plants 
                if not plant.renewable
            )
            
            total_energy = renewable_energy + non_renewable_energy
            
            # Add constraint: renewable_energy >= portion * total_energy
            setattr(
                model, f"{self.handle}::renewable_mix::day_{day}",
                pyomo.Constraint(
                    expr = renewable_energy >= portion * total_energy
                )
            )
        
        return model