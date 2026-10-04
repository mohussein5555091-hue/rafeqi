"""Warm-up before and cool-down after every session (data/rules/training.yaml `warmup`, `cooldown`).

Warm-up (about 8–10 min):
1. General: `general_minutes` of easy movement, the first option for where they train that every injury allows
   (and no jumping with the health flag).
2. Mobility: 3–4 moves for the day's muscles (upper / lower / full). A move ruled out by an injury's painful movements
   or restrictions, or loading a paused area, is skipped and the skip is explained.
3. Ramp-up: lighter sets of the day's first main exercise, worked out from that session's target (`ramp_up()`).
Cool-down (about 5–8 min): static stretches for the muscles trained that day, most-trained first, then slow breathing.
"""

import math
from dataclasses import dataclass, field

from app.engine.injuries import paused_by, ruled_out_by
from app.engine.rules import load_rules
from app.engine.types import ExerciseInfo, Person, Reason
from app.vocab import get_vocab


@dataclass
class Warmup:
    minutes: int
    general_id: str | None
    general_minutes: int
    moves: list[dict]  # [{id, amount: {en, ar}}]
    ramp_exercise_id: str | None  # the first main exercise (its target sets the ramp-up weights)
    ramp_sets: int
    skipped: list[dict] = field(default_factory=list)  # [{id, why: {en, ar}}]
    reasons: list[Reason] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"minutes": self.minutes, "general": {"id": self.general_id, "minutes": self.general_minutes}, "moves": self.moves,
                "ramp": {"id": self.ramp_exercise_id, "sets": self.ramp_sets}, "skipped": self.skipped}


@dataclass
class Cooldown:
    minutes: int
    stretches: list[dict]  # [{id, seconds, eachSide}]
    breathing: dict  # {id, minutes}
    reasons: list[Reason] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"minutes": self.minutes, "stretches": self.stretches, "breathing": self.breathing}


def _fits(ex: ExerciseInfo, p: Person) -> bool:
    eq = set(load_rules()["training"]["equipment_by_location"][p.location]) | {"bodyweight"}
    return set(ex.equipment) <= eq - set(p.missing_equipment)


def _blocked(ex: ExerciseInfo, p: Person) -> tuple[str, dict] | None:
    """(injury region, the painful movement or restriction label) when an injury rules this move out."""
    vocab = get_vocab()
    for inj in p.injuries:
        if (tag := ruled_out_by(ex, inj, vocab)) is not None:
            kind = "painful_movements" if tag in vocab.data["painful_movements"] else "restrictions"
            label = vocab.data[kind][tag]
            return inj.region, {"en": label["en"].lower() if kind == "painful_movements" else label["en"], "ar": label["ar"]}
    if (inj := paused_by(ex, p.injuries)) is not None:
        return inj.region, {"en": "a paused area", "ar": "منطقة متوقفة"}
    return None


def ramp_up(target_kg: float, step_kg: float) -> list[dict]:
    """Lighter sets before the first main exercise: [{pct, reps, weightKg}]. Weights round down to the weight step.
    Nothing for bodyweight or very light exercises (the mobility moves warm those up)."""
    r = load_rules()["training"]["warmup"]["ramp_up"]
    if target_kg < max(r["min_target_kg"], 0.01):
        return []
    sets = list(r["sets"]) + ([r["extra"]] if target_kg >= r["extra_from_kg"] else [])
    out = []
    for s in sets:
        kg = target_kg * s["pct"] / 100
        kg = math.floor(kg / step_kg) * step_kg if step_kg else kg
        out.append({"pct": s["pct"], "reps": s["reps"], "weightKg": round(max(kg, 0.0), 2)})
    return out


