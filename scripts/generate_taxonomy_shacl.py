#!/usr/bin/env python3
"""scripts/generate_taxonomy_shacl.py — D2546: SHACL formalization of canonicals.

Reads config/taxonomy_v5.yaml and emits config/taxonomy_shacl.ttl — SHACL shapes
that formalize the taxonomy ontology:
  - 43 domain + 61 discipline canonicals as closed, disjoint classes
  - kind-safety (D2500): a label must not be canonical in BOTH axes
  - R14 persistent-object stamps (schema_version, taxonomy_version, gen_model)

Run: python3 scripts/generate_taxonomy_shacl.py
The TTL is DERIVED from the YAML — regenerate, never hand-edit (C12 single source).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402


def _iri(s: str) -> str:
    out = s.lower().replace(" & ", "-and-").replace(" ", "-").replace("/", "-")
    return "".join(ch for ch in out if ch.isalnum() or ch == "-")


def _list(items: list[str]) -> str:
    return " ".join(f'"{i}"' for i in items)


def main() -> int:
    tax = yaml.safe_load(open(_ROOT / "config" / "taxonomy_v5.yaml", encoding="utf-8"))
    domains = [d["canonical"] for d in tax["domains"]]
    disciplines = [d["canonical"] for d in tax["disciplines"]]
    version = tax.get("version", "v5.5")

    ttl = f"""# config/taxonomy_shacl.ttl — SHACL formalization of Maxwell OS taxonomy (D2546)
# AUTO-GENERATED from config/taxonomy_v5.yaml — do NOT edit by hand.
# Regenerate: python3 scripts/generate_taxonomy_shacl.py
# Canonicals: {len(domains)} domains + {len(disciplines)} disciplines = {len(domains) + len(disciplines)} (taxonomy {version})

@prefix maxwell: <https://maxwell.os/taxonomy#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# ── R14: persistent-object stamps (every committed FB) ─────────────────────
maxwell:FoundationBlockShape
    a sh:NodeShape ;
    sh:targetClass maxwell:FoundationBlock ;
    sh:property [
        sh:path maxwell:fb_id ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
    ] ;
    sh:property [
        sh:path maxwell:schema_version ;
        sh:minCount 1 ;
    ] ;
    sh:property [
        sh:path maxwell:taxonomy_version ;
        sh:minCount 1 ;
        sh:in ( "{version}" ) ;
    ] .

# ── Closed canonical sets ──────────────────────────────────────────────────
maxwell:CanonicalDomainShape
    a sh:NodeShape ;
    sh:targetClass maxwell:CanonicalDomain ;
    sh:closed true ;
    sh:property [
        sh:path maxwell:label ;
        sh:in ( {_list(domains)} ) ;
    ] .

maxwell:CanonicalDisciplineShape
    a sh:NodeShape ;
    sh:targetClass maxwell:CanonicalDiscipline ;
    sh:closed true ;
    sh:property [
        sh:path maxwell:label ;
        sh:in ( {_list(disciplines)} ) ;
    ] .

# ── Kind-safety (D2500): domain and discipline canonicals are DISJOINT ─────
maxwell:CanonicalDomain
    a rdfs:Class ;
    owl:disjointWith maxwell:CanonicalDiscipline .
maxwell:CanonicalDiscipline
    a rdfs:Class ;
    owl:disjointWith maxwell:CanonicalDomain .
"""
    out = _ROOT / "config" / "taxonomy_shacl.ttl"
    out.write_text(ttl, encoding="utf-8")
    print(f"✅ Wrote {out} ({len(domains)} domains + {len(disciplines)} disciplines, taxonomy {version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
