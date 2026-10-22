"""
Citirea conținutului editat de club în Pages CMS (folderul content/).

Structura:
    content/setari.yml          date de contact, adresă, rețele sociale
    content/primul11.yml        echipa de start pentru următorul meci
    content/sponsori.yml        lista de sponsori
    content/stiri/*.md          știri (frontmatter YAML + text Markdown)
    content/produse/*.md        produse din magazin (frontmatter YAML + descriere)
    content/jucatori/<id>.yml   număr, post, poză și descriere pentru jucătorii noștri
    media/...                   poze încărcate din Pages CMS
"""

import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import markdown as md
import yaml
from django.conf import settings
from django.utils.safestring import mark_safe

LOCAL_TZ = ZoneInfo("Europe/Bucharest")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def content_dir():
    return Path(settings.CONTENT_DIR)


def read_yaml(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return default if data is None else data


def write_yaml(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def read_frontmatter(path):
    """Întoarce (date din frontmatter, text) pentru un fișier .md."""
    text = Path(path).read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2).strip()


def collection(name, pattern="*.md"):
    folder = content_dir() / name
    return sorted(folder.glob(pattern)) if folder.exists() else []


def media_name(value):
    """'/media/stiri/poza.jpg' (cum salvează Pages CMS) -> 'stiri/poza.jpg' (nume pentru ImageField)."""
    if not value:
        return ""
    value = str(value).strip()
    for prefix in ("/media/", "media/"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value.lstrip("/")


def media_url(value):
    name = media_name(value)
    if not name:
        return ""
    if name.startswith(("http://", "https://")):
        return name
    # settings.MEDIA_URL include deja prefixul site-ului (Django adaugă SCRIPT_NAME la URL-urile relative)
    return settings.MEDIA_URL + name


def render_markdown(text):
    """Markdown -> HTML; pozele inserate în text (/media/...) primesc prefixul site-ului."""
    html = md.markdown(text or "", extensions=["extra", "sane_lists", "nl2br"])
    prefix = settings.MEDIA_URL
    html = re.sub(r'(src|href)="/?media/', rf'\1="{prefix}', html)
    return mark_safe(html)


def to_datetime(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, 12, 0)
    elif value:
        try:
            dt = datetime.fromisoformat(str(value).strip())
        except ValueError:
            return None
    else:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=LOCAL_TZ)


def as_bool(value, default=True):
    if value is None or value == "":
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("false", "nu", "0", "no")
    return bool(value)


# --------------------------------------------------------------------------- setări

def site_settings():
    data = read_yaml(content_dir() / "setari.yml", {}) or {}
    return {
        "CLUB_EMAIL": data.get("email") or settings.CLUB_EMAIL,
        "CLUB_PHONE": str(data.get("telefon") or settings.CLUB_PHONE or ""),
        "CLUB_VENUE": data.get("stadion") or settings.CLUB_VENUE,
        "CLUB_FACEBOOK": data.get("facebook") or "",
        "CLUB_INSTAGRAM": data.get("instagram") or "",
        "CLUB_ABOUT": data.get("despre") or "",
    }


# --------------------------------------------------------------------------- Primul 11

# Formațiile din editor (Pages CMS). Liniile sunt de la apărare spre atac.
FORMATIONS = ["4-4-2", "4-3-3", "4-2-3-1", "4-1-4-1", "4-4-1-1", "4-5-1", "4-3-1-2",
              "3-5-2", "3-4-3", "3-4-1-2", "5-3-2", "5-4-1"]

LINES = [
    ("atacanti", "Atacanți"),
    ("mijlocasi_ofensivi", "Mijlocași ofensivi"),
    ("mijlocasi", "Mijlocași"),
    ("fundasi", "Fundași"),
    ("portar", "Portar"),
]


def _ids(value):
    if value in (None, ""):
        return []
    values = value if isinstance(value, list) else [value]
    ids = []
    for v in values:
        try:
            ids.append(int(str(v).strip()))
        except ValueError:
            continue
    return ids


def lineup_for_round(round_number):
    """
    Echipa de start salvată în content/primul11.yml, dacă e pentru etapa dată.
    Întoarce None dacă nu există sau e pentru altă etapă.
    """
    data = read_yaml(content_dir() / "primul11.yml", {}) or {}
    # „publicat” e opțional (versiunile vechi ale editorului îl aveau); implicit afișăm
    if not as_bool(data.get("publicat"), default=True):
        return None
    try:
        etapa = int(data.get("meci") or data.get("etapa") or 0)
    except (TypeError, ValueError):
        return None
    if not etapa or etapa != round_number:
        return None

    from teams.models import Player

    def unique(ids, exclude=()):
        seen, out = set(exclude), []
        for i in ids:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out

    if data.get("titulari"):
        # Formatul actual: o singură listă „titulari” (fiecare jucător o dată), în ordine:
        # portarul, apoi fundașii, mijlocașii, atacanții; liniile se împart după formație.
        starters = unique(_ids(data.get("titulari")))[:11]
        bench = unique(_ids(data.get("rezerve")), exclude=starters)
        players = {p.frf_id: p for p in Player.objects.filter(frf_id__in=starters + bench)}
        starters = [i for i in starters if i in players]
        outfield = starters[1:]
        parts = _formation_parts(data.get("formatie"), len(outfield))
        lines, pos = [], 0
        for n in parts:
            lines.append(outfield[pos:pos + n])
            pos += n
        rows = [{"key": "portar", "label": "Portar", "players": [players[i] for i in starters[:1]]}]
        for k, ids in enumerate(lines):
            key = "fundasi" if k == 0 else "atacanti" if k == len(lines) - 1 else "mijlocasi"
            rows.append({"key": key, "label": key, "players": [players[i] for i in ids]})
        rows = [r for r in reversed(rows) if r["players"]]
        bench_players = [players[i] for i in bench if i in players]
        formation = "-".join(str(len(r["players"])) for r in reversed(rows) if r["key"] != "portar")
    else:
        # Formatul vechi: câte o listă pe linie. Un jucător ales de două ori apare o singură dată.
        used, picked = set(), {}
        for key in ["portar", "fundasi", "mijlocasi", "mijlocasi_ofensivi", "atacanti", "rezerve"]:
            picked[key] = unique(_ids(data.get(key)), exclude=used)
            used.update(picked[key])
        players = {p.frf_id: p for p in Player.objects.filter(frf_id__in=used)}
        rows = []
        for key, label in LINES:
            members = [players[i] for i in picked[key] if i in players]
            if members:
                rows.append({"key": key, "label": label, "players": members})
        bench_players = [players[i] for i in picked["rezerve"] if i in players]
        formation = "-".join(str(len(r["players"])) for r in reversed(rows) if r["key"] != "portar")

    starters_count = sum(len(r["players"]) for r in rows)
    return {
        "round": etapa,
        "rows": rows,
        "formation": formation,
        "count": starters_count,
        "complete": starters_count == 11,
        "bench": bench_players,
        "coach": data.get("antrenor") or "",
        "note": data.get("nota") or "",
    }


def _formation_parts(value, outfield):
    """'4-2-3-1' -> [4, 2, 3, 1], potrivit cu numărul de jucători de câmp aleși."""
    try:
        parts = [int(x) for x in str(value or "").split("-") if x.strip()]
    except ValueError:
        parts = []
    if not parts or any(n <= 0 for n in parts):
        parts = [4, 4, 2]
    if sum(parts) == outfield:
        return parts
    # Echipă incompletă sau prea mulți jucători: completăm liniile în ordine, restul merg în atac.
    result, left = [], outfield
    for n in parts:
        take = min(n, left)
        result.append(take)
        left -= take
    if left:
        result[-1] += left
    return [n for n in result if n] or [outfield]
