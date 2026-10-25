"""Realistic synthetic records for the demo accounts, their pseudonymized copies and their fingerprints.

Every record carries stable record-level fingerprints, so a buyer agent can tell when a lot overlaps
what it already owns (the same run, night or receipt bought twice, or resold inside a bigger bundle).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import date, datetime, timedelta

KINDS = {
    "gps_track": {"label": "Running GPS tracks", "domain": "Mobility and fitness", "price": 12, "personal": True, "ext": "gpx"},
    "sleep_log": {"label": "Sleep logs", "domain": "Sleep and health", "price": 8, "personal": True, "ext": "csv"},
    "purchase_receipts": {"label": "Purchase receipts", "domain": "Shopping", "price": 3, "personal": True, "ext": "json"},
    "audio": {"label": "Voice clips", "domain": "Voice", "price": 6, "personal": True, "ext": "json"},
    "air": {"label": "Air-quality sensor data", "domain": "Environment", "price": 4, "personal": False, "ext": "csv"},
    "step_count": {"label": "Daily steps", "domain": "Mobility and fitness", "price": 4, "personal": True, "ext": "csv"},
    "commute": {"label": "Commute trips", "domain": "Mobility and fitness", "price": 7, "personal": True, "ext": "json"},
    "screen_time": {"label": "Screen time", "domain": "Digital habits", "price": 5, "personal": True, "ext": "json"},
    "energy_use": {"label": "Home energy use", "domain": "Home", "price": 5, "personal": True, "ext": "csv"},
}
NEW_KINDS = ("step_count", "commute", "screen_time", "energy_use")   # added after launch; market.py backfills them
DIRECT = {"owner_name", "email", "phone", "device_serial", "card_last4", "home", "passport_no", "dob", "address"}
PACKAGE_KIND = 'data_package'
PACKAGE_INFO = {'label': 'Data package', 'domain': 'Mixed data', 'personal': True}


def kind_info(kind):
    return PACKAGE_INFO if kind == PACKAGE_KIND else KINDS[kind]

# Real New York running loops (rough centre lat/lng, loop radius in km).
ROUTES = [("Central Park loop", 40.7812, -73.9665, 1.6), ("Prospect Park loop", 40.6602, -73.9690, 1.3),
          ("Hudson River Greenway", 40.7480, -74.0080, 2.2), ("East River Esplanade", 40.7600, -73.9530, 1.4),
          ("Williamsburg Bridge", 40.7134, -73.9724, 1.0), ("Astoria Park", 40.7790, -73.9220, 0.8)]
STORES = [("Trader Joe's", ["bananas", "oat milk", "frozen dumplings", "greek yogurt", "coffee beans"]),
          ("Whole Foods", ["salmon fillet", "spinach", "almond butter", "sourdough", "blueberries"]),
          ("CVS Pharmacy", ["ibuprofen", "vitamin D", "toothpaste", "sunscreen"]),
          ("Key Food", ["rice 5lb", "eggs dozen", "chicken thighs", "onions", "black beans"])]
SITES = [("Greenpoint", 40.7290, -73.9540), ("Red Hook", 40.6750, -74.0110), ("Harlem", 40.8116, -73.9465),
         ("Long Island City", 40.7447, -73.9485), ("Bushwick", 40.6944, -73.9213), ("Sunset Park", 40.6455, -74.0124)]


def fp(*parts) -> str:
    return hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]


def gps_track(rng: random.Random, who: str, day: date, home: tuple[float, float]) -> dict:
    name, clat, clng, rad = rng.choice(ROUTES)
    pts, t0 = [], datetime(day.year, day.month, day.day, rng.choice([6, 7, 18, 19]), rng.randint(0, 59))
    # leave home, run the loop, come back
    pts.append({"lat": home[0], "lng": home[1], "t": t0.isoformat(), "hr": 92})
    pace = rng.uniform(4.6, 6.4)  # min/km
    for i in range(36):
        a = 2 * math.pi * i / 36
        lat = clat + (rad / 111) * math.sin(a) + rng.gauss(0, 0.00005)
        lng = clng + (rad / 84) * math.cos(a) + rng.gauss(0, 0.00005)
        t = t0 + timedelta(minutes=6 + pace * (2 * math.pi * rad) * i / 36)
        pts.append({"lat": round(lat, 6), "lng": round(lng, 6), "t": t.isoformat(), "hr": int(140 + 20 * math.sin(a) + rng.gauss(0, 4))})
    pts.append({"lat": home[0], "lng": home[1], "t": (t + timedelta(minutes=6)).isoformat(), "hr": 110})
    km = round(2 * math.pi * rad + 2.2, 1)
    return {"route": name, "date": day.isoformat(), "distance_km": km, "avg_pace_min_km": round(pace, 2), "points": pts,
            "_fps": [fp("run", who, day, name)]}


def sleep_log(rng: random.Random, who: str, start: date, nights: int = 7) -> dict:
    rows = []
    for d in range(nights):
        day = start + timedelta(days=d)
        total = round(rng.gauss(7.0, 0.8), 2)
        deep, rem = round(total * rng.uniform(0.13, 0.22), 2), round(total * rng.uniform(0.18, 0.26), 2)
        rows.append({"night": day.isoformat(), "bedtime": f"{rng.choice([22, 23, 0])}:{rng.randint(0, 59):02d}", "total_h": total,
                     "deep_h": deep, "rem_h": rem, "light_h": round(total - deep - rem, 2), "rhr": rng.randint(50, 66), "hrv_ms": rng.randint(28, 80)})
    return {"nights": rows, "_fps": [fp("night", who, r["night"]) for r in rows]}


def receipts(rng: random.Random, who: str, month: int) -> dict:
    out = []
    for _ in range(rng.randint(4, 9)):
        store, items = rng.choice(STORES)
        lines = [{"item": i, "qty": rng.randint(1, 3), "price": round(rng.uniform(1.5, 14), 2)} for i in rng.sample(items, rng.randint(2, len(items)))]
        rid = f"R{rng.randint(100000, 999999)}"
        out.append({"receipt": rid, "store": store, "date": f"2026-{month:02d}-{rng.randint(1, 28):02d}", "lines": lines,
                    "total": round(sum(l["qty"] * l["price"] for l in lines), 2)})
    return {"receipts": out, "_fps": [fp("rcpt", who, r["receipt"]) for r in out]}


def voice(rng: random.Random, who: str, n: int = 5) -> dict:
    clips = [{"clip": f"c{rng.randint(1000, 9999)}", "seconds": rng.randint(4, 14), "lang": rng.choice(["en-US", "en-US", "ko-KR", "es-US"]),
              "prompt": rng.choice(["read digits 0-9", "say 'turn on the lights'", "read a news sentence", "count to twenty"]),
              "snr_db": round(rng.uniform(12, 35), 1)} for _ in range(n)]
    return {"clips": clips, "_fps": [fp("clip", who, c["clip"]) for c in clips]}


def air(rng: random.Random, site_idx: int, day: date) -> dict:
    name, lat, lng = SITES[site_idx % len(SITES)]
    rows = [{"t": f"{day.isoformat()}T{h:02d}:00", "pm25": round(max(2, rng.gauss(11 + 6 * math.sin(h / 24 * 2 * math.pi), 3)), 1),
             "no2_ppb": round(max(3, rng.gauss(18, 6)), 1), "o3_ppb": round(max(5, rng.gauss(30, 8)), 1)} for h in range(24)]
    return {"site": name, "lat": lat, "lng": lng, "readings": rows, "_fps": [fp("air", name, day)]}


APPS = [("Instagram", "social"), ("YouTube", "video"), ("Google Maps", "navigation"), ("Spotify", "music"), ("Slack", "work"),
        ("Duolingo", "education"), ("Citymapper", "navigation"), ("TikTok", "social"), ("Kindle", "reading"), ("Chrome", "browsing")]
MODES = [("subway", 0.55), ("bus", 0.15), ("bike", 0.12), ("walk", 0.1), ("rideshare", 0.08)]


def steps(rng: random.Random, who: str, start: date, days: int = 14) -> dict:
    rows = [{"day": (start + timedelta(days=d)).isoformat(), "steps": max(800, int(rng.gauss(8200, 2600))),
             "active_min": rng.randint(15, 95), "floors": rng.randint(0, 18)} for d in range(days)]
    return {"days": rows, "_fps": [fp("steps", who, r["day"]) for r in rows]}


def commute(rng: random.Random, who: str, start: date, home: tuple[float, float]) -> dict:
    work = (round(40.70 + rng.random() * 0.06, 4), round(-74.01 + rng.random() * 0.04, 4))
    trips = []
    for d in range(10):
        day = start + timedelta(days=d + (d // 5) * 2)
        mode = rng.choices([m for m, _ in MODES], [w for _, w in MODES])[0]
        mins = {"subway": 32, "bus": 44, "bike": 27, "walk": 55, "rideshare": 29}[mode] + rng.randint(-6, 12)
        for leg, (a, b) in enumerate([(home, work), (work, home)]):
            trips.append({"trip": f"{day.isoformat()}-{leg}", "date": day.isoformat(), "mode": mode, "minutes": mins + rng.randint(-4, 6),
                          "km": round(math.dist(a, b) * 100, 1), "from": {"lat": a[0], "lng": a[1]}, "to": {"lat": b[0], "lng": b[1]},
                          "depart": f"{(8 if leg == 0 else 17) + rng.randint(0, 1):02d}:{rng.randint(0, 59):02d}"})
    return {"trips": trips, "_fps": [fp("trip", who, t["trip"]) for t in trips]}


def screen_time(rng: random.Random, who: str, start: date, days: int = 7) -> dict:
    rows = []
    for d in range(days):
        apps = rng.sample(APPS, rng.randint(4, 7))
        rows.append({"day": (start + timedelta(days=d)).isoformat(), "pickups": rng.randint(40, 140),
                     "apps": [{"app": n, "category": c, "minutes": rng.randint(4, 95)} for n, c in apps]})
    return {"usage": rows, "_fps": [fp("screen", who, r["day"]) for r in rows]}


def energy(rng: random.Random, who: str, start: date, days: int = 7) -> dict:
    rows = [{"t": f"{(start + timedelta(days=d)).isoformat()}T{h:02d}:00",
             "kwh": round(max(0.05, 0.35 + 0.6 * (h in (7, 8, 18, 19, 20, 21)) + rng.gauss(0, 0.12)), 2)} for d in range(days) for h in range(24)]
    return {"meter": rows, "tariff": rng.choice(["Con Edison residential", "Con Edison time-of-use"]), "_fps": [fp("kwh", who, start, d) for d in range(days)]}


def make_record(kind: str, rng: random.Random, who: str, idx: int, home: tuple[float, float]) -> dict:
    base = date(2026, 9, 1) + timedelta(days=idx * rng.randint(2, 5))
    if kind == "gps_track":
        body = gps_track(rng, who, base, home)
    elif kind == "sleep_log":
        body = sleep_log(rng, who, base)
    elif kind == "purchase_receipts":
        body = receipts(rng, who, 9 + idx % 2)
    elif kind == "audio":
        body = voice(rng, who)
    elif kind == "step_count":
        body = steps(rng, who, base)
    elif kind == "commute":
        body = commute(rng, who, base, home)
    elif kind == "screen_time":
        body = screen_time(rng, who, base)
    elif kind == "energy_use":
        body = energy(rng, who, base)
    else:
        body = air(rng, idx, base)
    if KINDS[kind]["personal"]:
        body.update({"owner_name": who, "email": who.lower().replace(" ", ".") + "@example.com", "home": {"lat": home[0], "lng": home[1]},
                     "device_serial": f"{rng.choice(['GRM', 'OURA', 'PIX', 'APL'])}-{rng.randint(10000, 99999)}"})
    return body


def file_name(kind: str, body: dict, idx: int) -> str:
    if kind == "gps_track":
        return f"run_{body['date']}.gpx"
    if kind == "sleep_log":
        return f"sleep_week_of_{body['nights'][0]['night']}.csv"
    if kind == "purchase_receipts":
        return f"receipts_{body['receipts'][0]['date'][:7]}.json"
    if kind == "audio":
        return f"voice_clips_{idx + 1}.json"
    if kind == "step_count":
        return f"steps_from_{body['days'][0]['day']}.csv"
    if kind == "commute":
        return f"commute_{body['trips'][0]['date']}.json"
    if kind == "screen_time":
        return f"screen_time_week_of_{body['usage'][0]['day']}.json"
    if kind == "energy_use":
        return f"smart_meter_{body['meter'][0]['t'][:10]}.csv"
    return f"air_{body['site'].lower().replace(' ', '_')}_{body['readings'][0]['t'][:10]}.csv"


def pseudonymize(kind: str, body: dict) -> dict:
    """Direct identifiers out, times to the day, routes lose the stretch from and to home."""
    out = {k: v for k, v in body.items() if k not in DIRECT and not k.startswith("_")}
    if kind == "gps_track":
        out["points"] = [{"lat": round(p["lat"], 4), "lng": round(p["lng"], 4), "hr": p["hr"]} for p in body["points"][1:-1]]
        out["trimmed"] = "home start and end removed; coordinates to 4 decimals (about 10 m); times removed"
    if kind == "sleep_log":
        out["nights"] = [{k: v for k, v in n.items() if k != "bedtime"} for n in body["nights"]]
    if kind == "purchase_receipts":
        out["receipts"] = [{k: v for k, v in r.items() if k != "receipt"} for r in body["receipts"]]
    if kind == "commute":   # home and work blurred to about 1 km, trip ids dropped
        out["trips"] = [{**{k: v for k, v in t.items() if k not in ("trip", "from", "to")},
                         "from": {"lat": round(t["from"]["lat"], 2), "lng": round(t["from"]["lng"], 2)},
                         "to": {"lat": round(t["to"]["lat"], 2), "lng": round(t["to"]["lng"], 2)}} for t in body["trips"]]
    return out


def fingerprints(body: dict) -> list[str]:
    return list(body.get("_fps", []))


def dumps(o) -> str:
    return json.dumps(o, separators=(",", ":"), sort_keys=True)
