# Changelog

## 2.0.0

A rebuild of the model core following the September 2026 model review.
Inputs written for 1.x are rejected with messages naming their replacements;
`good.migrate` converts 1.x graphs and policy files. See
`docs/migration.md`. Review item numbers are in brackets.

### Fixed

* `import good` failed on the default branch because the `Visualization`
  folder did not match the import; it is now `good/visualization` and loads
  on first use [B1].
* Class lookup depended on `deep_reload(good)`; classes now register
  themselves when defined, and subclasses of subclasses work [B2].
* Asset aggregation crashed under NumPy 2 (`np.product`) [B3].
* The test suite targeted an API that no longer existed; it is rewritten and
  runs in CI [B4].
* Storage used one number as both energy and power capacity, had no losses,
  and started and ended empty. Stores now have power (MW) and energy (MWh)
  capacity, charge and discharge efficiencies, fixed-duration expansion that
  pays for both, and cyclic state of charge [F1, F8].
* Load shifting left the last step unconstrained, mixed J and W, measured
  windows in steps while the example passed seconds, and was not tied to the
  load. It is replaced by flexible demand following GenX, with cyclic
  pay-back and maximum delay and advance in hours [F2].
* Wind and solar were loads that could not be curtailed; they are producers
  with profiles [F3].
* The reserve margin counted every non-storage asset at nameplate; assets now
  count `capacity_credit × capacity`, and storage can count [F4].
* Capital costs were recovered in a single year; they are annualized with a
  capital charge rate or a discount rate and lifetime, plus fixed O&M [F5].
* Loads now take positive MW; negative values are rejected, so the example's
  EV "load" can no longer act as a generator [F6].
* `dispatchable=False` is honored (must-take or must-run), `min_output` sets a
  floor, and ramp limits are applied only where they can bind [F7].
* Opposite directions of a path can share one expansion decision (`corridor`)
  and pay once [F9].
* Clearing prices come from the balance constraint's dual by region, not by
  matching constraint names; every region gets a price.
* Line costs are counted once, by the line, instead of by cancellation between
  regions and edges.
* Removed broken modules (`policies/generic.py`, `policies/rps.py`), an
  undefined name in `Network.add_line`, a debug print and the Linux-only `cbc`
  binary.

### Data (example graphs)

* Wind profiles had 25 values per day because IPM's "Day Of Month" column was
  read as an hour; repaired [D1].
* Hydro profiles were never used (key mismatch) and were monthly indices, not
  per-unit values; they are now daily energy budgets [D2].
* Storage records gained durations, efficiencies and IPM battery costs [D3].
* Aggregation merged wind and solar with different profiles and could merge
  plants across states; groups now keep profiles and jurisdictions apart, and
  costs combine as capacity-weighted means [D4].
* Wind and solar capital costs were $/kW divided by 1e6; rescaled to $/MW
  with IPM fixed O&M and capital charge rates [D5].
* Transmission lines carry IPM inter-regional losses.
* Example data is stored as gzip-compressed JSON (4.5 MB instead of about
  100 MB). Assumptions and sources are listed in `docs/assumptions.md`.

### Changed

* Units are MW, MWh, hours and $ throughout (formerly W, J, s and $/J), which
  keeps the LP well scaled [efficiency 1].
* The model is built with linopy, vectorized by component class; Pyomo is no
  longer used. Fixed limits are variable bounds instead of constraints
  [efficiency 2, 3].
* HiGHS is the default solver and is installed with GOOD [efficiency 4].
* Aggregation uses k-means within groups instead of a pairwise similarity
  graph; `aggregate(graph, ratio=0.1)` replaces the `clustering` argument
  [efficiency 6].
* Policy criteria are declarative filters instead of lambda strings run with
  `eval`.
* Every input is validated against `good/schema.py`; all problems are reported
  together.
* Network defaults: unserved energy and surplus are allowed without limit at
  $10,000/MWh; the discount rate is 7%.
* Solutions: storage reports `charge`, `discharge`, `soc`, `new_capacity` and
  `new_energy`; loads report `demand`, `consumption` and flexible-demand
  results; producers and lines report `new_capacity` (formerly `capex`).

### Added

* `good.migrate` to convert 1.x graphs and policies, with documented assumptions.
* `Producer.energy_budget_window`, `Producer.min_output`, `capacity_credit`.
* MkDocs documentation (`docs/`), a two-region quickstart example, a LICENSE
  (BSD 3-Clause), `CITATION.cff`, this changelog and GitHub Actions CI.

## 1.1.3

Last release before the rebuild (3 November 2025).
