#!/usr/bin/env python3
"""scripts/check_agent_surface.py -- THE ADAPTER SURFACE'S READER (T-169 / BUG-845 / D-3037).

WHY THIS EXISTS. config/agent_surface.yaml declares where an agent harness is bound and what the core must
survive swapping. Until this file existed that declaration had NO READER - which is the disease this
repository names everywhere: a claim nothing reads is not a guarantee (BUG-845, D-3034).

THE THREE RULES, all vocabulary read from the surface file. This script names no path, no client and no
magic number of its own (C12); every class, shape, glob and ceiling below is a DECLARED value, and an
absent key is FATAL rather than defaulted, because an inferred rule can be made to accept anything.

  R1 PORTABLE   a declared portable artifact may not NAME a client or a provider. A skill that names one
                stops being drop-in, and a swap then has to REWRITE an artifact instead of re-pointing a
                binding. (Record artifacts may name one - their subject can BE a client, D-3038.)
  R2 BINDINGS   code outside the declared adapter roots may not BIND a client (a client home, a client app
                bundle, a client environment knob) unless the site is DECLARED in the register. The register
                may not GROW (SHRINK-ONLY, D-3023), may not keep a stale row, may not carry an undeclared
                class, and an `owed` row must name a row that EXISTS (D-3034: a declaration must resolve).
  R3 RESOLUTION every declaration must RESOLVE: an in-repo root exists or is declared optional, an external
                root is declared OUTSIDE the repository (never mirrored), a declared glob matches at least
                one file, the declared journal exists and its declared reader names this file, and the
                decision the surface cites exists in the register.

RC (the ladder reads the same contract - tri_state):
  0  every declaration resolves and no site owes a remedy
  1  FAULT - an undeclared binding, a stale or unresolvable declaration, an absent required key
  2  LOUD - a DECLARED site owes a remedy; printed with the row that owns it, never fatal (BUG-457), so the
     ladder keeps running while the debt stays visible

USAGE:
  python3 scripts/check_agent_surface.py              # the reading (wired into `just health`)
  python3 scripts/check_agent_surface.py --selftest   # known-answer controls, both directions
"""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Any, NoReturn

import yaml

RC_OK = 0
RC_FAULT = 1
RC_LOUD = 2

REPO_ROOT = Path(__file__).resolve().parents[1]
SURFACE = "config/agent_surface.yaml"
TASK_REGISTER = "config/task_register.yaml"
DECISION_REGISTER = "config/decisions.yaml"

#: The schema this rail reads. A key absent from the surface is FATAL: these names ARE the contract, and the
#: file that declares them is the ONE home for their values (C12).
REQUIRED_KEYS = (
    "schema_version",
    "decided",
    "core.survives_a_swap",
    "adapter.roots",
    "adapter.external_roots",
    "adapter.binding_sites.ceiling",
    "adapter.binding_sites.sites",
    "rules.portable_artifacts",
    "rules.record_artifacts",
    "rules.forbidden_in_portable",
    "rules.binding_site_classes",
    "rules.binding_scan.roots",
    "rules.binding_scan.globs",
    "rules.binding_shapes",
    "logging.journal",
    "logging.reader",
)


def fatal(message: str) -> NoReturn:
    """Refuse rather than infer: a rail whose own rules are guessed is a rail that can be made to pass."""
    raise SystemExit(f"FATAL: {message}")


def reading(path: Path) -> dict[str, Any]:
    """Read a declared YAML home; an absent or unparsable home is fatal, never an empty default."""
    if not path.is_file():
        fatal(f"{path} is absent - it is the ONE home this rail reads (C12)")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        fatal(f"{path} does not parse: {exc}")
    if not isinstance(data, dict):
        fatal(f"{path} is not a mapping")
    return data


def dig(data: dict[str, Any], dotted: str) -> Any:
    """Resolve a dotted key path; a missing key is fatal rather than defaulted (C12/D-2644)."""
    node: Any = data
    walked: list[str] = []
    for part in dotted.split("."):
        walked.append(part)
        if not isinstance(node, dict) or part not in node:
            fatal(f"{SURFACE} does not declare '{dotted}' (missing at '{'.'.join(walked)}')")
        node = node[part]
    return node


def as_list(value: Any, where: str) -> list[Any]:
    """A declared collection must be a list; a scalar in its place is a fault, not a one-item list."""
    if not isinstance(value, list):
        fatal(f"{SURFACE} declares {where} as {type(value).__name__}, not a list")
    return value


