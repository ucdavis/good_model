import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "generate_docs.py"


def test_generated_docs_are_current():
    """docs/inputs.md and docs/assumptions.md must match the code."""

    spec = importlib.util.spec_from_file_location("generate_docs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    stale = module.main(check=True)

    assert not stale, f"Run python scripts/generate_docs.py; stale pages: {stale}"
