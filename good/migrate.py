'''
Convert GOOD 1.x graphs and policy files to GOOD 2.0.

GOOD 1.x stored quantities in SI units (W, J, $/J, seconds) and had several
data problems. :func:`from_v1` converts units and fixes the data;
:func:`convert_policies` rewrites lambda-string policy criteria as
declarative filters. Every value the conversion *introduces* comes from
:data:`ASSUMPTIONS`, which names its source; edit it (or pass your own copy)
to change them. The notes of each conversion are stored in
``graph.graph["migration_notes"]``.

What changes
------------
* Units: W to MW, J to MWh, $/J to $/MWh, $/W to $/MW; loads become positive MW.
* Wind and solar become curtailable ``Producer`` assets (they were ``Load``).
* Wind profiles with 25 values per day (the IPM "Day Of Month" column read
  as an hour) are repaired to 24 values per day.
* Hydro profiles are monthly generation indices normalized to their lowest
  month. They become per-unit shapes with mean 1, used as a daily energy
  budget scaled by each plant's capacity factor.
* Profile references that miss only by a trailing ":" are matched; other
  missing references are dropped (the asset then uses its capacity factor).
* Wind and solar capital costs were IPM $/kW values divided by 1e6 instead of
  1e3; they are rescaled and given IPM fixed O&M and capital charge rates.
* Stores get power and energy capacity, efficiencies and, for new batteries,
  IPM cost assumptions.
* Transmission lines get IPM inter-regional losses and shared corridors.
'''

import re
from copy import deepcopy

import numpy as np

from .economics import capital_recovery_factor, implied_discount_rate

W_PER_MW = 1e6
J_PER_MWH = 3.6e9
BTU_PER_KWH_PER_UNIT = 3412.14  # heat rate: J/J to Btu/kWh

_IPM_RENEWABLE_CCR = 0.0978  # EPA Platform v6 Table 10-9, blended real rate, wind/solar/geothermal, 2023
_IPM_REAL_RATE = implied_discount_rate(_IPM_RENEWABLE_CCR, 20)  # 20-year book life, Table 10-12

ASSUMPTIONS = {
    "vre_capex_rescale": {
        "value": 1e3 * W_PER_MW,
        "source": "v1 wind/solar capex_cost equals EPA Platform v6 base capital cost (Table 4-16, "
                  "2023 vintage) plus regional adder (Tables 4-40, 4-44) in $/kW divided by 1e6; "
                  "multiplying by 1e9 gives $/MW.",
    },
    "solar": {
        "fom_cost": 10_740.0,
        "capital_charge_rate": _IPM_RENEWABLE_CCR,
        "capacity_credit": 0.10,
        "source": "FOM: EPA Platform v6 Table 4-16, solar PV 2023 vintage, $10.74/kW-yr. Charge rate: "
                  "Table 10-9. Capacity credit: PLACEHOLDER; IPM Table 4-32 gives 0-90% ranges by "
                  "resource class that fall with penetration.",
    },
    "wind": {
        "fom_cost": 48_720.0,
        "capital_charge_rate": _IPM_RENEWABLE_CCR,
        "capacity_credit": 0.15,
        "source": "FOM: EPA Platform v6 Table 4-16, onshore wind 2023 vintage, $48.72/kW-yr. Charge "
                  "rate: Table 10-9. Capacity credit: PLACEHOLDER; IPM Table 4-21 gives 0-90% ranges "
                  "by TRG that fall with penetration.",
    },
    "battery_new": {
        "capex_cost": 1_977_000.0,
        "fom_cost": 35_000.0,
        "operating_cost": 7.1,
        "duration": 4.0,
        "round_trip_efficiency": 0.85,
        "lifetime": 15.0,
        "discount_rate": _IPM_REAL_RATE,
        "capacity_credit": 1.0,
        "source": "EPA Platform v6 Table 4-35 (AEO 2018): $1,977/kW (2023, 4-hour, 2016$), FOM "
                  "$35/kW-yr, VOM $7.1/MWh, 85% efficiency, 100% reserve margin contribution. "
                  "Lifetime 15 years is an ASSUMPTION; the discount rate is the real rate implied by "
                  "IPM's 9.78% charge rate over 20 years.",
    },
    "battery_existing": {
        "duration": 4.0,
        "round_trip_efficiency": 0.85,
        "capacity_credit": 1.0,
        "source": "Same performance as new batteries (EPA Platform v6 Table 4-35). Duration of "
                  "existing batteries is an ASSUMPTION; many pre-2022 batteries are 1-2 hours.",
    },
    "pumped_hydro_existing": {
        "duration": 10.0,
        "round_trip_efficiency": 0.80,
        "capacity_credit": 1.0,
        "source": "PLACEHOLDER values; replace with plant-level energy capacity where available.",
    },
    "hydro": {
        "energy_budget_window": 24,
        "source": "Monthly hydro index becomes a daily energy budget: each plant may generate "
                  "capacity_factor x shape x capacity per day and up to full capacity in any hour.",
    },
    "transmission_loss": {
        "WECC": 0.028,
        "other": 0.024,
        "source": "EPA Platform v6 section 3.3.4: 2.8% inter-regional losses in WECC, 2.4% in "
                  "ERCOT and the Eastern Interconnection.",
    },
}

