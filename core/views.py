from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from teams import stats
from teams.models import Match

from .forms import ContactForm
from .models import News, Sponsor


def home(request):
    team = stats.our_team()
    context = {
        "team": team,
        "news": News.objects.filter(is_published=True)[:3],
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
            "next_opponent_row": (next((r for r in table if r.team.pk == next_match.opponent_of(team).pk), None)
                                  if next_match else None),
        })
    return render(request, "core/home.html", context)


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Mulțumim! Mesajul a fost trimis, vă vom răspunde în curând.")
        return redirect("contact")
    return render(request, "core/contact.html", {"form": form})


def news_list(request):
    return render(request, "core/news_list.html", {"news": News.objects.filter(is_published=True)})


def news_detail(request, slug):
    item = get_object_or_404(News, slug=slug, is_published=True)
    return render(request, "core/news_detail.html", {"item": item})
