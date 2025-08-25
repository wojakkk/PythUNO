# PythUNO
Python based uno game which allow user to play uno againt computer (its not actually ai you are playing with its logic based cpu which follows the classic UNO game logics to make decisions.)
## Overview
This project implements a **text-based UNO game** in Python, where the user plays against a computer opponent.  
The game follows the official UNO rules, including Wild and Wild Draw Four restrictions, and provides a simple console interface for interaction.

The computer opponent uses a **deterministic decision-making strategy** based on card advantage, rather than randomness or machine learning.

---

## Features
- **Complete UNO deck** with 108 cards (Numbers, Skip, Reverse, Draw Two, Wild, and Wild Draw Four).
- **Rule compliance**, including:
  - Wild Draw Four legality (can only be played if no other color matches).
  - Skip and Reverse acting equivalently in a 2-player match.
  - Automatic reshuffling of the discard pile into the draw pile when empty.
- **Human interaction**:
  - Play by index or card code (e.g., `R4`, `GSKIP`, `B+2`, `W`, `WD4`).
  - Type `d` to draw, `p` to pass, and `q` to quit.
  - Declare “UNO” when one card remains, or receive a penalty.
- **Computer strategy**:
  - Prefers playing numbers it has duplicates of.
  - Prioritizes colors with higher counts in its hand.
  - Uses action cards (Skip, Reverse, Draw Two) more aggressively when the opponent has few cards.
  - Conserves Wild cards unless necessary.
  - Selects Wild colors based on the strongest color in hand.

---

## Installation
Ensure that **Python 3.7+** is installed on your system.

Clone or download this repository, then navigate to the directory containing `uno.py`.

---

## Usage
Run the game with:

```bash
python uno.py
