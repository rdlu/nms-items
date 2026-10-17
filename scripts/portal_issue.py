"""Check portal addresses people contribute, from an issue or a pull request.

Contributions arrive two ways and are checked by the same rules, the ones the
TUI and the web page already use (nms_items.portals):

    check     an issue filed with the "Share a portal address" form: parse
              it, convert the address, look for duplicates, and write the
              bot's reply to --out (markdown) plus valid=true|false to
              $GITHUB_OUTPUT. Never touches the repo.
    apply     the same issue, once a maintainer labels it `accepted`: check
              again, then append it to data/locations.json as `shared`,
              crediting the reporter and the issue.
    vouch     after `apply`, on the pull request it opened: validate again,
              then post a `check` commit status on its head, since a PR
              opened with GITHUB_TOKEN starts no CI of its own.
    validate  data/locations.json as a whole, strictly -- what a pull request
              that edits it has to pass. The TUI's loader skips a broken row
              so a typo cannot take a screen down; a PR gets told instead.
    setup     once per repo, through `gh`: the labels the bot uses, the
              setting that lets a workflow open the pull request, and the one
              that holds every outside contributor's pull request for approval.
    lockdown  the emergency brake: GitHub interaction limits, so only existing
              users (or contributors, or collaborators) can open or comment,
              for a day up to a month. `unlock` lifts it.
    status    the limits, the fork approval policy, open submissions per
              author, and how often the workflow ran in the last 24 hours.

One person may have MAX_OPEN other submissions waiting at a time. Past that,
`check` puts the issue on hold instead of checking it, and a later edit checks
it once the others are reviewed. The owner, members and collaborators are
exempt.

The issue body is untrusted text. It is only ever read from the event file
and parsed here, never interpolated into a shell command.

Locally: `mise run contrib:validate`, `contrib:setup`, `contrib:lockdown`,
`contrib:unlock`, `contrib:status`; every one that writes takes `--dry-run`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from nms_items.portals import (  # noqa: E402
    GALAXY_NAMES, GLYPH_NAMES, KINDS, MAX_GALAXY, ORIGINS, Address, AddressError,
    LocationBook, Location, galaxy_name, parse_galaxy, resolve_choice,
)

LOCATIONS = ROOT / "data" / "locations.json"
FORM = ROOT / ".github" / "ISSUE_TEMPLATE" / "portal-address.yml"
REPO = "rdlu/nms-items-interface"
LABELS = {
    "portal-address": ("f5c451", "Shared through the portal address form"),
    "valid": ("3fb950", "The bot read the address cleanly"),
    "needs-fix": ("d1242f", "The bot found something to fix in the form"),
    "accepted": ("8a5a00", "Maintainer: add it - the bot opens the pull request"),
    "on-hold": ("bfbfbf", "The author has too many submissions waiting; edit it once they are reviewed"),
}

# How many other submissions one person may have waiting before the next one
# is put on hold, so a flood of issues cannot turn the bot into a runner-time
# sink. The owner and anyone with write access are trusted and exempt.
MAX_OPEN = 3
EXEMPT = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
LIMITS = ("existing_users", "contributors_only", "collaborators_only")
EXPIRIES = ("one_day", "three_days", "one_week", "one_month")

# The form's labels, as GitHub renders them into the issue body (`### Label`),
# mapped to the field each one fills. tests/test_contrib.py holds these to the
# labels in the form, so renaming one there cannot silently drop a field.
FIELDS = {
    "Name": "name",
    "Portal address": "code",
    "Galaxy": "galaxy",
    "Kind": "kind",
    "What is there": "detail",
    "Finding it": "where",
    "Source": "source",
}
REQUIRED = ("name", "code", "galaxy", "kind", "detail")
ROW_KEYS = {"name", "code", "kind", "origin", "galaxy", "detail", "where", "source", "added"}
NO_RESPONSE = "_No response_"


# -- reading an issue ---------------------------------------------------------

def parse_form(body: str) -> dict[str, str]:
    """`### Label` sections of an issue-form body, by field id."""
    fields: dict[str, str] = {}
    parts = re.split(r"^### +(.+?)\s*$", body or "", flags=re.M)
    for label, value in zip(parts[1::2], parts[2::2]):
        key = FIELDS.get(label.strip())
        if key is None:
            continue
        value = value.strip()
        fields[key] = "" if value == NO_RESPONSE else value
    return fields


def galaxy_from(text: str) -> int | None:
    """What the TUI takes, a number 1-256, or a name like `Euclid` or `1. Euclid`."""
    number = parse_galaxy(re.sub(r"\..*", "", text))
    if number is not None:
        return number
    lowered = [g.lower() for g in GALAXY_NAMES]
    name = text.strip().lower()
    return lowered.index(name) + 1 if name in lowered else None


def check(fields: dict[str, str], book: LocationBook) -> tuple[Location | None, list[str], list[str]]:
    """The entry the issue describes, or None; then errors and warnings."""
    errors: list[str] = []
    warnings: list[str] = []
    for key in REQUIRED:
        if not fields.get(key, "").strip():
            label = next(k for k, v in FIELDS.items() if v == key)
            errors.append(f"**{label}** is required.")

    address = None
    raw = fields.get("code", "").strip()
    if raw:
        try:
            address = Address.parse(raw)
        except AddressError as exc:
            errors.append(f"**Portal address** `{md(raw[:60])}` is not an address: {exc}.")
        else:
            if ":" in raw and "#" not in raw:
                warnings.append(
                    "That is a galactic address, which carries no planet: the code below "
                    "assumes the **1st** planet (glyph `0`). Edit the issue with the "
                    "portal code if it is another one.")
            warnings += address.warnings

    galaxy = galaxy_from(fields.get("galaxy", "") or "1")
    if galaxy is None:
        errors.append(f"**Galaxy** must be a number from 1 to {MAX_GALAXY}, or a name like Euclid.")

    kind = resolve_choice(fields.get("kind", ""), KINDS) if fields.get("kind") else None
    if fields.get("kind") and kind is None:
        errors.append(f"**Kind** must be one of: {', '.join(KINDS)}.")

    for key, limit in (("name", 60), ("detail", 200), ("where", 400), ("source", 200)):
        if len(fields.get(key, "")) > limit:
            errors.append(f"**{next(k for k, v in FIELDS.items() if v == key)}** is longer than {limit} characters.")

    if errors or address is None or galaxy is None or kind is None:
        return None, errors, warnings

    for loc in book.locations:
        if loc.code == address.portal_code and loc.galaxy == galaxy:
            note = f"`{loc.code}` in {galaxy_name(galaxy)} is already listed as **{md(loc.name)}** ({loc.kind})."
            # One system can hold a tool and a ship: only the same kind is a duplicate.
            (errors if loc.kind == kind else warnings).append(
                note + ("" if loc.kind != kind else " Nothing to add."))
    if errors:
        return None, errors, warnings

    return Location(
        name=fields["name"].strip(),
        code=address.portal_code,
        kind=kind,
        origin="shared",
        galaxy=galaxy,
        detail=fields["detail"].strip(),
        where=fields.get("where", "").strip(),
        source=fields.get("source", "").strip(),
    ), errors, warnings


def md(text: str) -> str:
    """Submitted text, safe inside the bot's table: no column breaks, no pings."""
    return text.replace("|", "\\|").replace("`", "'").replace("@", "@\u200b").replace("\n", " ")


