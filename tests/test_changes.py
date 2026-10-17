"""scripts/changes.sh: which CI steps a pull request's changed paths need.

The `check` job always runs (it is main's required status check), so this
decides how much of it does: a docs-only PR must not set up uv or node, and a
portal address alone gets only its validation.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def decide(*paths: str) -> dict[str, str]:
    out = subprocess.run(["bash", str(ROOT / "scripts" / "changes.sh")], input="".join(p + "\n" for p in paths),
                         capture_output=True, text=True, check=True).stdout
    return dict(line.split("=", 1) for line in out.splitlines())


NOTHING = {"python": "none", "web": "false", "locations": "false"}


@pytest.mark.parametrize("paths", [
    ("README.md",), ("LICENSE",), ("docs/notes.md", "README.md"), (".github/dependabot.yml",),
    ("mise-tasks/deploy", ".githooks/pre-push"),
])
def test_prose_and_tooling_need_nothing(paths) -> None:
    assert decide(*paths) == NOTHING


def test_a_portal_address_alone_needs_only_its_validation() -> None:
    assert decide("data/locations.json") == {**NOTHING, "locations": "true"}


def test_a_portal_address_with_code_runs_everything() -> None:
    assert decide("data/locations.json", "src/nms_items/portals.py") == {
        "python": "full", "web": "true", "locations": "true"}


def test_the_site_runs_its_slice() -> None:
    assert decide("site/App.svelte") == {**NOTHING, "python": "web", "web": "true"}


@pytest.mark.parametrize("path", [".github/workflows/ci.yml", "scripts/portal_issue.py", "data/items.json",
                                  "something/new.txt"])
def test_anything_else_runs_everything(path) -> None:
    assert decide(path) == {"python": "full", "web": "true", "locations": "false"}


def test_no_paths_need_nothing() -> None:
    assert decide() == NOTHING
