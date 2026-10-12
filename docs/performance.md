# Performance

## Measured run times

California example (6 regions, 1,091 assets, state RPS policies, wind, solar,
battery and transmission expansion), starting at hour 4,608. HiGHS 1.15,
linopy 0.7, on a laptop with an Apple-silicon CPU.
`python scripts/benchmark.py examples/data/California.json.gz 24 72 168 720`
reproduces the first rows.

| Window | Assets | Variables | Constraints | Build | Solve |
|---|---|---|---|---|---|
| 24 h | 1,091 | 28,563 | 6,248 | 1.0 s | 0.6 s |
| 72 h | 1,091 | 83,139 | 16,538 | 1.0 s | 1.9 s |
| 168 h | 1,091 | 192,291 | 37,118 | 1.0 s | 6.3 s |
| 720 h | 1,091 | 819,915 | 155,453 | 1.2 s | 117 s |
| 168 h | 263 (aggregated) | 52,359 | 34,757 | 0.8 s | 2.0 s |
| 720 h | 263 (aggregated) | 222,927 | 148,055 | 0.8 s | 57 s |

The 720-hour run peaked at 2.3 GB of memory. Building no longer grows with
the window, because each class adds its variables for all instances and hours
at once. Where capacity is fixed, output limits are variable bounds instead of
constraints.

For comparison, GOOD 1.1.3 took 12 s to build the 720-hour model. HiGHS did
not finish solving it after 18 minutes in 1.x units, and it reported a 2,190-hour
run as having no feasible solution because of numerical trouble.

## What makes a run slow

Runs without binding policies are fast: the aggregated 720-hour California
model solves in about 3 seconds without its policies, against 57 seconds with them. Run time grows sharply when **a binding portfolio
standard is combined with wind and solar expansion**. The solver must then
trade building renewables against curtailing them across hundreds of candidate
sites and every hour, and the LP becomes highly degenerate. That is inherent
to the problem, not to GOOD: GenX and PyPSA models with the same features
have the same structure. GOOD 1.x solved this case faster only because wind
and solar could not be curtailed.

HiGHS's interior-point method (`options={"solver": "ipm"}`) and PDLP were not
faster than the default dual simplex on these models.

## Ways to shorten runs

Choosing how to trade detail for speed is left to the modeler. In order of
effect:

1. **Aggregate assets.** `good.aggregate.aggregate(graph, ratio=0.1)` halved
   the 720-hour solve and tripled the speed of the 168-hour one for a 1.8%
   change in cost. See [Aggregation](aggregation.md).
2. **Model less time, or representative time.** A week solves in seconds. For
   capacity expansion, research on long-duration storage suggests reducing
   temporal detail last: a few representative weeks with linked storage keep
   more accuracy than fewer regions over a full year. GOOD takes any window
   through `steps`; building representative periods is up to the user.
3. **Use a commercial solver** if one is available (`network.solve("gurobi")`).
   Commercial barrier solvers are usually much faster on large degenerate LPs.
4. **Cap solve time** with `network.solve(options={"time_limit": 600})`.

## Keep the units

Inputs in MW, MWh and $/MWh keep the LP's coefficients within a few orders of
magnitude. A value of order 1e-6 or 1e9 in an input usually means a unit slip,
and it can stall the solver.

## Decomposition

Benders decomposition (for example Pecci and Jenkins, IEEE TPWRS 2025) splits
a capacity expansion problem into an investment problem and independent
operating sub-problems. It pays off for mixed-integer models (unit
commitment, lumpy builds) and for national, multi-year or multi-weather-year
runs that no single solve can handle. GOOD 2.0 is a pure LP at regional
scale, where a monolithic solve is simpler and fast enough, so it has no
decomposition.
