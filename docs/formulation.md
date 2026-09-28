# Formulation

GOOD solves one linear program covering a window of time steps. This page
states it in full; each block names the class that builds it.

## Sets and indices

| Symbol | Meaning |
|---|---|
| \(r \in R\) | regions |
| \(t \in T\) | time steps in the window, each lasting \(\Delta t\) hours |
| \(p \in P,\ s \in S,\ l \in L\) | producers, stores, loads; \(P_r, S_r, L_r\) are those in region \(r\) |
| \(\lambda \in \Lambda\) | transmission lines; \(\Lambda^{in}_r, \Lambda^{out}_r\) end or start at \(r\) |
| \(k \in K\) | policies |
| \(X\) | assets and lines with `capex_capacity > 0` (expandable) |

A bar marks an input (\(\bar C_p\) is existing capacity); \(N\) is new
capacity, a decision for expandable components and zero otherwise.

## Objective

\[
\min\ \Delta t \sum_{t} \Big[ \sum_{p} c_p x_{p,t} + \sum_{s} c_s d_{s,t} + \sum_{l} c^{f}_l \pi_{l,t}
+ \sum_{\lambda} c_\lambda f_{\lambda,t} + \sum_{r} \big(c^{u}_r u_{r,t} + c^{w}_r w_{r,t}\big) \Big]
+ \phi \sum_{i \in X} A_i N_i + \sum_{k} c^{nc}_k z_k
\]

* \(c\) are variable costs ($/MWh): `operating_cost`, `flex_cost`,
  `shortfall_cost` (\(c^u\)) and `wastage_cost` (\(c^w\)).
* \(\phi = |T|\,\Delta t / 8760\) is the modeled fraction of a year.
* \(A_i = \text{capex}_i \cdot \text{CCR}_i + \text{FOM}_i\) is the annualized
  cost of a unit of new capacity. \(\text{CCR}_i\) is `capital_charge_rate`
  if given, otherwise the capital recovery factor
  \(\rho(1+\rho)^n / ((1+\rho)^n - 1)\) with discount rate \(\rho\) and
  lifetime \(n\) years. For a store, \(\text{capex}_i\) is
  `capex_cost + duration × energy_capex_cost`. Lines in one corridor share
  one \(N\) and pay \(A\) once.
* \(z_k\) is policy \(k\)'s non-compliance slack, priced at
  `non_compliance_cost`.

## Regional balance (`Region`)

For every region and step,

\[
\sum_{p \in P_r} x_{p,t} + \sum_{s \in S_r} (d_{s,t} - c_{s,t}) + \sum_{l \in L_r} (\pi_{l,t} - \theta_{l,t})
+ \sum_{\lambda \in \Lambda^{in}_r} \eta_\lambda f_{\lambda,t} - \sum_{\lambda \in \Lambda^{out}_r} f_{\lambda,t}
+ u_{r,t} - w_{r,t} = \sum_{l \in L_r} D_{l,t}
\]

with \(0 \le u_{r,t} \le \bar u_r\) (unserved energy) and
\(0 \le w_{r,t} \le \bar w_r\) (surplus that cannot be absorbed). The
clearing price is the constraint's dual divided by \(\Delta t\), in $/MWh.

## Producers (`Producer`)

Capacity \(C_p = \bar C_p + N_p\), \(0 \le N_p \le \bar N_p\).
Availability \(\alpha_{p,t}\) is `capacity_factor × profile`. The hourly
limit is \(h_{p,t} = \alpha_{p,t}\), or \(h_{p,t} = 1\) when the producer
has an `energy_budget_window`.

\[
m_{p,t}\, C_p \le x_{p,t} \le h_{p,t}\, C_p
\]

where \(m_{p,t} = \min(\text{min\_output}_p, h_{p,t})\), or
\(m_{p,t} = h_{p,t}\) when `dispatchable` is false (output fixed at
availability). For producers whose capacity is fixed these are variable
bounds; for expandable producers they are constraints.

Ramping, when `ramp_rate` \(\gamma_p\) satisfies \(\gamma_p \Delta t < 1\):

