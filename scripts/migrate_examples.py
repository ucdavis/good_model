"""Rebuild examples/data from the GOOD 1.x example files.

The v1 files were removed from the working tree in 2.0 but remain in git
history. Extract them, then run this script:

    mkdir -p v1 && for f in California ERC WEC; do
        git show 3d9b666:Examples/$f.json > v1/$f.json; done
    git show 3d9b666:Examples/policies.json > v1/policies.json
    python scripts/migrate_examples.py v1 examples/data
"""

import json
import sys
from pathlib import Path

import numpy as np

import good


def rounded(graph, digits=4):
    """Round profiles to shrink the files; 1e-4 per-unit is far below data precision."""

    for _, node in graph.nodes(data=True):

        node["profiles"] = {
            key: np.round(np.asarray(values, dtype=float), digits).tolist()
            for key, values in (node.get("profiles") or {}).items()
        }

    return graph


def main(source, target):

    source, target = Path(source), Path(target)
    target.mkdir(parents=True, exist_ok=True)

    for name in ("California", "ERC", "WEC"):

        graph = good.graph.graph_from_json(source / f"{name}.json")
        migrated = rounded(good.migrate.from_v1(graph))

        good.graph.graph_to_json(migrated, target / f"{name}.json.gz")

        print(name, json.dumps(migrated.graph["migration_notes"]))

    policies = good.utilities.read_json(source / "policies.json")
    good.utilities.write_json(good.migrate.convert_policies(policies), target / "policies.json", indent=2)


if __name__ == "__main__":

    main(*sys.argv[1:3])
