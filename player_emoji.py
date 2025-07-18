from database_handler import db
import random

emoji = ["🐻", "🐯", "🐲", "🦅", "🐍", "🦉", "🐗", "🐸", "🐺", "🦏", "🐊", "🦎", "🐢"]


def get_emoji_for_game(p1id, p2id):
    p1_emoji = db.get_player_emoji(p1id)
    p2_emoji = db.get_player_emoji(p2id)

    if p1_emoji is None:
        p1_emoji = emoji[emoji_index_from_id(p1id)]
    if p2_emoji is None:
        p2_emoji = emoji[emoji_index_from_id(p2id)]

    if p1_emoji == p2_emoji:
        p2_emoji = random_choice_except(p1_emoji)

    return p1_emoji, p2_emoji


def emoji_index_from_id(player_id):
    hash_value = hash(player_id)
    hash_value = abs(hash_value)
    return hash_value % (len(emoji))


def random_choice_except(except_emoji):
    return random.choice([e for e in emoji if e != except_emoji])


import re
import unicodedata


def is_single_emoji(string):
    if not string:
        return False
    string = re.sub(r"[\uFE00-\uFE0F]", "", string)

    if len(string) == 1:
        return unicodedata.category(string) in ["So", "Sk"]
    if len(string) == 2 and all(
        unicodedata.name(c).startswith("REGIONAL INDICATOR SYMBOL LETTER")
        for c in string
    ):
        return True
    if len(string) > 1:
        base = string[0]
        if unicodedata.category(base) in ["So", "Sk"]:
            for modifier in string[1:]:
                if unicodedata.name(modifier).startswith(
                    ("EMOJI MODIFIER", "ZERO WIDTH JOINER")
                ):
                    continue
                else:
                    return False
            return True

    return False
