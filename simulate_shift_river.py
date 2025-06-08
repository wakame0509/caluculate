import eval7
from extract_features import extract_features_for_flop
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def simulate_shift_river_exhaustive(hand_str, flop_cards, turn_card, trials_per_river=20):
    hole_cards = [eval7.Card(str(c)) for c in hand_str_to_cards(hand_str)]
    flop_cards = [eval7.Card(str(c)) for c in flop_cards]
    turn_card = eval7.Card(str(turn_card))
    board4 = flop_cards + [turn_card]

    static_winrate = simulate_vs_random(hole_cards, board4, [], trials_per_river)
    river_candidates = generate_rivers(flop_cards, turn_card, hole_cards)

    results = []
    for river in river_candidates:
        full_board = board4 + [river]
        winrate = simulate_vs_random(hole_cards, board4, [river], trials_per_river)
        shift = winrate - static_winrate
        features = classify_flop_turn_pattern(flop_cards, turn_card, river)
        results.append({
            'river_card': str(river),
            'winrate': round(winrate, 1),
            'shift': round(shift, 1),
            'features': features
        })

    results_sorted = sorted(results, key=lambda x: x['shift'], reverse=True)
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return top10, bottom10


def generate_rivers(flop, turn, hole_cards):
    used = set(str(c) for c in flop + [turn] + hole_cards)
    deck = eval7.Deck()
    return [card for card in deck.cards if str(card) not in used]


def simulate_vs_random(my_hand, board4, river_card, iterations=20):
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


def run_shift_river(hand_str, flop_cards, turn_card, trials_per_river=20):
    return simulate_shift_river_exhaustive(hand_str, flop_cards, turn_card, trials_per_river)
