import eval7
from extract_features import extract_features_for_flop
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

RANK_TO_INT = {'2': 2, '3': 3, '4': 4, '5': 5,
               '6': 6, '7': 7, '8': 8, '9': 9,
               'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}


def simulate_shift_river_exhaustive(hand_str, flop_cards, turn_card, trials_per_river=45):
    hole_cards = [eval7.Card(str(c)) for c in hand_str_to_cards(hand_str)]
    flop_cards = [eval7.Card(str(c)) for c in flop_cards]
    turn_card = eval7.Card(str(turn_card))
    board4 = flop_cards + [turn_card]

    static_winrate = simulate_vs_random(hole_cards, board4, [], trials_per_river)
    river_candidates = generate_rivers(board4, hole_cards)

    results = []
    for river in river_candidates:
        full_board = board4 + [river]
        winrate = simulate_vs_random(hole_cards, board4, [river], trials_per_river)
        shift = winrate - static_winrate

        features = classify_flop_turn_pattern(flop_cards, turn_card, river)
        made_hand = detect_made_hand(hole_cards, full_board)
        features.append(f"made_{made_hand[0]}")

        results.append({
            'river_card': str(river),
            'winrate': round(winrate, 1),
            'shift': round(shift, 1),
            'features': features,
            'hand_rank': made_hand[0]  # ← 役を表示するために追加
        })

    results_sorted = sorted(results, key=lambda x: x['shift'], reverse=True)
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return top10, bottom10


def generate_rivers(board4, hole_cards):
    used = set(str(c) for c in board4 + hole_cards)
    deck = eval7.Deck()
    return [card for card in deck.cards if str(card) not in used]


def simulate_vs_random(my_hand, board4, river_card, iterations=45):
    my_hand = [eval7.Card(str(c)) for c in my_hand]
    board4 = [eval7.Card(str(c)) for c in board4]
    river_card = [eval7.Card(str(c)) for c in river_card]

    used_cards = my_hand + board4 + river_card
    wins = ties = total = 0

    for _ in range(iterations):
        deck = eval7.Deck()
        deck.cards = [c for c in deck.cards if str(c) not in [str(uc) for uc in used_cards]]
        deck.shuffle()
        opp_hand = deck.peek(2)

        my_full = my_hand + board4 + river_card
        opp_full = opp_hand + board4 + river_card

        my_score = eval7.evaluate(my_full)
        opp_score = eval7.evaluate(opp_full)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1
        total += 1

    return (wins + ties / 2) / total * 100


def detect_made_hand(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    ranks = [card.rank for card in all_cards]
    suits = [card.suit for card in all_cards]
    values = sorted([card.rank for card in all_cards], reverse=True)

    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    suit_counts = {s: suits.count(s) for s in set(suits)}
    counts = list(rank_counts.values())

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
    for i in range(len(unique_values) - 4 + 1):
        window = unique_values[i:i+5]
        if len(window) == 5 and window[0] - window[4] == 4:
            return True
    if set([14, 2, 3, 4, 5]).issubset(set(values)):  # wheel
        return True
    return False


def run_shift_river(hand_str, flop_cards, turn_card, trials_per_river=45):
    return simulate_shift_river_exhaustive(hand_str, flop_cards, turn_card, trials_per_river)