\[
|x_{p,t} - x_{p,t-1}| \le \gamma_p\, \Delta t\, C_p \qquad t > t_0
\]

Energy budget, for each window \(W\) of `energy_budget_window` steps
(aligned to step 0, so a window cut by the model's start or end gets a
pro-rated budget):

\[
\sum_{t \in W} x_{p,t} \le \sum_{t \in W} \alpha_{p,t}\, \bar C_p
\]

## Stores (`Store`)

Power \(P_s = \bar P_s + N_s\); energy \(E_s = \bar E_s + \delta_s N_s\), where
\(\bar E_s\) is `installed_energy` or `installed_capacity × duration` and
\(\delta_s\) is `duration`.

\[
0 \le c_{s,t} \le P_s, \qquad 0 \le d_{s,t} \le P_s, \qquad 0 \le e_{s,t} \le E_s
\]

\[
e_{s,t} = e_{s,t-1} + \big(\eta^{c}_s c_{s,t} - d_{s,t} / \eta^{d}_s\big)\Delta t
\]

For \(t = t_0\), \(e_{s,t-1}\) is \(e_{s,t_{end}}\) when the store is `cyclic`
(the default) and `initial_soc` \(\times E_s\) otherwise.

## Loads (`Load`)

Demand \(D_{l,t}\) is `installed_capacity × profile`. A load with
`flex_capacity` \(F_l > 0\) can defer demand (\(\pi\)) and serve deferred
demand later (\(\theta\)), following GenX's flexible-demand formulation:

\[
0 \le \pi_{l,t} \le \min(F_l, D_{l,t}), \qquad 0 \le \theta_{l,t} \le F_l / \eta_l
\]

\[
b_{l,t} = b_{l,t-1} + (\pi_{l,t} - \eta_l\, \theta_{l,t})\,\Delta t
\]

with the backlog \(b\) cyclic over the window, so all shifted demand is
served inside it. With `flex_max_delay` of \(k^d\) steps and
`flex_max_advance` of \(k^a\) steps (indices wrap around the window):

\[
\sum_{j=1}^{k^d} \theta_{l,t+j}\, \Delta t \ge b_{l,t}, \qquad
\sum_{j=1}^{k^a} \pi_{l,t+j}\, \Delta t \ge -b_{l,t}
\]

## Transmission (`Transmission`)

\[
0 \le f_{\lambda,t} \le \bar C_\lambda + N_{c(\lambda)}
\]

where \(c(\lambda)\) is the line's corridor. Energy \(f\) leaves the source
region and \(\eta_\lambda f\) arrives at the target.

## Policies

Totals of generation are taken over the window. For each asset
\(G_a = \Delta t \sum_t g_{a,t}\), where \(g\) is production for producers
and net discharge \(d - c\) for stores; an auxiliary variable holds each
\(G_a\) so that policy rows stay sparse.

**Portfolio standard** (`Portfolio_Standard`), with included set \(I\),
excluded set \(E\) and `ratio` \(\beta\):

\[
\sum_{a \in I} G_a + z_k \ge \beta \Big( \sum_{a \in I} G_a + \sum_{a \in E \setminus I} G_a \Big)
\]

**Capacity target** (`Capacity_Target`):

\[
\sum_{a \in I} C_a + z_k \ge \text{target}
\]

**Reserve margin** (`Reserve_Margin`), with supply set \(S\), demand set
\(D\), `margin` \(m\) and each asset's `capacity_credit` \(\kappa_a\):

\[
\sum_{a \in S} \kappa_a C_a + z_k \ge (1 + m)\, \max_t \sum_{l \in D} D_{l,t}
\]

Every slack is bounded, \(0 \le z_k \le\) `non_compliance_capacity`, which is
0 by default so policies hold strictly.

## What the model does not include

GOOD 2.0 has no unit commitment (start-ups, minimum up and down times),
operating reserves, DC power flow, investment periods or emissions limits.
`min_output` and `dispatchable=False` impose must-run behavior without
commitment decisions.