def reply(loc: Location | None, errors: list[str], warnings: list[str]) -> str:
    """The bot's comment: what is wrong, or what the address turned into."""
    lines = ["<!-- portal-address-bot -->"]
    if errors:
        lines += ["### ✗ This needs a fix before it can go in", ""]
        lines += [f"- {e}" for e in errors]
        lines += ["", "Edit the issue and I will check it again."]
    else:
        a = loc.address
        names = " ".join(f"{d}·{GLYPH_NAMES[int(d, 16)]}" for d in a.portal_code)
        lines += [
            "### ✓ Looks good", "",
            "| | |", "| --- | --- |",
            f"| Name | {md(loc.name)} |",
            f"| Portal code | `{a.portal_grouped}` |",
            f"| Galactic | `{a.galactic}` |",
            f"| Galaxy | {loc.galaxy}. {galaxy_name(loc.galaxy)} |",
            f"| Kind | {loc.kind} |",
            f"| Glyphs | {names} |",
            "", f"[Open it on nmsii.dlu.one](https://nmsii.dlu.one/#/portals?code={a.portal_code})",
            "", "A maintainer adds the `accepted` label to merge it into the shared list.",
        ]
    if warnings:
        lines += ["", "**Worth a look:**"] + [f"- {w}" for w in warnings]
    return "\n".join(lines) + "\n"