_EMISSION_KEYS = ("nox", "so2", "co2", "ch4", "n2o", "pm")


# ---------------------------------------------------------------------------- policies

_LAMBDA = re.compile(
    r"""^\s*lambda\s+(?P<arg>\w+)\s*:\s*(?P<neg>not\s+)?(?P=arg)\.get\(\s*['"](?P<key>\w+)['"]"""
    r"""(?:\s*,\s*[^)]*)?\)\s*(?:(?P<op>==|!=)\s*(?P<val>'[^']*'|"[^"]*"|True|False|-?\d+(?:\.\d+)?))?\s*$"""
)


def _literal(text):

    if text in ("True", "False"):

        return text == "True"

    if text[0] in "'\"":

        return text[1:-1]

    return float(text) if "." in text else int(text)


def lambda_to_filter(text):
    '''
    Translate one v1 lambda criterion into a (key, condition) pair.

    Handles the forms used in the v1 example files, such as
    ``lambda a: a.get('renewable', False)``,
    ``lambda a: not a.get('renewable', False)`` and
    ``lambda a: a.get('jurisdiction', '') == 'CA'``. The text is parsed, never
    executed; anything else raises ``ValueError``.
    '''

    match = _LAMBDA.match(text)

    if not match:

        raise ValueError(f"Cannot translate policy criterion {text!r}; rewrite it as a filter by hand.")

    key, op, value, negated = match["key"], match["op"], match["val"], bool(match["neg"])

    if op is None:

        return key, ({"not": True} if negated else True)

    if negated:

        raise ValueError(f"Cannot translate policy criterion {text!r}; rewrite it as a filter by hand.")

    value = _literal(value)

    return key, (value if op == "==" else {"not": value})


def criteria_to_filter(criteria):
    '''Combine a v1 dict (or list) of lambda strings into one filter dictionary.'''

    items = criteria.values() if isinstance(criteria, dict) else criteria
    spec = {}

    for text in items:

        key, condition = lambda_to_filter(text)

        if key in spec and spec[key] != condition:

            raise ValueError(f"Criteria put two different conditions on {key!r}; combine them by hand.")

        spec[key] = condition

    return spec


def convert_policies(policies):
    '''Return a GOOD 2.0 copy of a v1 policy dictionary.'''

    renames = {
        "inclusion_criteria": "include",
        "exclusion_criteria": "exclude",
        "demand_criteria": "demand",
        "supply_criteria": "supply",
    }

    converted = {}

    for handle, policy in deepcopy(policies).items():

        for old, new in renames.items():

            if old in policy:

                policy[new] = criteria_to_filter(policy.pop(old))

        policy.pop("sign", None)
        policy.pop("assets", None)

        converted[handle] = policy

    return converted


# ---------------------------------------------------------------------------- profiles

