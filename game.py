import random
import asyncio
import discord
from player import Player
from dataclasses import dataclass
from typing import Optional
from awaitable_view import AwaitableView
from itertools import chain
from cards import (
    special_attack_cards,
    counter,
    Stance,
    attack_cards,
    move_cards,
    move_actions,
    tactics,
    footwork,
    special_attack_cards,
    change_stance,
)


@dataclass
class GameState:
    channel: discord.TextChannel
    p1: Player
    p2: Player
    winner_future = asyncio.Future()
    turn_summary: list[str]
    board_size: int = 5
    in_progress: bool = True

    def __init__(
        self,
        player1: discord.Member,
        player2: discord.Member,
        channel: discord.TextChannel,
        p1_challenge_interaction: discord.Interaction,
        p2_challenge_interaction: discord.Interaction,
        p1_emoji: Optional[str] = None,
        p2_emoji: Optional[str] = None,
    ):
        self.channel = channel
        self.turn_summary = []
        p1_special = random.choice(special_attack_cards)
        p2_special = random.choice([s for s in special_attack_cards if s != p1_special])

        emojiList = ["🐻", "🐯", "🐲", "🦅", "🐍", "🦉", "🐗", "🐸", "🐺"]
        p1_emoji = (
            p1_emoji
            if p1_emoji is not None
            else random.choice(["🐻", "🐯", "🐲", "🦅", "🐍", "🦉", "🐗", "🐸", "🐺"])
        )
        p2_emoji = (
            p2_emoji
            if p2_emoji is not None and p2_emoji != p1_emoji
            else random.choice([e for e in emojiList if e != p1_emoji])
        )

        self.p1 = Player(
            cell=0,
            special=p1_special,
            name=player1.display_name,
            mention=player1.mention,
            emoji=p1_emoji,
            initial_challenge=p1_challenge_interaction,
        )

        self.p2 = Player(
            cell=self.board_size - 1,
            special=p2_special,
            name=player2.display_name,
            mention=player2.mention,
            emoji=p2_emoji,
            initial_challenge=p2_challenge_interaction,
        )

    async def run_until_end(self):
        print(f"Started duel between {self.p1.name} and {self.p2.name}")
        finished = False
        is_turn_one = True
        while not finished:
            finished = await self.start_turn(is_turn_one)
            is_turn_one = False

    def symbol_for_cell(self, index):
        if index == self.p1.cell and index == self.p2.cell:
            return f"[{self.p1.emoji}{self.p2.emoji}]"
        elif index == self.p1.cell:
            return self.p1.emoji
        elif index == self.p2.cell:
            return self.p2.emoji
        else:
            return "\_"

    async def start_turn(self, is_turn_one=False):

        # post game state and board, then clear summary
        msg = ""
        if is_turn_one:
            msg += f"**{self.p1.mention} and {self.p2.mention}, your duel begins!**\n\n"
        if len(self.turn_summary):
            msg += "\n" + "\n".join(self.turn_summary) + "\n\n"
        self.turn_summary.clear()
        board = " ".join([self.symbol_for_cell(i) for i in range(self.board_size)])
        msg += f"{board}\n\n"
        msg += self.p1.make_state_string() + "\n"
        msg += self.p2.make_state_string()
        await self.channel.send(msg)

        self.p1.clear_plays()
        self.p2.clear_plays()

        tasks = (
            self.collect_move_choices(self.p1, False),
            self.collect_move_choices(self.p2, False),
        )
        results = await asyncio.gather(*tasks, return_exceptions=True)

        if isinstance(results[0], TimeoutError) and isinstance(
            results[1], TimeoutError
        ):
            await self.end_game(None, None, forfeit=True)
            return True
        elif isinstance(results[0], Exception) and not isinstance(
            results[0], TimeoutError
        ):
            raise results[0]
        elif isinstance(results[1], Exception) and not isinstance(
            results[1], TimeoutError
        ):
            raise results[1]
        elif isinstance(results[0], TimeoutError):
            await self.end_game(self.p2, self.p1, forfeit=True)
            return True

        elif isinstance(results[1], TimeoutError):
            await self.end_game(self.p1, self.p2, forfeit=True)
            return True

        print(f"p1 is playing  {[c.name for c in self.p1.chosen_plays]}")
        print(f"p2 is playing  {[c.name for c in self.p2.chosen_plays]}")

        self.resolve_plays(True)

        (winner, loser) = self.check_for_game_end()
        if winner:
            await self.end_game(winner, loser)
            return True

        self.resolve_plays(False)

        (winner, loser) = self.check_for_game_end()
        if winner:
            await self.end_game(winner, loser)
            return True

    async def end_game(self, winner, loser, forfeit=False):
        # winner is only none if double timeout
        # send summary and win message

        if forfeit and winner is None:
            await self.channel.send("u both timed out gg go home")
        elif forfeit:
            await self.channel.send(
                f"gg {winner.mention} wins bc their opp fell aslp clapclap"
            )
        else:
            msg = "\n".join(self.turn_summary)
            msg += "\n\n"
            msg += (
                " ".join([self.symbol_for_cell(i) for i in range(self.board_size)])
                + "\n\n"
            )
            msg += self.p1.make_state_string() + "\n"
            msg += self.p2.make_state_string() + "\n"
            msg += f"gg {winner.mention} wins gj clapclap"
            await self.channel.send(msg)
        self.in_progress = False
        self.winner_future.set_result((winner, loser))

    def resolve_plays(self, is_first_half_of_turn):
        chosen_play_index = 0 if is_first_half_of_turn else 1
        p1play = self.p1.chosen_plays[chosen_play_index]
        p2play = self.p2.chosen_plays[chosen_play_index]

        print(f"Resolving {p1play.name} and {p2play.name}")

        self.resolve_movement(p1play, p2play)

        # resolve attacks
        p1attacked = p1play in attack_cards
        p2attacked = p2play in attack_cards
        p1counter = p1play is counter
        p2counter = p2play is counter
        p1success = p1attacked and self.does_attack_succeed(True, p1play)
        p2success = p2attacked and self.does_attack_succeed(False, p2play)

        print(
            f"p1attacked: {p1attacked}, p2attacked: {p2attacked}, p1play: {p1play.name}, p2play: {p2play.name}, p1counter: {p1counter}, p2counter: {p2counter}, p1success: {p1success}, p2success: {p2success}"
        )

        # clash
        if p1success and p2success:
            self.turn_summary.append(self.tp(p1play.clash_msg, True))
            self.turn_summary.append(self.tp(p2play.clash_msg, False))
            self.turn_summary.append("Sparks fly as the blades clash! No damage!")
        # counter by 2
        elif p1success and p2counter:
            self.turn_summary.append(self.tp(p1play.counter_msg, True))
            self.turn_summary.append(
                f"-- but {self.p2.name} reverses the blow with a perfect counter!"
            )
            self.p1.take_hit()
        # counter by 1
        elif p2success and p1counter:
            self.turn_summary.append(self.tp(p2play.counter_msg, False))
            self.turn_summary.append(
                f"-- but {self.p1.name} reverses the blow with a perfect counter!"
            )
            self.p2.take_hit()
        elif p2counter and not p1attacked:
            self.turn_summary.append(
                f"{self.p2.name} braces to counter an attack that never comes!"
            )
        elif p1counter and not p2attacked:
            self.turn_summary.append(
                f"{self.p1.name} braces to counter an attack that never comes!"
            )
        elif p2counter and p1attacked and not p1success:
            self.turn_summary.append(self.tp(p1play.counter_msg, True))
            self.turn_summary.append(
                f"-- {self.p2.name} is braced to counter, but the attack goes wide!"
            )
        elif p1counter and p2attacked and not p2success:
            self.turn_summary.append(self.tp(p2play.counter_msg, False))
            self.turn_summary.append(
                f"-- {self.p1.name} is braced to counter, but the attack goes wide!"
            )
        # p1 hit
        elif p1success:
            if p2attacked:
                self.turn_summary.append(self.tp(p2play.miss_msg, False))
            self.turn_summary.append(self.tp(p1play.success_msg, True))
            self.p2.take_hit()
        # p2 hit
        elif p2success:
            if p1attacked:
                self.turn_summary.append(self.tp(p1play.miss_msg, True))
            self.turn_summary.append(self.tp(p2play.success_msg, False))
            self.p1.take_hit()
        # if nobody hit, still need to print misses
        elif not p1success and not p2success:
            if p1attacked:
                self.turn_summary.append(self.tp(p1play.miss_msg, True))
            if p2attacked:
                self.turn_summary.append(self.tp(p2play.miss_msg, False))

        # special used handling isn't necessary because it's done at point of move choice

        if p1attacked and p1play.changes_stance:
            self.p1.stance = (
                Stance.HEAVEN if self.p1.stance is Stance.EARTH else Stance.EARTH
            )
            print(f"p1 stance is now {self.p1.stance} due to a stance change attack")
            self.turn_summary.append(
                f"{self.p1.name}'s technique leaves them in {self.p1.stance.value} stance."
            )
        if p2attacked and p2play.changes_stance:
            self.p2.stance = (
                Stance.HEAVEN if self.p2.stance is Stance.EARTH else Stance.EARTH
            )
            print(f"p2 stance is now {self.p2.stance} due to a stance change attack")
            self.turn_summary.append(
                f"{self.p2.name}'s technique leaves them in {self.p2.stance.value} stance."
            )

        if not is_first_half_of_turn:
            p1card = self.get_card_played(self.p1, False)
            p2card = self.get_card_played(self.p2, False)
            self.p1.lock(p1card if p1card not in special_attack_cards else None)
            self.p2.lock(p2card if p2card not in special_attack_cards else None)

    def tp(self, template_string, is_p1):
        a = self.p1 if is_p1 else self.p2
        b = self.p2 if is_p1 else self.p1
        other_stance = Stance.EARTH if a.stance is Stance.HEAVEN else Stance.HEAVEN
        return (
            template_string.replace("{a}", a.name)
            .replace("{b}", b.name)
            .replace("{other_stance}", other_stance.value)
        )

    def does_attack_succeed(self, is_p1, card):
        print(
            f"Checking if {'p1' if is_p1 else 'p2'} hits successfully with {card.name}"
        )
        if is_p1:
            hit_cells = [c + self.p1.cell for c in card.hits_cells]
            print(
                f"p1 in {self.p1.cell} used {card.name} hitting {hit_cells} which {'does' if self.p2.cell in hit_cells else 'does not'} hit {self.p2.name} in {self.p2.cell}"
            )
            return self.p2.cell in hit_cells
        else:
            hit_cells = [self.p2.cell - c for c in card.hits_cells]
            print(
                f"p2 in {self.p2.cell} used {card.name} hitting {hit_cells} which {'does' if self.p1.cell in hit_cells else 'does not'} hit {self.p1.name} in {self.p1.cell}"
            )
            return self.p1.cell in hit_cells

    def clamp(self, index, min_val, max_val):
        # print(f"Clamping index {index} between {min_val} and {max_val}")
        return min((max(min_val, index)), max_val)

    def moves_would_pass(self, p1vector, p2vector):
        return self.p1.cell + p1vector > self.p2.cell - p2vector

    def check_for_game_end(self):
        # winner, loser
        if self.p1.is_dead():
            return (self.p2, self.p1)
        elif self.p2.is_dead():
            return (self.p1, self.p2)
        else:
            return (None, None)

    def find_midpoint(self):
        mid = (self.p1.cell + self.p2.cell) / 2
        if abs(mid - 2) <= 0.5:
            return round(mid)
        else:
            return int(mid + 0.5) if mid > 2 else int(mid)

    def append_movement_to_summary(self, player, play):
        if play:
            is_p1 = player is self.p1
            self.turn_summary.append(self.tp(play.msg, is_p1))

    def resolve_movement(self, p1play, p2play):
        p1move = p1play if p1play in move_actions else None
        p2move = p2play if p2play in move_actions else None
        p1magnitude = p1move.magnitude if p1move else 0
        p2magnitude = p2move.magnitude if p2move else 0
        p1change_stance = p1play is change_stance
        p2change_stance = p2play is change_stance
        players_started_in_same_cell = self.p1.cell == self.p2.cell

        print(
            f"Resolving movement: p1: {p1move.name if p1move else None}, p2: {p2move.name if p2move else None}, p1magnitude: {p1magnitude}, p2magnitude: {p2magnitude}"
        )

        # if same stance and would overlap, set to midpoint
        if (
            self.p1.stance == self.p2.stance
            and p1magnitude > 0
            and p2magnitude > 0
            and self.moves_would_pass(p1magnitude, p2magnitude)
        ):
            midpoint = self.find_midpoint()
            self.p1.cell = midpoint
            self.p2.cell = midpoint
            self.append_movement_to_summary(self.p1, p1move)
            self.append_movement_to_summary(self.p2, p2move)
        elif self.p1.stance == self.p2.stance or self.p1.stance == Stance.HEAVEN:
            # if same stance but no overlap, OR p1 is heaven, resolve p1 first
            self.p1.cell = self.clamp(self.p1.cell + p1magnitude, 0, self.p2.cell)
            if p1change_stance:
                self.p1.stance = (
                    Stance.HEAVEN if self.p1.stance is Stance.EARTH else Stance.EARTH
                )
                print(
                    f"p1 stance is now {self.p1.stance} due to a change stance action"
                )
            self.append_movement_to_summary(self.p1, p1move)
            self.p2.cell = self.clamp(
                self.p2.cell - p2magnitude, self.p1.cell, self.board_size - 1
            )
            if p2change_stance:
                self.p2.stance = (
                    Stance.HEAVEN if self.p1.stance is Stance.EARTH else Stance.EARTH
                )
                print(
                    f"p2 stance is now {self.p2.stance} due to a change stance action"
                )
            self.append_movement_to_summary(self.p2, p2move)
        elif self.p1.stance == Stance.EARTH:
            self.p2.cell = self.clamp(
                self.p2.cell - p2magnitude, self.p1.cell, self.board_size - 1
            )
            if p2change_stance:
                self.p2.stance = (
                    Stance.HEAVEN if self.p1.stance is Stance.EARTH else Stance.EARTH
                )
            self.append_movement_to_summary(self.p2, p2move)
            self.p1.cell = self.clamp(self.p1.cell + p1magnitude, 0, self.p2.cell)
            if p1change_stance:
                self.p1.stance = (
                    Stance.HEAVEN if self.p1.stance is Stance.EARTH else Stance.EARTH
                )
            self.append_movement_to_summary(self.p1, p1move)

        if self.p1.cell == self.p2.cell and not players_started_in_same_cell:
            self.turn_summary.append(f"The two warriors come toe to toe!")

    def get_card_played(self, player, is_first):
        index = 0 if is_first else 1
        if len(player.chosen_plays) < index + 1:
            return None
        play = player.chosen_plays[index]
        if play in attack_cards or play is counter:
            return play
        else:
            # is move
            if play in footwork.actions:
                return footwork
            elif play in tactics.actions:
                return tactics
            else:
                print(f"Unknown card played first for player {player.name}")
                return None

    def make_play_selection_view(self, player, will_switch_stance):

        first_card_played = self.get_card_played(player, True)

        playerStance = player.stance
        if will_switch_stance:
            playerStance = (
                Stance.HEAVEN if playerStance == Stance.EARTH else Stance.EARTH
            )

        # Get all standard attack cards - locked card + unused special card - first play
        available_attack_cards = [
            c
            for c in attack_cards
            if player.locked is not c
            and not c.is_special
            and c is not first_card_played
        ]
        if not player.special_used:
            available_attack_cards.append(player.special)
        # filter out off-stance cards
        available_attack_cards = [
            c
            for c in available_attack_cards
            if c.requires_stance == playerStance or c.requires_stance == None
        ]
        available_attack_cards.sort()

        # gotta retroactively determine the move card played to prevent it showing again
        # first_move_card_played = (
        #     next(c for c in move_cards if player.chosen_plays[0] in c.actions)
        #     if len(player.chosen_plays) > 0 and player.chosen_plays[0] in move_actions
        #     else None
        # )

        available_move_cards = [
            c
            for c in move_cards
            if player.locked is not c and c is not first_card_played
        ]
        available_move_actions = list(
            chain(*[move.actions for move in available_move_cards])
        )
        available_move_actions.sort()

        available_plays = available_attack_cards + available_move_actions

        buttons_with_values = []
        for play in available_plays:
            button = discord.ui.Button(
                style=discord.ButtonStyle.primary, label=play.button_text
            )
            buttons_with_values.append((button, play))
        view = AwaitableView(buttons_with_values, 800)
        return view

    async def collect_move_choices(self, player, is_first_response):
        root_interaction = player.initial_challenge
        if not player.special_used:
            special_info = f"Special available: {player.special.name}\n"
        else:
            special_info = f"Special already used ({player.special.name})\n"
        first_header = f"{special_info}Choose first move:"
        first_view = self.make_play_selection_view(player, False)

        first_message = None
        if is_first_response:
            first_message = await root_interaction.response.send_message(
                first_header, view=first_view, ephemeral=True
            )
        else:
            first_message = await root_interaction.followup.send(
                first_header, view=first_view, ephemeral=True
            )
        first_play = await first_view.wait_for_value()
        player.add_queued_play(first_play)

        if first_play == None:
            await first_message.delete()
            raise TimeoutError
        will_change_stance = first_play.changes_stance
        if first_play in special_attack_cards:
            player.special_used = True

        second_header = (
            f"{special_info}First Move: {first_play.name}\nChoose second move:"
        )

        second_view = self.make_play_selection_view(player, will_change_stance)
        await first_message.edit(content=second_header, view=second_view)
        second_play = await second_view.wait_for_value()
        if second_play == None:
            await first_message.delete()
            raise TimeoutError
        if second_play in special_attack_cards:
            player.special_used = True
        await first_message.delete()
        player.add_queued_play(second_play)
