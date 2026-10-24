from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from teams import stats
from teams.models import Match

from . import content
from .models import News, Sponsor


def home(request):
    team = stats.our_team()
    published = list(News.objects.filter(is_published=True)[:5])
    context = {
        "team": team,
        "news": published[:3],
        "sponsors": Sponsor.objects.all(),
    }
    if team:
        matches = list(stats.team_matches(team))
        played = [m for m in matches if m.is_finished]
        upcoming = [m for m in matches if not m.is_finished]
        table = stats.standings()
        our_row = next((r for r in table if r.team.pk == team.pk), None)
        next_match = upcoming[0] if upcoming else None
        last_match = played[-1] if played else None
        for m in played[-5:]:
            m.our_result = m.result_for(team)
        context.update({
            "next_match": next_match,
            "last_match": last_match,
            "last_result": last_match.result_for(team) if last_match else None,
            "recent": list(reversed(played[-5:])),
            "table": table,
            "our_row": our_row,
            "summary": stats.team_summary(team, played),
            "our_scorers": stats.top_scorers(limit=5, team=team),
            "next_round": (Match.objects.filter(round=next_match.round).select_related("home", "away")
                           if next_match else []),
            "lineup": content.lineup_for_round(next_match.round) if next_match else None,
            "next_opponent_row": (next((r for r in table if r.team.pk == next_match.opponent_of(team).pk), None)
                                  if next_match else None),
        })
    if team:
        context["xi"] = _player_cards(team, context.get("lineup"))
    context["slides"] = content.slideshow() or _auto_slides(context, published)
    context["featured"] = _featured_cards(published)
    return render(request, "core/home.html", context)


def _auto_slides(ctx, news):
    """Slide-uri automate, până când clubul încarcă poze în Pages CMS (Slideshow)."""
    slides = []
    nm, row = ctx.get("next_match"), ctx.get("our_row")
    slides.append({
        "eyebrow": "Bine ați venit",
        "title": "CS Sânandrei Timiș",
        "text": (f"Locul {row.position} în {settings.COMPETITION_NAME} · {row.points} puncte"
                 if row and row.played else "Fotbal în inima Timișului"),
        "link": reverse("squad_list"), "button": "Cunoaște lotul", "image": "",
    })
    if nm:
        when = timezone.localtime(nm.date).strftime("%d.%m.%Y, %H:%M") if nm.date else "dată neanunțată"
        slides.append({
            "eyebrow": f"Următorul meci · Etapa {nm.round}",
            "title": f"{nm.home.name} – {nm.away.name}",
            "text": f"{when} · {nm.venue or 'teren nestabilit'}",
            "link": nm.get_absolute_url(), "button": "Detalii meci", "image": "",
        })
    for item in [n for n in news if n.image][:2]:
        slides.append({
            "eyebrow": f"Știri · {timezone.localtime(item.published_at):%d.%m.%Y}",
            "title": item.title, "text": item.summary,
            "link": item.get_absolute_url(), "button": "Citește", "image": item.image.url,
        })
    return slides


ROLE_LABEL = {"portar": "Portar", "fundasi": "Fundaș", "mijlocasi": "Mijlocaș",
              "mijlocasi_ofensivi": "Mijlocaș ofensiv", "atacanti": "Atacant"}


def _player_cards(team, lineup):
    """
    Cardurile cu echipa de start de pe prima pagină (stil fcbarcelona.com), de la portar la atacanți.
    Fără echipă de start anunțată pentru următorul meci, secțiunea nu apare.
    """
    if not lineup:
        return None
    order = [(p, ROLE_LABEL.get(row["key"], "")) for row in reversed(lineup["rows"]) for p in row["players"]]
    by_id = {p.pk: p for p in stats.player_stats(team=team, players=[p for p, _ in order])}
    players = [(by_id[p.pk], role) for p, role in order if p.pk in by_id]
    if not players:
        return None
    return {
        "title": "Echipa de start", "subtitle": f"Formația {lineup['formation']}", "is_lineup": True,
        "cards": [{"player": p, "role": role} for p, role in players],
        "bench": lineup["bench"], "coach": lineup["coach"],
    }


def _featured_cards(news):
    """Cele două carduri de sub slideshow: ultimele două știri publicate (fără știri, cardurile nu apar)."""
    return [{"title": n.title, "url": n.get_absolute_url(), "image": n.image.url if n.image else "",
             "label": "Știri", "date": n.published_at} for n in news[:2]]


def contact(request):
    # Site static: formularul e trimis din browser către Web3Forms (vezi static/js/site.js).
    return render(request, "core/contact.html")


def news_list(request):
    return render(request, "core/news_list.html", {"news": News.objects.filter(is_published=True)})


def news_detail(request, slug):
    item = get_object_or_404(News, slug=slug, is_published=True)
    return render(request, "core/news_detail.html", {"item": item})


def not_found(request):
    return render(request, "404.html", status=404)
