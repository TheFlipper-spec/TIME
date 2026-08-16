"""Witnesses: personalities, dialogue trees, tasks, intimidation.

Each witness reacts differently:
- some talk freely (their willingness depends on public support),
- some need a favor first (Nick — clear his criminal record, Boris — find his cat),
- and there is always the risky alternative: force the information out.
"""
from __future__ import annotations

import random

from ..audio import play
from .clues import get as get_clue
from .story import deliver_postcards, update_stage

L = lambda ru, en: {"ru": ru, "en": en}  # noqa: E731


# ------------------------------------------------------------- dialogue -----
class Choice:
    def __init__(self, label: dict, effect=None, next_turn=None, cond=None) -> None:
        self.label = label
        self.effect = effect          # fn(state, scene) -> None or Turn
        self.next = next_turn         # Turn or None (close)
        self.cond = cond              # fn(state, scene) -> bool


class Turn:
    def __init__(self, speaker: str, text: dict, choices: list | None = None,
                 on_enter=None) -> None:
        self.speaker = speaker
        self.text = text
        self.choices = choices or []
        self.on_enter = on_enter


# ------------------------------------------------------------- registry -----
WITNESSES: dict[str, dict] = {
    "marta": {
        "name": L("Марта Семёновна", "Marta Semyonovna"),
        "portrait": 11,
        "desc": L("Пожилая соседка Виктора. Говорят, она ничего не пропускает.",
                  "Viktor's elderly neighbor. They say nothing escapes her."),
    },
    "nick": {
        "name": L("Ник Армстронг", "Nick Armstrong"),
        "portrait": 22,
        "desc": L("Молодой парень с нехорошей репутацией. Всё время трёт ладони.",
                  "A young man with a bad reputation. He keeps rubbing his hands."),
    },
    "boris": {
        "name": L("Борис", "Boris"),
        "portrait": 33,
        "desc": L("Хозяин магазина. Любит порядок и своего кота Рыжика.",
                  "The shopkeeper. Loves order and his cat Ryzhik."),
    },
    "volkov": {
        "name": L("Капитан Волков", "Captain Volkov"),
        "portrait": 44,
        "desc": L("Капитан полиции. Ведёт дело Соколова вместе с вами.",
                  "Police captain. Works the Sokolov case alongside you."),
    },
    "krylov": {
        "name": L("Офицер Крылов", "Officer Krylov"),
        "portrait": 55,
        "desc": L("Молодой полицейский. Дежурит в доме Соколова.",
                  "A young officer. Stands watch at Sokolov's house."),
    },
    "krylov2": {
        "name": L("Офицер Лебедев", "Officer Lebedev"),
        "portrait": 56,
        "desc": L("Эксперт-криминалист. Любит порядок и тишину.",
                  "A forensic expert. Loves order and silence."),
    },
    "banker": {
        "name": L("Генрих Вагнер", "Heinrich Wagner"),
        "portrait": 66,
        "desc": L("Управляющий банком. Вежлив, но счёт любит.",
                  "The bank manager. Polite, but keeps a close eye on the numbers."),
    },
    "w1": {
        "name": L("Прохожий", "Passerby"),
        "portrait": 77,
        "desc": L("Житель Тихореченска.", "A resident of Tikhorchensk."),
    },
    "w2": {
        "name": L("Прохожая", "Passerby"),
        "portrait": 88,
        "desc": L("Жительница Тихореченска.", "A resident of Tikhorchensk."),
    },
    "w3": {
        "name": L("Старик на лавочке", "Old man on a bench"),
        "portrait": 99,
        "desc": L("Местный старожил. Любит посидеть в парке.",
                  "A local old-timer. Likes to sit in the park."),
    },
    "emit": {
        "name": L("Егор Митин (EMIT)", "Yegor Mitin (EMIT)"),
        "portrait": 13,
        "desc": L("Человек из досье. Кажется, он вас заметил.",
                  "The man from the file. It seems he has noticed you."),
    },
}


# -------------------------------------------------------------- helpers -----
def _grant(state, scene, clue_id: str, toast_key: str | None = None) -> None:
    """Register a clue with feedback (sound + toast + stage update)."""
    if state.add_clue(clue_id):
        clue = get_clue(clue_id)
        lang = scene.app.settings.language
        play("clue")
        if toast_key:
            scene.toast(scene.app.tr.t(clue.name.get(lang, clue.name_ru), **{}))
        else:
            scene.toast(clue.name.get(lang, clue.name_ru))
        update_stage(state)
        scene.on_plot_progress()
    else:
        play("click")


def _task(state, task_id: str) -> None:
    state.tasks.setdefault(task_id, "active")


