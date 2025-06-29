import eval7
import random
import pandas as pd
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def convert_rank_to_value(rank):
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    if isinstance(rank, int):
        return rank
    return rank_map[str(rank)]

def simulate_shift_river_exhaustive(hand_str, flop_cards_str, turn_card_str, trials_per_river=45):
    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(c) for c in flop_cards_str]
    turn_card = eval7.Card(turn_card_str)
    board4 = flop_cards + [turn_card]

    static_winrate = simulate_vs_random(hole_cards, [], board4, trials_per_river)
    river_candidates = generate_rivers(board4, hole_cards)

    results = []
    for river in river_candidates:
        full_board = board4 + [river]
        winrate = simulate_vs_random(hole_cards, [river], board4, trials_per_river)
        shift = winrate - static_winrate

        features = classify_flop_turn_pattern(flop_cards, turn_card, river)
        made_hand = detect_made_hand(hole_cards, full_board)
        features.append(f"made_{made_hand[0]}" if made_hand else "made_―")

        if detect_overcard(hole_cards, full_board):
            features.append("overcard")

        results.append({
            'river_card': str(river),
            'winrate': round(winrate, 1),
            'shift': round(shift, 1),
            'features': features,
            'hand_rank': made_hand[0] if made_hand else '―'
        })

    df = pd.DataFrame(results)
    df_sorted = df.sort_values(by='shift', ascending=False)
    filename = f'results_river_{hand_str}_{str(turn_card)}.csv'
    df_sorted.to_csv(filename, index=False)

    results_sorted = df_sorted.to_dict(orient='records')
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return results_sorted, top10, bottom10

def generate_rivers(board4, hole_cards):
    used_cards = set(board4 + hole_cards)
    deck = list(eval7.Deck())
    return [card for card in deck if card not in used_cards]

def simulate_vs_random(my_hand, river_cards, board4, iterations=45):
    used_cards = set(my_hand + board4 + river_cards)
    full_board = board4 + river_cards
    wins = ties = 0

    for _ in range(iterations):
        deck = [card for card in eval7.Deck() if card not in used_cards]
        random.shuffle(deck)
        opp_hand = deck[:2]

        my_score = eval7.evaluate(my_hand + full_board)
        opp_score = eval7.evaluate(opp_hand + full_board)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    return (wins + ties / 2) / iterations * 100

def detect_made_hand(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    ranks = [card.rank for card in all_cards]
    suits = [card.suit for card in all_cards]
    values = sorted([convert_rank_to_value(card.rank) for card in all_cards], reverse=True)

    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    suit_counts = {s: suits.count(s) for s in set(suits)}
    counts = list(rank_counts.values())

    for suit in suit_counts:
        suited_cards = [card for card in all_cards if card.suit == suit]
        suited_values = sorted(set(convert_rank_to_value(card.rank) for card in suited_cards), reverse=True)
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

def is_straight(values):
    unique_values = sorted(set(values), reverse=True)
    for i in range(len(unique_values) - 4):
        if unique_values[i] - unique_values[i + 4] == 4:
            return True
    if set([14, 2, 3, 4, 5]).issubset(set(values)):
        return True
    return False

def detect_overcard(hole_cards, board_cards):
    ranks = [convert_rank_to_value(c.rank) for c in hole_cards]
    board_values = [convert_rank_to_value(c.rank) for c in board_cards]
    if ranks[0] == ranks[1]:  # ペア
        pair_rank = ranks[0]
        return any(b > pair_rank for b in board_values)
    return False

def run_shift_river(hand_str, flop_cards_str, turn_card_str, trials_per_river=45):
    return simulate_shift_river_exhaustive(hand_str, flop_cards_str, turn_card_str, trials_per_river)