# -- the per-author cap ---------------------------------------------------------

def open_elsewhere(issue: dict, open_issues: list[dict]) -> int:
    """The author's other open submissions; `open_issues` is `gh issue list --json number`."""
    return sum(1 for i in open_issues if i.get("number") != issue.get("number"))


def on_hold(issue: dict, others: int) -> bool:
    """Too many already waiting, unless the author is trusted."""
    return issue.get("author_association") not in EXEMPT and others >= MAX_OPEN


def hold_reply(others: int) -> str:
    """The bot's comment on an issue it will not check yet."""
    return "\n".join([
        "<!-- portal-address-bot -->",
        "### ⏸ On hold for now", "",
        f"Thank you for sharing! You already have {others} other portal "
        f"{'address' if others == 1 else 'addresses'} waiting for review, and I take "
        f"{MAX_OPEN} at a time from one person.",
        "",
        f"Please wait until your open submissions are reviewed. Once fewer than {MAX_OPEN} "
        "others are open, edit this issue (any small change will do) and I will check it.",
    ]) + "\n"


# -- the whole file, for a pull request ----------------------------------------

def validate(path: Path) -> list[str]:
    """Every problem in the file; empty means it may be merged."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{path.name} is not valid JSON: {exc}"]
    problems = []
    for key in ("_source", "_note", "locations"):
        if key not in raw:
            problems.append(f"missing top-level `{key}`")
    seen: dict[tuple, str] = {}
    for i, row in enumerate(raw.get("locations", [])):
        where = f"locations[{i}] ({row.get('name', '?') if isinstance(row, dict) else '?'})"
        if not isinstance(row, dict):
            problems.append(f"{where}: not an object")
            continue
        for key in sorted(set(row) - ROW_KEYS):
            problems.append(f"{where}: unknown field `{key}`")
        for key in ("name", "code", "kind", "origin", "galaxy", "detail", "source"):
            if row.get(key) in (None, ""):
                problems.append(f"{where}: `{key}` is required")
        try:
            code = Address.from_portal_code(str(row.get("code", ""))).portal_code
            if code != row.get("code"):
                problems.append(f"{where}: write the code as `{code}` - 12 upper-case hex digits")
        except AddressError as exc:
            problems.append(f"{where}: code is not dialable - {exc}")
            code = None
        if row.get("kind") not in KINDS:
            problems.append(f"{where}: kind must be one of {', '.join(KINDS)}")
        if row.get("origin") not in ORIGINS:
            problems.append(f"{where}: origin must be one of {', '.join(ORIGINS)}")
        galaxy = row.get("galaxy")
        if not isinstance(galaxy, int) or not 1 <= galaxy <= MAX_GALAXY:
            problems.append(f"{where}: galaxy must be a number from 1 to {MAX_GALAXY}")
        added = row.get("added", "")
        if added and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", added):
            problems.append(f"{where}: added must be YYYY-MM-DD")
        if code:
            key = (code, galaxy, row.get("kind"))
            if key in seen:
                problems.append(f"{where}: same address, galaxy and kind as {seen[key]}")
            seen[key] = where
    return problems


# -- entry points --------------------------------------------------------------

def load_issue(event_path: str) -> dict:
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return event["issue"]


def set_output(name: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"{name}={value}\n")


def gh(args: list[str], dry_run: bool = False) -> None:
    """Make a `gh` call that changes something, or only print it."""
    if dry_run:
        print("would run: gh " + shlex.join(args))
        return
    subprocess.run(["gh", *args], check=True)


def gh_read(args: list[str]) -> tuple[bool, str]:
    """A read-only `gh` call: (ok, its output or its error)."""
    done = subprocess.run(["gh", *args], capture_output=True, text=True)
    return done.returncode == 0, (done.stdout if done.returncode == 0 else done.stderr).strip()


def setup(dry_run: bool = False) -> None:
    for name, (colour, about) in LABELS.items():
        gh(["label", "create", name, "-R", REPO, "--force",
            "--color", colour, "--description", about], dry_run)
        print(f"label     {name}")
    # Off by default on every repo: GITHUB_TOKEN may push a branch but not open
    # a pull request. The accept-issue job needs it; nothing else does.
    gh(["api", "-X", "PUT", f"repos/{REPO}/actions/permissions/workflow",
        "-f", "default_workflow_permissions=read",
        "-F", "can_approve_pull_request_reviews=true"], dry_run)
    print("actions   may open pull requests (default token stays read-only)")
    # The default only holds a first-time contributor's fork PR for approval;
    # this holds every outside contributor's, so no fork PR spends runner time
    # until a maintainer has looked at it.
    gh(["api", "-X", "PUT", f"repos/{REPO}/actions/permissions/fork-pr-contributor-approval",
        "-f", "approval_policy=all_external_contributors"], dry_run)
    print("actions   fork pull requests from every outside contributor wait for approval")


CHECK = "check"  # the required status check on main: ci.yml's job name


def vouch_call(sha: str, repo: str, run_url: str) -> list[str]:
    """The `gh` call that reports `check` passed on the bot's pull request."""
    return ["api", "-X", "POST", f"repos/{repo}/statuses/{sha}",
            "-f", "state=success", "-f", f"context={CHECK}",
            "-f", "description=portal address validated by the contributions bot",
            "-f", f"target_url={run_url}"]