# ----------------------------------------------------------------- marta ----
def talk_marta(state, scene) -> Turn:
    if not state.clues and state.support < 30:
        return Turn("marta", L(
            "Говорят, по городу ходит детектив, а улик — ни одной. Вот найдёте хоть одну — тогда и поговорим.",
            "They say a detective walks around town without a single clue. Find at least one — then we'll talk.",
        ))
    if not state.has_clue("marta_testimony"):
        return Turn("marta", L(
            "Ох, горе-то какое… В ту ночь, с 22 на 23, я не спала — сердце. Слышу: крик! Я к окну. А из дома Виктора выходит мужчина — высокий, в тёмном плаще, кепка до бровей. И шепчет что-то… я разобрала слово — «время». Сел на автобус №7 и уехал. Жуть!",
            "Oh, what a tragedy… That night, from the 22nd to the 23rd, I couldn't sleep — my heart. I heard a scream! I went to the window. A man came out of Viktor's house — tall, in a dark coat, cap pulled to his brows. And whispering something… I caught the word — “time”. He got on bus №7 and left. Terrible!",
        ), choices=[Choice(L("Спасибо, Марта Семёновна", "Thank you, Marta Semyonovna"),
                           effect=lambda s, g: _grant(s, g, "marta_testimony"))])
    return Turn("marta", L(
        "Виктор в последние недели сам не свой был. Говорил: кто-то оставляет ему записки. Я думала — шутки чьи-то… А оно вон как обернулось.",
        "Viktor had been strange these last weeks. He said someone kept leaving him notes. I thought it was somebody's joke… And look how it turned out.",
    ))


# ------------------------------------------------------------------ nick ----
def talk_nick(state, scene) -> Turn:
    if state.flags.get("nick_ran"):
        return Turn("nick", L(
            "Вали отсюда, псих! Я тебе уже всё сказал!",
            "Get lost, psycho! I already told you everything!",
        ))
    if state.flags.get("nick_agreed") and state.tasks.get("nick_clear") != "done":
        return Turn("nick", L(
            "Ну что? Договорился с капитаном? Пока он не снимет обвинения — я больше ничего не скажу.",
            "So? Did you talk to the captain? Until the charges are dropped — I'm not saying anything else.",
        ))
    if state.tasks.get("nick_clear") == "done":
        if not state.has_clue("nick_testimony"):
            return Turn("nick", L(
                "Капитан снял обвинения. Ладно, детектив, ты мужик слова. Слушай: в ту ночь я шатался у остановки. В 00:20 из дома Соколова вышел тип — плащ, кепка. Нёс что-то завёрнутое в тряпку. Сел на №7 и укатил. Больше я его не видел… до сегодняшнего дня.",
                "The captain dropped the charges. Alright, detective, you're a man of your word. Listen: that night I was hanging around the bus stop. At 00:20 a guy came out of Sokolov's house — coat, cap. Carrying something wrapped in a cloth. He got on №7 and rode off. I never saw him again… until today.",
            ), choices=[Choice(L("До сегодняшнего дня?", "Until today?"),
                               effect=lambda s, g: _grant(s, g, "nick_testimony")),
                        Choice(L("Спасибо, Ник", "Thanks, Nick"),
                               effect=lambda s, g: _grant(s, g, "nick_testimony"))])
        return Turn("nick", L(
            "Тот тип — странный. Кепку не снимает даже в помещении. И часы… часы у него наоборот надеты, я видел. Люди так не ходят.",
            "That guy — weird. He doesn't take his cap off even indoors. And the watch… he wears his watch backwards, I saw it. People don't do that.",
        ))
    if not state.flags.get("nick_prints_known"):
        return Turn("nick", L(
            "Я вас не знаю и знать не хочу. Проваливайте.",
            "I don't know you and I don't want to. Get lost.",
        ), choices=[
            Choice(L("Выбить информацию силой", "Beat the information out of him"),
                   effect=lambda s, g: _force_nick(s, g)),
            Choice(L("Уйти", "Leave")),
        ])
    # player knows the prints belong to Nick
    return Turn("nick", L(
        "Ладно, ладно… Это мои отпечатки на ручке. Я заходил — но уже ПОСЛЕ убийства, дом стоял открытый! Клянусь, я ничего не брал! Я видел кое-что… но рот у меня на замке, пока у меня проблемы с законом.",
        "Fine, fine… Those prints on the handle are mine. I went in — but only AFTER the murder, the house was left open! I swear I took nothing! I saw something… but my mouth stays shut while I've got trouble with the law.",
    ), choices=[
        Choice(L("Я замолвлю слово перед капитаном", "I'll put in a word with the captain"),
               effect=lambda s, g: _agree_nick(s, g)),
        Choice(L("Выбить информацию силой", "Beat the information out of him"),
               effect=lambda s, g: _force_nick(s, g)),
        Choice(L("Уйти", "Leave")),
    ])


