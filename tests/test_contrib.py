"""The contribution bot: the issue form, what it reads back, what it accepts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import portal_issue as bot  # noqa: E402
from nms_items.portals import KINDS, LocationBook  # noqa: E402


def form_fields() -> dict[str, str]:
    """id -> label for every input in the issue form, read without a YAML parser."""
    text = bot.FORM.read_text()
    ids = re.findall(r"^\s+id: (\S+)$", text, flags=re.M)
    labels = re.findall(r"^\s+label: (.+)$", text, flags=re.M)
    return dict(zip(ids, labels))


def body(**fields: str) -> str:
    """An issue body the way GitHub renders a submitted form."""
    labels = {v: k for k, v in bot.FIELDS.items()}
    return "\n\n".join(f"### {labels[key]}\n\n{value or '_No response_'}" for key, value in fields.items())


GOOD = dict(name="Test Prime", code="0123 4567 89AB", galaxy="1", kind="starship",
            detail="S-class hauler", where="", source="visited myself")


def test_the_form_and_the_parser_agree() -> None:
    form = form_fields()
    assert {bot.FIELDS[label]: label for label in bot.FIELDS} == form


def test_the_form_offers_exactly_the_kinds() -> None:
    text = bot.FORM.read_text()
    block = text.split("id: kind", 1)[1].split("validations", 1)[0]
    assert re.findall(r"^\s+- (\S+)$", block, flags=re.M) == KINDS


def test_a_good_issue_passes_and_says_what_it_read() -> None:
    loc, errors, _ = bot.check(bot.parse_form(body(**GOOD)), LocationBook.load())
    assert not errors and loc is not None
    assert (loc.code, loc.kind, loc.origin, loc.galaxy) == ("0123456789AB", "starship", "shared", 1)
    assert loc.where == ""
    text = bot.reply(loc, errors, [])
    assert "✓" in text and "nmsii.dlu.one/#/portals?code=0123456789AB" in text


def test_a_galactic_address_converts_with_a_warning() -> None:
    fields = bot.parse_form(body(**{**GOOD, "code": "0BBB:007E:07E5:0123"}))
    loc, errors, warnings = bot.check(fields, LocationBook.load())
    assert not errors and loc.code.startswith("0")
    assert any("planet" in w for w in warnings)


@pytest.mark.parametrize("change, complaint", [
    ({"code": "not glyphs"}, "Portal address"),
    ({"code": ""}, "Portal address"),
    ({"name": ""}, "Name"),
    ({"galaxy": "999"}, "Galaxy"),
    ({"kind": "spaceship"}, "Kind"),
    ({"detail": "x" * 500}, "What is there"),
])
def test_a_bad_issue_is_told_what_to_fix(change, complaint) -> None:
    loc, errors, _ = bot.check(bot.parse_form(body(**{**GOOD, **change})), LocationBook.load())
    assert loc is None and any(complaint in e for e in errors)
    assert "✗" in bot.reply(loc, errors, [])


def test_a_listed_address_is_a_duplicate_only_for_the_same_kind() -> None:
    book = LocationBook.load()
    known = book.locations[0]
    same = body(**{**GOOD, "code": known.code, "galaxy": str(known.galaxy), "kind": known.kind})
    other = next(k for k in KINDS if k != known.kind)
    differs = body(**{**GOOD, "code": known.code, "galaxy": str(known.galaxy), "kind": other})
    assert bot.check(bot.parse_form(same), book)[0] is None
    loc, _, warnings = bot.check(bot.parse_form(differs), book)
    assert loc is not None and any("already listed" in w for w in warnings)


def test_galaxy_takes_a_number_or_a_name() -> None:
    assert [bot.galaxy_from(t) for t in ("1", "Euclid", "2. Hilbert Dimension", "0", "Andromeda?")] \
        == [1, 1, 2, None, None]


def test_the_committed_file_passes_the_pull_request_check() -> None:
    assert bot.validate(ROOT / "data" / "locations.json") == []


def test_the_pull_request_check_catches_what_the_loader_forgives(tmp_path) -> None:
    raw = json.loads((ROOT / "data" / "locations.json").read_text())
    raw["locations"] += [
        {**raw["locations"][0]},                                     # duplicate
        {**raw["locations"][0], "code": "0123456789ab", "kind": "boat"},
        {**raw["locations"][0], "code": "XYZ", "galaxy": 0, "colour": "red"},
    ]
    path = tmp_path / "locations.json"
    path.write_text(json.dumps(raw))
    problems = "\n".join(bot.validate(path))
    for expected in ("same address", "0123456789AB", "kind must be", "not dialable", "galaxy must", "unknown field"):
        assert expected in problems


def test_apply_appends_and_credits(tmp_path, monkeypatch) -> None:
    data = tmp_path / "locations.json"
    data.write_text((ROOT / "data" / "locations.json").read_text())
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"issue": {"number": 7, "user": {"login": "someone"}, "body": body(**GOOD)}}))
    monkeypatch.setattr(bot, "LOCATIONS", data)
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "out"))
    monkeypatch.setattr(sys, "argv", ["portal_issue.py", "apply", "--event", str(event), "--out", str(tmp_path / "r.md")])
    bot.main()
    added = json.loads(data.read_text())["locations"][-1]
    assert added["code"] == "0123456789AB" and added["source"] == "visited myself - @someone via #7"
    assert "valid=true" in (tmp_path / "out").read_text()
    assert bot.validate(data) == []


# -- abuse protection ------------------------------------------------------------

def issue(number: int = 9, association: str = "NONE") -> dict:
    return {"number": number, "author_association": association,
            "user": {"login": "someone"}, "body": body(**GOOD)}


def test_the_cap_is_three_other_open_submissions() -> None:
    assert bot.MAX_OPEN == 3


def test_the_issue_itself_does_not_count_against_the_cap() -> None:
    mine = [{"number": n} for n in (1, 2, 9)]
    assert bot.open_elsewhere(issue(9), mine) == 2
    assert bot.open_elsewhere(issue(9), []) == 0


@pytest.mark.parametrize("others, held", [(0, False), (2, False), (3, True), (10, True)])
def test_a_stranger_past_the_cap_is_held(others, held) -> None:
    assert bot.on_hold(issue(), others) is held


@pytest.mark.parametrize("association", sorted(bot.EXEMPT))
def test_the_owner_and_collaborators_are_never_held(association) -> None:
    assert not bot.on_hold(issue(association=association), 50)


def test_the_hold_reply_is_polite_and_edits_in_place() -> None:
    text = bot.hold_reply(4)
    assert text.startswith("<!-- portal-address-bot -->")   # the same comment, edited
    assert "4 other portal addresses" in text and "wait until your open submissions are reviewed" in text
    assert "1 other portal address waiting" in bot.hold_reply(1)
    assert "✓" not in text and "✗" not in text


def test_the_on_hold_label_is_set_up() -> None:
    assert "on-hold" in bot.LABELS and bot.LABELS["on-hold"][1]


def run_check(tmp_path, monkeypatch, association: str, open_numbers: list[int]) -> tuple[str, str]:
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"issue": issue(9, association)}))
    mine = tmp_path / "open.json"
    mine.write_text(json.dumps([{"number": n} for n in open_numbers]))
    out = tmp_path / "out"
    out.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    monkeypatch.setattr(sys, "argv", ["portal_issue.py", "check", "--event", str(event),
                                      "--open", str(mine), "--out", str(tmp_path / "r.md")])
    bot.main()
    return (tmp_path / "r.md").read_text(), out.read_text()


def test_check_holds_instead_of_checking(tmp_path, monkeypatch) -> None:
    reply, outputs = run_check(tmp_path, monkeypatch, "NONE", [1, 2, 3, 9])
    assert "On hold" in reply and "held=true" in outputs and "valid=" not in outputs


def test_check_runs_normally_once_the_count_drops(tmp_path, monkeypatch) -> None:
    reply, outputs = run_check(tmp_path, monkeypatch, "NONE", [1, 2, 9])
    assert "Looks good" in reply and "held=false" in outputs and "valid=true" in outputs


def test_check_never_holds_a_collaborator(tmp_path, monkeypatch) -> None:
    reply, outputs = run_check(tmp_path, monkeypatch, "COLLABORATOR", [1, 2, 3, 4, 9])
    assert "held=false" in outputs and "valid=true" in outputs


def test_setup_dry_run_asks_for_approval_of_every_outside_fork_pr(capsys) -> None:
    bot.setup(dry_run=True)
    calls = [line for line in capsys.readouterr().out.splitlines() if line.startswith("would run:")]
    assert any("label create on-hold" in c for c in calls)
    assert any("actions/permissions/fork-pr-contributor-approval" in c
               and "approval_policy=all_external_contributors" in c and "-X PUT" in c for c in calls)


def test_lockdown_and_unlock_dry_runs(capsys) -> None:
    bot.lockdown("contributors_only", "one_week", dry_run=True)
    bot.unlock(dry_run=True)
    out = capsys.readouterr().out
    assert f"gh api -X PUT repos/{bot.REPO}/interaction-limits -f limit=contributors_only -f expiry=one_week" in out
    assert f"gh api -X DELETE repos/{bot.REPO}/interaction-limits" in out


SHA = "0123456789abcdef0123456789abcdef01234567"


def test_vouch_posts_the_required_check_on_the_bot_pr(capsys, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    assert bot.vouch(SHA, dry_run=True) == 0
    out = capsys.readouterr().out
    assert (f"gh api -X POST repos/owner/repo/statuses/{SHA} -f state=success -f context=check "
            "-f 'description=portal address validated by the contributions bot' "
            "-f target_url=https://github.com/owner/repo/actions/runs/42") in out


def test_vouch_refuses_a_broken_file_or_a_bad_sha(tmp_path, capsys) -> None:
    broken = tmp_path / "locations.json"
    broken.write_text('{"locations": [{"name": "x"}]}')
    assert bot.vouch(SHA, broken, dry_run=True) == 1
    assert bot.vouch("HEAD; rm -rf /", dry_run=True) == 1
    assert "would run" not in capsys.readouterr().out


def test_the_check_name_is_ci_jobs_name() -> None:
    """The status the bot posts must be the one main requires: ci.yml's job."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert re.search(rf"^  {bot.CHECK}:$", ci, flags=re.M)
    # A path filter would leave the required check unreported on some PRs.
    assert "paths-ignore" not in ci and "paths:" not in ci


def test_only_the_owner_gated_accept_job_may_post_statuses() -> None:
    text = (ROOT / ".github" / "workflows" / "contrib.yml").read_text()
    jobs = re.split(r"^  (?=[\w-]+:$)", text.split("\njobs:\n", 1)[1], flags=re.M)
    writers = [job.split(":", 1)[0] for job in jobs if "statuses: write" in job]
    assert writers == ["accept-issue"]
    accept = next(job for job in jobs if job.startswith("accept-issue:"))
    assert "github.event.sender.login == github.repository_owner" in accept
    assert accept.index("portal_issue.py validate") < accept.index("portal_issue.py vouch")
