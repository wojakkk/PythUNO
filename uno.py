
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNO (Text-Based) — Human vs Computer (single file)

How to run
----------
$ python uno.py

Controls
--------
- Enter the index number of a card to play it (e.g., 2).
- Or type its code (e.g., R4, GSKIP, B+2, W, WD4).
- 'd' to draw a card. If it’s playable, you can choose to play it immediately.
- 'p' to pass (only after drawing if still unplayable).
- 'q' to quit.
- If you are about to have one card left, you must type "uno" when prompted;
  otherwise you'll be penalized by drawing 2 cards (house rule for this game).

Rules implemented
-----------------
- Full 108-card deck: Red/Green/Blue/Yellow with numbers 0–9, Skip, Reverse, Draw Two (×2 each except 0 ×1);
  plus Wild (×4) and Wild Draw Four (×4).
- Match by color OR value/symbol. Wild is always playable. Wild Draw Four is restricted:
  the player may only play WD4 if they have NO card matching the current color.
- Reverse in 2-player mode behaves like Skip (i.e., the next player loses a turn).
- If the first flipped discard is an action card, its effect applies before the first turn.
- When the draw pile empties, it's refilled by shuffling the discard pile (except the top card).

CPU strategy (deterministic, no randomness)
-------------------------------------------
- Chooses from all playable cards using a simple scoring heuristic:
  • Prefer values you hold duplicates of (e.g., two different “4”s).\
  • Prefer colors you have many of (to maintain favorable color).\
  • Prioritize Skip/Reverse/+2 if the opponent is low on cards.\
  • Avoid spending Wilds early when other plays exist.\
  • Only play WD4 if legal; otherwise it’s heavily penalized.
- On Wild/Wild+4, CPU switches to the color it holds most.

