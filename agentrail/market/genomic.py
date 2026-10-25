"""Genomic outputs computed on the provider's side. Raw variants (positions, alleles) never leave in
an aggregate trade: only per-locus counts of alternate alleles."""
from __future__ import annotations


def aggregate(rows: list[dict], cols: list, loci: list) -> list[dict]:
    out = []
    for c in cols:
        if not c.startswith("genome."):
            continue
        variants = [v for r in rows for v in (r.get(c) or [])]
        for g in loci:
            alt = sum({"0/0": 0, "0/1": 1, "1/1": 2}.get(v["gt"], 0) for v in variants if v["gene"] == g)
            out.append({"column": c, "locus": g, "alt_alleles": alt, "carrier": alt > 0})
    return out
