from dataclasses import dataclass
from enum import Enum


class Stance(Enum):
    HEAVEN = "Heaven"
    EARTH = "Earth"


@dataclass
class Card:
    name: str

    def __lt__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.name < other.name


@dataclass
class AttackCard(Card):
    button_text: str
    is_special: bool
    success_msg: str
    miss_msg: str
    counter_msg: str
    clash_msg: str
    hits_cells: list[int]
    requires_stance: Stance
    changes_stance: bool
    button_colour: str


@dataclass
class MoveAction:
    name: str
    button_colour: str
    button_text: str
    magnitude: int
    msg: str
    changes_stance: bool

    def __lt__(self, other):
        if not isinstance(other, MoveAction):
            return NotImplemented
        return self.name < other.name


@dataclass
class MoveCard(Card):
    actions: tuple[MoveAction, MoveAction]


############################ special
zantetsu = AttackCard(
    name="Zan-Tetsu Strike",
    button_text="Zan-Tetsu Strike (2 & 3)",
    is_special=True,
    success_msg="{a} rises and unleashes a devastating Zan-Tetsu strike, and {b} takes the full force of the blow!",
    miss_msg="{a} rises and attempts a Zan-Tetsu strike, but {b} deftly evades!",
    counter_msg="{a} rises and attempts a Zan-Tetsu strike...",
    clash_msg="{a} rises and attempts a Zan-Tetsu strike...",
    hits_cells=[2, 3],
    requires_stance=Stance.EARTH,
    changes_stance=True,
    button_colour="yellow",
)

kesa = AttackCard(
    name="Kesa Strike",
    button_text="Kesa Strike (same cell & 1)",
    is_special=True,
    success_msg="{a} drops low and launches a piercing Kesa strike! {b} can't turn it aside!",
    miss_msg="{a} drops low and attempts a Kesa strike, but {b} manages to evade!",
    counter_msg="{a} drops low and attempts a Kesa strike...",
    clash_msg="{a} drops low and attempts a Kesa strike...",
    hits_cells=[0, 1],
    requires_stance=Stance.HEAVEN,
    changes_stance=True,
    button_colour="green",
)

counter = AttackCard(
    name="Counterattack",
    button_text="Counterattack",
    is_special=True,
    success_msg=None,
    miss_msg=None,
    counter_msg=None,
    clash_msg=None,
    hits_cells=[],
    requires_stance=None,
    changes_stance=False,
    button_colour="orange",
)

############################ Regular attacks

low_strike = AttackCard(
    name="Low Strike",
    button_text="Low Strike (1)",
    is_special=False,
    success_msg="{a} throws out a swift low strike, and the attack finds its mark!",
    miss_msg="{a} attempts a low strike, but {b} bats it aside!",
    counter_msg="{a} delivers a swift low strike...",
    clash_msg="{a} delivers a swift low strike...",
    hits_cells=[1],
    requires_stance=Stance.EARTH,
    changes_stance=False,
    button_colour="green",
)

high_strike = AttackCard(
    name="High Strike",
    button_text="High Strike (2)",
    is_special=False,
    success_msg="{a} brings down a fierce high strike directly onto {b}!",
    miss_msg="{a} attempts a high strike, but {b} avoids the blow!",
    counter_msg="{a} attempts a fierce high strike...",
    clash_msg="{a} attempts a fierce high strike...",
    hits_cells=[2],
    requires_stance=Stance.HEAVEN,
    changes_stance=False,
    button_colour="yellow",
)

balanced_strike = AttackCard(
    name="Balanced Strike",
    button_text="Balanced Strike (same cell)",
    is_special=False,
    success_msg="{a} delivers a balanced strike!",
    miss_msg="{a} attempts a balanced strike, but {b} dodges!",
    counter_msg="{a} delivers a balanced strike...",
    clash_msg="{a} delivers a balanced strike...",
    hits_cells=[0],
    requires_stance=None,
    changes_stance=False,
    button_colour="grey",
)

############################# movement actions

approach = MoveAction(
    name="Approach",
    magnitude=1,
    msg="{a} steps forward.",
    button_colour="blue",
    changes_stance=False,
    button_text="Footwork: Approach (1)",
)
retreat = MoveAction(
    name="Retreat",
    magnitude=-1,
    msg="{a} steps back.",
    button_colour="blue",
    changes_stance=False,
    button_text="Footwork: Retreat (1)",
)
charge = MoveAction(
    name="Charge",
    magnitude=2,
    msg="{a} charges forward!",
    button_colour="blue",
    changes_stance=False,
    button_text="Tactics: Charge! (2)",
)
change_stance = MoveAction(
    name="Change Stance",
    magnitude=0,
    msg="{a} shifts into {other_stance} stance.",
    button_colour="blue",
    changes_stance=True,
    button_text="Tactics: Change Stance",
)

########################## movement cards

footwork = MoveCard(name="Footwork", actions=(approach, retreat))

tactics = MoveCard(name="Tactics", actions=(charge, change_stance))

attack_cards = (zantetsu, kesa, low_strike, high_strike, balanced_strike)
move_cards = (footwork, tactics)
special_attack_cards = (zantetsu, kesa, counter)
move_actions = (approach, retreat, charge, change_stance)
# stance_change_cards_or_actions = [zantetsu, kesa, change_stance]


def attack_card_or_move_action_from_string(card_name: str):
    for card in attack_cards + move_actions:
        if card.name == card_name:
            return card
    return None
