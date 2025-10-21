import eval7
import random
import pandas as pd
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def convert_rank_to_value(rank):
    rank_map = {'2':2,'3':3,'4':4,'5':5,'6':6,
                '7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    if isinstance(rank, int):
        return rank
    return rank_map[str(rank)]

def generate_turns(flop_cards, hole_cards, n_turns=None):
    used_cards = set(flop_cards + hole_cards)
    deck = [c for c in eval7.Deck() if c not in used_cards]
    if n_turns is None or n_turns >= len(deck):
        return deck
    random.shuffle(deck)
    return deck[:n_turns]

def generate_rivers(board4, hole_cards):
    used_cards = set(board4 + hole_cards)
    return [c for c in eval7.Deck() if c not in used_cards]

def simulate_vs_random(my_hand, board_full, iterations=1000):
    used_cards = set(board_full + my_hand)
    wins = ties = 0
    for _ in range(iterations):
        deck = [c for c in eval7.Deck() if c not in used_cards]
        random.shuffle(deck)
        opp_hand = deck[:2]
        my_score = eval7.evaluate(my_hand + board_full)
        opp_score = eval7.evaluate(opp_hand + board_full)
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

    for suit in suit_counts:
        suited_cards = [c for c in all_cards if c.suit == suit]
        suited_values = sorted(set(convert_rank_to_value(c.rank) for c in suited_cards), reverse=True)
        if is_straight(suited_values):
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

def count_holecards_in_made_hand(hole_cards, board_cards, hand_name):
    all_cards = hole_cards + board_cards
    ranks = [c.rank for c in all_cards]
    rank_counts = {r: ranks.count(r) for r in set(ranks)}

    if hand_name in ["pair", "two_pair", "set", "full_house", "quads"]:
        hole_ranks = [c.rank for c in hole_cards]
        count = sum(min(rank_counts[r], hole_ranks.count(r)) for r in hole_ranks)
        return min(count, 2)
    elif hand_name in ["straight", "straight_flush"]:
        values = sorted(set([convert_rank_to_value(c.rank) for c in all_cards]))
        hole_values = set(convert_rank_to_value(c.rank) for c in hole_cards)
        for i in range(len(values) - 4):
            window = set(values[i:i + 5])
            cnt = len(hole_values.intersection(window))
            if cnt > 0:
                return min(cnt, 2)
        wheel = {14, 2, 3, 4, 5}
        cnt = len(hole_values.intersection(wheel)) if wheel.issubset(set(values)) else 0
        return min(cnt, 2)
    elif hand_name == "flush":
        suit_groups = {}
        for c in all_cards:
            suit_groups.setdefault(c.suit, []).append(c)
        flush_suit = None
        for s, clist in suit_groups.items():
            if len(clist) >= 5:
                flush_suit = s
                break
        if flush_suit:
            cnt = sum(1 for c in hole_cards if c.suit == flush_suit)
            return min(cnt, 2)
        return 0
    return 0

def is_overcard_river(hole_cards, river_card):
    if hole_cards[0].rank != hole_cards[1].rank:
        return False
    pair_rank = convert_rank_to_value(hole_cards[0].rank)
    river_rank = convert_rank_to_value(river_card.rank)
    return river_rank > pair_rank

def is_straight(values):
    unique_values = sorted(set(values), reverse=True)
    for i in range(len(unique_values) - 4):
        if unique_values[i] - unique_values[i + 4] == 4:
            return True
    if set([14, 2, 3, 4, 5]).issubset(set(values)):
        return True
    return False

def simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate, turn_count=1, trials_per_river=1000):
    # --- 型をfloatに統一 ---
    try:
        static_turn_winrate = float(static_turn_winrate)
    except:
        static_turn_winrate = 0.0

    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(c) if isinstance(c, str) else c for c in flop_cards_str]
    turn_candidates = generate_turns(flop_cards, hole_cards, n_turns=turn_count)
    all_results = []

    # --- 複数ターンに対応 ---
    for turn_card in turn_candidates:
        board4 = flop_cards + [turn_card]
        feats_before = classify_flop_turn_pattern(flop_cards, turn_card)
        made_before = detect_made_hand(hole_cards, board4)
        river_candidates = generate_rivers(board4, hole_cards)

        for river in river_candidates:
            full_board = board4 + [river]
            river_winrate = simulate_vs_random(hole_cards, full_board, iterations=trials_per_river)
            shift = round(float(river_winrate) - static_turn_winrate, 2)

            features = []
            made_after = detect_made_hand(hole_cards, full_board)
            hole_involved = count_holecards_in_made_hand(hole_cards, full_board, made_after[0])

            # --- 役変化時 ---
            if made_after[0] != made_before[0] and made_after[0] != "high_card":
                features.append(f"newmade_{made_after[0]}_hc{hole_involved}")
            else:
                feats_after = classify_flop_turn_pattern(flop_cards, turn_card, river)
                new_feats = [f for f in feats_after if f not in feats_before]
                features.extend([f"newmade_{f}" for f in new_feats])
                if is_overcard_river(hole_cards, river):
                    features.append("newmade_overcard")

            all_results.append({
                'turn_card': str(turn_card),
                'river_card': str(river),
                'winrate': round(river_winrate, 2),
                'shift': shift,
                'features': features,
                'hand_rank': made_after[0],
                'hole_involved': hole_involved
            })

    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by='shift', ascending=False)
    df_sorted.to_csv(f'results_river_multiple_turns_{hand_str}.csv', index=False)

    results_sorted = df_sorted.to_dict(orient='records')
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return results_sorted, top10, bottom10
def run_shift_river(hand_str, flop_cards_str, static_turn_winrate, turn_count=1, trials_per_river=1000):
    return simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate, turn_count, trials_per_river)
