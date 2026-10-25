"""The health data catalog: every column a study may ask for, with its sensitivity tier, the data
use (DUO) limits it carries, and how long a recipient may keep it.

  T0  everyday       wearable and phone measures (steps, sleep, resting heart rate, weight)
  T1  lifestyle      meals, medication-taking logs, mood, surveys
  T2  clinical       diagnoses, prescriptions, lab results, hospital vitals
  T3  highly sensitive  genomic variants, CT and MRI imaging, mental health, reproductive health

Every value here is synthetic, the genomic variants and the images included. T0 and T1 come from
the person's own store (UniQdata); T2 and T3 have no concept there and are an engine-side source.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

TIERS = ("T0", "T1", "T2", "T3")
TIER_NAME = {"T0": "everyday", "T1": "lifestyle", "T2": "clinical", "T3": "highly sensitive"}
# Re-identification risk class per tier (a label for the owner, not a measured probability).
RISK = {"T0": "low", "T1": "moderate", "T2": "high", "T3": "identifying by itself"}
RETENTION_DAYS = {"T0": 365, "T1": 365, "T2": 180, "T3": 90}
DELETION = {
    "T0": "delete at retention end; signed deletion confirmation",
    "T1": "delete at retention end; signed deletion confirmation",
    "T2": "delete at retention end; signed deletion confirmation; on withdrawal, deletion request within 30 days",
    "T3": "plaintext only in the recipient's controlled workspace; view keys expire; on withdrawal, keys stop and "
          "a deletion request goes out",
}

# GA4GH Data Use Ontology codes used by the catalog.
DUO = {
    "DUO:0000042": "GRU - general research use",
    "DUO:0000006": "HMB - health or medical or biomedical research",
    "DUO:0000007": "DS - disease specific research",
    "DUO:0000016": "GSO - genetic studies only",
    "DUO:0000021": "IRB - ethics approval required",
    "DUO:0000044": "NPOA - population origins or ancestry research prohibited",
    "DUO:0000046": "NCU - non-commercial use only",
    "DUO:0000022": "GS - geographical restriction",
    "DUO:0000025": "TS - time limit on use",
}
# Codes every request for a column of this tier must carry (restrictions travel with the data).
TIER_DUO = {"T0": ["DUO:0000006"], "T1": ["DUO:0000006"], "T2": ["DUO:0000006", "DUO:0000021"],
            "T3": ["DUO:0000006", "DUO:0000021", "DUO:0000025", "DUO:0000044"]}


@dataclass(frozen=True)
class Column:
    id: str
    label: str
    tier: str
    kind: str                     # numeric | category | text | variants | image | record
    unit: str = ""
    lo: float | None = None
    hi: float | None = None
    duo_extra: tuple = ()         # codes on top of the tier's (genomic: GSO)
    source: str = "uniqdata"      # uniqdata | engine

    @property
    def duo(self) -> list[str]:
        return sorted(set(TIER_DUO[self.tier]) | set(self.duo_extra))

    @property
    def retention_days(self) -> int:
        return RETENTION_DAYS[self.tier]

    @property
    def deletion(self) -> str:
        return DELETION[self.tier]

    def card(self) -> dict:
        return {"id": self.id, "label": self.label, "tier": self.tier, "tier_name": TIER_NAME[self.tier],
                "kind": self.kind, "unit": self.unit, "range": [self.lo, self.hi], "duo": self.duo,
                "retention_days": self.retention_days, "deletion": self.deletion, "risk": RISK[self.tier],
                "source": self.source}


def _n(i, label, tier, unit, lo, hi, **k):
    return Column(i, label, tier, "numeric", unit, lo, hi, **k)


GENOMIC = ("DUO:0000016",)
CATALOG: dict[str, Column] = {c.id: c for c in [
    # T0 everyday
    _n("steps.daily", "Steps", "T0", "steps/day", 0, 60000),
    _n("sleep.daily", "Sleep duration", "T0", "min/day", 0, 1000),
    _n("sleep.efficiency", "Sleep efficiency", "T0", "%", 40, 100),
    _n("heart_rate.daily", "Resting heart rate", "T0", "bpm", 25, 220),
    _n("hrv.daily", "Heart rate variability (RMSSD)", "T0", "ms", 5, 200),
    _n("activity.minutes", "Active minutes", "T0", "min/day", 0, 600),
    _n("active_energy.daily", "Active energy", "T0", "kcal/day", 0, 5000),
    _n("weight", "Body weight", "T0", "kg", 30, 250),
    _n("body_fat", "Body fat", "T0", "%", 3, 60),
    _n("spo2.night", "Overnight SpO2", "T0", "%", 80, 100),
    _n("resp_rate.night", "Overnight respiratory rate", "T0", "breaths/min", 6, 30),
    _n("skin_temp.delta", "Skin temperature deviation", "T0", "C", -3, 3),
    _n("screen_time", "Screen time", "T0", "min/day", 0, 1200),
    _n("body_temp.daily", "Body temperature", "T0", "C", 34, 40),
    # T1 lifestyle
    _n("meal.kcal", "Meal energy (logged)", "T1", "kcal/day", 0, 6000),
    _n("meal.protein", "Protein (logged)", "T1", "g/day", 0, 400),
    _n("meal.carbs", "Carbohydrate (logged)", "T1", "g/day", 0, 900),
    _n("meal.sugar", "Added sugar (logged)", "T1", "g/day", 0, 300),
    _n("caffeine", "Caffeine", "T1", "mg/day", 0, 1200),
    _n("alcohol", "Alcohol", "T1", "drinks/day", 0, 20),
    _n("water", "Water intake", "T1", "ml/day", 0, 6000),
    Column("med.adherence", "Medication-taking log", "T1", "record"),
    _n("mood.score", "Mood (self-rated)", "T1", "0-10", 0, 10),
    _n("stress.score", "Stress (self-rated)", "T1", "0-10", 0, 10),
    _n("fatigue.survey", "Fatigue survey", "T1", "0-10", 0, 10),
    _n("energy.survey", "Energy survey", "T1", "0-10", 0, 10),
    Column("survey.psqi", "Sleep quality questionnaire (PSQI)", "T1", "numeric", "score", 0, 21),
    Column("smoking.status", "Smoking status", "T1", "category"),
    # T2 clinical
    Column("dx.codes", "Diagnoses (ICD-10)", "T2", "record", source="engine"),
    Column("rx.list", "Prescriptions", "T2", "record", source="engine"),
    _n("lab.hba1c", "HbA1c", "T2", "%", 3, 15, source="engine"),
    _n("lab.ldl", "LDL cholesterol", "T2", "mg/dL", 20, 300, source="engine"),
    _n("lab.creatinine", "Creatinine", "T2", "mg/dL", 0.2, 10, source="engine"),
    _n("lab.glucose", "Fasting glucose", "T2", "mg/dL", 40, 400, source="engine"),
    _n("lab.tsh", "TSH", "T2", "mIU/L", 0.01, 50, source="engine"),
    _n("blood_pressure.daily", "Blood pressure (systolic)", "T2", "mmHg", 70, 220),
    _n("vitals.clinic_hr", "Clinic heart rate", "T2", "bpm", 30, 200, source="engine"),
    _n("vitals.bmi", "BMI (clinic)", "T2", "kg/m2", 12, 70, source="engine"),
    Column("allergy.list", "Allergies", "T2", "record", source="engine"),
    Column("procedure.list", "Procedures", "T2", "record", source="engine"),
    # T3 highly sensitive
    Column("genome.vcf", "Genomic variants (VCF)", "T3", "variants", duo_extra=GENOMIC, source="engine"),
    Column("genome.pgx", "Pharmacogenomic variants", "T3", "variants", duo_extra=GENOMIC, source="engine"),
    Column("imaging.ct", "CT imaging (DICOM)", "T3", "image", source="engine"),
    Column("imaging.mri", "MRI imaging (DICOM)", "T3", "image", source="engine"),
    Column("mental.dx", "Mental health diagnoses", "T3", "record", source="engine"),
    _n("mental.phq9", "Depression questionnaire (PHQ-9)", "T3", "score", 0, 27, source="engine"),
    Column("repro.cycle", "Menstrual cycle log", "T3", "record", source="engine"),
    Column("repro.pregnancy", "Pregnancy history", "T3", "record", source="engine"),
]}


# Names the people's store (UniQdata) uses for the same columns.
ALIASES = {"body_weight.daily": "weight", "meal.log": "meal.kcal", "medication.taken": "med.adherence",
           "mood.daily": "mood.score", "spo2.daily": "spo2.night", "activity.daily": "activity.minutes",
           "diagnosis.code": "dx.codes", "prescription.active": "rx.list", "genome.variant": "genome.vcf"}


def canon(col: str) -> str:
    return ALIASES.get(col, col)


def by_tier(tier: str) -> list[Column]:
    return [c for c in CATALOG.values() if c.tier == tier]


def tier_of(cols) -> str:
    return max((CATALOG[c].tier for c in cols), key=TIERS.index)


def duo_for(cols) -> list[str]:
    return sorted({d for c in cols for d in CATALOG[c].duo})


# ---------------- synthetic values ----------------

GENES = {"CYP1A2": ("chr15", 74748845), "MCM6": ("chr2", 135839626), "BRCA1": ("chr17", 43044295), "BRCA2": ("chr13", 32315474), "CYP2C19": ("chr10", 94762681),
         "CYP2D6": ("chr22", 42126499), "APOE": ("chr19", 44905796), "SLCO1B1": ("chr12", 21130388)}
PGX = ("CYP2C19", "CYP2D6", "SLCO1B1")


def _rng(pid, col, day):
    return random.Random(hashlib.sha256(f"{pid}|{col}|{day}".encode()).digest())


def synth(col: str, pid: str, day: int = 0):
    """One synthetic value for one person and day. Deterministic per (person, column, day)."""
    c, r = CATALOG[col], _rng(pid, col, day)
    if c.kind == "numeric":
        span = c.hi - c.lo
        mid = c.lo + span * (0.35 + 0.3 * _rng(pid, col, -1).random())
        v = r.gauss(mid, span * 0.05)
        return round(min(c.hi, max(c.lo, v)), 2)
    if c.kind == "category":
        return r.choice(["never", "former", "current"])
    if c.kind == "record":
        return {"med.adherence": lambda: {"taken": r.random() < 0.85, "dose": "1 tab"},
                "dx.codes": lambda: r.sample(["I10", "E11.9", "G47.00", "J45.909", "E78.5"], 2),
                "rx.list": lambda: r.sample(["amlodipine 5mg", "metformin 500mg", "atorvastatin 20mg"], 1),
                "allergy.list": lambda: r.sample(["penicillin", "none"], 1),
                "procedure.list": lambda: r.sample(["colonoscopy", "none"], 1),
                "mental.dx": lambda: r.sample(["F41.1", "F32.0", "none"], 1),
                "repro.cycle": lambda: {"cycle_day": r.randint(1, 30)},
                "repro.pregnancy": lambda: {"gravida": r.randint(0, 3)}}[col]()
    if c.kind == "variants":
        return synth_vcf(pid, PGX if col == "genome.pgx" else tuple(GENES))
    if c.kind == "image":
        return synth_dicom(pid, "CT" if col == "imaging.ct" else "MR", day)
    raise ValueError(col)


def synth_vcf(pid: str, genes=tuple(GENES)) -> list[dict]:
    """A few synthetic variants per gene: chrom, pos, ref, alt, genotype. Not a real genome."""
    out = []
    for g in genes:
        chrom, start = GENES[g]
        r = _rng(pid, "vcf", g)
        for k in range(r.randint(2, 5)):
            ref = r.choice("ACGT")
            out.append({"gene": g, "chrom": chrom, "pos": start + r.randint(0, 80000),
                        "ref": ref, "alt": r.choice([b for b in "ACGT" if b != ref]),
                        "gt": r.choice(["0/1", "1/1", "0/1", "0/0"])})
    return out


def synth_dicom(pid: str, modality: str, day: int = 0, size: int = 16) -> dict:
    """DICOM-like metadata plus a tiny synthetic pixel grid (no real scan)."""
    r = _rng(pid, modality, day)
    return {"Modality": modality, "PatientName": f"Synthetic^{pid}", "PatientID": pid,
            "PatientBirthDate": "1990-01-01", "PatientAge": 36, "InstitutionName": "Synthetic Hospital",
            "StudyInstanceUID": f"1.2.826.0.1.{int(hashlib.sha256(pid.encode()).hexdigest()[:8], 16)}.{day}",
            "SeriesInstanceUID": f"1.2.826.0.1.{int(hashlib.sha256(pid.encode()).hexdigest()[:8], 16)}.{day}.1", "StudyDate": f"2026-09-{1 + day % 28:02d}", "BodyPartExamined": "CHEST"
            if modality == "CT" else "HEAD", "Rows": size, "Columns": size, "SliceThickness": 1.0,
            "pixels": [[r.randint(0, 255) for _ in range(size)] for _ in range(size)]}


def seed_plan(people: list[str]) -> dict:
    """What goes where when seeding the 50 accounts: T0/T1 through the person's store, T2/T3 engine-side."""
    return {"uniqdata": [c.id for c in CATALOG.values() if c.source == "uniqdata"],
            "engine": [c.id for c in CATALOG.values() if c.source == "engine"], "people": len(people)}
