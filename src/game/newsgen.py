"""Evening news generation: headlines depend on the day's progress."""
from __future__ import annotations

from .clues import get as get_clue

ANCHOR = {"ru": "Анна Светлова", "en": "Anna Svetlova"}


def clues_found_on(state, day: int) -> list[str]:
    return [cid for cid, d in state.clue_found_day.items() if d == day]


def generate_news(state, for_day: int) -> dict:
    """Build the news bulletin for the day that just ended.

    Returns dict with ru/en headline, body, tone ('good'|'ok'|'bad'), support
    delta and whether a day-7 finale applies.
    """
    found = clues_found_on(state, for_day)
    value = sum(get_clue(c).value for c in found)
    lang = state.flags.get("lang", "ru")

    if for_day == 1 and not found:
        news = {
            "tone": "bad",
            "support_delta": -5,
            "headline": {"ru": "Убийство в Тихореченске: зацепок нет",
                         "en": "Murder in Tikhorchensk: no leads"},
            "body": {"ru": "Прошла ночь после гибели Виктора Соколова, а полиция так и не нашла следов преступника. Город в тревоге.",
                     "en": "A night has passed since Viktor Sokolov's death, and the police still have no trace of the culprit. The city is worried."},
        }
    elif not found:
        news = {
            "tone": "bad",
            "support_delta": -8,
            "headline": {"ru": "Расследование буксует",
                         "en": "The investigation is stalling"},
            "body": {"ru": "Детектив Майк и полиция не сообщают о новых уликах. Жители начинают терять надежду.",
                     "en": "Detective Mike and the police report no new evidence. The residents are losing hope."},
        }
    elif value >= 6:
        news = {
            "tone": "good",
            "support_delta": 12,
            "headline": {"ru": "Прорыв в деле Соколова!",
                         "en": "A breakthrough in the Sokolov case!"},
            "body": {"ru": "Частный детектив Майк передал полиции важные улики. Город верит: убийца будет найден.",
                     "en": "Private detective Mike handed the police important evidence. The city believes the killer will be found."},
        }
    elif value >= 3:
        news = {
            "tone": "good",
            "support_delta": 7,
            "headline": {"ru": "У детектива появились зацепки",
                         "en": "The detective has new leads"},
            "body": {"ru": "Расследование продолжается: найдены новые улики. Жители Тихореченска следят за ходом дела.",
                     "en": "The investigation continues: new evidence found. The residents of Tikhorchensk are following the case."},
        }
    else:
        news = {
            "tone": "ok",
            "support_delta": 2,
            "headline": {"ru": "Дело Соколова: работа идёт",
                         "en": "The Sokolov case: work continues"},
            "body": {"ru": "Детектив Майк работает над делом. Город ждёт новостей.",
                     "en": "Detective Mike is working on the case. The city awaits news."},
        }

    # Killer plays with the city once the identity is out
    if state.plot_stage >= 4:
        news["headline"] = {
            "ru": "Город в панике: убийца всё ещё на свободе",
            "en": "The city is in panic: the killer is still free",
        }
        news["body"] = {
            "ru": "Стали известны подробности: у убийцы Соколова есть имя — EMIT. Полиция просит горожан быть осторожными.",
            "en": "Details have emerged: Sokolov's killer has a name — EMIT. The police ask residents to be careful.",
        }
        news["support_delta"] = max(news["support_delta"], 2)
    if state.plot_stage >= 5:
        news["headline"] = {
            "ru": "Орудие убийства найдено!",
            "en": "The murder weapon has been found!",
        }
        news["body"] = {
            "ru": "Детектив Майк нашёл нож со следами крови жертвы. Убийца EMIT объявлен в розыск.",
            "en": "Detective Mike found the knife with traces of the victim's blood. The killer EMIT is now wanted.",
        }
        news["support_delta"] = max(news["support_delta"], 8)

    news["clues_today"] = len(found)
    news["clues_value"] = value
    news["for_day"] = for_day
    return news


def apply_news(state, news: dict) -> int:
    delta = news.get("support_delta", 0)
    old = state.support
    state.support = max(0.0, min(100.0, state.support + delta))
    applied = int(state.support - old)
    return applied