def vouch(sha: str, path: Path = LOCATIONS, dry_run: bool = False) -> int:
    """Validate the file again, then mark `sha` as passing `check`.

    A pull request the bot opens with GITHUB_TOKEN starts no workflow, so
    ci.yml never reports `check` on it and the required check would wait
    forever. The bot has just run the same validation ci.yml would run on a
    change to data/locations.json alone, so it reports the result itself.
    """
    problems = validate(path)
    if problems:
        print("not vouching: " + "; ".join(problems), file=sys.stderr)
        return 1
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        print(f"not vouching: {sha!r} is not a commit SHA", file=sys.stderr)
        return 1
    repo = os.environ.get("GITHUB_REPOSITORY", REPO)
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.environ.get("GITHUB_RUN_ID")
    run_url = f"{server}/{repo}/actions/runs/{run_id}" if run_id else f"{server}/{repo}/actions"
    gh(vouch_call(sha, repo, run_url), dry_run)
    print(f"vouched   {CHECK}=success on {sha[:7]}")
    return 0


def lockdown(limit: str, expiry: str, dry_run: bool = False) -> None:
    gh(["api", "-X", "PUT", f"repos/{REPO}/interaction-limits",
        "-f", f"limit={limit}", "-f", f"expiry={expiry}"], dry_run)
    print(f"locked    to {limit.replace('_', ' ')}, for {expiry.replace('_', ' ')}")


def unlock(dry_run: bool = False) -> None:
    gh(["api", "-X", "DELETE", f"repos/{REPO}/interaction-limits"], dry_run)
    print("unlocked  interaction limits removed")


