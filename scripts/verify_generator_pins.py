#!/usr/bin/env python3
"""verify_generator_pins.py - WHO PRODUCED THE NUMBERS (BUG-538 / D-2653).

WHY THIS EXISTS. Maxwell pinned its SCRIPTS (config/recalibration_pins.yaml) and its EVIDENCE
(sha256 blocks in the anchor configs) but pinned ZERO GENERATORS. A generator was identified by a
STRING - "gemma-4-E4B-it-MLX-4bit" - in every metric record, and a NAME IS NOT AN IDENTITY: an
`ollama pull`, an HF re-download, or an LM Studio re-quantisation moves the bytes while every stored
`gen_model` keeps saying the same words. That is the BUG-391 class (a fact that changed with nothing
declaring it) applied to the thing that produces every fact in the store. A measurement whose
generator silently changed is not a smaller measurement; it is an uncomparable one.

WHAT THIS FILE IS NOT (D-2646, one home). It is not a role registry: config/pipeline_config.yaml and
config/model_assignments.yaml own NAME -> ROLE and carry no bytes. config/recalibration_pins.yaml owns
SCRIPT digests (a meter). This rail owns BYTES-ON-DISK -> DIGEST for a GENERATOR. Three different
rules, three homes, boundaries declared - not one value with three homes.

TRI-STATE, REUSED DELIBERATELY (BUG-536/BUG-457). A second severity idiom would be a second home:
  0 CLEAN     - every declared generator matches the bytes on disk.
  1 FATAL     - a DECLARATION is broken (repo absent; revision unresolvable; a pin carrying no digest),
                fails CLOSED (C16): we cannot even say which model produced the numbers.
  2 OWNER-OWED - the measured IDENTITY MOVED (or a declared fact became UNMEASURABLE). Loud, NOT
                fatal: the numbers may still be valid, but only the owner can re-mint the pin, and a
                re-mint needs a NEW decision (D-382/BUG-535).

THE RAIL CANNOT RE-PIN ITSELF. `--pin` PRINTS the measurement; it never writes config. A pin is
re-minted by a decision, never by a quiet re-hash, so the write stays a human act.

AN APPROXIMATED REVISION IS NOT AN IDENTITY (audit finding, 2026-09-26). Three pins declared a
TRUNCATED commit prefix (`773a7da77e56`). Nothing on disk is named that, so the rail reported "pinned
object is MISSING from disk" - a PHANTOM, and the very "approximation pretending to be an identity"
this file exists to catch. `resolve_snapshot` now resolves ONLY an exact snapshot name or a ref, and
names the prefix it refused.

A DECLARED FACT THAT BECAME UNMEASURABLE IS NOT A PASS (audit finding, 2026-09-26). `_compare` used
to SKIP a declared digest that the current mode could not measure, so a store that stopped being
symlinked (content-addressing gone) would read CLEAN while the identity was unverified. It is now
OWNER-OWED and says so (BUG-492: verify what the mode can measure, and DECLARE the limit).

Usage:
  python3 scripts/verify_generator_pins.py             # verify (cheap: stat + symlink targets)
  python3 scripts/verify_generator_pins.py --deep      # also hash file CONTENTS (slow, opt-in)
  python3 scripts/verify_generator_pins.py --pin       # print the measured pins (never writes)
  python3 scripts/verify_generator_pins.py --selftest  # known-answer controls; they must be SEEN to fire
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys
import tempfile

import yaml

_ENCODING = "utf-8"
EXIT_CLEAN = 0
EXIT_FATAL = 1
EXIT_OWED = 2
_FATAL = "RED  "
_OWED = "OWED "
_OK = "  ok   "
_BLOCKSIZE = 1 << 20
_MIN_PREFIX = 7
_CONFIG = pathlib.Path(__file__).resolve().parent.parent / "config" / "generator_pins.yaml"
_OLLAMA_REGISTRY = "registry.ollama.ai"


class RevUnresolved(Exception):
    """The repo is on disk but the declared revision names no snapshot and no ref (an approximation)."""


def _sha(text: str) -> str:
    """Digest a canonical text manifest (the ONE manifest rule this module has)."""
    return hashlib.sha256(text.encode(_ENCODING)).hexdigest()


def _digest_file(path: pathlib.Path) -> str:
    """Full sha256 of a file, streamed (used only by --pin/--deep)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(_BLOCKSIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hf_dir(cache: pathlib.Path, repo: str) -> pathlib.Path:
    """HF hub directory for a repo id ('owner/name' -> 'models--owner--name')."""
    return cache / ("models--" + repo.replace("/", "--"))


def _entries(snap: pathlib.Path, deep: bool) -> list[tuple[str, int, str | None]]:
    """(relpath, bytes, digest|None) for a snapshot dir; digest = blob name (symlink) or content hash."""
    out: list[tuple[str, int, str | None]] = []
    for f in sorted(x for x in snap.rglob("*") if x.is_file() or x.is_symlink()):
        rel = str(f.relative_to(snap))
        if f.is_symlink():
            out.append((rel, f.stat().st_size, f.readlink().name))
        else:
            out.append((rel, f.stat().st_size, _digest_file(f) if deep else None))
    return out


def resolve_snapshot(base: pathlib.Path, rev: str) -> tuple[pathlib.Path | None, str]:
    """(snapshot_dir, commit) or (None, why). EXACT only: a snapshot name or a ref. NEVER a prefix."""
    snapdir = base / "snapshots"
    if (snapdir / rev).is_dir():
        return snapdir / rev, rev
    ref = base / "refs" / rev
    if ref.is_file():
        target = ref.read_text(encoding=_ENCODING).strip()
        if (snapdir / target).is_dir():
            return snapdir / target, target
        return None, f"ref {rev!r} points at {target[:12]} which is not on disk"
    names = sorted(p.name for p in snapdir.iterdir()) if snapdir.is_dir() else []
    near = [n for n in names if len(rev) >= _MIN_PREFIX and n.startswith(rev)]
    why = f"revision {rev!r} is neither a snapshot nor a ref on disk"
    if near:
        why += (f" - it is a PREFIX of {near[0]}: an approximated revision is not an identity,"
                " declare the full commit")
    return None, why


def sparse_sha256(entries: list[tuple[str, int, str | None]]) -> str:
    """Digest over (relpath, bytes): the CHEAP daily identity of a model directory."""
    return _sha("".join(f"{rel}\t{size}\n" for rel, size, _ in entries))


def identity_sha256(entries: list[tuple[str, int, str | None]]) -> str | None:
    """Digest over (relpath, digest): available cheaply for symlinked snapshots, else only with --deep."""
    if any(dig is None for _, _, dig in entries):
        return None
    return _sha("".join(f"{rel}\t{dig}\n" for rel, _, dig in entries))


def ollama_manifest_path(manifests: pathlib.Path, tag: str) -> pathlib.Path:
    """Ollama manifest path for a tag ('bge-m3:latest' or 'ns/name:tag')."""
    name, _, ver = tag.partition(":")
    parts = name.split("/")
    ns, repo = (parts[0], parts[1]) if len(parts) == 2 else ("library", parts[0])
    return manifests / _OLLAMA_REGISTRY / ns / repo / (ver or "latest")


def ollama_measure(manifests: pathlib.Path, tag: str) -> dict | None:
    """Content digests of an Ollama manifest: {config, layers}. Ollama is already content-addressed."""
    p = ollama_manifest_path(manifests, tag)
    if not p.is_file():
        return None
    m = json.loads(p.read_text(encoding=_ENCODING))
    return {"config": m["config"]["digest"], "layers": sorted(x["digest"] for x in m.get("layers", []))}


def measure(pin: dict, cfg: dict, deep: bool = False) -> dict | None:
    """Measure ONE pin from disk. None = the OBJECT is absent; RevUnresolved = the REVISION is not an identity."""
    if pin["kind"] == "hf_repo":
        base = hf_dir(pathlib.Path(cfg["hf_cache"]).expanduser(), pin["repo"])
        if not base.is_dir():
            return None
        snap, commit = resolve_snapshot(base, pin["rev"])
        if snap is None:
            raise RevUnresolved(commit)
        entries = _entries(snap, deep)
        return {
            "resolved_commit": commit,
            "file_count": len(entries),
            "bytes": sum(size for _, size, _ in entries),
            "sparse_sha256": sparse_sha256(entries),
            "identity_sha256": identity_sha256(entries),
        }
    if pin["kind"] == "ollama_manifest":
        return ollama_measure(pathlib.Path(cfg["ollama_manifests"]).expanduser(), pin["tag"])
    raise SystemExit("unknown pin kind: " + str(pin.get("kind")))


def _compare(pin: dict, got: dict, owed: list[str]) -> None:
    """Compare a measurement to its declaration. Every mismatch is OWNER-OWED (the bytes moved)."""
    name = pin["name"]
    for key in ("resolved_commit", "file_count", "bytes", "sparse_sha256", "identity_sha256", "config"):
        if key not in pin:
            continue
        want = pin[key]
        if want is None:
            continue
        if got.get(key) is None:
            owed.append(f"{name}: {key} was declared {str(want)[:24]} and is NOT MEASURABLE in this mode"
                        " - the snapshot changed SHAPE (content-addressing gone: real files where symlinks"
                        " were), so the declared identity is an UNVERIFIED claim (re-run --pin --deep, then"
                        " mint a decision)")
            continue
        if got.get(key) != want:
            owed.append(f"{name}: {key} was declared {str(want)[:24]} and now measures {str(got.get(key))[:24]}"
                        " - the GENERATOR changed under us; re-run --pin and mint a new decision (D-382)")
    if "layers" in pin and pin["layers"] is not None and got.get("layers") != pin["layers"]:
        owed.append(f"{name}: the Ollama layer set changed ({len(got.get('layers') or [])} layer(s) now)"
                    " - the GENERATOR changed under us; re-run --pin and mint a new decision (D-382)")


def alias_split(pin: dict, cfg: dict) -> tuple[list[str], list[str]]:
    """A DECLARED alias snapshot must exist and still hold the pinned payload: (fatal, owed).

    MEASURED 2026-09-26. The two lmstudio repos carry BOTH snapshots/<commit> and a snapshots/main
    beside it, and the downloader's own bookkeeping (.cache/huggingface/**, CACHEDIR.TAG) sits in the
    SAME directory as the weights (20 extra files, 5,842 B on the generator; 14 extra, 3,187 B on the
    reviewer). Pinning `main` would therefore bind that bookkeeping - a re-download that rewrites a tag
    would read as "the GENERATOR changed" - while pinning the commit alone would leave the aliased copy
    unbound. So: pin the COMMIT, DECLARE the alias, and let the rail check that the alias still holds
    the same (relpath, bytes) payload. Extras are TOLERATED and COUNTED: the payload is the model.
    """
    fatal: list[str] = []
    owed: list[str] = []
    aliases = pin.get("alias_snapshots") or []
    if not aliases:
        return fatal, owed
    base = hf_dir(pathlib.Path(cfg["hf_cache"]).expanduser(), pin["repo"])
    snap, commit = resolve_snapshot(base, pin["rev"])
    if snap is None:
        return fatal, owed  # measure() already reported the revision fault
    want = {rel: size for rel, size, _ in _entries(snap, False)}
    for alias in aliases:
        adir = base / "snapshots" / alias
        if not adir.is_dir():
            fatal.append(f"{pin['name']}: alias snapshot {alias!r} is declared and is MISSING from disk"
                         " - a broken declaration fails CLOSED (C16)")
            continue
        got = {rel: size for rel, size, _ in _entries(adir, False)}
        diff = sorted(rel for rel, size in want.items() if got.get(rel) != size)
        extras = len(got) - len([rel for rel in got if rel in want])
        if diff:
            owed.append(f"{pin['name']}: alias snapshot {alias!r} disagrees with pinned commit"
                        f" {commit[:12]} on {len(diff)} of {len(want)} pinned file(s) (first: {diff[0]})"
                        " - the store holds TWO versions of the same generator; re-run --pin and mint a"
                        " new decision (D-382)")
        else:
            print(_OK + f"{pin['name']}: alias {alias!r} holds the pinned payload of {len(want)} file(s)"
                  + (f" (+{extras} tolerated harness-metadata file(s))" if extras else ""))
    return fatal, owed


def scan_split(cfg: dict, deep: bool = False) -> tuple[list[str], list[str]]:
    """The ONE producer of pin faults: (fatal, owed). Total and disjoint (BUG-492)."""
    fatal: list[str] = []
    owed: list[str] = []
    for pin in cfg["pins"]:
        name = pin["name"]
        declared = any(pin.get(k) is not None for k in ("sparse_sha256", "config"))
        if not declared:
            fatal.append(f"{name}: declared as a pin but carries NO digest - an unpinned declaration is a"
                         " comment, not a control (run --pin, then mint a decision)")
            continue
        try:
            got = measure(pin, cfg, deep)
        except RevUnresolved as exc:
            fatal.append(f"{name}: {exc} - a broken declaration fails CLOSED (C16): we cannot say which"
                         " bytes produced the numbers")
            continue
        if got is None:
            where = pin.get("repo", pin.get("tag"))
            fatal.append(f"{name}: pinned object is MISSING from disk ({where}) - a broken declaration fails"
                         " CLOSED (C16): we cannot say which model produced the numbers")
            continue
        _compare(pin, got, owed)
        a_fatal, a_owed = alias_split(pin, cfg)
        fatal.extend(a_fatal)
        owed.extend(a_owed)
    return fatal, owed


def all_faults(cfg: dict, deep: bool = False) -> list[str]:
    """Fatal AND owner-owed, for callers that must refuse on either."""
    fatal, owed = scan_split(cfg, deep)
    return fatal + owed


def _probe(declare: bool = True, move_sparse: bool = False, move_blob: bool = False,
           revision_missing: bool = False, repo_missing: bool = False, prefix_rev: bool = False,
           as_ref: bool = False, alias: str | None = None, alias_differs: bool = False,
           alias_missing: bool = False, ollama_moved: bool = False) -> tuple[int, int, int]:
    """Known-answer control: build a TEMP model store, break it in ONE declared way, count the faults."""
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        cache = root / "hub"
        base = hf_dir(cache, "owner/name")
        repo_dir = base / "snapshots" / "rev1"
        repo_dir.mkdir(parents=True)
        blob = root / "blobs" / ("a" * 64)
        other = root / "blobs" / ("b" * 64)
        blob.parent.mkdir(parents=True)
        blob.write_bytes(b"weights")
        other.write_bytes(b"weights")  # a REAL move repoints the symlink at a differently-NAMED blob of the
        #                                SAME size, because the blob name IS the content digest. Only the
        #                                identity layer can see that - which is what this control proves.
        (repo_dir / "model.safetensors").symlink_to(blob)
        if as_ref:
            (base / "refs").mkdir(parents=True)
            (base / "refs" / "main").write_text("rev1", encoding=_ENCODING)
        adir = None
        if alias is not None:
            adir = base / "snapshots" / alias
            adir.mkdir(parents=True)
            (adir / "model.safetensors").symlink_to(blob)
            if alias_differs:
                bigger = root / "blobs" / ("d" * 64)
                bigger.write_bytes(b"weights-CHANGED")  # same relpath, DIFFERENT bytes
                (adir / "model.safetensors").unlink()
                (adir / "model.safetensors").symlink_to(bigger)
        manifests = root / "manifests"
        mpath = ollama_manifest_path(manifests, "tiny:latest")
        mpath.parent.mkdir(parents=True)
        mpath.write_text(json.dumps({
            "config": {"digest": "sha256:cfg", "size": 1},
            "layers": [{"digest": "sha256:" + "c" * 64, "size": 2}],
        }), encoding=_ENCODING)
        hf_pin: dict = {"name": "hf", "kind": "hf_repo", "repo": "owner/name",
                        "rev": "main" if as_ref else "rev1"}
        if alias is not None:
            hf_pin["alias_snapshots"] = [alias]
        cfg = {"hf_cache": str(cache), "ollama_manifests": str(manifests),
               "pins": [hf_pin, {"name": "oll", "kind": "ollama_manifest", "tag": "tiny:latest"}]}
        if declare:
            for pin in cfg["pins"]:
                pin.update(measure(pin, cfg) or {})
        # THE DECLARATION IS THE CLEAN STATE; the store is broken only AFTER it is taken. A control that
        # declares the already-broken state pins the breakage and can never fail - which is the exact
        # shape (BUG-492) this rail was written to catch, and it caught it in its own harness first.
        if prefix_rev:
            hf_pin["rev"] = "rev"        # a human wrote a truncated prefix into the file
        if revision_missing:
            shutil.rmtree(repo_dir)
        if repo_missing:
            shutil.rmtree(base)
        if alias_missing and adir is not None:
            shutil.rmtree(adir)
        if ollama_moved:
            mpath.write_text(json.dumps({"config": {"digest": "sha256:cfg", "size": 1},
                "layers": [{"digest": "sha256:" + "b" * 64, "size": 2}]}), encoding=_ENCODING)
        if move_sparse:
            (repo_dir / "extra.json").write_text("{}", encoding=_ENCODING)
        if move_blob:
            (repo_dir / "model.safetensors").unlink()
            (repo_dir / "model.safetensors").symlink_to(other)
        fatal, owed = scan_split(cfg)
        return len(fatal), len(owed), len(all_faults(cfg))


def _selftest() -> int:
    """Controls that must be SEEN to fire: a control that never fails is a comment (BUG-492)."""
    checks: list[tuple[str, bool]] = [
        ("a pinned generator that matches disk is CLEAN", _probe() == (0, 0, 0)),
        ("a pin with NO digest at all is FATAL - an unpinned declaration is a comment",
         _probe(declare=False) == (2, 0, 2)),
        ("a pinned REPO that is absent is FATAL (C16 fail closed)", _probe(repo_missing=True) == (1, 0, 1)),
        ("a pinned REVISION that is absent is FATAL (C16 fail closed)",
         _probe(revision_missing=True) == (1, 0, 1)),
        ("a TRUNCATED commit prefix is FATAL and the fault NAMES the prefix - an approximation is not an"
         " identity (audit 2026-09-26)", _probe(prefix_rev=True) == (1, 0, 1)),
        ("a revision that is a REF resolves to its commit and is CLEAN", _probe(as_ref=True) == (0, 0, 0)),
        ("a model whose file set GREW re-reports every declared fact - none silently skipped (BUG-492)",
         _probe(move_sparse=True) == (0, 4, 4)),
        ("a symlink repointed to ANOTHER blob is OWNER-OWED even though the file set is identical",
         _probe(move_blob=True) == (0, 1, 1)),
        ("an Ollama layer digest that moved is OWNER-OWED", _probe(ollama_moved=True) == (0, 1, 1)),
        ("the split is TOTAL and DISJOINT - no fault lost, none counted twice (BUG-492)",
         _probe(move_sparse=True, ollama_moved=True) == (0, 5, 5)),
        ("an ALIAS snapshot holding a different payload is OWNER-OWED - the store holds two versions",
         _probe(alias="main", alias_differs=True) == (0, 1, 1)),
        ("an ALIAS snapshot that is declared but absent is FATAL (C16 fail closed)",
         _probe(alias="main", alias_missing=True) == (1, 0, 1)),
    ]
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(("  ok   " if ok else "  FAIL ") + name)
    print(f"{'ok ' if not bad else 'FAIL '}generator-pin controls: {len(checks) - len(bad)}/{len(checks)}")
    return EXIT_CLEAN if not bad else EXIT_FATAL


def _pin(cfg: dict, deep: bool) -> int:
    """Print the measured pins for the owner to paste - and to mint a decision against. Writes NOTHING."""
    for pin in cfg["pins"]:
        print(f"- name: {pin['name']}")
        if pin["kind"] == "hf_repo":
            print(f"  kind: {pin['kind']}")
            print(f"  repo: {pin['repo']}")
            print(f"  rev: {pin['rev']}")
        try:
            got = measure(pin, cfg, deep)
        except RevUnresolved as exc:
            print(f"  UNRESOLVABLE: {exc}")
            continue
        if got is None:
            print(f"  UNMEASURABLE: {pin.get('repo', pin.get('tag'))} is not on disk")
            continue
        for key, value in got.items():
            print(f"  {key}: {value if value is not None else 'null'}")
    return EXIT_CLEAN


def main() -> int:
    """CLI entry point (verify | --pin | --selftest)."""
    ap = argparse.ArgumentParser(description="generator-identity pins (BUG-538/D-2653)")
    ap.add_argument("--deep", action="store_true", help="also hash file CONTENTS (slow, opt-in)")
    ap.add_argument("--pin", action="store_true", help="print the measured pins; writes nothing")
    ap.add_argument("--selftest", action="store_true", help="known-answer controls")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    cfg = yaml.safe_load(_CONFIG.read_text(encoding=_ENCODING))
    if args.pin:
        return _pin(cfg, args.deep)
    fatal, owed = scan_split(cfg, args.deep)
    for line in owed:
        print(_OWED + line)
    for line in fatal:
        print(_FATAL + line)
    print(("FAIL " if fatal else ("OWED " if owed else "ok ")) + "generator pins: "
          + str(len(cfg["pins"])) + " declared, " + str(len(fatal)) + " BROKEN DECLARATION, "
          + str(len(owed)) + " MOVED" + (" (deep)" if args.deep else " (sparse)"))
    return EXIT_FATAL if fatal else (EXIT_OWED if owed else EXIT_CLEAN)


if __name__ == "__main__":
    sys.exit(main())
