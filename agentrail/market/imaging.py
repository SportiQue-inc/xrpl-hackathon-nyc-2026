"""Pseudonymization of synthetic imaging before it is offered (DICOM-like dicts).

Steps, in order (agentrail/deid.py holds the primitives):
  gate     an image with burned-in text is blocked, not offered
  header   direct identifiers removed; the patient becomes a per-study participant number
  uids     study, series and instance UIDs remapped by HMAC (own secret) into 2.25.<integer>
  dates    shifted by one consistent per-subject offset (intervals are kept)
  age      bucketed (<40 / 40-64 / 65+)
  deface   the face region of head scans is zeroed

Every output carries a record of the profile version and the steps applied. This lowers the risk
that an image is linked back to a person; it does not remove it.
"""
from __future__ import annotations

import datetime as dt

from .. import deid

PROFILE = "agentrail-imaging-pseudo-v1 (DICOM PS3.15 basic profile subset)"
UIDS = ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID")


def deidentify(d: dict, person: str, participant_number: str = "UQ-0000") -> dict | None:
    if deid.burned_in_gate(d):
        return None
    out = {k: v for k, v in d.items() if k not in deid.NEVER and k != "PatientAge"}
    steps = ["header: direct identifiers removed; patient -> participant number"]
    out["PatientIdentityRemoved"] = "YES"
    out["ParticipantNumber"] = participant_number
    for u in UIDS:
        if u in d:
            out[u] = deid.remap_uid(d[u])
    steps.append("uids: HMAC remap into 2.25.*")
    if "StudyDate" in d:
        shift = deid.date_shift_days(person)
        out["StudyDate"] = (dt.date.fromisoformat(d["StudyDate"]) - dt.timedelta(days=shift)).isoformat()
        steps.append("dates: one per-subject shift")
    if "PatientAge" in d:
        out["AgeGroup"] = deid.age_group(d["PatientAge"])
        steps.append("age: bucketed")
    px = [row[:] for row in d.get("pixels", [])]
    if d.get("BodyPartExamined") == "HEAD":
        h = len(px)
        for r in px[h // 2:]:
            r[: len(r) // 2] = [0] * (len(r) // 2)
        steps.append("deface: face region zeroed")
    out["pixels"] = px
    out["pseudonymization"] = {"profile": PROFILE, "steps": steps}
    return out
