"""Investment cost annualization.

GOOD charges new capacity an annualized cost, scaled by the fraction of a
year the model covers:

    cost = new_capacity * (capex_cost * capital_charge_rate + fom_cost) * year_fraction

``capital_charge_rate`` is either given directly (for example EPA IPM's real
capital charge rates) or computed from a real discount rate and a lifetime
with the capital recovery factor below.
"""

HOURS_PER_YEAR = 8760.0


def capital_recovery_factor(discount_rate, lifetime):
    """Annual payment per unit of overnight cost.

    ``discount_rate`` is a fraction (0.07 for 7%) and ``lifetime`` is in years.
    """

    if lifetime is None or lifetime <= 0:
        raise ValueError(f"lifetime must be a positive number of years, got {lifetime!r}")

    if discount_rate is None or discount_rate < 0:
        raise ValueError(f"discount_rate must be a non-negative fraction, got {discount_rate!r}")

    if discount_rate == 0:
        return 1.0 / lifetime

    growth = (1.0 + discount_rate) ** lifetime

    return discount_rate * growth / (growth - 1.0)


def annualized_cost(capex_cost, fom_cost=0.0, lifetime=None, discount_rate=None,
                    capital_charge_rate=None):
    """Annual cost of one unit of new capacity ($/unit-yr).

    ``capex_cost`` is the overnight cost ($/MW or $/MWh), ``fom_cost`` the
    fixed O&M cost ($/MW-yr). Supply ``capital_charge_rate`` or both
    ``lifetime`` and ``discount_rate``.
    """

    if capex_cost == 0:
        return float(fom_cost)

    if capital_charge_rate is None:
        capital_charge_rate = capital_recovery_factor(discount_rate, lifetime)

    return float(capex_cost) * float(capital_charge_rate) + float(fom_cost)


def implied_discount_rate(capital_charge_rate, lifetime, tolerance=1e-10):
    """Discount rate at which the capital recovery factor equals ``capital_charge_rate``.

    Useful for applying a published capital charge rate (for example EPA
    IPM's) to a technology with a different lifetime.
    """

    if capital_charge_rate <= 1.0 / lifetime:

        return 0.0

    low, high = 0.0, 1.0

    while high - low > tolerance:

        middle = (low + high) / 2

        if capital_recovery_factor(middle, lifetime) < capital_charge_rate:

            low = middle

        else:

            high = middle

    return (low + high) / 2
