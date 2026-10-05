"""AI settings: which model writes each task, the limits, and whether AI runs at all.

Everything comes from the environment (.env locally, Render's Environment page online); nothing here is shown to users.
- RAFEQI_AI_ENABLED=true and ANTHROPIC_API_KEY=… turn it on. Off (the default): every text is the template.
- RAFEQI_AI_MODEL_PLAN / RAFEQI_AI_MODEL_REVIEW: the model for each task.
- RAFEQI_AI_RUNS_PER_WEEK (default 2): AI runs per person per week (Saturday–Friday); more use the template.
- RAFEQI_AI_MONTHLY_LIMIT_USD (default 5): when this month's AI calls (all people) reach it, the template is used.
  This is the app owner's spending cap for the AI service, tracked in llm_calls.cost_usd; it never reaches the
  screens (the app has no prices of any kind for users).
"""

from dataclasses import dataclass, field

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config import ROOT_DIR

TASKS = ("plan_explanation", "weekly_review")

# The AI service's published rates (US dollars per million tokens: input, output), to keep the monthly cap. Check them
# against the provider's current pricing page before turning AI on; unknown models count at the highest rate.
RATES_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
    "claude-sonnet-5-5": (3.0, 15.0),
    "claude-opus-5-5": (5.0, 25.0),
}


class AiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", env_prefix="RAFEQI_AI_", extra="ignore")

    enabled: bool = False
    model_plan: str = "claude-sonnet-5-5"
    model_review: str = "claude-sonnet-5-5"
    max_tokens: int = 900
    runs_per_week: int = 2
    monthly_limit_usd: float = 5.0
    timeout_s: float = 60.0


class KeySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    anthropic_api_key: str = ""


@dataclass(frozen=True)
class AiConfig:
    enabled: bool = False
    models: dict[str, str] = field(default_factory=lambda: {"plan_explanation": "claude-sonnet-5-5", "weekly_review": "claude-sonnet-5-5"})
    max_tokens: int = 900
    runs_per_week: int = 2
    monthly_limit_usd: float = 5.0
    timeout_s: float = 60.0
    api_key: str = ""


def load_config() -> AiConfig:
    s, k = AiSettings(), KeySettings()
    return AiConfig(enabled=s.enabled and bool(k.anthropic_api_key), models={"plan_explanation": s.model_plan, "weekly_review": s.model_review},
                    max_tokens=s.max_tokens, runs_per_week=s.runs_per_week, monthly_limit_usd=s.monthly_limit_usd,
                    timeout_s=s.timeout_s, api_key=k.anthropic_api_key)


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate_in, rate_out = RATES_PER_MTOK.get(model, max(RATES_PER_MTOK.values()))
    return round((prompt_tokens * rate_in + completion_tokens * rate_out) / 1_000_000, 6)
