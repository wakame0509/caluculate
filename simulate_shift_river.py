import eval7
import pandas as pd
import random
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def convert_rank_to_value(rank):
    rank_dict = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                 '7': 7, '8': 8, '9': 9, 'T': 10,
                 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    if isinstance(rank, int):
        return rank
    return rank_dict[str(rank)]

def simulate_shift_turn_exhaustive(hand_str, flop_cards, static_winrate, trials_per_turn=20):
    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(str(c)) for c in flop_cards]
    turn_candidates = generate_turns(flop_cards, hole_cards)

    made_before = detect_made_hand(hole_cards, flop_cards)
    overcard_on_flop = detect_overcard(hole_cards, flop_cards)

    results = []
    for turn in turn_candidates:
        board4 = flop_cards + [turn]
        winrate = simulate_vs_random(hole_cards, flop_cards, [turn], trials_per_turn)
        shift = winrate - static_winrate

        features = []
        made_after = detect_made_hand(hole_cards, board4)

        if made_after != made_before and made_after[0] != "high_card":
            features.append(f"newmade_{made_after[0]}")
        else:
            board_feats = classify_flop_turn_pattern(flop_cards, turn)
            features.extend([f"newmade_{f}" for f in board_feats])

            # ターンで新たにオーバーカードが出たときのみ付ける
            overcard_on_turn = detect_overcard(hole_cards, board4)
            if overcard_on_turn and not overcard_on_flop:
                features.append("newmade_overcard")

        results.append({
            'turn_card': str(turn),
            'winrate': round(winrate, 2),
            'shift': round(shift, 2),
            'features': features,
            'hand_rank': made_after[0] if made_after else '―'
        })

    df = pd.DataFrame(results)
    df_sorted = df.sort_values(by='shift', ascending=False)
    df_sorted.to_csv(f'results_turn_{hand_str}.csv', index=False)

    results_sorted = df_sorted.to_dict(orient='records')
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return results_sorted, top10, bottom10

def generate_turns(flop, hole_cards):
    used = set(flop + hole_cards)
    deck = list(eval7.Deck())
    return [card for card in deck if card not in used]

def simulate_vs_random(my_hand, flop_cards, turn_cards, iterations=20):
    used_cards = set(my_hand + flop_cards + turn_cards)
    wins = ties = 0
    full_board_base = flop_cards + turn_cards

    for _ in range(iterations):
        deck = [card for card in eval7.Deck() if card not in used_cards]
        random.shuffle(deck)
        opp_hand = deck[:2]
        remaining_board = deck[2: 2 + (5 - len(full_board_base))]
        full_board = full_board_base + remaining_board

        my_score = eval7.evaluate(my_hand + full_board)
        opp_score = eval7.evaluate(opp_hand + full_board)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    return (wins + ties / 2) / iterations * 100

def detect_made_hand(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    ranks = [c.rank for c in all_cards]
    suits = [c.suit for c in all_cards]
    values = sorted([convert_rank_to_value(c.rank) for c in all_cards], reverse=True)

    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    suit_counts = {s: suits.count(s) for s in set(suits)}
    counts = list(rank_counts.values())

    suit_groups = {}
    for c in all_cards:
        suit_groups.setdefault(c.suit, []).append(convert_rank_to_value(c.rank))

    for suited_vals in suit_groups.values():
        if len(suited_vals) >= 5:
            suited_vals = sorted(set(suited_vals), reverse=True)
            for i in range(len(suited_vals) - 4):
                if suited_vals[i] - suited_vals[i + 4] == 4:
                    return ["straight_flush"]
            if set([14, 2, 3, 4, 5]).issubset(set(suited_vals)):
                return ["straight_flush"]

    if 4 in counts:
        return ["quads"]
    if 3 in counts and 2 in counts:
        return ["full_house"]
    if max(suit_counts.values()) >= 5:
        return ["flush"]
    if is_straight(values):
        return ["straight"]
    if 3 in counts:
        return ["set"]
    if counts.count(2) >= 2:
        return ["two_pair"]
    if 2 in counts:
        return ["pair"]
    return ["high_card"]

def is_straight(values):
    unique = sorted(set(values), reverse=True)
    for i in range(len(unique) - 4):
        if unique[i] - unique[i + 4] == 4:
            return True
    if set([14, 2, 3, 4, 5]).issubset(set(values)):
        return True
    return False

def detect_overcard(hole_cards, board_cards):
    if hole_cards[0].rank != hole_cards[1].rank:
        return False
    pair_rank = convert_rank_to_value(hole_cards[0].rank)
    board_values = [convert_rank_to_value(c.rank) for c in board_cards]
    return any(b > pair_rank for b in board_values)

def run_shift_turn(hand_str, flop_cards, static_winrate, trials_per_turn=20):
    return simulate_shift_turn_exhaustive(hand_str, flop_cards, static_winrate, trials_per_turn)
