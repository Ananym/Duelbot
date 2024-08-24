from dataclasses import dataclass, field
from cards import Stance, Card, AttackCard, MoveAction
from typing import Optional
import discord
import random


@dataclass
class Player:
    cell: int
    special: AttackCard
    name: str
    mention: str
    emoji: str
    initial_challenge: discord.Interaction
    chosen_plays: list[AttackCard | MoveAction]
    hp: int = 2
    special_used: bool = False
    locked: Optional[Card] = None
    stance: Stance = Stance.HEAVEN

    def __init__(
        self,
        cell: int,
        special: AttackCard,
        name: str,
        mention: str,
        emoji: str,
        initial_challenge: discord.Interaction,
    ):
        self.cell = cell
        self.special = special
        self.name = name
        self.mention = mention
        self.emoji = emoji
        self.initial_challenge = initial_challenge
        self.hp = 2
        self.stance = Stance.HEAVEN
        self.chosen_plays = []
        self.special_used = False
        self.locked = None

    def make_state_string(self):
        stanceEmoji = "⚡" if self.stance == Stance.HEAVEN else "🏔"
        hp = " ".join(["♥" for _ in range(self.hp)])
        msg = f"{self.emoji} {self.name} | {hp} | {stanceEmoji} {self.stance.value} | {'Special ✖' if self.special_used else 'Special ✔'}"
        if self.locked:
            msg += f" | 🔒 {self.locked.name}"
        return msg

    def lock(self, card: Card):
        self.locked = card

    def take_hit(self):
        self.hp -= 1

    def is_dead(self):
        return self.hp <= 0

    def change_stance(self):
        self.stance = Stance.EARTH if self.stance == Stance.HEAVEN else Stance.HEAVEN

    def clear_plays(self):
        self.chosen_plays = []

    def add_queued_play(self, play):
        self.chosen_plays.append(play)