def repo_path(repo: Path, declared_path: str) -> Path:
    """Turn a declared in-repo path into a filesystem path without inventing one."""
    return repo / declared_path


def tool_files(repo: Path, scan: dict[str, Any]) -> list[Path]:
    """The CODE a binding could hide in: declared roots x declared globs, plus declared bare files."""
    globs = [str(g) for g in as_list(scan["globs"], "rules.binding_scan.globs")]
    skip = {str(s) for s in as_list(scan.get("skip", []), "rules.binding_scan.skip")}
    found: set[Path] = set()
    for root in (str(r) for r in as_list(scan["roots"], "rules.binding_scan.roots")):
        base = repo_path(repo, root)
        if not base.is_dir():
            continue
        for pattern in globs:
            for path in base.glob(pattern):
                if not path.is_file():
                    continue
                parents = path.relative_to(base).parts[:-1]
                if any(part in skip or part.startswith(".") for part in parents):
                    continue
                found.add(path)
    for name in as_list(scan.get("files", []), "rules.binding_scan.files"):
        path = repo_path(repo, str(name))
        if path.is_file():
            found.add(path)
    return sorted(found)


def binding_hits(
    repo: Path,
    files: list[Path],
    shapes: list[Any],
    adapter_roots: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split every shape hit into IN the declared adapter roots and OUTSIDE them (where it must be declared)."""
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for shape in shapes:
        if not isinstance(shape, dict) or "id" not in shape or "pattern" not in shape:
            fatal(f"{SURFACE} declares a binding shape without an 'id' or a 'pattern' (a shape is a DECLARED thing)")
        try:
            compiled.append((str(shape["id"]), re.compile(str(shape["pattern"]))))
        except re.error as exc:
            fatal(f"the declared binding shape '{shape['id']}' is not a valid pattern: {exc}")
    inside: list[dict[str, Any]] = []
    outside: list[dict[str, Any]] = []
    for path in files:
        relative = path.relative_to(repo).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            fatal(f"cannot read {relative}: {type(exc).__name__}: {exc}")
        in_root = any(relative.startswith(f"{root}") for root in adapter_roots)
        for shape_id, pattern in compiled:
            for number, line in enumerate(text.splitlines(), 1):
                if pattern.search(line):
                    hit = {"path": relative, "line": number, "shape": shape_id}
                    (inside if in_root else outside).append(hit)
                    break
    return inside, outside


def expand(repo: Path, pattern: str) -> list[Path]:
    """Expand a declared glob to FILES. A pattern ending in '/**' means 'everything under it': pathlib yields
    that trailing '**' as DIRECTORIES only, so the normalisation is what makes the declaration resolve."""
    if pattern.endswith("/**"):
        pattern = f"{pattern}/*"
    return [path for path in sorted(repo.glob(pattern)) if path.is_file()]


def portable_faults(repo: Path, data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """R1: a portable artifact that names a client stops being drop-in; a glob resolving to nothing is a claim."""
    faults: list[str] = []
    tokens = [str(t) for t in as_list(dig(data, "rules.forbidden_in_portable"), "rules.forbidden_in_portable")]
    scanned = 0
    for glob in (str(g) for g in as_list(dig(data, "rules.portable_artifacts"), "rules.portable_artifacts")):
        matched = expand(repo, glob)
        if not matched:
            faults.append(f"R1 the declared portable artifact '{glob}' matches NO file - a declaration must resolve (D-3034)")
        for path in matched:
            scanned += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                lowered = line.lower()
                for token in tokens:
                    if re.search(rf"\b{re.escape(token.lower())}\b", lowered):
                        faults.append(
                            f"R1 {path.relative_to(repo).as_posix()}:{number} names '{token}' - a portable "
                            f"artifact may not name a harness or a provider (move the binding into the adapter root)"
                        )
    #: A RECORD artifact may NAME a client (its subject can BE one, D-3038) - but every declared record glob
    #: must still resolve, because a declaration that matches nothing is a claim about a population that is not
    #: there (D-3034). This is the ONE direction of the record class this rail may enforce.
    records = 0
    for glob in (str(g) for g in as_list(dig(data, "rules.record_artifacts"), "rules.record_artifacts")):
        matched = expand(repo, glob)
        if not matched:
            faults.append(f"R1 the declared record artifact '{glob}' matches NO file - a declaration must resolve (D-3034)")
        records += len(matched)
    return faults, [f"portable artifacts scanned: {scanned} | record artifacts (name-allowed): {records}"]


def root_faults(repo: Path, data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """R3 for the roots: in-repo roots exist (or are declared optional), external roots are never mirrored."""
    faults: list[str] = []
    facts: list[str] = []
    for entry in as_list(dig(data, "adapter.roots"), "adapter.roots"):
        declared_path = str(entry["path"]) if isinstance(entry, dict) else str(entry)
        optional = bool(entry.get("optional")) if isinstance(entry, dict) else False
        if not repo_path(repo, declared_path).is_dir() and not optional:
            faults.append(f"R3 the declared adapter root '{declared_path}' does not resolve - and it is not declared optional")
    present = 0
    external = as_list(dig(data, "adapter.external_roots"), "adapter.external_roots")
    for entry in external:
        declared_path = str(entry)
        if not declared_path.startswith("~"):
            faults.append(
                f"R3 the external root '{declared_path}' is not written as an OUTSIDE-the-repository path - "
                f"an external root is declared, never mirrored (a copy of it would drift)"
            )
            continue
        if Path(declared_path).expanduser().exists():
            present += 1
    facts.append(f"external roots declared: {len(external)} (present on this machine: {present})")
    return faults, facts


def site_faults(
    repo: Path,
    data: dict[str, Any],
    outside: list[dict[str, Any]],
) -> tuple[list[str], list[str], int]:
    """R2: every binding OUTSIDE the adapter roots is declared, resolvable, and within a shrink-only ceiling."""
    faults: list[str] = []
    loud: list[str] = []
    classes = [str(c) for c in as_list(dig(data, "rules.binding_site_classes"), "rules.binding_site_classes")]
    ceiling = int(dig(data, "adapter.binding_sites.ceiling"))
    sites = as_list(dig(data, "adapter.binding_sites.sites"), "adapter.binding_sites.sites")
    if len(sites) > ceiling:
        faults.append(
            f"R2 the binding register holds {len(sites)} site(s) against a declared ceiling of {ceiling} "
            f"(SHRINK-ONLY, D-3023): the remedy for a new site is to route the binding through this surface, "
            f"never to raise the ceiling"
        )
    hit_paths = {str(hit["path"]) for hit in outside}
    declared_paths: set[str] = set()
    row_ids = {
        str(row.get("id"))
        for row in as_list((reading(repo / TASK_REGISTER) or {}).get("tasks", []), f"{TASK_REGISTER}#tasks")
        if isinstance(row, dict)
    }
    for site in sites:
        if not isinstance(site, dict) or "path" not in site or "class" not in site:
            fatal(f"{SURFACE} declares a binding site without a 'path' or a 'class'")
        declared_path = str(site["path"])
        declared_paths.add(declared_path)
        klass = str(site["class"])
        if klass not in classes:
            faults.append(f"R2 {declared_path} carries the class '{klass}', which is outside the declared vocabulary {classes}")
        if not repo_path(repo, declared_path).is_file():
            faults.append(f"R3 the declared binding site '{declared_path}' does not exist on disk")
        if declared_path not in hit_paths:
            faults.append(
                f"R2 the declared binding site '{declared_path}' no longer carries a declared shape - a stale "
                f"declaration is a claim about a site that is not there (D-3034)"
            )
        if klass == "owed":
            row = str(site.get("row") or "")
            if not row:
                faults.append(
                    f"R2 the site '{declared_path}' is declared owed with NO named row - acceptance must be a "
                    f"word, never a default (D-3040)"
                )
            elif row not in row_ids:
                faults.append(f"R3 the site '{declared_path}' names the row '{row}', which does not exist in {TASK_REGISTER}")
            else:
                loud.append(f"OWED {declared_path} (row {row}) - {str(site.get('why') or '').splitlines()[0][:90]}")
    for path in sorted(hit_paths - declared_paths):
        faults.append(
            f"R2 {path} BINDS a client and is neither inside a declared adapter root nor in the register: "
            f"move the binding into the adapter root (or declare the site with its class and reason)"
        )
    return faults, loud, len(sites)


def resolution_faults(repo: Path, data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """R3 for the declarations themselves: a citation, a journal, its reader and a named decision must resolve."""
    faults: list[str] = []
    facts: list[str] = []
    journal = str(dig(data, "logging.journal"))
    reader = str(dig(data, "logging.reader"))
    if not repo_path(repo, journal).is_file():
        faults.append(f"R3 the declared journal '{journal}' does not exist (the reader would report an empty register)")
    else:
        facts.append(f"journal resolves: {journal}")
    reader_script = repo_path(repo, reader)
    if not reader_script.is_file():
        faults.append(f"R3 the declared journal reader '{reader}' does not exist")
    elif SURFACE not in reader_script.read_text(encoding="utf-8", errors="replace"):
        faults.append(
            f"R3 the declared reader '{reader}' does not name '{SURFACE}' - the ONE home a reader must read (C12)"
        )
    else:
        facts.append(f"reader names the one home: {reader}")
    decided = [str(d) for d in as_list(dig(data, "decided"), "decided")]
    register = reading(repo / DECISION_REGISTER)
    ids = {str(item.get("id")) for item in (register.get("decisions") or []) if isinstance(item, dict)}
    missing = [d for d in decided if d not in ids]
    if missing:
        faults.append(f"R3 the surface cites {missing}, which the decision register does not carry (D-3034: it must resolve)")
    else:
        facts.append(f"cited decision(s) resolve: {', '.join(decided)}")
    return faults, facts


def audit(repo: Path, surface_path: Path) -> tuple[list[str], list[str], dict[str, Any]]:
    """Run the three rules and return (faults, loud debt lines, printed facts)."""
    data = reading(surface_path)
    for dotted in REQUIRED_KEYS:
        node: Any = data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                fatal(f"{surface_path} does not declare '{dotted}' - an absent rule is never defaulted (C12)")
            node = node[part]
    adapter_roots = [
        str(entry["path"]) if isinstance(entry, dict) else str(entry)
        for entry in as_list(dig(data, "adapter.roots"), "adapter.roots")
    ]
    scan = dig(data, "rules.binding_scan")
    shapes = as_list(dig(data, "rules.binding_shapes"), "rules.binding_shapes")
    files = tool_files(repo, scan)
    inside, outside = binding_hits(repo, files, shapes, adapter_roots)
    faults: list[str] = []
    facts: list[str] = []
    for collect in (portable_faults, root_faults, resolution_faults):
        found, extra = collect(repo, data)
        faults.extend(found)
        facts.extend(extra)
    rows, loud, site_count = site_faults(repo, data, outside)
    faults.extend(rows)
    facts.insert(
        0,
        f"code scanned: {len(files)} file(s) | shapes: {len(shapes)} | hits inside a declared root: {len(inside)} "
        f"| binding register: {site_count} declared site(s)",
    )
    return faults, loud, {"facts": facts, "hits": outside}


def report(repo: Path, surface_path: Path) -> int:
    """Print the reading and return the rail's rc (0 clean, 1 fault, 2 declared debt)."""
    faults, loud, extra = audit(repo, surface_path)
    print(f"agent-surface: {surface_path.relative_to(repo) if surface_path.is_relative_to(repo) else surface_path}")
    for fact in extra["facts"]:
        print(f"  {fact}")
    for hit in extra["hits"]:
        print(f"  site {hit['path']}:{hit['line']} [{hit['shape']}]")
    for line in loud:
        print(f"  {line}")
    for fault in faults:
        print(f"  !! {fault}")
    if faults:
        print(f"agent-surface: {len(faults)} fault(s) - an undeclared binding is how a swap becomes archaeology (BUG-845)")
        return RC_FAULT
    if loud:
        print(f"agent-surface: rc=2 LOUD - {len(loud)} declared site(s) owe a remedy; the ladder keeps running (BUG-457)")
        return RC_LOUD
    print("agent-surface: ok - every declared root resolves, no portable artifact names a client, and no code binds one outside the adapter surface")
    return RC_OK


def set_key(data: dict[str, Any], dotted: str, value: Any) -> None:
    """Set a dotted key in a fixture copy. The selftest perturbs ONE declared thing per control."""
    parts = dotted.split(".")
    node = data
    for part in parts[:-1]:
        node = node[part]
    node[parts[-1]] = value


def write_fixture(root: Path, data: dict[str, Any], leak: bool = False) -> None:
    """A minimal tree that satisfies the declared shape, so each control perturbs exactly one thing."""
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "agent" / "adapters").mkdir(parents=True, exist_ok=True)
    (root / "agent" / "skills" / "one").mkdir(parents=True, exist_ok=True)
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "governance").mkdir(parents=True, exist_ok=True)
    (root / "config" / "agent_surface.yaml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    (root / "config" / "task_register.yaml").write_text(
        yaml.safe_dump({"tasks": [{"id": "T-175", "state": "open"}, {"id": "T-1", "state": "done"}]}),
        encoding="utf-8",
    )
    (root / "config" / "decisions.yaml").write_text(
        yaml.safe_dump({"decisions": [{"id": "D-3037", "state": "ACTIVE"}]}), encoding="utf-8"
    )
    (root / "governance" / "delegate_journal.jsonl").write_text("", encoding="utf-8")
    (root / "scripts" / "delegate_journal.py").write_text(
        f'"""reads {SURFACE}"""\n', encoding="utf-8"
    )
    (root / "agent" / "adapters" / "CONTRACT.md").write_text("# the one surface\n", encoding="utf-8")
    (root / "agent" / "skills" / "one" / "SKILL.md").write_text("# a portable skill\n", encoding="utf-8")
    (root / "pipeline").mkdir(parents=True, exist_ok=True)
    (root / "pipeline" / "clean.py").write_text("VALUE = 1\n", encoding="utf-8")
    if leak:
        (root / "pipeline" / "leak.py").write_text("HOME = '~/.config/goose/config.yaml'\n", encoding="utf-8")


