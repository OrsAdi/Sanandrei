"""
Scraper pentru frf-ajf.ro (AJF Timiș).

Funcțiile `parse_*` primesc HTML și întorc structuri simple (dict/list),
fără acces la baza de date — astfel pot fi testate ușor. Funcția `fetch`
descarcă o pagină.
"""

import re
import time
import urllib.request
from datetime import date, datetime

from bs4 import BeautifulSoup

BASE_URL = "https://www.frf-ajf.ro"
USER_AGENT = "Mozilla/5.0 (compatible; SanandreiSiteBot/1.0)"

MONTHS = {
    "ianuarie": 1, "februarie": 2, "martie": 3, "aprilie": 4, "mai": 5, "iunie": 6,
    "iulie": 7, "august": 8, "septembrie": 9, "octombrie": 10, "noiembrie": 11, "decembrie": 12,
}

TEAM_ID_RE = re.compile(r"/echipe/[^/\"]*-(\d+)\.html")
MATCH_ID_RE = re.compile(r"/meciuri/[^/\"]*-(\d+)\.html")
PLAYER_ID_RE = re.compile(r"/jucatori/[^/\"]*-(\d+)\.html")
MINUTE_RE = re.compile(r"(\d+)\s*'")


def fetch(url, retries=3, timeout=60):
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001 - reîncercăm orice eroare de rețea
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise last_error


def _id(regex, href):
    m = regex.search(href or "")
    return int(m.group(1)) if m else None


def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def parse_ro_datetime(text):
    """'Sambata, 3  Octombrie 2026, 11:00' -> datetime(2026, 10, 3, 11, 0)."""
    m = re.search(r"(\d{1,2})\s+([A-Za-zăâîșşțţ]+)\s+(\d{4})(?:,?\s*(\d{1,2}):(\d{2}))?", text or "")
    if not m:
        return None
    month = MONTHS.get(m.group(2).lower())
    if not month:
        return None
    if int(m.group(3)) < 2000:  # FRF afișează "1 Ianuarie 1970" pentru meciurile neprogramate
        return None
    hour, minute = (int(m.group(4)), int(m.group(5))) if m.group(4) else (0, 0)
    return datetime(int(m.group(3)), month, int(m.group(1)), hour, minute)


def parse_dmy(text):
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})", text or "")
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def _parse_score(text):
    """'2 - 1 (0-0)' -> (2, 1, 0, 0); '?-?' -> None."""
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)(?:\s*\((\d+)\s*-\s*(\d+)\))?", text or "")
    if not m:
        return None
    ht = (int(m.group(3)), int(m.group(4))) if m.group(3) else (None, None)
    return int(m.group(1)), int(m.group(2)), *ht


def parse_round(html, round_no):
    """Lista meciurilor dintr-o etapă (pagina .../meciuri/etapa-N)."""
    soup = BeautifulSoup(html, "html.parser")
    matches = []
    for panel in soup.select("div.panel-calendar-match"):
        info = panel.select("div.matchCompetitionList")
        when = _text(info[0]) if info else ""
        venue = _text(info[1]).removeprefix("Teren:").strip() if len(info) > 1 else ""

        desktop = panel.select_one("div.hidden-sm.hidden-xs .matchScoreList") or panel.select_one(".matchScoreList")
        team_links = [a for a in panel.select("div.matchTeamList a") if TEAM_ID_RE.search(a.get("href", ""))]
        if not desktop or len(team_links) < 2:
            continue
        score_link = desktop.find("a")
        home_a, away_a = team_links[0], team_links[1]
        score = _parse_score(_text(score_link))
        match = {
            "frf_id": _id(MATCH_ID_RE, score_link.get("href")),
            "frf_url": score_link.get("href", ""),
            "round": round_no,
            "date": parse_ro_datetime(when),
            "venue": venue,
            "home": {"frf_id": _id(TEAM_ID_RE, home_a["href"]), "name": _text(home_a), "url": home_a["href"]},
            "away": {"frf_id": _id(TEAM_ID_RE, away_a["href"]), "name": _text(away_a), "url": away_a["href"]},
            "is_finished": score is not None,
            "home_score": score[0] if score else None,
            "away_score": score[1] if score else None,
            "ht_home": score[2] if score else None,
            "ht_away": score[3] if score else None,
        }
        if match["frf_id"]:
            matches.append(match)
    return matches


def _parse_lineup_block(block):
    """Un bloc 'blueColored' cu titulari + rezerve pentru o echipă."""
    players = []
    is_starter = True
    for el in block.find_all(["h4", "div"]):
        if el.name == "h4":
            is_starter = "titular" in _text(el).lower()
            continue
        if "row" not in (el.get("class") or []):
            continue
        link = el.select_one("h5 a")
        if not link:
            continue
        img = el.select_one(".images img")
        photo = img.get("src", "") if img else ""
        if "avatar" in photo:
            photo = ""
        info = _text(el.select_one(".summary p"))
        card = ""
        m = re.search(r"Carnet:\s*(.*?)\s*(\d{2}-\d{2}-\d{4}|$)", info)
        if m:
            card = m.group(1).strip()
        players.append({
            "frf_id": _id(PLAYER_ID_RE, link.get("href")),
            "name": _text(link),
            "birth_date": parse_dmy(info),
            "card_number": card,
            "photo_url": photo,
            "is_starter": is_starter,
        })
    return players