def _agree_nick(state, scene) -> None:
    state.flags["nick_agreed"] = True
    _task(state, "nick_clear")
    scene.toast(scene.app.tr.t("notebook.task_nick_clear"))
    play("confirm")


def _force_nick(state, scene) -> Turn:
    state.stats["intimidations"] += 1
    chance = state.intimidation_chance
    if random.random() < chance:
        play("alert")
        state.support = max(0.0, state.support - 5)
        state.add_clue("nick_testimony")
        state.clue_found_day["nick_testimony"] = state.day
        update_stage(state)
        scene.on_plot_progress()
        scene.toast(get_clue("nick_testimony").name.get(scene.app.settings.language))
        return Turn("nick", L(
            "Не надо! Не бейте! Всё скажу! В 00:20 он вышел из дома — плащ, кепка, что-то в тряпке. Сел на №7. Больше не видел!",
            "No! Don't hit me! I'll tell you everything! At 00:20 he came out of the house — coat, cap, something wrapped in cloth. Got on №7. Never saw him again!",
        ))
    state.flags["nick_ran"] = True
    state.support = max(0.0, state.support - 15)
    play("error")
    scene.toast(scene.app.tr.t("dialogue.force_fail"))
    return Turn("nick", L(
        "Помогите! Детектив бьёт людей! Вали отсюда, псих!",
        "Help! The detective is beating people! Get away from me, psycho!",
    ))


# ---------------------------------------------------------------- boris -----
def talk_boris(state, scene) -> Turn:
    if state.tasks.get("cat") == "active" and not state.flags.get("cat_carried"):
        return Turn("boris", L(
            "Рыжик! Ты нашёл моего Рыжика? Нет? Тогда зачем пришёл? Кот пропал вчера вечером, он гуляет в парке!",
            "Ryzhik! Did you find my Ryzhik? No? Then why are you here? The cat went missing last night — he roams the park!",
        ), choices=[Choice(L("Найду вашего кота", "I'll find your cat"),
                           effect=lambda s, g: _task(s, "cat")),
                    Choice(L("Мне нужно кое-что другое…", "I need something else…"),
                           next_turn=Turn("boris", L(
                               "Без кота разговора не будет. Я за него переживаю!",
                               "No cat, no talk. I'm worried about him!",
                           )))])
    if state.flags.get("cat_carried"):
        return Turn("boris", L(
            "Рыжик! Родной мой! Спасибо, детектив! Вот, держите — за беспокойство. И… знаете, раз вы так помогли — скажу. Вечером 22-го, перед закрытием, заходил мужик — плащ, кепка, руки дрожат. Купил скотч и перчатки. Расплатился мелочью. Запомнил я его — таких лиц не забывают.",
            "Ryzhik! My dear! Thank you, detective! Here — for your trouble. And… since you helped me — I'll tell you. On the evening of the 22nd, before closing, a man came in — coat, cap, shaking hands. Bought tape and gloves. Paid in coins. I remember him — you don't forget faces like that.",
        ), choices=[Choice(L("Спасибо, Борис", "Thank you, Boris"),
                           effect=lambda s, g: (_task_done(s, "cat"),
                                                s.earn(20, "task"),
                                                _grant(s, g, "boris_testimony")))])
    if state.support >= 40 or state.has_clue("boris_testimony"):
        if not state.has_clue("boris_testimony"):
            return Turn("boris", L(
                "Слышал, город про вас хорошо говорит. Ладно, помогу: вечером 22-го заходил мужик — плащ, кепка, руки дрожат. Купил скотч и перчатки. Мелочью расплатился. Таких лиц я не забываю.",
                "I hear the city speaks well of you. Fine, I'll help: on the evening of the 22nd a man came in — coat, cap, shaking hands. Bought tape and gloves. Paid in coins. I don't forget faces like that.",
            ), choices=[Choice(L("Спасибо, Борис", "Thank you, Boris"),
                               effect=lambda s, g: _grant(s, g, "boris_testimony"))])
        return Turn("boris", L(
            "Ах да, тот тип в кепке… Больше я его в магазине не видел. И, честно говоря, не хочу видеть.",
            "Oh, that man in the cap… I never saw him in the shop again. And honestly, I don't want to.",
        ))
    return Turn("boris", L(
        "Здравствуйте. Что-нибудь купить? Или… вы по делу убийства? Знаете, я бы помог, но город недоволен работой полиции. Найдите сначала моего кота Рыжика — он в парке. Вернёте — поговорим.",
        "Hello. Buying something? Or… here about the murder? You know, I would help, but the city is unhappy with the police. First find my cat Ryzhik — he is in the park. Bring him back — then we'll talk.",
    ), choices=[Choice(L("Найти кота", "Find the cat"), effect=lambda s, g: _task(s, "cat")),
                Choice(L("До свидания", "Goodbye"))])