def build_warmup(kind: str, p: Person, catalogue: dict[str, ExerciseInfo], first_main: str | None, first_main_kg: float) -> Warmup:
    w = load_rules()["training"]["warmup"]
    regions = load_rules()["safety"]["region_names"]
    avoid_patterns = set(w["conservative_avoid_patterns"]) if p.conservative else set()

    general = next((catalogue[i] for i in w["general_by_location"][p.location]
                    if i in catalogue and _fits(catalogue[i], p) and catalogue[i].pattern not in avoid_patterns
                    and _blocked(catalogue[i], p) is None), None)

    moves, skipped = [], []
    for m in w["moves_by_kind"][kind]:
        ex = catalogue.get(m["id"])
        if ex is None or not _fits(ex, p) or len(moves) >= w["moves"]["max"]:
            continue
        if (b := _blocked(ex, p)) is not None:
            area, why = b
            t = w["explain"]["skipped"]
            skipped.append({"id": ex.id, "why": {"en": t["en"].format(name=ex.name["en"], why=why["en"], area=regions[area]["en"]),
                                                 "ar": t["ar"].format(name=ex.name["ar"], why=why["ar"], area=regions[area]["ar"])}})
            continue
        moves.append({"id": ex.id, "amount": m["amount"]})

    ramp_sets = len(ramp_up(first_main_kg, 1)) if first_main else 0
    general_min = w["general_minutes"] if general else 0
    minutes = round(general_min + len(moves) * w["move_minutes"] + ramp_sets * w["ramp_up"]["set_minutes"])
    first_name = catalogue[first_main].name if first_main else {"en": "your first exercise", "ar": "أول تمرين"}
    gname = general.name if general else {"en": "easy movement", "ar": "حركة خفيفة"}
    t = w["explain"] if ramp_sets else w["explain"]["no_ramp"]
    reasons = [Reason("training.warmup", t["en"].format(minutes=minutes, general=general_min, name=gname["en"].lower(), moves=len(moves), first=first_name["en"]),
                      t["ar"].format(minutes=minutes, general=general_min, name=gname["ar"], moves=len(moves), first=first_name["ar"]), w["source"])]
    reasons += [Reason("training.warmup.skipped", x["why"]["en"], x["why"]["ar"], w["source"]) for x in skipped]
    return Warmup(minutes, general.id if general else None, general_min, moves, first_main, ramp_sets, skipped, reasons)


def build_cooldown(trained: dict[str, int], p: Person, catalogue: dict[str, ExerciseInfo]) -> Cooldown:
    """`trained`: body region → sets that worked it as a primary muscle today."""
    c = load_rules()["training"]["cooldown"]
    large = set(c["large_regions"])

    def ok(ex_id: str) -> bool:
        ex = catalogue.get(ex_id)
        return ex is not None and _fits(ex, p) and _blocked(ex, p) is None

    scored = [(sum(trained.get(m, 0) for m in catalogue[i].muscles), n, i) for n, i in enumerate(c["candidates"]) if ok(i)]
    chosen = [i for score, _, i in sorted(scored, key=lambda x: (-x[0], x[1])) if score > 0][: c["stretches"]["max"]]
    for i in c["fallback"]:
        if len(chosen) >= c["stretches"]["min"]:
            break
        if i not in chosen and ok(i):
            chosen.append(i)

    stretches, seconds = [], 0
    for i in chosen:
        hold = c["hold_sec_large"] if set(catalogue[i].muscles) & large else c["hold_sec"]
        each = i in c["each_side"]
        stretches.append({"id": i, "seconds": hold, "eachSide": each})
        seconds += hold * (2 if each else 1)
    b = c["breathing"]
    breathing = {"id": b["id"], "minutes": b["minutes"]} if ok(b["id"]) else {"id": None, "minutes": b["minutes"]}
    minutes = round(seconds / 60 + b["minutes"])
    hold = f"{c['hold_sec']}–{c['hold_sec_large']}"
    t = c["explain"]
    return Cooldown(minutes, stretches, breathing,
                    [Reason("training.cooldown", t["en"].format(minutes=minutes, stretches=len(stretches), hold=hold),
                            t["ar"].format(minutes=minutes, stretches=len(stretches), hold=hold), c["source"])])
