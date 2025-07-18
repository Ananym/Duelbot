import unittest
from game_logic import GameState, Stance, Card
from unittest.mock import MagicMock, patch
import asyncio


class MockMember:

    def __init__(self, name, id):
        self.name = name
        self.id = id


class TestGameLogic(unittest.IsolatedAsyncioTestCase):

    @patch("game_logic.Card")
    async def test_movement_off_board(self, mock_card):
        # Test movement off board for Player 1
        self.game.board = [self.player1, None, None, None, self.player2]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Earth,
        }

        moves = {
            self.player1.id: ("Retreat", "Retreat"),
            self.player2.id: ("Advance", "Advance"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(self.game.board,
                         [self.player1, None, None, self.player2, None])

        # Test movement off board for Player 2
        self.game.board = [self.player1, None, None, None, self.player2]
        moves = {
            self.player1.id: ("Advance", "Advance"),
            self.player2.id: ("Advance", "Advance"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(self.game.board,
                         [None, self.player1, None, None, self.player2])

    @patch("game_logic.Card")
    async def test_simultaneous_attacks(self, mock_card):
        self.game.board = [None, self.player1, self.player2, None, None]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Heaven,
        }

        moves = {
            self.player1.id: ("Balanced Strike", "Balanced Strike"),
            self.player2.id: ("Balanced Strike", "Balanced Strike"),
        }

        await self.game.resolve_moves(moves, False)

        # Both players should still have 2 hitpoints
        self.assertEqual(self.game.hitpoints[self.player1.id], 2)
        self.assertEqual(self.game.hitpoints[self.player2.id], 2)

    @patch("game_logic.Card")
    async def test_stance_based_card_availability(self, mock_card):
        self.game.board = [None, self.player1, self.player2, None, None]

        # Set initial stances
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Earth,
        }

        # Check available cards for each player
        heaven_cards = self.game.get_available_cards(self.player1.id)
        earth_cards = self.game.get_available_cards(self.player2.id)

        # Verify that stance-specific cards are available
        self.assertIn("High Strike", [card.name for card in heaven_cards])
        self.assertNotIn("Low Strike", [card.name for card in heaven_cards])
        self.assertIn("Low Strike", [card.name for card in earth_cards])
        self.assertNotIn("High Strike", [card.name for card in earth_cards])

        # Switch stances
        self.game.stances[self.player1.id] = Stance.Earth
        self.game.stances[self.player2.id] = Stance.Heaven

        # Check available cards again
        new_earth_cards = self.game.get_available_cards(self.player1.id)
        new_heaven_cards = self.game.get_available_cards(self.player2.id)

        # Verify that available cards have changed with stance
        self.assertIn("Low Strike", [card.name for card in new_earth_cards])
        self.assertNotIn("High Strike",
                         [card.name for card in new_earth_cards])
        self.assertIn("High Strike", [card.name for card in new_heaven_cards])
        self.assertNotIn("Low Strike",
                         [card.name for card in new_heaven_cards])

    async def asyncSetUp(self):
        self.player1 = MockMember("Player1", 1)
        self.player2 = MockMember("Player2", 2)
        self.channel = MagicMock()
        self.interaction1 = MagicMock()
        self.interaction2 = MagicMock()

        self.game = GameState(
            self.player1,
            self.player2,
            self.channel,
            self.interaction1,
            self.interaction2,
        )

        # Mock the send_game_state method to prevent actual Discord API calls
        self.game.send_game_state = MagicMock()

    async def test_initial_game_state(self):
        self.assertEqual(self.game.board,
                         [self.player1, None, None, None, self.player2])
        self.assertEqual(self.game.stances[self.player1.id], Stance.Heaven)
        self.assertEqual(self.game.stances[self.player2.id], Stance.Heaven)
        self.assertEqual(self.game.hitpoints[self.player1.id], 2)
        self.assertEqual(self.game.hitpoints[self.player2.id], 2)
        self.assertEqual(len(self.game.hands[self.player1.id]),
                         5)  # 4 standard + 1 special
        self.assertEqual(len(self.game.hands[self.player2.id]),
                         5)  # 4 standard + 1 special

    @patch("game_logic.Card")
    async def test_movement_priority(self, mock_card):
        self.game.board = [None, self.player1, self.player2, None, None]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Earth,
        }

        moves = {
            self.player1.id: ("Footwork", "Approach"),
            self.player2.id: ("Footwork", "Approach"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(
            self.game.board,
            [None, None, [self.player1, self.player2], None, None])

    @patch("game_logic.Card")
    async def test_players_moving_into_same_cell(self, mock_card):
        self.game.board = [None, self.player1, None, self.player2, None]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Heaven,
        }

        moves = {
            self.player1.id: ("Tactics", "Charge"),
            self.player2.id: ("Footwork", "Approach"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(
            self.game.board,
            [None, None, [self.player1, self.player2], None, None])

    @patch("game_logic.Card")
    async def test_attack_resolution(self, mock_card):
        self.game.board = [None, self.player1, None, self.player2, None]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Earth,
        }

        moves = {
            self.player1.id: ("High Strike", "High Strike"),
            self.player2.id: ("Low Strike", "Low Strike"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(self.game.hitpoints[self.player2.id],
                         1)  # P1's High Strike hits
        self.assertEqual(self.game.hitpoints[self.player1.id],
                         2)  # P2's Low Strike misses

    @patch("game_logic.Card")
    async def test_counterattack(self, mock_card):
        self.game.board = [None, self.player1, self.player2, None, None]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Earth,
        }

        moves = {
            self.player1.id: ("Low Strike", "Low Strike"),
            self.player2.id: ("Counterattack", "Counterattack"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(self.game.hitpoints[self.player1.id],
                         1)  # P1 takes damage from counterattack
        self.assertEqual(self.game.hitpoints[self.player2.id],
                         2)  # P2 doesn't take damage

    @patch("game_logic.Card")
    async def test_special_attack_stance_change(self, mock_card):
        self.game.board = [None, self.player1, self.player2, None, None]
        self.game.stances = {
            self.player1.id: Stance.Heaven,
            self.player2.id: Stance.Earth,
        }

        moves = {
            self.player1.id: ("Kesa Strike", "Kesa Strike"),
            self.player2.id: ("Zan-Tetsu Strike", "Zan-Tetsu Strike"),
        }

        await self.game.resolve_moves(moves, False)

        self.assertEqual(self.game.stances[self.player1.id], Stance.Earth)
        self.assertEqual(self.game.stances[self.player2.id], Stance.Heaven)
        self.assertNotIn(
            "Kesa Strike",
            [card.name for card in self.game.hands[self.player1.id]])
        self.assertNotIn(
            "Zan-Tetsu Strike",
            [card.name for card in self.game.hands[self.player2.id]])

    @patch("game_logic.Card")
    async def test_card_lockout(self, mock_card):
        self.game.board = [self.player1, None, None, None, self.player2]

        moves = {
            self.player1.id: ("Footwork", "Approach"),
            self.player2.id: ("Footwork", "Retreat"),
        }

        await self.game.resolve_moves(moves, True)  # Second half of the turn

        self.assertEqual(self.game.set_aside[self.player1.id].name, "Footwork")
        self.assertEqual(self.game.set_aside[self.player2.id].name, "Footwork")

    @patch("game_logic.Card")
    async def test_stance_change_effect_on_second_half(self, mock_card):
        self.game.board = [self.player1, None, None, None, self.player2]
        self.game.stances = {
            self.player1.id: Stance.Earth,
            self.player2.id: Stance.Earth,
        }

        moves = {
            self.player1.id: ("Tactics", "Switch Stance"),
            self.player2.id: ("Footwork", "Approach"),
        }

        await self.game.resolve_moves(moves, False)  # First half of the turn

        self.assertEqual(self.game.stances[self.player1.id], Stance.Heaven)
        self.assertEqual(self.game.board,
                         [self.player1, None, None, self.player2, None])

        moves = {
            self.player1.id: ("Footwork", "Approach"),
            self.player2.id: ("Footwork", "Approach"),
        }

        await self.game.resolve_moves(moves, True)  # Second half of the turn

        # P1 should move first due to being in Heaven stance
        self.assertEqual(self.game.board,
                         [None, self.player1, self.player2, None, None])


if __name__ == "__main__":
    unittest.main()