def _task_done(state, task_id: str) -> None:
    state.tasks[task_id] = "done"


# ---------------------------------------------------------------- volkov ----
def talk_volkov(state, scene) -> Turn:
    # fingerprints identification (drives the player to Nick)
    if state.has_clue("fingerprints") and not state.flags.get("nick_prints_known"):
        state.flags["nick_prints_known"] = True
        state.add_note(
            "Отпечатки", "По базе полиции отпечатки на ручке принадлежат Нику Армстронгу — мелкому воришке. Стоит с ним поговорить.",
            "Fingerprints", "According to the police database, the prints on the handle belong to Nick Armstrong — a small-time thief. Worth a talk.",
            clue_id="fingerprints",
        )
        return Turn("volkov", L(
            "Отпечатки проверили: Ник Армстронг. Мелкий воришка, вечно трётся у остановки. Ты с ним поговори — но он себе на уме. Если понадобится — могу прижать его по старому делу, когда город будет на нашей стороне.",
            "We ran the prints: Nick Armstrong. A small-time thief, always hanging around the bus stop. Talk to him — but he's a slippery one. If needed, I can squeeze him over an old case, once the city is on our side.",
        ))
    if state.tasks.get("nick_clear") == "active" and state.support < 50:
        return Turn("volkov", L(
            "Армстронг — рецидивист. Я не могу просто так снять с него обвинения: горожане и так недовольны. Заручись поддержкой города — тогда посмотрим.",
            "Armstrong is a repeat offender. I can't just drop the charges: the townsfolk are already unhappy. Earn the city's support — then we'll see.",
        ))
    if state.tasks.get("nick_clear") == "active" and state.support >= 50:
        state.tasks["nick_clear"] = "done"
        state.support = min(100.0, state.support + 3)
        play("confirm")
        return Turn("volkov", L(
            "Ладно. Скажу, что Армстронг помог следствию — обвинения за кражу снимут. Но смотри: если он снова что-то украдёт — отвечать будешь ты.",
            "Fine. I'll say Armstrong helped the investigation — the theft charges will be dropped. But mind you: if he steals again — you'll answer for it.",
        ))
    if state.plot_stage >= 5:
        return Turn("volkov", L(
            "Нож найден — это главное. Теперь EMIT официально в розыске. Майк… если увидишь его — не геройствуй. Зови нас.",
            "The knife found — that's the key piece. Now EMIT is officially wanted. Mike… if you see him — don't play the hero. Call us.",
        ))
    if state.plot_stage >= 4:
        return Turn("volkov", L(
            "EMIT, значит… Егор Митин. По бумагам — мелкий, а смотри ты. Телефонная вышка — косвенная улика. Нужно орудие убийства, Майк. И помни: его видели у выезда из города. Если увидишь — сразу зови нас.",
            "EMIT, huh… Yegor Mitin. On paper he's small-time, but look at that. A cell tower is circumstantial. We need the murder weapon, Mike. And remember: he was seen near the town exit. If you see him — call us at once.",
        ))
    if state.plot_stage >= 3:
        return Turn("volkov", L(
            "Надпись кровью… TIME. И записка. Это почерк безумца, но безумца умного. Он играет с нами, Майк. Не дай ему выиграть.",
            "A bloody inscription… TIME. And the note. The handiwork of a madman — but a clever one. He's playing with us, Mike. Don't let him win.",
        ))
    if state.plot_stage >= 2:
        return Turn("volkov", L(
            "Билет за 00:10, встреча на календаре… Виктор ждал кого-то в ночь убийства. Похоже, он знал убийцу и сам открыл ему дверь. Проверь то число — 23 ноября.",
            "A ticket at 00:10, a meeting on the calendar… Viktor was expecting someone on the night of the murder. It seems he knew the killer and opened the door himself. Check that date — November 23.",
        ))
    if state.has_clue("victim_note"):
        return Turn("volkov", L(
            "Записка Виктора… «любит играть со временем». Странно. Очень странно. Кто играет со временем, Майк? Подумай над этим.",
            "Viktor's note… “likes to play with time”. Strange. Very strange. Who plays with time, Mike? Think about it.",
        ))
    return Turn("volkov", L(
        "Пока пусто, Майк. Единственная зацепка — пропавший нож с кухни. Дверь не взломана: Виктор сам открыл убийце. Значит, он его знал. Осмотри дом — что-то мы могли упустить.",
        "Nothing yet, Mike. The only lead is the missing kitchen knife. The door wasn't forced: Viktor let the killer in himself. So he knew him. Search the house — we might have missed something.",
    ))


