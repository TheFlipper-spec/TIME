"""Clue definitions: names, descriptions, rewards.

Rewards are paid the next morning: the more the clue advances the
investigation, the higher the reward.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Clue:
    id: str
    name_ru: str
    name_en: str
    desc_ru: str
    desc_en: str
    reward: float
    value: int = 1          # investigation weight (used by the news)

    @property
    def name(self) -> dict:
        return {"ru": self.name_ru, "en": self.name_en}

    @property
    def desc(self) -> dict:
        return {"ru": self.desc_ru, "en": self.desc_en}


CLUES: dict[str, Clue] = {c.id: c for c in [
    Clue("fingerprints",
         "Отпечатки пальцев на ручке",
         "Fingerprints on the door handle",
         "На дверной ручке дома Соколова — чужие отпечатки. Записано в блокнот: нужно проверить, чьи они.",
         "On the door handle of Sokolov's house — someone else's prints. Noted: they need to be checked.",
         40, 2),
    Clue("ticket",
         "Автобусный билет",
         "Bus ticket",
         "Под диваном в гостиной — билет маршрута №7, 23.11.2023, 00:10. Кто-то был здесь в ночь убийства.",
         "Under the sofa in the living room — a route №7 ticket, 23.11.2023, 00:10. Someone was here on the night of the murder.",
         60, 3),
    Clue("victim_note",
         "Записка Виктора",
         "Viktor's note",
         "В ящике письменного стола записка в руке Виктора: «Боюсь, он меня нашёл. Если что-то случится — вспомните, он любит играть со временем».",
         "In the desk drawer, a note in Viktor's hand: “I'm afraid he found me. If anything happens — remember, he likes to play with time”.",
         50, 2),
    Clue("calendar",
         "Календарь с пометкой",
         "Marked calendar",
         "В кабинете на календаре красным обведено 23 ноября: «встреча, 00:00». Виктор сам назначил встречу в ночь убийства.",
         "In the study, November 23 is circled in red on the calendar: “meeting, 00:00”. Viktor scheduled a meeting for the night of the murder.",
         80, 3),
    Clue("blood_trail",
         "Следы крови на кухне",
         "Blood traces in the kitchen",
         "На полу кухни, у мусорного ведра, — засохшие следы крови. Полиция их не заметила.",
         "On the kitchen floor, by the trash can — dried traces of blood. The police missed them.",
         30, 1),
    Clue("marta_testimony",
         "Показания Марты Семёновны",
         "Testimony of Marta Semyonovna",
         "Соседка слышала крики в ночь с 22 на 23 ноября и видела мужчину в тёмном плаще и кепке у дома Виктора около 00:15. Он что-то шептал — ей послышалось слово «время».",
         "The neighbor heard screams on the night of Nov 22–23 and saw a man in a dark coat and cap near Viktor's house at about 00:15. He was whispering — she thought she heard the word “time”.",
         40, 2),
    Clue("nick_testimony",
         "Показания Ника Армстронга",
         "Testimony of Nick Armstrong",
         "Ник видел, как в 00:20 с 22 на 23 ноября мужчина в тёмном плаще вышел из дома Соколова с чем-то завёрнутым в тряпку и сел на автобус №7.",
         "Nick saw a man in a dark coat leave Sokolov's house at 00:20 on the night of Nov 22–23, carrying something wrapped in a cloth, and board bus №7.",
         70, 3),
    Clue("boris_testimony",
         "Показания Бориса",
         "Testimony of Boris",
         "Вечером 22 ноября в магазин заходил мужчина в тёмном плаще и кепке — купил скотч и перчатки. Руки у него дрожали.",
         "On the evening of Nov 22, a man in a dark coat and cap came into the shop — he bought tape and gloves. His hands were shaking.",
         50, 2),
    Clue("writing_time",
         "Надпись на стене",
         "Writing on the wall",
         "На стене гостиной — крупная надпись кровью: TIME. Убийца оставил подпись.",
         "On the living room wall — a large inscription in blood: TIME. The killer left his signature.",
         200, 5),
    Clue("killer_note",
         "Записка убийцы",
         "The killer's note",
         "На столе записка: «Порой люди спешат и делают всё буквально. Не пора ли вам задуматься и сделать наоборот». Слово «наоборот» написано кровью жертвы.",
         "On the table, a note: “People are always in a hurry and take everything literally. Isn't it time you thought and did the opposite.” The word “opposite” is written in the victim's blood.",
         150, 5),
    Clue("database_emit",
         "Досье: EMIT",
         "File: EMIT",
         "По базам найден EMIT — Егор Митин. В ночь убийства его телефон был зарегистрирован у вышки в 200 метрах от дома Соколова. Известен привычкой носить часы наоборот.",
         "Databases found EMIT — Yegor Mitin. On the night of the murder his phone was registered at a cell tower 200 m from Sokolov's house. Known for wearing his watch backwards.",
         100, 4),
    Clue("bloody_knife",
         "Кровавый нож",
         "The bloody knife",
         "Под половицей в доме Митина — кухонный нож в засохшей крови. Похоже, это нож из кухни Виктора.",
         "Under a floorboard in Mitin's house — a kitchen knife with dried blood. It looks like Viktor's kitchen knife.",
         250, 5),
    Clue("postcard_box",
         "Коробка открыток",
         "A box of postcards",
         "В доме Митина — коробка почтовых открыток. Те самые открытки, что приходили Майку.",
         "In Mitin's house — a box of postcards. The very postcards that were sent to Mike.",
         30, 1),
]}


def get(clue_id: str) -> Clue:
    return CLUES[clue_id]


def total_reward(ids: list[str]) -> float:
    return sum(CLUES[i].reward for i in ids if i in CLUES)