def parse_match(html):
    """Detaliile unui meci: echipe de start, evenimente, arbitru, pauză."""
    soup = BeautifulSoup(html, "html.parser")
    data = {"referee": "", "ht": (None, None), "home_players": [], "away_players": [], "events": []}

    m = re.search(r"Pauza:\s*(\d+)\s*-\s*(\d+)", soup.get_text(" "))
    if m:
        data["ht"] = (int(m.group(1)), int(m.group(2)))

    for td in soup.select("td"):
        strong = td.find("strong")
        if strong and _text(strong) == "Arbitru":
            link = td.find("a")
            data["referee"] = _text(link)
            break

    blocks = soup.select("div.col-md-4.blueColored")
    if len(blocks) >= 2:
        data["home_players"] = _parse_lineup_block(blocks[0])
        data["away_players"] = _parse_lineup_block(blocks[1])

    for box in soup.select("div.timeline_box"):
        classes = box.get("class") or []
        kind_code = next((c.removeprefix("timeline_box_") for c in classes if c.startswith("timeline_box_")), "")
        minute_m = MINUTE_RE.search(_text(box.select_one(".date")))
        minute = int(minute_m.group(1)) if minute_m else 0
        column = box.find_parent("div", class_="col-sm-6")
        side = "away" if column and column.get("data-align") == "right" else "home"
        p = box.find("p")
        links = p.find_all("a") if p else []
        detail_el = p.find("span") if p else None
        detail = _text(detail_el)

        event = {"minute": minute, "side": side, "detail": "", "player_id": None, "player_out_id": None}
        if kind_code == "CH":
            event["kind"] = "sub"
            if links:
                event["player_id"] = _id(PLAYER_ID_RE, links[0].get("href"))
                event["player_name"] = _text(links[0])
            if len(links) > 1:
                event["player_out_id"] = _id(PLAYER_ID_RE, links[1].get("href"))
        else:
            if links:
                event["player_id"] = _id(PLAYER_ID_RE, links[0].get("href"))
                event["player_name"] = _text(links[0])
            if kind_code == "G":
                low = detail.lower()
                if "(a)" in low:
                    event["kind"] = "own_goal"
                elif "(p)" in low or "penal" in low:
                    event["kind"] = "penalty"
                else:
                    event["kind"] = "goal"
            elif kind_code == "YC":
                event["kind"] = "yellow"
                event["detail"] = detail.removeprefix("CG:").strip()
            elif kind_code == "RC":
                reason = detail.removeprefix("CR:").strip()
                event["kind"] = "second_yellow" if "al doilea avertisment" in reason.lower() else "red"
                event["detail"] = reason
            else:
                continue
        data["events"].append(event)
    return data


def parse_roster(html):
    """Lotul de jucători al unei echipe (pagina .../echipe/<slug>.html/jucatori)."""
    soup = BeautifulSoup(html, "html.parser")
    players = []
    seen = set()
    for item in soup.select("li.item"):
        link = item.select_one("h4.title a[href*='/jucatori/']")
        if not link:
            continue
        pid = _id(PLAYER_ID_RE, link.get("href"))
        name = _text(link)
        if not pid or not name or pid in seen:
            continue
        seen.add(pid)
        text = _text(item)
        m = re.search(r"Nr\. carnet:\s*(.*)$", text)
        card = m.group(1).strip() if m else ""
        img = item.find("img")
        photo = img.get("src", "") if img else ""
        players.append({
            "frf_id": pid,
            "name": name,
            "birth_date": parse_dmy(text),
            "card_number": card,
            "photo_url": "" if "avatar" in photo else photo,
        })
    return players


def compute_minutes(players, events, full_time=90):
    """
    Calculează minutul de intrare/ieșire și minutele jucate pentru fiecare jucător
    pe baza titularilor și a schimbărilor / eliminărilor.
    Întoarce {player_id: (minute_in, minute_out, minutes_played)} doar pentru cei care au jucat.
    """
    last_minute = max([full_time] + [min(e["minute"], 120) for e in events])
    end = full_time if last_minute <= full_time + 10 else last_minute
    entered = {}
    left = {}
    for p in players:
        if p["is_starter"] and p["frf_id"]:
            entered[p["frf_id"]] = 0
    for e in sorted(events, key=lambda e: e["minute"]):
        minute = min(e["minute"], end)
        if e["kind"] == "sub":
            if e.get("player_id"):
                entered.setdefault(e["player_id"], minute)
            if e.get("player_out_id"):
                left.setdefault(e["player_out_id"], minute)
        elif e["kind"] in ("red", "second_yellow") and e.get("player_id"):
            left.setdefault(e["player_id"], minute)
    result = {}
    for pid, start in entered.items():
        stop = left.get(pid, end)
        result[pid] = (start, left.get(pid), max(0, min(stop, end) - start))
    return result
