"""Input schema for GOOD components.

Every component checks its keyword arguments against one of the models below
when it is added to a :class:`~good.optimization.network.Network`.

Units throughout GOOD 2.x:

* power and capacity: MW
* energy: MWh
* time step: hours
* operating costs: $/MWh
* overnight capital costs: $/MW (storage energy: $/MWh)
* fixed O&M: $/MW-yr
* profiles: per-unit of installed capacity, indexed by time step

Keys that are not listed here (``fuel``, ``jurisdiction``, ``co2`` and so on)
are kept as free-form attributes and can be used by policy filters.
Fields that existed in GOOD 1.x but changed meaning are rejected with a
message that explains the replacement.
"""

import math
from typing import Any, ClassVar, Dict, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_MIGRATE = "See docs/migration.md, or convert v1 graphs with good.migrate.from_v1()."


class ComponentParams(BaseModel):
    """Fields shared by every component. Unknown keys are kept as attributes."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    LEGACY: ClassVar[Dict[str, str]] = {}

    @model_validator(mode="before")
    @classmethod
    def reject_legacy_fields(cls, data):

        if isinstance(data, dict):

            for key, hint in cls.LEGACY.items():

                if key in data:

                    raise ValueError(f"'{key}' was removed in GOOD 2.0. {hint}")

        return data


def _as_profile(value):

    if value is None:

        return None

    if isinstance(value, str):

        raise ValueError(
            f"profile {value!r} was not resolved to data. Profile keys must match an "
            "entry in the node's 'profiles' dictionary."
        )

    array = np.asarray(value, dtype=float)

    if array.ndim != 1:

        raise ValueError("profile must be a one-dimensional sequence")

    if not np.all(np.isfinite(array)):

        raise ValueError("profile contains NaN or infinite values")

    if np.any(array < 0):

        raise ValueError("profile contains negative values")

    return array


class ExpansionParams(ComponentParams):
    """Fields for components whose capacity can be expanded."""

    capex_capacity: float = Field(
        0.0, ge=0, description="Maximum new capacity the model may build (MW); inf for unlimited."
    )
    capex_cost: float = Field(0.0, ge=0, description="Overnight capital cost of new capacity ($/MW).")
    fom_cost: float = Field(0.0, ge=0, description="Fixed O&M cost of new capacity ($/MW-yr).")
    lifetime: Optional[float] = Field(
        None, gt=0, description="Economic lifetime used to annualize capex_cost (years)."
    )
    discount_rate: Optional[float] = Field(
        None, ge=0, description="Real discount rate; defaults to the Network's discount_rate."
    )
    capital_charge_rate: Optional[float] = Field(
        None, gt=0, description="Annual charge per unit of overnight cost; overrides lifetime and discount_rate."
    )

    @property
    def extensible(self):

        return self.capex_capacity > 0

    @model_validator(mode="after")
    def need_annualization(self):

        if self.extensible and self.capex_cost > 0:

            if self.lifetime is None and self.capital_charge_rate is None:

                raise ValueError(
                    "expandable components with a capex_cost need a lifetime (years) or a "
                    "capital_charge_rate so the overnight cost can be annualized"
                )

        return self


class RegionParams(ComponentParams):
    """A balancing region. Unset slack fields take the Network's defaults."""

    shortfall_capacity: Optional[float] = Field(None, ge=0, description="Maximum unserved energy per step (MW).")
    shortfall_cost: Optional[float] = Field(None, ge=0, description="Cost of unserved energy ($/MWh).")
    wastage_capacity: Optional[float] = Field(None, ge=0, description="Maximum dumped surplus per step (MW).")
    wastage_cost: Optional[float] = Field(None, ge=0, description="Cost of dumping surplus energy ($/MWh).")


class LinkParams(ComponentParams):
    """A directed edge between two regions. Holds transmission lines."""


