import random
import eval7
from preflop_winrates_random import get_static_preflop_winrate
from extract_features import extract_features_for_flop
from flop_generator import generate_flops_by_type

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
    wins = 0
    ties = 0

    for _ in range(iterations):
        deck = list(eval7.Deck())
        used = my_hand + opp_hand + board
        used_str = set(str(c) for c in used)
        deck = [card for card in deck if str(card) not in used_str]

        random.shuffle(deck)
        remaining_board = deck[:5 - len(board)]
        full_board = board + remaining_board

        my_val = eval7.evaluate(my_hand + full_board)
        opp_val = eval7.evaluate(opp_hand + full_board)

        if my_val > opp_val:
            wins += 1
        elif my_val == opp_val:
            ties += 1

    return (wins + ties / 2) / iterations * 100

def simulate_shift_flop_montecarlo(hand_str, flop_type, trials=10000):
    deck = list(eval7.Deck())
    hole_cards = hand_str_to_cards(hand_str)
    static_winrate = get_static_preflop_winrate(hand_str)
    feature_shifts = {}

    candidate_flops = generate_flops_by_type(flop_type)

    for _ in range(trials):
        flop = list(random.choice(candidate_flops))
        used = hole_cards + flop
        used_str = set(str(c) for c in used)
        deck_remaining = [c for c in deck if str(c) not in used_str]

        opp_hand = random.sample(deck_remaining, 2)
        winrate = simulate_vs_random(hole_cards, opp_hand, flop, iterations=20)
        shift = winrate - static_winrate

        features = extract_features_for_flop(flop)
        for feat in features:
            if feat not in feature_shifts:
                feature_shifts[feat] = []
            feature_shifts[feat].append(shift)

    avg_feature_shift = {
        feat: round(sum(shifts) / len(shifts), 2)
        for feat, shifts in feature_shifts.items()
    }
    return static_winrate, avg_feature_shift

def simulate_shift_flop_montecarlo_specific(hand_str, flop, trials=10000):
    deck = list(eval7.Deck())
    hole_cards = hand_str_to_cards(hand_str)
    static_winrate = get_static_preflop_winrate(hand_str)
    feature_shifts = {}

    for _ in range(trials):
        used = hole_cards + flop
        used_str = set(str(c) for c in used)
        deck_remaining = [c for c in deck if str(c) not in used_str]

        opp_hand = random.sample(deck_remaining, 2)
        winrate = simulate_vs_random(hole_cards, opp_hand, flop, iterations=20)
        shift = winrate - static_winrate

        features = extract_features_for_flop(flop)
        for feat in features:
            if feat not in feature_shifts:
                feature_shifts[feat] = []
            feature_shifts[feat].append(shift)

    avg_feature_shift = {
        feat: round(sum(shifts) / len(shifts), 2)
        for feat, shifts in feature_shifts.items()
    }
    return static_winrate, avg_feature_shift

def run_shift_flop(hand_str, flop_input, trials=10000):
    """
    フロップタイプ or 具体的なフロップカードに応じて処理を分岐。
    """
    if isinstance(flop_input, str):
        return simulate_shift_flop_montecarlo(hand_str, flop_input, trials)
    elif isinstance(flop_input, list):
        return simulate_shift_flop_montecarlo_specific(hand_str, flop_input, trials)
    else:
        raise ValueError("flop_input must be a string (type) or list (specific flop)")
