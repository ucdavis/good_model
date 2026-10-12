"""Time building and solving an example graph.

    python scripts/benchmark.py examples/data/California.json.gz 72 168 720
"""

import sys
import time

import good


def run(path, hours, start=4608, policies="examples/data/policies.json"):

    graph = good.graph.graph_from_json(path)
    rules = good.utilities.read_json(policies)

    t0 = time.time()
    network = good.Network(steps=(start, start + hours)).from_graph(graph, rules)
    network.build()
    t1 = time.time()
    network.solve()
    t2 = time.time()
    network.solution_graph()
    t3 = time.time()

    size = network.size()

    print(
        f"{hours:>5} h | {size['variables']:>9,} vars {size['constraints']:>9,} cons | "
        f"build {t1 - t0:6.1f} s | solve {t2 - t1:6.1f} s | results {t3 - t2:5.1f} s | "
        f"objective {network.objective_value:,.0f}"
    )


if __name__ == "__main__":

    path, *hours = sys.argv[1:]

    for h in hours:

        run(path, int(h), start=0 if int(h) > 8760 - 4608 else 4608)
