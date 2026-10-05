"""When the AI runs: after a plan is built (onboarding, "Regenerate my plan") and after each weekly check-in. Never
anywhere else (there is no chat). Each run happens after the answer has been sent, in the background, with its own
database session, so a slow or failing model never slows the screens down. AI off (the default): nothing runs.
"""

from sqlalchemy.orm import Session

from app.ai import tasks
from app.ai.config import load_config
from app.models import Plan, WeeklyReview


def enabled() -> bool:
    return load_config().enabled


def after_plan(bind, plan_id: str) -> None:
    with Session(bind=bind, expire_on_commit=False) as db:
        plan = db.get(Plan, plan_id)
        if plan is not None:
            tasks.explain_plan(db, plan)
            db.commit()


def after_review(bind, review_id: str) -> None:
    from app.views.body import review_out

    with Session(bind=bind, expire_on_commit=False) as db:
        review = db.get(WeeklyReview, review_id)
        if review is not None:
            stats = review_out(db, review)["stats"]
            tasks.write_review(db, review, stats)
            db.commit()
