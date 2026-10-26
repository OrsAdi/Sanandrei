from django import template

register = template.Library()

RESULT_LABELS = {"V": "Victorie", "E": "Egal", "I": "Înfrângere"}


@register.filter
def initials(name):
    parts = [p for p in (name or "").split() if p]
    return "".join(p[0] for p in parts[:2]).upper()


@register.filter
def result_label(code):
    return RESULT_LABELS.get(code, "")


@register.filter
def pct(value, total):
    try:
        return round(100 * float(value) / float(total)) if float(total) else 0
    except (TypeError, ValueError):
        return 0


@register.filter
def signed(value):
    try:
        return f"+{value}" if int(value) > 0 else str(value)
    except (TypeError, ValueError):
        return value


@register.inclusion_tag("teams/_form.html")
def form_pills(results, large=False):
    return {"results": results, "large": large}


@register.filter
def opponent_name(match, team):
    """Numele adversarului echipei date într-un meci."""
    return match.opponent_of(team).name if match and team else ""
