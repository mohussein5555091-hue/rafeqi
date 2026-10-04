"""Injuries: which exercises an injury rules out, how much lighter the rest go, and red flags. Never diagnoses.

An injury's painful movements and restrictions are ids from data/vocab/movements.yaml; their `excludes` say which
exercise tags they rule out (every listed field must match). `joint_of_injury` (set on every painful movement and
on most restrictions) limits it to exercises that load the injured area's joints (body area → joints:
data/rules/safety.yaml region_joints): squatting that hurts a lower back rules out the barbell squat, not the leg press,
and "no overhead lifting" for a lower back doesn't rule out arm circles.
"""

from dataclasses import dataclass

from app.engine.rules import load_rules
from app.engine.types import ExerciseInfo, InjuryInfo
from app.vocab import Vocab, get_vocab


def joints_for(region: str) -> set[str]:
    return set(load_rules()["safety"]["region_joints"].get(region, []))


def loads_injury(ex: ExerciseInfo, inj: InjuryInfo) -> bool:
    return bool(set(ex.joints) & joints_for(inj.region))


def _matches(excludes: dict, ex: ExerciseInfo, inj: InjuryInfo) -> bool:
    if not excludes:
        return False
    if "movement_patterns" in excludes and ex.pattern not in excludes["movement_patterns"]:
        return False
    if "ranges_of_motion" in excludes and ex.rom not in excludes["ranges_of_motion"]:
        return False
    if excludes.get("joint_of_injury") and not loads_injury(ex, inj):
        return False
    return True


def ruled_out_by(ex: ExerciseInfo, inj: InjuryInfo, vocab: Vocab | None = None) -> str | None:
    """The painful movement or restriction id that rules this exercise out for this injury, or None."""
    if inj.status == "resolved":
        return None
    data = (vocab or get_vocab()).data
    for m in inj.painful_movements:
        if _matches(data["painful_movements"][m].get("excludes") or {}, ex, inj):
            return m
    for r in inj.restrictions:
        if _matches(data["restrictions"][r].get("excludes") or {}, ex, inj):
            return r
    return None


def paused_by(ex: ExerciseInfo, injuries: tuple[InjuryInfo, ...]) -> InjuryInfo | None:
    """A red flag paused an area this exercise loads."""
    return next((i for i in injuries if i.paused and i.status != "resolved" and loads_injury(ex, i)), None)


def allowed(ex: ExerciseInfo, injuries: tuple[InjuryInfo, ...], vocab: Vocab | None = None) -> bool:
    return paused_by(ex, injuries) is None and all(ruled_out_by(ex, i, vocab) is None for i in injuries)


@dataclass(frozen=True)
class LoadCut:
    injury: InjuryInfo
    factor: float
    why: str  # "recovering" | a restriction id (e.g. noHeavyLoad)


def load_cuts(ex: ExerciseInfo, injuries: tuple[InjuryInfo, ...], vocab: Vocab | None = None) -> list[LoadCut]:
    """Lighter loads for exercises that load an injured area: "recovering" injuries and load restrictions."""
    data = (vocab or get_vocab()).data
    rules = load_rules()["training"]["injuries"]
    cuts = []
    for inj in injuries:
        if inj.status == "resolved" or not loads_injury(ex, inj):
            continue
        if inj.status == "recovering":
            cuts.append(LoadCut(inj, rules["recovering_load_factor"], "recovering"))
        for r in inj.restrictions:
            if "load_factor" in data["restrictions"][r]:
                cuts.append(LoadCut(inj, data["restrictions"][r]["load_factor"], r))
    return cuts


@dataclass(frozen=True)
class PainEntry:
    pain: int
    sharp_pain: bool = False
    swelling: bool = False
    numbness: bool = False
    worsening: bool = False


def red_flag(logs: list[PainEntry]) -> str | None:
    """Oldest first. Returns why the area should pause ("sharp_pain", "pain_at_7", "pain_rising"…) or None."""
    if not logs:
        return None
    rules = load_rules()["safety"]["red_flags"]
    last = logs[-1]
    for flag in rules["flags"]:
        if getattr(last, flag):
            return flag
    if last.pain >= rules["pause_at_pain"]:
        return f"pain_at_{last.pain}"
    n = rules["rising_logs"]
    recent = [e.pain for e in logs[-n:]]
    if len(recent) == n and all(b > a for a, b in zip(recent, recent[1:])):
        return "pain_rising"
    return None
