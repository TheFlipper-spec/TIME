"""Plot progression: stages, postcards from the killer, endings."""
from __future__ import annotations

POSTCARDS = [
    {
        "id": 1,
        "stage": 1,
        "title": {"ru": "Открытка №1", "en": "Postcard №1"},
        "text": {
            "ru": "Ты любишь оставлять следы, детектив. Я тоже люблю. Только мои следы ведут назад.",
            "en": "You like to leave traces, detective. So do I. Only mine lead backwards.",
        },
    },
    {
        "id": 2,
        "stage": 2,
        "title": {"ru": "Открытка №2", "en": "Postcard №2"},
        "text": {
            "ru": "Двадцать третьего, ночью, я помню каждый миг. Вопрос в том, помнишь ли ты…",
            "en": "On the twenty-third, at night, I remember every moment. The question is whether you do…",
        },
    },
    {
        "id": 3,
        "stage": 3,
        "title": {"ru": "Открытка №3", "en": "Postcard №3"},
        "text": {
            "ru": "Ты прочитал моё имя. А сможешь ли ты прочитать меня?",
            "en": "You read my name. But can you read me?",
        },
    },
    {
        "id": 4,
        "stage": 4,
        "title": {"ru": "Открытка №4", "en": "Postcard №4"},
        "text": {
            "ru": "Мы ещё встретимся, детектив. Время на моей стороне.",
            "en": "We will meet again, detective. Time is on my side.",
        },
    },
    {
        "id": 5,
        "stage": 5,
        "title": {"ru": "Открытка №5", "en": "Postcard №5"},
        "text": {
            "ru": "Ты взял моё. Я заберу твоё. Скоро.",
            "en": "You took what's mine. I'll take what's yours. Soon.",
        },
    },
]


def compute_stage(state) -> int:
    """Plot stage derived from the clues found:
    0 start · 1 fingerprints · 2 date known · 3 TIME found · 4 EMIT known · 5 knife found
    """
    stage = 0
    if state.has_clue("fingerprints"):
        stage = max(stage, 1)
    if state.has_clue("ticket") or state.has_clue("calendar"):
        stage = max(stage, 2)
    if state.has_clue("writing_time") and state.has_clue("killer_note"):
        stage = max(stage, 3)
    if state.has_clue("database_emit"):
        stage = max(stage, 4)
    if state.has_clue("bloody_knife"):
        stage = max(stage, 5)
    return stage


def update_stage(state) -> int:
    new = compute_stage(state)
    if new > state.plot_stage:
        state.plot_stage = new
    return state.plot_stage


def new_postcards_for(state) -> list[dict]:
    """Postcards that should arrive at Mike's mailbox now (by stage)."""
    stage = compute_stage(state)
    return [p for p in POSTCARDS if p["stage"] <= stage and p["id"] not in state.postcards]


def deliver_postcards(state, mailbox: bool = True) -> list[dict]:
    """Deliver pending postcards; returns newly delivered ones."""
    pending = new_postcards_for(state)
    delivered = []
    for p in pending:
        if mailbox or state.flags.get("postcard_direct", False):
            state.postcards.append(p["id"])
            state.stats["postcards_received"] += 1
            delivered.append(p)
    return delivered


def clue_notes(state) -> list[dict]:
    """Auto notes recorded in the notebook when certain clues combine."""
    notes = []
    if state.has_clue("writing_time") and state.has_clue("killer_note"):
        if not any(n.get("clue") == "emit_hint" for n in state.notebook_notes):
            notes.append({
                "clue": "emit_hint",
                "title": {"ru": "Надпись на стене", "en": "Writing on the wall"},
                "text": {"ru": "TIME и записка про «наоборот». Кажется, убийца оставил не просто надпись.",
                         "en": "TIME and the note about doing things “the other way around”. It seems the killer left more than a scribble."},
            })
    if state.plot_stage >= 4:
        if not any(n.get("clue") == "emit_home" for n in state.notebook_notes):
            notes.append({
                "clue": "emit_home",
                "title": {"ru": "Где живёт EMIT", "en": "Where EMIT lives"},
                "text": {"ru": "Дом Митина — на окраине, у южной дороги. Стоит проверить.",
                         "en": "Mitin's house is on the outskirts, by the south road. Worth checking."},
            })
    return notes