# ---------------------------------------------------------------- krylov ----
def talk_krylov2(state, scene) -> Turn:
    if state.flags.get("krylov2_talked"):
        return Turn("krylov2", L(
            "Я работаю. Если что-то найдёте — скажете капитану.",
            "I'm working. If you find anything — tell the captain.",
        ))
    state.flags["krylov2_talked"] = True
    return Turn("krylov2", L(
        "Детектив Майк? Наслышан. Мы тут всё облазили: ни отпечатков, ни следов. Только пустая подставка для ножей на кухне. Скажу честно: впервые вижу такое чистое место преступления. Убийца знал, что делает.",
        "Detective Mike? I've heard of you. We went over everything: no prints, no traces. Only the empty knife block in the kitchen. Honestly: I've never seen such a clean crime scene. The killer knew what he was doing.",
    ), choices=[Choice(L("Спасибо", "Thanks"))])


def talk_krylov(state, scene) -> Turn:
    if state.flags.get("krylov_talked"):
        return Turn("krylov", L(
            "Я на посту. Если что-то найдёте — кричите.",
            "I'm on watch. If you find anything — shout.",
        ))
    state.flags["krylov_talked"] = True
    return Turn("krylov", L(
        "Привет, детектив. Мы тут с утра. Странное дело: в доме всё на своих местах. Единственное — на кухне пустое место в подставке для ножей. Нож пропал. И ни отпечатков, ни следов взлома. Чисто, как в аптеке. Капитан сказал: ты умеешь… по-другому искать. Удачи.",
        "Hey, detective. We've been here since morning. Strange case: everything in the house is in its place. The only thing — an empty slot in the kitchen knife block. The knife is gone. No prints, no signs of a break-in. Clean as a whistle. The captain said you know how to… search differently. Good luck.",
    ), choices=[Choice(L("Спасибо", "Thanks"))])


# -------------------------------------------------------------- wanderers ---
def talk_wanderer(state, scene, wid: str) -> Turn:
    # Observing the past: people don't know about the murder yet.
    if scene is not None and hasattr(scene, "world_now"):
        try:
            from datetime import datetime
            if scene.world_now() < datetime(2023, 11, 23, 6, 0):
                past_lines = {
                    "w1": L("Холодно сегодня. Зима в этом году ранняя.",
                            "Cold today. Winter came early this year."),
                    "w2": L("Автобусы ходят по расписанию, и то хорошо.",
                            "The buses run on schedule — that's something."),
                    "w3": L("Говорят, у Соколова по ночам гости бывают. Странный он в последнее время.",
                            "They say Sokolov has guests at night. He's been acting strange lately."),
                }
                return Turn(wid, past_lines.get(wid, past_lines["w1"]))
        except Exception:
            pass
    lines = {
        "w1": L("Жуткое дело. Я теперь двери запираю и в окна не смотрю.",
                "Terrible business. I lock my doors now and don't look out the windows."),
        "w2": L("Говорят, Соколов в ту ночь ждал гостя. Свет в окнах до полуночи горел.",
                "They say Sokolov was expecting a guest that night. The lights were on past midnight."),
        "w3": L("Странный тип по ночам у дома Соколова бродил. За неделю до убийства. Я думал — Виктор сам. А теперь…",
                "A strange fellow wandered around Sokolov's house at night. A week before the murder. I thought it was Viktor himself. But now…"),
    }
    base = lines.get(wid, lines["w1"])
    if state.support >= 50:
        extra = L("Раз вы за дело взялись, детектив — город спит спокойнее.",
                  "Now that you're on the case, detective — the city sleeps easier.")
        return Turn(wid, {"ru": base["ru"] + " " + extra["ru"],
                          "en": base["en"] + " " + extra["en"]})
    return Turn(wid, base)


# ------------------------------------------------------------------ emit ----
def emit_chase_line(state, scene) -> Turn:
    return Turn("emit", L(
        "…Ты. Значит, дошёл. Ну, догоняй, детектив. Время не ждёт.",
        "…You. So you made it. Well, catch me, detective. Time waits for no one.",
    ))