def repair_25_hour_days(profile):
    '''
    Drop the day-of-month column from a 365 x 25 profile.

    The v1 pipeline read IPM Table 4-39's "Day Of Month" column as a 25th hourly
    value (day / 1000). Raises ``ValueError`` if the first value of each day is
    not the day of the month divided by 1000.
    '''

    values = np.asarray(profile, dtype=float)

    if values.size != 365 * 25:

        raise ValueError(f"expected 9125 values, got {values.size}")

    days = values.reshape(365, 25)
    month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    day_of_month = np.concatenate([np.arange(1, n + 1) for n in month_lengths])

    if not np.allclose(days[:, 0], day_of_month / 1000, atol=1e-9):

        raise ValueError("first value of each day is not the day of month / 1000; not repairing")

    return days[:, 1:].ravel()


def hydro_shape(profile, hours=8760):
    '''
    Per-unit monthly shape with mean 1 from a v1 hydro index (lowest month = 1).
    Pads a missing final hour by repeating the last value.
    '''

    values = np.asarray(profile, dtype=float)

    if values.size < hours:

        values = np.concatenate([values, np.full(hours - values.size, values[-1])])

    values = values[:hours]

    return values / values.mean()


def _pad(profile, hours=8760):

    values = np.asarray(profile, dtype=float)

    if values.size == hours - 1:

        return np.concatenate([values, values[-1:]])

    return values


# ---------------------------------------------------------------------------- assets

def _interconnect(region):

    return "WECC" if str(region).startswith("WEC") else "other"


def _common(asset):
    '''Unit conversions that apply to every asset.'''

    out = dict(asset)

    for key in _EMISSION_KEYS:

        if key in out and out[key] is not None:

            out[key] = float(out[key]) * J_PER_MWH  # kg/J -> kg/MWh

    if "heat_rate" in out and out["heat_rate"] is not None:

        out["heat_rate"] = float(out["heat_rate"]) * BTU_PER_KWH_PER_UNIT  # J/J -> Btu/kWh

    if "operating_cost" in out:

        out["operating_cost"] = float(out["operating_cost"]) * J_PER_MWH  # $/J -> $/MWh

    out.pop("extensible", None)

    return out


def _producer(asset, a):

    out = _common(asset)
    out["installed_capacity"] = float(asset.get("installed_capacity", 0)) / W_PER_MW

    capex_capacity = float(asset.get("capex_capacity", 0) or 0)
    out["capex_capacity"] = capex_capacity / W_PER_MW if np.isfinite(capex_capacity) else np.inf
    out["capex_cost"] = float(asset.get("capex_cost", 0) or 0) * W_PER_MW

    return out


def _vre(asset, a, notes):

    kind = asset.get("type")
    out = _producer(asset, a)
    out["_class"] = "Producer"
    out["dispatchable"] = True  # curtailable
    out["capex_cost"] = float(asset.get("capex_cost", 0) or 0) * a["vre_capex_rescale"]["value"]

    for key in ("capacity_credit",):

        out[key] = a[kind][key]

    if out.get("capex_capacity", 0) > 0:

        out["fom_cost"] = a[kind]["fom_cost"]
        out["capital_charge_rate"] = a[kind]["capital_charge_rate"]

    notes["vre_to_producer"] = notes.get("vre_to_producer", 0) + 1

    return out


def _store(asset, a):

    out = _common(asset)

    for key in ("production_rate", "consumption_rate", "efficiency", "initial", "profile"):

        out.pop(key, None)

    power = float(asset.get("installed_capacity", 0) or 0) / W_PER_MW
    expandable = float(asset.get("capex_capacity", 0) or 0) > 0

    if expandable:

        spec = a["battery_new"]
        out.update(
            installed_capacity=power,
            capex_capacity=np.inf,
            capex_cost=spec["capex_cost"],
            fom_cost=spec["fom_cost"],
            operating_cost=spec["operating_cost"],
            duration=spec["duration"],
            lifetime=spec["lifetime"],
            discount_rate=spec["discount_rate"],
            capacity_credit=spec["capacity_credit"],
        )

    else:

        pumped = "pump" in str(asset.get("fuel", "")).lower()
        spec = a["pumped_hydro_existing" if pumped else "battery_existing"]
        out.update(
            installed_capacity=power,
            duration=spec["duration"],
            capacity_credit=spec["capacity_credit"],
            capex_capacity=0.0,
            capex_cost=0.0,
        )

    one_way = float(np.sqrt(spec["round_trip_efficiency"]))
    out["charge_efficiency"] = one_way
    out["discharge_efficiency"] = one_way
    out["_class"] = "Store"

    return out