def selftest() -> int:
    """Known-answer controls in BOTH directions: the rail must go RED on each defect and GREEN on its absence."""
    live = REPO_ROOT / SURFACE
    checks: list[tuple[str, bool]] = []

    def faults_for(root: Path, surface: Path) -> list[str]:
        return audit(root, surface)[0]

    live_faults, live_loud, _ = audit(REPO_ROOT, live)
    owed = [s for s in as_list(dig(reading(live), "adapter.binding_sites.sites"), "sites") if str(s.get("class")) == "owed"]
    checks.append(("the_live_surface_reads_with_no_fault", not live_faults))
    checks.append(("the_live_reading_is_as_loud_as_its_owed_sites", len(live_loud) == len(owed)))

    with tempfile.TemporaryDirectory(prefix="agent_surface_") as tmp:
        base = Path(tmp)
        good = reading(live)

        def fresh(leak: bool = False) -> tuple[Path, Path, dict[str, Any]]:
            root = base / f"case_{len(checks)}_{'leak' if leak else 'clean'}"
            root.mkdir(parents=True, exist_ok=True)
            data = yaml.safe_load(yaml.safe_dump(good, sort_keys=False))
            set_key(data, "adapter.binding_sites.ceiling", 0)
            set_key(data, "adapter.binding_sites.sites", [])
            set_key(data, "logging.journal", "governance/delegate_journal.jsonl")
            set_key(data, "logging.reader", "scripts/delegate_journal.py")
            set_key(data, "decided", ["D-3037"])
            set_key(data, "rules.portable_artifacts", ["agent/skills/**/SKILL.md"])
            set_key(data, "rules.record_artifacts", ["governance/**"])
            write_fixture(root, data, leak=leak)
            return root, root / SURFACE, data

        root, surface, data = fresh(leak=True)
        found = faults_for(root, surface)
        checks.append(("an_undeclared_client_binding_outside_the_roots_is_a_fault",
                       any("pipeline/leak.py" in f and "BINDS" in f for f in found)))

        root, surface, data = fresh(leak=False)
        (root / "agent" / "adapters" / "leak.py").write_text("HOME = '~/.config/goose/config.yaml'\n", encoding="utf-8")
        found = faults_for(root, surface)
        checks.append(("a_client_binding_inside_the_declared_adapter_root_is_not_a_fault", not found))

        root, surface, data = fresh(leak=True)
        set_key(data, "adapter.binding_sites.ceiling", 1)
        set_key(data, "adapter.binding_sites.sites",
                [{"path": "pipeline/leak.py", "class": "owed", "row": "T-175", "why": "a remedy is owed"}])
        write_fixture(root, data, leak=True)
        faults, loud, _ = audit(root, surface)
        checks.append(("a_declared_site_that_owes_a_remedy_is_loud_not_fatal", not faults and bool(loud)))

        root, surface, data = fresh(leak=True)
        set_key(data, "adapter.binding_sites.ceiling", 1)
        set_key(data, "adapter.binding_sites.sites",
                [{"path": "pipeline/leak.py", "class": "owed", "row": "", "why": "no row"}])
        write_fixture(root, data, leak=True)
        checks.append(("an_owed_site_with_no_named_row_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=True)
        set_key(data, "adapter.binding_sites.ceiling", 1)
        set_key(data, "adapter.binding_sites.sites",
                [{"path": "pipeline/leak.py", "class": "maybe", "why": "an undeclared class"}])
        write_fixture(root, data, leak=True)
        checks.append(("a_site_class_outside_the_declared_vocabulary_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=True)
        set_key(data, "adapter.binding_sites.ceiling", 1)
        set_key(data, "adapter.binding_sites.sites",
                [{"path": "scripts/ghost.py", "class": "owed", "row": "T-175", "why": "a site that is not there"}])
        write_fixture(root, data, leak=True)
        checks.append(("a_declared_site_that_does_not_exist_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        set_key(data, "adapter.binding_sites.ceiling", 1)
        set_key(data, "adapter.binding_sites.sites",
                [{"path": "pipeline/clean.py", "class": "prose_citation", "why": "a stale declaration"}])
        write_fixture(root, data, leak=False)
        checks.append(("a_declared_site_that_no_longer_carries_a_shape_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=True)
        set_key(data, "adapter.binding_sites.ceiling", 1)
        set_key(data, "adapter.binding_sites.sites",
                [{"path": "pipeline/leak.py", "class": "owed", "row": "T-999", "why": "a row that is not there"}])
        write_fixture(root, data, leak=True)
        checks.append(("an_owed_site_naming_a_row_that_does_not_exist_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=True)
        set_key(data, "adapter.binding_sites.ceiling", 0)
        write_fixture(root, data, leak=True)
        checks.append(("the_register_may_not_grow_past_its_declared_ceiling", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        (root / "agent" / "skills" / "one" / "SKILL.md").write_text("# run this in goose\n", encoding="utf-8")
        checks.append(("a_portable_artifact_that_names_a_client_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        set_key(data, "rules.portable_artifacts", ["agent/skills/**/NOTHING.md"])
        write_fixture(root, data, leak=False)
        checks.append(("a_declared_portable_glob_that_matches_no_file_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        set_key(data, "adapter.external_roots", ["config/goose/config.yaml"])
        write_fixture(root, data, leak=False)
        checks.append(("an_external_root_written_inside_the_repository_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        set_key(data, "adapter.roots", ["agent/adapters/", "agent/absent/"])
        write_fixture(root, data, leak=False)
        checks.append(("an_in_repo_adapter_root_that_does_not_resolve_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        set_key(data, "decided", ["D-9999"])
        write_fixture(root, data, leak=False)
        checks.append(("a_cited_decision_that_the_register_does_not_carry_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        (root / "scripts" / "delegate_journal.py").write_text('"""a reader that names no home"""\n', encoding="utf-8")
        checks.append(("a_declared_journal_reader_that_does_not_name_the_one_home_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        set_key(data, "logging.reader", "scripts/absent_reader.py")
        write_fixture(root, data, leak=False)
        checks.append(("a_declared_journal_reader_that_does_not_exist_is_a_fault", bool(faults_for(root, surface))))

        root, surface, data = fresh(leak=False)
        del data["rules"]["binding_shapes"]
        write_fixture(root, data, leak=False)
        try:
            faults_for(root, surface)
            checks.append(("an_absent_required_key_is_fatal_not_defaulted", False))
        except SystemExit:
            checks.append(("an_absent_required_key_is_fatal_not_defaulted", True))

    for label, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    passed = sum(1 for _, ok in checks if ok)
    print(f"selftest: {passed}/{len(checks)}")
    return RC_OK if passed == len(checks) else RC_FAULT


def main(argv: list[str]) -> int:
    """Dispatch: the reading, or the known-answer controls. An unknown flag is fatal (C16)."""
    if "--selftest" in argv:
        return selftest()
    if argv:
        fatal(f"unknown argument(s) {argv} - this rail reads one declared home and names no option")
    return report(REPO_ROOT, REPO_ROOT / SURFACE)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