class ProducerParams(ExpansionParams):
    """A generator: thermal, hydro, wind, solar or any other source of energy."""

    installed_capacity: float = Field(0.0, ge=0, description="Existing capacity (MW).")
    operating_cost: float = Field(0.0, description="Variable cost of production ($/MWh).")
    profile: Optional[Any] = Field(
        None, description="Per-unit availability by time step. Omit for 1.0 in every step."
    )
    capacity_factor: float = Field(
        1.0, ge=0, le=1, description="Multiplies the profile; with no profile it is a flat availability."
    )
    dispatchable: bool = Field(
        True, description="False fixes output at availability (must-take or must-run)."
    )
    min_output: float = Field(
        0.0, ge=0, le=1, description="Minimum output as a fraction of capacity in every step."
    )
    ramp_rate: Optional[float] = Field(
        None, gt=0, description="Maximum change in output per hour as a fraction of capacity."
    )
    energy_budget_window: Optional[int] = Field(
        None, ge=1,
        description=(
            "When set, the profile is an energy budget: output over each window of this many steps "
            "may not exceed the summed availability, and hourly output may reach full capacity."
        ),
    )
    capacity_credit: float = Field(
        1.0, ge=0, le=1, description="Fraction of capacity counted toward reserve margins."
    )

    @field_validator("profile", mode="before")
    @classmethod
    def check_profile(cls, value):

        return _as_profile(value)

    @model_validator(mode="after")
    def consistent(self):

        if self.energy_budget_window is not None:

            if not self.dispatchable:

                raise ValueError("energy_budget_window requires a dispatchable producer")

            if self.extensible:

                raise ValueError("energy_budget_window is not supported for expandable producers")

        elif self.profile is not None and np.any(self.profile * self.capacity_factor > 1 + 1e-9):

            raise ValueError(
                "profile x capacity_factor exceeds 1.0; per-unit availability cannot exceed "
                "capacity (use energy_budget_window for energy-budget profiles such as hydro)"
            )

        return self


class StoreParams(ExpansionParams):
    """Energy storage with separate power (MW) and energy (MWh) capacity."""

    LEGACY: ClassVar[Dict[str, str]] = {
        "production_rate": "Use installed_capacity (MW) with duration (h) or installed_energy (MWh). " + _MIGRATE,
        "consumption_rate": "Use installed_capacity (MW) with duration (h) or installed_energy (MWh). " + _MIGRATE,
        "efficiency": "Use charge_efficiency and discharge_efficiency (one-way). " + _MIGRATE,
        "initial": "Stores are cyclic by default; set cyclic=False and initial_soc (fraction) instead. " + _MIGRATE,
    }

    installed_capacity: float = Field(0.0, ge=0, description="Existing charge/discharge power (MW).")
    duration: Optional[float] = Field(
        None, gt=0, description="Hours of storage at full power; sets energy capacity of existing and new builds."
    )
    installed_energy: Optional[float] = Field(
        None, ge=0, description="Existing energy capacity (MWh); overrides installed_capacity x duration."
    )
    charge_efficiency: float = Field(1.0, gt=0, le=1, description="One-way charging efficiency.")
    discharge_efficiency: float = Field(1.0, gt=0, le=1, description="One-way discharging efficiency.")
    operating_cost: float = Field(0.0, description="Variable cost per MWh discharged ($/MWh).")
    energy_capex_cost: float = Field(
        0.0, ge=0, description="Overnight cost of new energy capacity ($/MWh), added to capex_cost."
    )
    cyclic: bool = Field(True, description="State of charge at the end of the horizon wraps to the start.")
    initial_soc: float = Field(
        0.0, ge=0, le=1, description="Starting state of charge as a fraction of energy capacity (cyclic=False only)."
    )
    capacity_credit: float = Field(1.0, ge=0, le=1, description="Fraction of power capacity counted toward reserve margins.")

    @model_validator(mode="after")
    def energy_defined(self):

        if self.installed_energy is None and self.duration is None and (self.installed_capacity > 0 or self.extensible):

            raise ValueError("stores need a duration (h) or an installed_energy (MWh)")

        if self.extensible and self.duration is None:

            raise ValueError("expandable stores need a duration (h) for new builds")

        return self

    @property
    def energy_capacity(self):

        if self.installed_energy is not None:

            return self.installed_energy

        return self.installed_capacity * (self.duration or 0.0)


class LoadParams(ComponentParams):
    """Electricity demand, optionally with a flexible (deferrable) part."""

    LEGACY: ClassVar[Dict[str, str]] = {
        "shift_capacity": "Load shifting is now flexible demand: use flex_capacity (MW) and flex_max_delay (h). " + _MIGRATE,
        "shift_window": "Load shifting is now flexible demand: use flex_max_delay and flex_max_advance (h). " + _MIGRATE,
        "capex_capacity": "Loads are demand only and cannot be expanded; model generation as a Producer. " + _MIGRATE,
        "capex_cost": "Loads are demand only and cannot be expanded; model generation as a Producer. " + _MIGRATE,
    }

    installed_capacity: float = Field(0.0, description="Demand scale (MW); the profile multiplies it.")
    profile: Optional[Any] = Field(None, description="Per-unit demand by time step. Omit for constant demand.")
    flex_capacity: float = Field(
        0.0, ge=0, description="Maximum demand that can be deferred or made up in one step (MW)."
    )
    flex_max_delay: Optional[float] = Field(
        None, gt=0, description="Deferred demand must be served within this many hours."
    )
    flex_max_advance: Optional[float] = Field(
        None, gt=0, description="Demand served early must be due within this many hours."
    )
    flex_efficiency: float = Field(
        1.0, gt=0, le=1, description="Energy served per unit deferred; below 1 means shifting costs energy."
    )
    flex_cost: float = Field(0.0, ge=0, description="Cost per MWh of deferred demand ($/MWh).")

    @field_validator("profile", mode="before")
    @classmethod
    def check_profile(cls, value):

        return _as_profile(value)

    @field_validator("installed_capacity")
    @classmethod
    def positive_demand(cls, value):

        if value < 0:

            raise ValueError(
                f"installed_capacity is {value}. Since GOOD 2.0 loads take positive MW of demand; "
                "flip the sign, or model generation as a Producer. " + _MIGRATE
            )

        return value

    @property
    def flexible(self):

        return self.flex_capacity > 0