def _load(asset):

    out = dict(asset)

    for key in ("capex_capacity", "capex_cost", "shift_capacity", "shift_window", "extensible", "operating_cost"):

        out.pop(key, None)

    out["installed_capacity"] = abs(float(asset.get("installed_capacity", 0))) / W_PER_MW

    return out


def _line(line, source, a):

    out = dict(line)
    out.pop("extensible", None)
    out["installed_capacity"] = float(line.get("installed_capacity", 0)) / W_PER_MW
    out["operating_cost"] = float(line.get("operating_cost", 0) or 0) * J_PER_MWH

    capex_capacity = float(line.get("capex_capacity", 0) or 0)
    out["capex_capacity"] = capex_capacity / W_PER_MW if np.isfinite(capex_capacity) else np.inf
    out["capex_cost"] = float(line.get("capex_cost", 0) or 0) * W_PER_MW

    if "efficiency" not in line:

        out["efficiency"] = 1.0 - a["transmission_loss"][_interconnect(source)]

    return out


def from_v1(graph, assumptions=None):
    '''
    Return a GOOD 2.0 copy of a GOOD 1.x graph. See the module docstring for
    what changes. ``assumptions`` defaults to :data:`ASSUMPTIONS`.
    '''

    a = deepcopy(ASSUMPTIONS if assumptions is None else assumptions)
    graph = deepcopy(graph)
    notes = {}

    for source, node in graph._node.items():

        profiles = node.get("profiles", {}) or {}

        for key, values in list(profiles.items()):

            if len(values) == 365 * 25:

                profiles[key] = repair_25_hour_days(values).tolist()
                notes["wind_profiles_repaired"] = notes.get("wind_profiles_repaired", 0) + 1

            elif key.endswith(":hydro"):

                profiles[key] = hydro_shape(values).tolist()
                notes["hydro_profiles_normalized"] = notes.get("hydro_profiles_normalized", 0) + 1

            else:

                profiles[key] = _pad(values).tolist()

        assets = {}

        for handle, asset in (node.get("assets", {}) or {}).items():

            reference = asset.get("profile")

            if isinstance(reference, str) and reference not in profiles:

                if reference.rstrip(":") in profiles:

                    asset = {**asset, "profile": reference.rstrip(":")}
                    notes["profile_keys_fixed"] = notes.get("profile_keys_fixed", 0) + 1

                else:

                    asset = {**asset, "profile": None}
                    notes["missing_profiles_dropped"] = notes.get("missing_profiles_dropped", 0) + 1

            _class = asset.get("_class")
            kind = asset.get("type")

            if _class == "Load" and kind in ("solar", "wind"):

                converted = _vre(asset, a, notes)

            elif _class == "Load":

                converted = _load(asset)

            elif _class == "Store":

                converted = _store(asset, a)

            else:

                converted = _producer(asset, a)

                if kind == "hydro" and converted.get("profile"):

                    converted["energy_budget_window"] = a["hydro"]["energy_budget_window"]

            assets[handle] = converted

        node["assets"] = assets

    pairs = set(graph.edges)

    for source, target, edge in graph.edges(data=True):

        corridor = "|".join(sorted((str(source), str(target)))) if (target, source) in pairs else None

        lines = {}

        for handle, line in (edge.get("lines", {}) or {}).items():

            converted = _line(line, source, a)

            if corridor is not None:

                converted.setdefault("corridor", corridor)

            lines[handle] = converted

        edge["lines"] = lines

    graph.graph["good_format"] = 2
    graph.graph["migration_notes"] = notes
    graph.graph["migration_assumptions"] = {k: v.get("source", "") for k, v in a.items()}

    return graph


def is_v1(graph):
    '''Heuristic: True when a graph looks like GOOD 1.x input.'''

    if graph.graph.get("good_format") == 2:

        return False

    for _, node in graph.nodes(data=True):

        for asset in (node.get("assets", {}) or {}).values():

            if asset.get("_class") == "Load" and float(asset.get("installed_capacity", 0) or 0) < 0:

                return True

            if float(asset.get("installed_capacity", 0) or 0) > 1e5:  # watts

                return True

    return False
