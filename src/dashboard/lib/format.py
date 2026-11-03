"""Display formats from ui_spec.md: times h:mm:ss, gaps +m′ss″, distances and speeds with units."""
import math


def _missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def hms(seconds):
    if _missing(seconds):
        return "—"
    s = int(round(seconds))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _clock(seconds):
    s = abs(int(round(seconds)))
    hours, minutes, secs = s // 3600, s % 3600 // 60, s % 60
    if hours:
        return f"{hours}h{minutes:02d}′{secs:02d}″"
    return f"{minutes}′{secs:02d}″"


def gap(seconds):
    """Gap behind a leader. Zero shows as a dash."""
    if _missing(seconds) or round(seconds) == 0:
        return "—"
    return f"+{_clock(seconds)}"


def signed(seconds):
    """Change in gap: + lost, − gained."""
    if _missing(seconds):
        return "—"
    if round(seconds) == 0:
        return "±0″"
    return f"{'+' if seconds > 0 else '−'}{_clock(seconds)}"


def bonus(seconds):
    return "—" if _missing(seconds) or seconds == 0 else f"−{_clock(seconds)}"


def penalty(seconds):
    return "—" if _missing(seconds) or seconds == 0 else f"+{_clock(seconds)}"


def rank_move(actual, other):
    """Rank under another scenario, with an arrow when it differs from the actual rank."""
    if _missing(other):
        return "—"
    other = int(other)
    if other == actual:
        return f"= {other}"
    return f"{'▲' if other < actual else '▼'} {other}"


def difference(value):
    """Places gained or lost: positive shows ▲, negative shows ▼."""
    if _missing(value):
        return "—"
    value = int(value)
    if value == 0:
        return "="
    return f"▲{value}" if value > 0 else f"▼{-value}"


def ordinal(n):
    n = int(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def long_date(value):
    return value.strftime("%a %-d %b %Y")


def short_date(value):
    return value.strftime("%-d %b")


def rank_or_dash(value):
    return "—" if _missing(value) else str(int(value))
