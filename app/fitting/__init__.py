"""Rule-based fitting. The functions in this package are the source of truth."""

from app.fitting.engine import recommend
from app.fitting.profile import GolferProfile

__all__ = ["GolferProfile", "recommend"]
