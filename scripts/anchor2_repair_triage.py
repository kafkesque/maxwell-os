#!/usr/bin/env python3
"""ANCHOR-2 repair-queue triage: bucket the disagreements by CAUSE, not by row.

Reads the human blind sheet + the pipeline key and classifies each disagreed row:
  A. boundary/definition  - discipline differs (the label semantics or the boundary note is wrong)
  B. domain under-prediction - human named domains the pipeline never emitted
  C. domain over-prediction  - the pipeline emitted domains the human rejected
Writes governance/anchor2_repair_triage_20260921.md. Read-only over the source files.
"""
import csv, json, pathlib, collections

R = pathlib.Path(__file__).resolve().parent.parent


def norm(v: object) -> str:
    return " ".join(str(v or "").strip().lower().replace("_", " ").replace("-", " ").split())


def main() -> int:
    sheet = list(csv.DictReader((R / "governance" / "ANCHOR2_BLIND_SHEET_20260920.csv").open(encoding="utf-8")))
    key = json.loads((R / "governance" / "ANCHOR2_KEY_20260920.json").read_text(encoding="utf-8"))["key"]
    buckets = collections.defaultdict(list)
    tally = collections.Counter()
    for row in sheet:
        fb = row["fb_id"]
        k = key.get(fb) or {}
        hd, pd = norm(row.get("discipline_verdict")), norm(k.get("pipeline_discipline"))
        hdom = {norm(x) for x in str(row.get("domains_verdict") or "").split(",") if norm(x)}
        pdom = {norm(x) for x in (k.get("pipeline_domains") or [])}
        miss, extra = hdom - pdom, pdom - hdom
        if hd and pd and hd != pd:
            buckets["A_boundary"].append((row["row"], hd, pd))
            tally["A_boundary"] += 1
        if miss:
            buckets["B_domain_under"].append((row["row"], sorted(miss)))
            tally["B_domain_under"] += 1
        if extra:
            buckets["C_domain_over"].append((row["row"], sorted(extra)))
            tally["C_domain_over"] += 1
    lines = ["# ANCHOR-2 repair-queue triage (generated)", "",
             "Buckets are by CAUSE. A row can appear in more than one (see the R2 sheet rationale).", ""]
    for name in ("A_boundary", "B_domain_under", "C_domain_over"):
        lines.append("## %s - %d rows" % (name, tally[name]))
        for entry in buckets[name]:
            lines.append("- " + json.dumps(entry, ensure_ascii=False))
        lines.append("")
    miss_c = collections.Counter(d for _r, ds in buckets["B_domain_under"] for d in ds)
    extra_c = collections.Counter(d for _r, ds in buckets["C_domain_over"] for d in ds)
    lines += ["## Systematic menu gaps (fix the MENU, not the rows)", "",
              "never-emitted by pipeline: " + json.dumps(miss_c.most_common(12)), "",
              "falsely-emitted by pipeline: " + json.dumps(extra_c.most_common(12)), ""]
    out = R / "governance" / "anchor2_repair_triage_20260921.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("A_boundary", tally["A_boundary"], "B_under", tally["B_domain_under"], "C_over", tally["C_domain_over"])
    print("never-emitted:", miss_c.most_common(6))
    print("falsely-emitted:", extra_c.most_common(6))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
