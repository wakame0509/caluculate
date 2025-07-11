import random
import eval7
from preflop_winrates_random import get_static_preflop_winrate
from board_patterns import classify_flop_turn_pattern
from flop_generator import generate_flops_by_type

def convert_rank_to_value(rank):
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    if isinstance(rank, int):
        return rank
    return rank_map[str(rank)]

def hand_str_to_cards(hand_str):
    rank1, rank2 = hand_str[0], hand_str[1]
    suited = hand_str[2:] == 's'
    offsuit = hand_str[2:] == 'o'
    suits = ['s', 'h', 'd', 'c']
    if suited:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[0])]
    elif offsuit:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[1])]
    else:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[1])]

def simulate_vs_random(my_hand, opp_hand, board, iterations=20):
    wins = ties = 0
    used_cards = set(my_hand + opp_hand + board)
    for _ in range(iterations):
        deck = [card for card in eval7.Deck() if card not in used_cards]
        random.shuffle(deck)
        full_board = board + deck[:5 - len(board)]
        my_val = eval7.evaluate(my_hand + full_board)
        opp_val = eval7.evaluate(opp_hand + full_board)
        if my_val > opp_val:
            wins += 1
        elif my_val == opp_val:
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
        value = convert_rank_to_value(c.rank)
        suit_groups.setdefault(c.suit, []).append(value)

    for suited_vals in suit_groups.values():
        if len(suited_vals) >= 5:
            suited_vals = sorted(set(suited_vals), reverse=True)
            for i in range(len(suited_vals) - 4):
                if suited_vals[i] - suited_vals[i + 4] == 4:
                    return "straight_flush"
            if set([14, 2, 3, 4, 5]).issubset(set(suited_vals)):
                return "straight_flush"

    if 4 in counts:
        return "quads"
    if 3 in counts and 2 in counts:
        return "full_house"
    if max(suit_counts.values()) >= 5:
        return "flush"
    if is_straight(values):
        return "straight"
    if 3 in counts:
        return "set"
    if counts.count(2) >= 2:
        return "two_pair"
    if 2 in counts:
        return "pair"
    return "high_card"

def is_straight(values):
    unique = sorted(set(values), reverse=True)
    for i in range(len(unique) - 4):
        if unique[i] - unique[i + 4] == 4:
            return True
    if set([14, 2, 3, 4, 5]).issubset(set(values)):
        return True
    return False

def simulate_shift_flop_montecarlo(hand_str, flop_type, trials=10000):
    hole_cards = hand_str_to_cards(hand_str)
    static_wr = get_static_preflop_winrate(hand_str)
    feature_shifts = {}
    total_wr = 0

    candidate_flops = generate_flops_by_type(flop_type)

    for _ in range(trials):
        flop_raw = random.choice(candidate_flops)
        flop = [eval7.Card(str(c)) for c in flop_raw]
        used_ids = set(str(c) for c in hole_cards + flop)
        deck = [card for card in eval7.Deck() if str(card) not in used_ids]

        opp_hand = random.sample(deck, 2)
        winrate = simulate_vs_random(hole_cards, opp_hand, flop, iterations=20)
        total_wr += winrate
        shift = winrate - static_wr

        features = []
        made_hand = detect_made_hand(hole_cards, flop)
        if made_hand != "high_card":
            features.append(f"newmade_{made_hand}")
        else:
            new_feats = classify_flop_turn_pattern(flop, turn=None)
            features.extend(["newmade_" + f for f in new_feats])

        for feat in features:
            feature_shifts.setdefault(feat, []).append(shift)

    avg_shifts = {feat: round(sum(lst) / len(lst), 2) for feat, lst in feature_shifts.items()}
    average_wr = total_wr / trials
    return average_wr, avg_shifts

def simulate_shift_flop_montecarlo_specific(hand_str, flop, trials=10000):
    flop = [eval7.Card(str(c)) for c in flop]
    hole_cards = hand_str_to_cards(hand_str)
    static_wr = get_static_preflop_winrate(hand_str)
    feature_shifts = {}
    total_wr = 0

    for _ in range(trials):
        used_ids = set(str(c) for c in hole_cards + flop)
        deck = [card for card in eval7.Deck() if str(card) not in used_ids]

        opp_hand = random.sample(deck, 2)
        winrate = simulate_vs_random(hole_cards, opp_hand, flop, iterations=20)
        total_wr += winrate
        shift = winrate - static_wr

        features = []
        made_hand = detect_made_hand(hole_cards, flop)
        if made_hand != "high_card":
            features.append(f"newmade_{made_hand}")
        else:
            new_feats = classify_flop_turn_pattern(flop, turn=None)
            features.extend(["newmade_" + f for f in new_feats])

        for feat in features:
            feature_shifts.setdefault(feat, []).append(shift)

    avg_shifts = {feat: round(sum(lst) / len(lst), 2) for feat, lst in feature_shifts.items()}
    average_wr = total_wr / trials
    return average_wr, avg_shifts

def run_shift_flop(hand_str, flop_input, trials=10000):
    if isinstance(flop_input, str):
        return simulate_shift_flop_montecarlo(hand_str, flop_input, trials)
    elif isinstance(flop_input, list):
        return simulate_shift_flop_montecarlo_specific(hand_str, flop_input, trials)
    else:
        raise ValueError("flop_input must be a string (flop type) or list (specific flop)")
