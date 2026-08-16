"""Interactive props: clues with timeline windows, furniture, doors.

Every prop has a visibility window in absolute world time — this is how time
travel changes the world: a clue may only exist on 23 November 2023.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

L = lambda ru, en: {"ru": ru, "en": en}  # noqa: E731


@dataclass
class Prop:
    id: str
    map_id: str
    x: int
    y: int
    kind: str = "inspect"
    title: dict = field(default_factory=dict)
    text: dict = field(default_factory=dict)
    clue_id: Optional[str] = None
    window: Optional[list] = None        # list of (start_dt, end_dt) or None = always
    cond: Optional[Callable] = None      # fn(state) -> bool
    marker: bool = True                  # draw the "inspect me" marker

    def visible(self, state, world_dt: datetime) -> bool:
        if self.cond is not None and not self.cond(state):
            return False
        if self.window is None:
            return True
        for start, end in self.window:
            if start <= world_dt <= end:
                return True
        return False


D = datetime

# -------------------------------------------------------------- town props --
TOWN_PROPS: list[Prop] = [
    Prop("mailbox", "town", 12, 12, "mailbox",
         L("Почтовый ящик", "Mailbox"),
         L("Ваш почтовый ящик. Изнутри пахнет бумагой и приключениями.",
           "Your mailbox. It smells of paper and adventure inside."),
         marker=False),
    Prop("home_door", "town", 10, 11, "enter",
         L("Дверь дома", "Front door"),
         L("Дом Майка. Тёплый свет в окнах.", "Mike's home. Warm light in the windows."),
         marker=False),
    Prop("shop_door", "town", 73, 11, "enter",
         L("Дверь магазина", "Shop door"),
         L("Магазин Бориса. На витрине — консервы и кофе.", "Boris's shop. Tinned food and coffee in the window."),
         marker=False),
    Prop("police_door", "town", 12, 31, "enter",
         L("Дверь участка", "Station door"),
         L("Городское отделение полиции.", "The city police station."),
         marker=False),
    Prop("bank_door", "town", 71, 31, "enter",
         L("Дверь банка", "Bank door"),
         L("Банк. Стекло, колонны и вежливые охранники.", "The bank. Glass, columns and polite guards."),
         marker=False),
    Prop("warehouse_door", "town", 81, 51, "warehouse_door",
         L("Дверь склада", "Warehouse door"),
         L("Старый склад у выезда из города. Дверь на цепи.", "An old warehouse by the town exit. The door is chained."),
         marker=False),
    Prop("emit_door", "town", 12, 50, "emit_door",
         L("Дверь дома Митина", "Mitin's door"),
         L("Обшарпанный дом на окраине.", "A shabby house on the outskirts."),
         marker=False),
    Prop("victim_door", "town", 47, 51, "victim_door",
         L("Дверь дома Соколова", "Sokolov's door"),
         L("Дом, где произошло убийство. Лента полиции снята.",
           "The house where the murder happened. The police tape is gone."),
         marker=True),
    Prop("busstop", "town", 56, 43, "inspect",
         L("Остановка", "Bus stop"),
         L("Расписание: маршрут №7 — каждые 20 минут, последний рейс в 00:30.",
           "Timetable: route №7 — every 20 minutes, last bus at 00:30."),
         marker=False),
    Prop("exit_sign", "town", 93, 41, "inspect",
         L("Выезд из города", "Town exit"),
         L("Дорогу перекрыла полиция: по городу разыскивают убийцу. Без пропуска — никак.",
           "The road is blocked by the police: the killer is being hunted in town. No pass — no way out."),
         marker=False),
    Prop("trash_near_victim", "town", 55, 52, "inspect",
         L("Мусорный бак", "Trash can"),
         L("Пусто. Кто-то уже всё выбросил.", "Empty. Someone already threw everything out."),
         marker=False),
]

# --------------------------------------------------------- interior props ---
INTERIOR_PROPS: dict[str, list[Prop]] = {
    "home": [
        Prop("bed", "home", 6, 4, "bed",
             L("Кровать", "Bed"),
             L("Тёплая кровать. Сон снимает усталость: чем больше усталость — тем дольше сон.",
               "A warm bed. Sleep relieves fatigue: the more tired you are — the longer you sleep."),
             marker=False),
        Prop("wardrobe", "home", 10, 1, "wardrobe",
             L("Шкаф", "Wardrobe"),
             L("Пальто, перчатки, шляпа. Детектив без перчаток — не детектив.",
               "Coat, gloves, hat. A detective without gloves is no detective."),
             marker=False),
        Prop("computer", "home", 16, 2, "computer",
             L("Компьютер", "Computer"),
             L("Рабочий компьютер с доступом к базам данных.",
               "Work computer with access to the databases."),
             marker=False),
        Prop("fridge", "home", 19, 4, "fridge",
             L("Холодильник", "Fridge"),
             L("Остатки вчерашнего ужина. Слегка подозрительно, но съедобно.",
               "Leftovers from yesterday's dinner. Slightly suspicious, but edible."),
             marker=False),
        Prop("bookshelf", "home", 2, 1, "inspect",
             L("Книжная полка", "Bookshelf"),
             L("Детективы, криминалистика, «Время как иллюзия» — с даром Майка особенно актуально.",
               "Detective novels, forensics, “Time as an Illusion” — especially relevant given Mike's gift."),
             marker=False),
        Prop("home_exit", "home", 12, 2, "exit",
             L("Выйти на улицу", "Go outside"),
             L("", ""), marker=False),
    ],
    "shop": [
        Prop("shop_counter", "shop", 5, 4, "counter_shop",
             L("Прилавок", "Counter"),
             L("Здесь можно купить еду и лекарства.", "Food and medicine are sold here."),
             marker=False),
        Prop("shop_exit", "shop", 4, 2, "exit",
             L("Выйти", "Leave"), L("", ""), marker=False),
        Prop("shelves", "shop", 12, 1, "inspect",
             L("Полки", "Shelves"),
             L("Консервы, крупы, кофе… и аптечка за прилавком.",
               "Tinned food, grains, coffee… and a first-aid kit behind the counter."),
             marker=False),
    ],
    "bank": [
        Prop("bank_counter", "bank", 5, 4, "counter_bank",
             L("Окно кредитования", "Loan window"),
             L("Кредиты под 25% за 3 дня. Жёстко, но быстро.",
               "Loans at 25% for 3 days. Harsh, but quick."),
             marker=False),
        Prop("bank_exit", "bank", 4, 2, "exit",
             L("Выйти", "Leave"), L("", ""), marker=False),
    ],
    "police": [
        Prop("board", "police", 17, 2, "inspect",
             L("Доска дела", "Case board"),
             L("Фото Виктора Соколова, план дома, карта города. Пустое место там, где должен быть убийца.",
               "A photo of Viktor Sokolov, the house plan, a city map. An empty spot where the killer should be."),
             marker=False),
        Prop("police_exit", "police", 4, 2, "exit",
             L("Выйти", "Leave"), L("", ""), marker=False),
    ],
    "victim": [
        Prop("sofa", "victim", 7, 4, "inspect",
             L("Диван", "Sofa"),
             L("Под диваном что-то блестит…", "Something glitters under the sofa…"),
             clue_id="ticket",
             window=[(D(2023, 11, 23, 6, 0), D(2024, 1, 1))],
             marker=True),
        Prop("desk", "victim", 15, 3, "inspect",
             L("Письменный стол", "Desk"),
             L("В ящике стола — записка…", "In the desk drawer — a note…"),
             clue_id="victim_note",
             marker=True),
        Prop("calendar", "victim", 17, 1, "inspect",
             L("Календарь", "Calendar"),
             L("23 ноября обведено красным: «встреча, 00:00».",
               "November 23 is circled in red: “meeting, 00:00”."),
             clue_id="calendar",
             marker=True),
        Prop("knife_block", "victim", 3, 4, "inspect",
             L("Подставка для ножей", "Knife block"),
             L("Все ножи на месте… кроме одного. Пустой слот смотрит на вас укором.",
               "All the knives are in place… except one. The empty slot stares back accusingly."),
             marker=False),
        Prop("blood_trail", "victim", 4, 5, "inspect",
             L("Пол на кухне", "Kitchen floor"),
             L("У мусорного ведра — тёмные пятна. Похоже на засохшую кровь.",
               "By the trash can — dark stains. Looks like dried blood."),
             clue_id="blood_trail",
             window=[(D(2023, 11, 23, 0, 0), D(2023, 11, 24, 23, 59))],
             marker=True),
        Prop("wall_writing", "victim", 10, 1, "inspect",
             L("Стена в гостиной", "Living room wall"),
             L("Крупная надпись кровью: TIME.",
               "A large inscription in blood: TIME."),
             clue_id="writing_time",
             window=[(D(2023, 11, 23, 0, 0), D(2023, 11, 24, 7, 59))],
             marker=True),
        Prop("table", "victim", 11, 5, "inspect",
             L("Стол", "Table"),
             L("На столе записка. Слово «наоборот» написано красным.",
               "A note on the table. The word “opposite” is written in red."),
             clue_id="killer_note",
             window=[(D(2023, 11, 23, 0, 0), D(2023, 11, 24, 7, 59))],
             marker=True),
        Prop("photo", "victim", 19, 3, "inspect",
             L("Фотография", "Photograph"),
             L("Виктор Соколов за стойкой своего кафе. Улыбается. Кажется, добрый был человек.",
               "Viktor Sokolov behind the counter of his café. Smiling. He seems to have been a kind man."),
             marker=False),
        Prop("victim_exit", "victim", 4, 2, "exit",
             L("Выйти", "Leave"), L("", ""), marker=False),
    ],
    "emit": [
        Prop("floorboard", "emit", 15, 4, "inspect",
             L("Половица", "Floorboard"),
             L("Одна половица выглядит… подозрительно свободной.",
               "One floorboard looks… suspiciously loose."),
             clue_id="bloody_knife",
             cond=lambda s: s.plot_stage >= 4,
             marker=True),
        Prop("mirror", "emit", 10, 1, "inspect",
             L("Зеркало", "Mirror"),
             L("На зеркале маркером выведено: TIME. Кто-то очень любит это слово.",
               "On the mirror, in marker: TIME. Someone loves that word."),
             cond=lambda s: s.plot_stage >= 4,
             marker=False),
        Prop("postcard_box", "emit", 6, 4, "inspect",
             L("Коробка", "Box"),
             L("Коробка почтовых открыток. Те самые открытки, что приходили вам.",
               "A box of postcards. The very postcards that were sent to you."),
             clue_id="postcard_box",
             cond=lambda s: s.plot_stage >= 4,
             marker=True),
        Prop("emit_exit", "emit", 4, 2, "exit",
             L("Выйти", "Leave"), L("", ""), marker=False),
    ],
    "warehouse": [
        Prop("crates", "warehouse", 10, 3, "inspect",
             L("Ящики", "Crates"),
             L("Пыльные ящики. Здесь давно никого не было… или были?",
               "Dusty crates. Nobody has been here in a long time… or have they?"),
             marker=False),
        Prop("warehouse_exit", "warehouse", 4, 2, "exit",
             L("Выйти", "Leave"), L("", ""), marker=False),
    ],
}


def props_for(map_id: str) -> list[Prop]:
    if map_id == "town":
        return TOWN_PROPS
    return INTERIOR_PROPS.get(map_id, [])


def find_prop(map_id: str, prop_id: str) -> Optional[Prop]:
    for p in props_for(map_id):
        if p.id == prop_id:
            return p
    return None
