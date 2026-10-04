"""Each exercise's exact target for a session, from last time and data/rules/progression.yaml (double progression).

"Done as planned" saves exactly this target, so the next session's target follows from it.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import yaml

from app.config import get_settings
from app.workouts import ExerciseResult, rep_range

Reason = Literal["start", "addReps", "addWeight", "repeat", "dropWeight", "findWeight"]


@dataclass(frozen=True)
class Target:
    sets: int
    reps: int
    weight_kg: float
    reason: Reason

    def as_result(self) -> ExerciseResult:
        """What "Done as planned" logs."""
        return ExerciseResult(sets=self.sets, reps=self.reps, weight_kg=self.weight_kg)


@lru_cache
def load_rules() -> dict:
    rules = yaml.safe_load((get_settings().rules_dir / "progression.yaml").read_text(encoding="utf-8"))
    if not isinstance(rules.get("reps_per_step"), int) or rules["reps_per_step"] < 1:
        raise ValueError("progression.yaml: reps_per_step must be a whole number of at least 1")
    return rules


def next_target(sets: int, reps: str, weight_step_kg: float, start_weight_kg: float, last: ExerciseResult | None,
                rules: dict | None = None) -> Target:
    """sets / reps (e.g. "8–10") / weight step come from the program; `last` is the previous result for this exercise."""
    rules = rules or load_rules()
    low, high = rep_range(reps)
    if last is None or last.sets == 0:
        return Target(sets, low, start_weight_kg, "start")
    weight = last.weight_kg
    if last.struggled or last.sets < sets:
        if last.struggled and last.reps < low and weight_step_kg > 0:
            return Target(sets, low, max(0.0, weight - weight_step_kg), "dropWeight")
        return Target(sets, min(max(last.reps, low), high), weight, "repeat")
    if last.reps >= high:
        if weight_step_kg > 0:
            return Target(sets, low, weight + weight_step_kg, "addWeight")
        return Target(sets, high, weight, "repeat")
    return Target(sets, min(last.reps + rules["reps_per_step"], high), weight, "addReps")


def session_target(sets: int, reps: str, weight_step_kg: float, start_weight_kg: float, last: ExerciseResult | None, *,
                   last_in_this_program: bool, load_ratio: float = 1.0, weight_offset_kg: float = 0.0) -> Target:
    """The target for a session in a given plan version.

    Each weekly review makes a new plan version. Its first session continues from last time's progression, then applies
    what changed in that version, once: `load_ratio` = this version's load factor ÷ the previous one's (e.g. 0.9 after
    pain went up; 1.0 when nothing changed) and `weight_offset_kg` (± one step for "too easy" / "too hard").
    After that first session, targets come from the logs as usual, so nothing compounds week after week.
    """
    if last is None:
        weight = max(0.0, start_weight_kg + weight_offset_kg)
        return Target(sets, rep_range(reps)[0], weight, "start")
    t = next_target(sets, reps, weight_step_kg, start_weight_kg, last)
    if last_in_this_program or (load_ratio == 1.0 and not weight_offset_kg):
        return t
    weight = (t.weight_kg + weight_offset_kg) * load_ratio
    if weight_step_kg > 0:
        weight = (weight // weight_step_kg) * weight_step_kg
    return Target(t.sets, t.reps, max(0.0, round(weight, 2)), t.reason)