This project contains no ML/LLM components—just explicit logic.
"""
from __future__ import annotations
import random
import sys
import re
from collections import Counter
from typing import List, Optional, Tuple

COLORS = ["Red", "Green", "Blue", "Yellow"]
VALUES_NUM = [str(n) for n in range(10)]
VALUES_ACTION = ["Skip", "Reverse", "Draw Two"]
WILD = "Wild"
WILD4 = "Wild Draw Four"

# ---------- Card & Deck ----------

class Card:
    __slots__ = ("color", "value")
    def __init__(self, color: Optional[str], value: str):
        self.color = color  # None for wilds
        self.value = value

    def is_wild(self) -> bool:
        return self.value in (WILD, WILD4)

    def matches(self, top_color: str, top_value: str) -> bool:
        """A card is playable if it matches color or value, or is a wild."""
        return self.is_wild() or self.color == top_color or self.value == top_value

    def code(self) -> str:
        """Short code for typing: e.g., R4, GSKIP, B+2, W, WD4"""
        if self.value == WILD:
            return "W"
        if self.value == WILD4:
            return "WD4"
        c = self.color[0].upper() if self.color else ""
        if self.value == "Skip":
            return f"{c}SKIP"
        if self.value == "Reverse":
            return f"{c}REV"
        if self.value == "Draw Two":
            return f"{c}+2"
        return f"{c}{self.value}"

    def __str__(self) -> str:
        if self.is_wild():
            return self.value
        return f"{self.color} {self.value}"

    def __repr__(self) -> str:
        return f"Card({self.color!r}, {self.value!r})"


def build_deck() -> List[Card]:
    deck: List[Card] = []
    # For each color: 0×1, 1–9×2, Skip×2, Reverse×2, Draw Two×2
    for color in COLORS:
        deck.append(Card(color, "0"))
        for v in range(1, 10):
            deck.append(Card(color, str(v)))
            deck.append(Card(color, str(v)))
        for action in VALUES_ACTION:
            deck.append(Card(color, action))
            deck.append(Card(color, action))
    # Wilds
    for _ in range(4):
        deck.append(Card(None, WILD))
        deck.append(Card(None, WILD4))
    random.shuffle(deck)
    return deck

# ---------- Game State ----------

class Player:
    def __init__(self, name: str, is_human: bool):
        self.name = name
        self.is_human = is_human
        self.hand: List[Card] = []

    def draw(self, pile: List[Card], count: int) -> List[Card]:
        drawn = []
        for _ in range(count):
            if not pile:
                break
            drawn.append(pile.pop())
        self.hand.extend(drawn)
        return drawn

    def remove_card(self, card: Card):
        self.hand.remove(card)


class UnoGame:
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
        self.draw_pile: List[Card] = build_deck()
        self.discard_pile: List[Card] = []
        self.players = [Player("You", True), Player("Computer", False)]
        self.current_idx = 0   # 0 -> You start by default; may change after first flip
        self.direction = 1     # 1 forward, -1 backward (makes sense with >2 players; here 2 players only)
        self.current_color: Optional[str] = None  # Active color (can be decided by Wild)
        self.current_value: Optional[str] = None  # Top card value (for matching)
        # Deal
        for _ in range(7):
            for p in self.players:
                p.draw(self.draw_pile, 1)
        self._flip_initial_discard_and_apply_effect()

    # ----- Pile maintenance -----

    def _refill_draw_pile_if_needed(self):
        if not self.draw_pile:
            if len(self.discard_pile) <= 1:
                return  # extremely rare corner case
            top = self.discard_pile[-1]
            rest = self.discard_pile[:-1]
            random.shuffle(rest)
            self.draw_pile = rest
            self.discard_pile = [top]

    def _flip_initial_discard_and_apply_effect(self):
        # Flip until non-Wild shows up as starting card (Wild as first can be awkward).
        while True:
            top = self.draw_pile.pop()
            if top.is_wild():
                # Put back and reshuffle deeper
                self.draw_pile.insert(0, top)  # push to bottom
                random.shuffle(self.draw_pile)
                continue
            self.discard_pile.append(top)
            self.current_color = top.color
            self.current_value = top.value
            print(f"Starting card: {top}")
            # If initial is action card, apply its startup effect
            if top.value == "Skip" or top.value == "Reverse":
                print("Startup effect: First player's turn is skipped.")
                self.current_idx = self._next_player_index()  # skip the starting player
            elif top.value == "Draw Two":
                victim = self.players[self.current_idx]
                drawn = victim.draw(self.draw_pile, 2)
                print(f"Startup effect: {victim.name} draws 2 cards: {', '.join(map(str, drawn))}")
                # Victim also loses their first turn
                self.current_idx = self._next_player_index()
            break

    def _next_player_index(self) -> int:
        # With two players, Reverse == Skip (because direction flip hands turn back)
        return (self.current_idx + self.direction) % len(self.players)

    # ----- Core helpers -----

    def playable_cards(self, hand: List[Card]) -> List[Card]:
        assert self.current_color and self.current_value
        return [c for c in hand if c.matches(self.current_color, self.current_value)]

    def can_play_wd4(self, hand: List[Card]) -> bool:
        """You may only play WD4 if you have no card matching the current color (official rule)."""
        assert self.current_color is not None
        for c in hand:
            if c.color == self.current_color and not c.is_wild():
                return False
        return True

    def place_card(self, player: Player, card: Card, chosen_color: Optional[str] = None):
        """Place card on discard and apply its effect; chosen_color applies to Wilds."""
        player.remove_card(card)
        self.discard_pile.append(card)
        # Update current matching state
        if card.is_wild():
            if card.value == WILD4 and not self.can_play_wd4(player.hand + [card]):  # shouldn't happen if validated
                pass
            # Choose color
            self.current_color = chosen_color or random.choice(COLORS)
            self.current_value = card.value  # "Wild" or "Wild Draw Four" becomes the value to match
        else:
            self.current_color = card.color
            self.current_value = card.value

        # Apply action effects
        if card.value == "Skip" or card.value == "Reverse":
            # In 2-player, Reverse is same as Skip
            self.current_idx = self._next_player_index()  # skip next player's turn
        elif card.value == "Draw Two":
            victim_idx = self._next_player_index()
            victim = self.players[victim_idx]
            self._refill_draw_pile_if_needed()
            drawn = victim.draw(self.draw_pile, 2)
            print(f"{victim.name} draws 2: {', '.join(map(str, drawn))}")
            # Also skip their turn
            self.current_idx = victim_idx  # move pointer to victim
            self.current_idx = self._next_player_index()  # then skip them
        elif card.value == WILD4:
            victim_idx = self._next_player_index()
            victim = self.players[victim_idx]
            self._refill_draw_pile_if_needed()
            drawn = victim.draw(self.draw_pile, 4)
            print(f"{victim.name} draws 4: {', '.join(map(str, drawn))}")
            # Skip their turn
            self.current_idx = victim_idx
            self.current_idx = self._next_player_index()

    # ----- Human turn -----

    def human_turn(self, player: Player) -> bool:
        """Returns True if the game continues, False if user quits."""
        assert player.is_human
        while True:
            self._refill_draw_pile_if_needed()
            top = self.discard_pile[-1]
            print("\n" + "="*60)
            print(f"Top of discard: [{top}]  (Active color: {self.current_color})")
            print(f"Your hand ({len(player.hand)}):")
            for i, c in enumerate(player.hand, 1):
                print(f"  {i:>2}. {c}  ({c.code()})")
            playable = self.playable_cards(player.hand)
            if playable:
                print(f"Playable now: {', '.join(c.code() for c in playable)}")
            else:
                print("No playable card — you must draw (type 'd').")

            choice = input("Play index/code, 'd' to draw, 'q' to quit: ").strip().lower()

            if choice in {"q", "quit", "exit"}:
                print("Goodbye!")
                return False

            # Draw
            if choice in {"d", "draw"}:
                self._refill_draw_pile_if_needed()
                drawn = player.draw(self.draw_pile, 1)
                if not drawn:
                    print("No cards to draw! Passing.")
                    self.current_idx = self._next_player_index()
                    return True
                card = drawn[0]
                print(f"You drew: {card} ({card.code()})")
                if card.matches(self.current_color, self.current_value) and (card.value != WILD4 or self.can_play_wd4(player.hand)):
                    yn = input("Play it? (y/n): ").strip().lower()
                    if yn.startswith("y"):
                        chosen_color = None
                        if card.is_wild():
                            chosen_color = self._prompt_color_choice()
                        self.place_card(player, card, chosen_color)
                        self._maybe_check_uno(player)
                        self.current_idx = self._next_player_index()
                        return True
                print("You didn't (or couldn't) play the drawn card. Turn passes.")
                self.current_idx = self._next_player_index()
                return True

            # Try index
            idx = None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(player.hand):
                    card = player.hand[idx]
                else:
                    print("Invalid index.")
                    continue
            else:
                # Try code like R4, GSKIP, etc.
                card = self._find_card_by_code(player.hand, choice)
                if card is None:
                    print("Couldn't parse that. Try again.")
                    continue

            # Validate playability
            if not card.matches(self.current_color, self.current_value):
                print("You can't play that card right now.")
                continue
            if card.value == WILD4 and not self.can_play_wd4(player.hand):
                print("Illegal WD4: You still have the active color in your hand.")
                continue

            chosen_color = None
            if card.is_wild():
                chosen_color = self._prompt_color_choice()
            self.place_card(player, card, chosen_color)
            self._maybe_check_uno(player)
            self.current_idx = self._next_player_index()
            return True

    def _prompt_color_choice(self) -> str:
        while True:
            c = input("Choose color [r/g/b/y]: ").strip().lower()
            mapping = {"r": "Red", "g": "Green", "b": "Blue", "y": "Yellow"}
            if c in mapping:
                print(f"Active color set to {mapping[c]}")
                return mapping[c]
            print("Invalid color.")

    def _find_card_by_code(self, hand: List[Card], text: str) -> Optional[Card]:
        t = text.upper().replace(" ", "")
        for c in hand:
            if c.code().upper().replace(" ", "") == t:
                return c
        # Also accept things like "red 4" or "blue reverse"
        m = re.match(r"(red|green|blue|yellow)\s*(\+2|skip|rev|reverse|[0-9])$", text, re.I)
        if m:
            col = m.group(1).title()
            val = m.group(2).lower()
            for c in hand:
                if c.color == col:
                    if (c.value == "Draw Two" and val in {"+2"}) or \
                       (c.value == "Reverse" and val in {"rev", "reverse"}) or \
                       (c.value == "Skip" and val == "skip") or \
                       (c.value.isdigit() and c.value == val):
                        return c
        if t in {"W", "WILD"}:
            for c in hand:
                if c.value == WILD:
                    return c
        if t in {"WD4", "WILD4", "WILD+4", "W+4"}:
            for c in hand:
                if c.value == WILD4:
                    return c
        return None

    def _maybe_check_uno(self, player: Player):
        if len(player.hand) == 1:
            if player.is_human:
                said = input('Type "uno" to declare UNO: ').strip().lower()
                if said != "uno":
                    self._refill_draw_pile_if_needed()
                    penalty = player.draw(self.draw_pile, 2)
                    print(f'Penalty! You didn\'t declare UNO. Drew: {", ".join(map(str, penalty))}')
            else:
                print("Computer says UNO!")

    # ----- CPU turn -----

    def cpu_turn(self, player: Player):
        assert not player.is_human
        self._refill_draw_pile_if_needed()
        top = self.discard_pile[-1]
        playable = self.playable_cards(player.hand)
        print("\n" + "-"*60)
        print(f"Top of discard: [{top}]  (Active color: {self.current_color})")
        print(f"Computer has {len(player.hand)} cards.")
        if not playable:
            # Draw one; play immediately if possible
            drawn = player.draw(self.draw_pile, 1)
            if not drawn:
                print("Computer cannot draw (empty pile). Passing.")
                self.current_idx = self._next_player_index()
                return
            card = drawn[0]
            print(f"Computer draws: {card}")
            if card.matches(self.current_color, self.current_value) and (card.value != WILD4 or self.can_play_wd4(player.hand)):
                chosen_color = None
                if card.is_wild():
                    chosen_color = self._cpu_choose_color(player)
                    print(f"Computer plays drawn {card} and sets color to {chosen_color}.")
                else:
                    print(f"Computer plays drawn {card}.")
                self.place_card(player, card, chosen_color)
                self._maybe_check_uno(player)
                self.current_idx = self._next_player_index()
                return
            print("Computer passes.")
            self.current_idx = self._next_player_index()
            return

        # Choose best playable card
        opponent_cards = len(self.players[0].hand)
        card, chosen_color = self._cpu_choose_best_card(player, playable, opponent_cards)
        if card.is_wild():
            print(f"Computer plays {card} and sets color to {chosen_color}.")
        else:
            print(f"Computer plays {card}.")
        self.place_card(player, card, chosen_color)
        self._maybe_check_uno(player)
        self.current_idx = self._next_player_index()

    def _cpu_choose_color(self, player: Player) -> str:
        counts = Counter(c.color for c in player.hand if c.color)
        if not counts:
            return random.choice(COLORS)
        return max(COLORS, key=lambda col: counts[col])

    def _cpu_choose_best_card(self, player: Player, playable: List[Card], opponent_cards: int) -> Tuple[Card, Optional[str]]:
        # Count numbers & colors in hand for heuristics
        num_counts = Counter(c.value for c in player.hand if c.value.isdigit())
        col_counts = Counter(c.color for c in player.hand if c.color)
        has_color_match_other_than_wild = any(c.color == self.current_color and not c.is_wild() for c in player.hand)

        def score(card: Card) -> float:
            s = 0.0
            # Prefer values we can duplicate (e.g., multiple "4" across colors)
            if card.value.isdigit() and num_counts[card.value] > 1:
                s += 10.0

            # Prefer colors we hold many of (keeps the run going)
            if card.color:
                s += 2.0 * col_counts[card.color]
                # Small extra to bleed oversupplied colors
                s += 0.2 * max(0, col_counts[card.color] - 2)

            # Action cards when opponent is low
            if card.value in {"Skip", "Reverse"}:
                s += 7.0 if opponent_cards <= 2 else 3.0
            if card.value == "Draw Two":
                s += 12.0 if opponent_cards <= 3 else 8.0

            # Wild usage policy: save them unless needed
            if card.value == WILD:
                # Discourage early use when other options exist
                s += 1.0
                if len(playable) == 1:
                    s += 6.0  # must use
            if card.value == WILD4:
                # Only legal if no other color matches; otherwise heavily penalize
                if has_color_match_other_than_wild:
                    s -= 100.0
                else:
                    s += 9.0
                    if opponent_cards <= 3:
                        s += 6.0

            # Slight preference for matching the current number (keeps number runs)
            if card.value == self.current_value and card.value.isdigit():
                s += 2.0

            return s

        best = max(playable, key=score)
        chosen_color = None
        if best.is_wild():
            chosen_color = self._cpu_choose_color(player)
        return best, chosen_color

    # ----- Game loop -----

    def play(self):
        while True:
            # Win check
            for p in self.players:
                if len(p.hand) == 0:
                    print("\n" + "#" * 60)
                    print(f"{p.name} wins!")
                    print("#" * 60)
                    return

            current = self.players[self.current_idx]
            if current.is_human:
                ok = self.human_turn(current)
                if not ok:
                    return
            else:
                self.cpu_turn(current)


def main():
    seed = None
    # Optional seed for reproducibility: pass an integer as first arg
    if len(sys.argv) >= 2:
        try:
            seed = int(sys.argv[1])
        except ValueError:
            seed = None
    game = UnoGame(seed=seed)
    game.play()

if __name__ == "__main__":
    main()
