"""Declarative asset filters used by policies.

A filter is a dictionary that maps an asset attribute to a condition. An asset
matches when every condition holds:

    {"renewable": True}                     equal to a value
    {"jurisdiction": ["CA", "NV"]}          one of several values
    {"_class": {"not": "Store"}}            not equal (value or list of values)
    {"installed_capacity": {">=": 50}}      comparison: ">", ">=", "<", "<="

An asset that lacks the attribute fails every condition except "not". An empty
filter matches every asset.

Filters replace the lambda strings used before GOOD 2.0, which were run with
``eval``. ``good.migrate.convert_policies`` translates the lambda patterns used
in the example policy files.
"""

import operator

from .exceptions import GOOD_LegacyInput

_COMPARISONS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}

_MISSING = object()


def _check_legacy(spec):

    for value in spec.values():

        if isinstance(value, str) and value.strip().startswith("lambda"):

            raise GOOD_LegacyInput(
                "Policy criteria are no longer Python lambda strings. Write them as "
                "attribute filters such as {'renewable': True, 'jurisdiction': 'CA'}, "
                "or convert v1 policy files with good.migrate.convert_policies()."
            )


def _condition_holds(value, condition):

    if isinstance(condition, dict):

        for op, target in condition.items():

            if op == "not":

                targets = target if isinstance(target, (list, tuple, set)) else [target]

                if value is not _MISSING and value in targets:

                    return False

            elif op in _COMPARISONS:

                if value is _MISSING or value is None:

                    return False

                if not _COMPARISONS[op](value, target):

                    return False

            else:

                raise ValueError(
                    f"Unknown filter operator {op!r}; use 'not', '>', '>=', '<' or '<='."
                )

        return True

    if value is _MISSING:

        return False

    if isinstance(condition, (list, tuple, set)):

        return value in condition

    return value == condition


def matches(attributes, spec):
    """True when the attribute dictionary satisfies every condition in ``spec``."""

    return all(
        _condition_holds(attributes.get(key, _MISSING), condition)
        for key, condition in (spec or {}).items()
    )


def select(assets, spec):
    """Handles of the assets whose attributes match ``spec``.

    ``assets`` maps handle to attribute dictionary.
    """

    spec = spec or {}

    _check_legacy(spec)

    return [handle for handle, attributes in assets.items() if matches(attributes, spec)]