def status(dry_run: bool = False) -> None:
    since = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    limits_call = ["api", f"repos/{REPO}/interaction-limits"]
    forks_call = ["api", f"repos/{REPO}/actions/permissions/fork-pr-contributor-approval",
                  "-q", ".approval_policy"]
    open_call = ["issue", "list", "-R", REPO, "-l", "portal-address", "--state", "open",
                 "--limit", "500", "--json", "number,author"]
    runs_call = ["api", f"repos/{REPO}/actions/workflows/contrib.yml/runs?created=>={since}&per_page=1",
                 "-q", ".total_count"]
    if dry_run:
        for args in (limits_call, forks_call, open_call, runs_call):
            print("would run: gh " + shlex.join(args))
        return

    ok, out = gh_read(limits_call)
    limits = json.loads(out or "{}") if ok else None
    if limits is None:
        print(f"limits    unavailable: {out}")
    elif not limits:
        print("limits    none - anyone may open issues and pull requests")
    else:
        print(f"limits    {limits.get('limit')} only, until {limits.get('expires_at')}")

    ok, out = gh_read(forks_call)
    print(f"forks     {out if ok else 'unavailable: ' + out}")

    ok, out = gh_read(open_call)
    if ok:
        authors: dict[str, int] = {}
        for issue in json.loads(out or "[]"):
            login = (issue.get("author") or {}).get("login", "?")
            authors[login] = authors.get(login, 0) + 1
        total = sum(authors.values())
        print(f"open      {total} portal-address issue{'' if total == 1 else 's'}")
        for login, n in sorted(authors.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"          {n:>3}  {login}{'  (next one goes on hold)' if n >= MAX_OPEN else ''}")
    else:
        print(f"open      unavailable: {out}")

    ok, out = gh_read(runs_call)
    print(f"runs      {out if ok else 'unavailable: ' + out} Contributions runs in the last 24h")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("check", "apply"):
        p = sub.add_parser(name)
        p.add_argument("--event", default=os.environ.get("GITHUB_EVENT_PATH"), required=False)
        p.add_argument("--out", default="bot-reply.md")
    sub.choices["check"].add_argument(
        "--open", metavar="JSON",
        help="the author's open portal-address issues, as `gh issue list --json number` writes them")
    p = sub.add_parser("validate")
    p.add_argument("path", nargs="?", default=str(LOCATIONS))
    for name in ("setup", "lockdown", "unlock", "status", "vouch"):
        p = sub.add_parser(name)
        p.add_argument("--dry-run", action="store_true", help="print the gh calls instead of making them")
    sub.choices["lockdown"].add_argument("--limit", choices=LIMITS, default="existing_users")
    sub.choices["lockdown"].add_argument("--expiry", choices=EXPIRIES, default="one_day")
    sub.choices["vouch"].add_argument("sha", help="the bot's pull request head commit")
    args = parser.parse_args()

    if args.cmd == "vouch":
        sys.exit(vouch(args.sha, dry_run=args.dry_run))

    if args.cmd == "setup":
        return setup(args.dry_run)
    if args.cmd == "lockdown":
        return lockdown(args.limit, args.expiry, args.dry_run)
    if args.cmd == "unlock":
        return unlock(args.dry_run)
    if args.cmd == "status":
        return status(args.dry_run)

    if args.cmd == "validate":
        problems = validate(Path(args.path))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        text = ("### ✓ data/locations.json is valid\n" if not problems else
                "### ✗ data/locations.json has problems\n\n" + "\n".join(f"- {p}" for p in problems)) + "\n"
        if summary:
            Path(summary).write_text(text, encoding="utf-8")
        print(text)
        sys.exit(1 if problems else 0)

    issue = load_issue(args.event)
    if args.cmd == "check" and args.open:
        others = open_elsewhere(issue, json.loads(Path(args.open).read_text(encoding="utf-8") or "[]"))
        if on_hold(issue, others):
            Path(args.out).write_text(hold_reply(others), encoding="utf-8")
            set_output("held", "true")
            print(Path(args.out).read_text(encoding="utf-8"))
            return
    set_output("held", "false")
    book = LocationBook.load(LOCATIONS)
    loc, errors, warnings = check(parse_form(issue.get("body") or ""), book)
    Path(args.out).write_text(reply(loc, errors, warnings), encoding="utf-8")
    set_output("valid", "true" if loc else "false")
    if args.cmd == "apply" and loc:
        login = issue["user"]["login"]
        credit = f"@{login} via #{issue['number']}"
        loc.source = f"{loc.source} - {credit}" if loc.source else credit
        loc.added = date.today().isoformat()
        book.add(loc)
    print(Path(args.out).read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
