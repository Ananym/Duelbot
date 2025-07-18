#!/usr/bin/env python3

import unittest
from unittest.mock import MagicMock
from game import GameState
from cards import Stance, approach, charge, retreat, change_stance

class MockMember:
    def __init__(self, name, id):
        self.name = name
        self.id = id
        self.display_name = name
        self.mention = f"<@{id}>"

class TestMovementPriority(unittest.TestCase):
    def setUp(self):
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
        
    def test_heaven_vs_earth_priority(self):
        """Test Heaven always moves first regardless of action"""
        # Setup: P1 in Heaven, P2 in Earth, both 1 space apart
        self.game.p1.cell = 1
        self.game.p2.cell = 2
        self.game.p1.stance = Stance.HEAVEN
        self.game.p2.stance = Stance.EARTH
        
        # Heaven Approach vs Earth Charge - Heaven should move first
        self.game.resolve_movement(approach, charge)
        
        # P1 (Heaven) should move first to P2's position
        self.assertEqual(self.game.p1.cell, 2)
        self.assertEqual(self.game.p2.cell, 2)  # P2 can't move past P1
        
    def test_same_stance_charge_vs_approach(self):
        """Test Charge has priority over Approach in same stance"""
        # Setup: Both in Heaven, 2 spaces apart
        self.game.p1.cell = 1
        self.game.p2.cell = 3
        self.game.p1.stance = Stance.HEAVEN
        self.game.p2.stance = Stance.HEAVEN
        
        # P1 Charge vs P2 Approach - Charge should move first
        self.game.resolve_movement(charge, approach)
        
        # P1 (Charge) should move first, reaching P2's position
        self.assertEqual(self.game.p1.cell, 3)
        self.assertEqual(self.game.p2.cell, 3)  # P2 can't move past P1
        
    def test_same_stance_approach_vs_change_stance(self):
        """Test Approach has priority over Change Stance in same stance"""
        # Setup: Both in Earth, 2 spaces apart
        self.game.p1.cell = 1
        self.game.p2.cell = 3
        self.game.p1.stance = Stance.EARTH
        self.game.p2.stance = Stance.EARTH
        
        # P1 Approach vs P2 Change Stance - Approach should move first
        self.game.resolve_movement(approach, change_stance)
        
        # P1 (Approach) should move first
        self.assertEqual(self.game.p1.cell, 2)
        self.assertEqual(self.game.p2.cell, 3)  # P2 stays (change stance has no movement)
        
    def test_same_stance_simultaneous_charge(self):
        """Test simultaneous Charge actions result in collision"""
        # Setup: Both in Heaven, 2 spaces apart
        self.game.p1.cell = 1
        self.game.p2.cell = 3
        self.game.p1.stance = Stance.HEAVEN
        self.game.p2.stance = Stance.HEAVEN
        
        # Both charge toward each other
        self.game.resolve_movement(charge, charge)
        
        # Should meet in middle (collision rule)
        self.assertEqual(self.game.p1.cell, 2)
        self.assertEqual(self.game.p2.cell, 2)
        
    def test_same_stance_approach_vs_retreat(self):
        """Test simultaneous Approach/Retreat actions"""
        # Setup: Both in Earth, 2 spaces apart
        self.game.p1.cell = 1
        self.game.p2.cell = 3
        self.game.p1.stance = Stance.EARTH
        self.game.p2.stance = Stance.EARTH
        
        # P1 approaches, P2 retreats
        self.game.resolve_movement(approach, retreat)
        
        # Both move simultaneously
        self.assertEqual(self.game.p1.cell, 2)  # P1 moves forward
        self.assertEqual(self.game.p2.cell, 4)  # P2 moves back
        
    def test_different_stance_approach_vs_approach(self):
        """Test Heaven Approach vs Earth Approach - Heaven should move first"""
        # Setup: P1 in Heaven, P2 in Earth, 2 spaces apart
        self.game.p1.cell = 1
        self.game.p2.cell = 3
        self.game.p1.stance = Stance.HEAVEN
        self.game.p2.stance = Stance.EARTH
        
        # Both approach toward each other
        self.game.resolve_movement(approach, approach)
        
        # P1 (Heaven) should move first
        self.assertEqual(self.game.p1.cell, 2)  # P1 moves first
        self.assertEqual(self.game.p2.cell, 2)  # P2 moves to same cell (can't pass P1)
        
    def test_same_stance_approach_vs_approach(self):
        """Test simultaneous Approach vs Approach in same stance"""
        # Setup: Both in Heaven, 2 spaces apart
        self.game.p1.cell = 1
        self.game.p2.cell = 3
        self.game.p1.stance = Stance.HEAVEN
        self.game.p2.stance = Stance.HEAVEN
        
        # Both approach toward each other
        self.game.resolve_movement(approach, approach)
        
        # Should meet in middle (collision rule for same priority)
        self.assertEqual(self.game.p1.cell, 2)
        self.assertEqual(self.game.p2.cell, 2)

if __name__ == '__main__':
    unittest.main()