import itertools
import random
from hand_utils import all_starting_hands

ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
suits = ['h', 'd', 'c', 's']

def generate_all_flops():
    deck = [r + s for r in ranks for s in suits]
    all_flops = list(itertools.combinations(deck, 3))
    return all_flops

def classify_flop(flop):
    suits = [card[1] for card in flop]
    ranks_only = [card[0] for card in flop]
    unique_suits = len(set(suits))
    high_cards = ['A', 'K', 'Q', 'J', 'T']
    high_count = sum(1 for r in ranks_only if r in high_cards)

    if unique_suits == 3:
        if high_count >= 2:
            return "High Card Rainbow"
        elif high_count == 0:
            return "Low Card Rainbow"
        else:
            return "Mixed Rainbow"
    elif unique_suits == 2:
        return "Two Tone"
    else:
        return "Monotone"

def generate_flops_by_type(flop_type, count=10):
    all_flops = generate_all_flops()
    matched = [f for f in all_flops if classify_flop(f) == flop_type]
    return random.sample(matched, min(count, len(matched)))
