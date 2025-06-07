import eval7
import random
from extract_features import extract_features_for_flop
from preflop_winrates_random import get_static_preflop_winrate

def simulate_shift_flop(hero_hand, flop_list, opponent_hand_combos, trials=10000):
    hero_cards = list(hero_hand)
    shifts = []
    features_count = {}

    for _ in range(trials):
        flop = random.choice(flop_list)
        board = list(flop)

        used = set(hero_cards + board)
        opp_hand = random.choice([h for h in opponent_hand_combos if not any(c in used for c in h)])
        used.update(opp_hand)

        deck = [c for c in eval7.Deck() if c not in used]
        turn_river = random.sample(deck, 2)
        full_board = board + turn_river

        hero_eval = eval7.evaluate(hero_cards + full_board)
        opp_eval = eval7.evaluate(list(opp_hand) + full_board)

        win = hero_eval > opp_eval
        tie = hero_eval == opp_eval
        shift = 1 if win else 0.5 if tie else 0
        shifts.append(shift)

        feats = extract_features_for_flop(flop)
        for f in feats:
            features_count[f] = features_count.get(f, 0) + shift

    avg_shift = sum(shifts) / len(shifts)
    feature_avg = {k: round(v / len(shifts), 4) for k, v in features_count.items()}
    return round(avg_shift * 100, 2), feature_avg