class TransmissionParams(ExpansionParams):
    """A directed transmission line from the edge's source to its target."""

    installed_capacity: float = Field(0.0, ge=0, description="Existing transfer capability (MW).")
    efficiency: float = Field(1.0, gt=0, le=1, description="Share of sent energy that arrives.")
    operating_cost: float = Field(0.0, description="Wheeling cost per MWh sent ($/MWh).")
    corridor: Optional[str] = Field(
        None,
        description=(
            "Lines with the same corridor share one expansion decision, so the two directions "
            "of a path are expanded and paid for once."
        ),
    )


class PolicyParams(ComponentParams):
    """Fields shared by policies."""

    non_compliance_capacity: float = Field(0.0, ge=0, description="Largest allowed shortfall against the policy.")
    non_compliance_cost: float = Field(0.0, ge=0, description="Cost per unit of shortfall.")


class PortfolioStandardParams(PolicyParams):
    """Share of generation that must come from the included assets."""

    LEGACY: ClassVar[Dict[str, str]] = {
        "inclusion_criteria": "Use 'include' with an attribute filter. Convert v1 files with good.migrate.convert_policies().",
        "exclusion_criteria": "Use 'exclude' with an attribute filter. Convert v1 files with good.migrate.convert_policies().",
    }

    ratio: float = Field(..., ge=0, le=1, description="Required share of included generation.")
    include: Dict[str, Any] = Field(default_factory=dict, description="Filter for qualifying assets.")
    exclude: Optional[Dict[str, Any]] = Field(
        None, description="Filter for the other assets in the denominator."
    )


class CapacityTargetParams(PolicyParams):
    """Minimum total capacity of the included assets."""

    LEGACY: ClassVar[Dict[str, str]] = {
        "inclusion_criteria": "Use 'include' with an attribute filter. Convert v1 files with good.migrate.convert_policies().",
    }

    target: float = Field(..., ge=0, description="Minimum capacity (MW).")
    include: Dict[str, Any] = Field(default_factory=dict, description="Filter for qualifying assets.")


class ReserveMarginParams(PolicyParams):
    """Credited capacity must exceed demand by a margin in every step."""

    LEGACY: ClassVar[Dict[str, str]] = {
        "sign": "Loads are positive since GOOD 2.0, so no sign flip is needed. " + _MIGRATE,
        "demand_criteria": "Use 'demand' with an attribute filter. Convert v1 files with good.migrate.convert_policies().",
        "supply_criteria": "Use 'supply' with an attribute filter. Convert v1 files with good.migrate.convert_policies().",
    }

    margin: float = Field(..., ge=0, description="Required margin above demand (0.15 for 15%).")
    demand: Dict[str, Any] = Field(default_factory=lambda: {"_class": "Load"}, description="Filter for loads.")
    supply: Dict[str, Any] = Field(
        default_factory=lambda: {"_class": {"not": "Load"}}, description="Filter for credited assets."
    )


def json_schema():
    """JSON Schema for every component model, keyed by class name."""

    models = {
        "Region": RegionParams,
        "Link": LinkParams,
        "Producer": ProducerParams,
        "Store": StoreParams,
        "Load": LoadParams,
        "Transmission": TransmissionParams,
        "Portfolio_Standard": PortfolioStandardParams,
        "Capacity_Target": CapacityTargetParams,
        "Reserve_Margin": ReserveMarginParams,
    }

    return {name: model.model_json_schema() for name, model in models.items()}


def field_table(model):
    """Rows of (field, default, description) for documentation."""

    rows = []

    for name, field in model.model_fields.items():

        default = field.default

        if default is not None and not isinstance(default, (int, float, bool, str)):

            default = "…"

        if isinstance(default, float) and math.isinf(default):

            default = "inf"

        rows.append((name, "required" if field.is_required() else default, field.description or ""))

    return rows
