from django.conf import settings
from django.db import models
from django.urls import reverse


class Team(models.Model):
    frf_id = models.PositiveIntegerField(unique=True, help_text="ID-ul echipei pe frf-ajf.ro")
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    frf_url = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    venue = models.CharField(max_length=150, blank=True)
    points_adjustment = models.IntegerField(
        default=0, help_text="Puncte scăzute/adăugate de comisii (ex: -3). Se aplică în clasament.")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_ours(self):
        return self.frf_id == settings.OUR_TEAM_FRF_ID

    def get_absolute_url(self):
        return reverse("team_detail", args=[self.slug])


class Player(models.Model):
    POSITIONS = [
        ("Portar", "Portar"),
        ("Fundaș", "Fundaș"),
        ("Mijlocaș", "Mijlocaș"),
        ("Atacant", "Atacant"),
    ]

    frf_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    birth_date = models.DateField(null=True, blank=True)
    card_number = models.CharField("Nr. carnet", max_length=50, blank=True)
    photo_url = models.URLField(blank=True, help_text="Poza de pe frf-ajf.ro (dacă există)")
    registered = models.BooleanField(default=False, help_text="Apare în lotul oficial al clubului pe FRF")

    # Câmpuri editabile din Admin (nu sunt suprascrise de sincronizare)
    number = models.PositiveIntegerField(null=True, blank=True)
    position = models.CharField(max_length=50, choices=POSITIONS, blank=True)
    bio = models.TextField(blank=True, help_text="A little details about the player")
    image = models.ImageField(upload_to="players/", blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        prefix = f"{self.number} - " if self.number else ""
        return f"{prefix}{self.name}"

    def get_absolute_url(self):
        return reverse("player_detail", args=[self.pk])

    @property
    def picture(self):
        if self.image:
            return self.image.url
        return self.photo_url

    @property
    def age(self):
        if not self.birth_date:
            return None
        from datetime import date

        today = date.today()
        b = self.birth_date
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))


class Match(models.Model):
    frf_id = models.PositiveIntegerField(unique=True)
    frf_url = models.URLField(blank=True)
    round = models.PositiveSmallIntegerField("Etapa")
    date = models.DateTimeField(null=True, blank=True)
    venue = models.CharField(max_length=150, blank=True)
    home = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_matches")
    away = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_matches")
    home_score = models.PositiveSmallIntegerField(null=True, blank=True)
    away_score = models.PositiveSmallIntegerField(null=True, blank=True)
    ht_home = models.PositiveSmallIntegerField(null=True, blank=True)
    ht_away = models.PositiveSmallIntegerField(null=True, blank=True)
    is_finished = models.BooleanField(default=False)
    referee = models.CharField(max_length=100, blank=True)
    details_synced = models.BooleanField(default=False, help_text="Echipele de start și evenimentele au fost importate")

    class Meta:
        ordering = ["round", "date", "pk"]
        verbose_name_plural = "matches"

    def __str__(self):
        return f"Etapa {self.round}: {self.home} - {self.away}"

    def get_absolute_url(self):
        return reverse("match_detail", args=[self.pk])

    @property
    def score(self):
        if not self.is_finished:
            return None
        return f"{self.home_score} - {self.away_score}"

    @property
    def has_halftime(self):
        return self.ht_home is not None and self.ht_away is not None

    def involves(self, team):
        return team.pk in (self.home_id, self.away_id)

    def opponent_of(self, team):
        return self.away if self.home_id == team.pk else self.home

    def goals_for(self, team):
        return self.home_score if self.home_id == team.pk else self.away_score

    def goals_against(self, team):
        return self.away_score if self.home_id == team.pk else self.home_score

    def result_for(self, team):
        """'V' (victorie), 'E' (egal) sau 'I' (înfrângere) din perspectiva echipei."""
        if not self.is_finished:
            return None
        gf, ga = self.goals_for(team), self.goals_against(team)
        if gf > ga:
            return "V"
        if gf < ga:
            return "I"
        return "E"


class Appearance(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="appearances")
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="appearances")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="appearances")
    is_starter = models.BooleanField(default=False)
    minute_in = models.PositiveSmallIntegerField(null=True, blank=True)
    minute_out = models.PositiveSmallIntegerField(null=True, blank=True)
    minutes_played = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = [("match", "player")]
        ordering = ["-is_starter", "player__name"]

    def __str__(self):
        return f"{self.player} @ {self.match}"


class MatchEvent(models.Model):
    GOAL = "goal"
    OWN_GOAL = "own_goal"
    PENALTY = "penalty"
    YELLOW = "yellow"
    SECOND_YELLOW = "second_yellow"
    RED = "red"
    SUB = "sub"
    KINDS = [
        (GOAL, "Gol"),
        (OWN_GOAL, "Autogol"),
        (PENALTY, "Gol din penalty"),
        (YELLOW, "Cartonaș galben"),
        (SECOND_YELLOW, "Al doilea galben"),
        (RED, "Cartonaș roșu"),
        (SUB, "Schimbare"),
    ]
    GOAL_KINDS = (GOAL, PENALTY)

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="events")
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="events",
                             help_text="Echipa jucătorului (la autogol: echipa care a greșit)")
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    player_out = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    kind = models.CharField(max_length=20, choices=KINDS)
    minute = models.PositiveSmallIntegerField(default=0)
    detail = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["minute", "pk"]

    def __str__(self):
        return f"{self.minute}' {self.get_kind_display()} {self.player}"

    @property
    def is_home(self):
        return self.team_id == self.match.home_id

    @property
    def icon(self):
        return {
            self.GOAL: "⚽",
            self.PENALTY: "⚽",
            self.OWN_GOAL: "⚽",
            self.YELLOW: "🟨",
            self.SECOND_YELLOW: "🟨🟥",
            self.RED: "🟥",
            self.SUB: "🔁",
        }[self.kind]


class SyncRun(models.Model):
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    ok = models.BooleanField(default=False)
    summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"Sincronizare {self.started_at:%d.%m.%Y %H:%M} ({'OK' if self.ok else 'eșuată'})"
