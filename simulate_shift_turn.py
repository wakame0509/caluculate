import eval7
from preflop_winrates_random import get_static_preflop_winrate
from turn_generator import generate_turn_cards
from board_patterns import classify_board_pattern
from hand_utils import hand_str_to_cards

def simulate_shift_turn_exhaustive(hand_str, flop_cards, trials_per_turn=20):
    """
    指定ハンド＆フロップに対して、すべてのターンカードを考慮して
    勝率変動と特徴量を集計し、ランキング化する。
    """
    hole_cards = list(hand_str_to_cards(hand_str))
    static_winrate = simulate_vs_random(hole_cards, flop_cards, [], trials_per_turn)
    turn_cards = generate_turn_cards(flop_cards, hole_cards)

    results = []

    for turn in turn_cards:
        board = flop_cards + [turn]
        winrate = simulate_vs_random(hole_cards, flop_cards, [turn], trials_per_turn)
        shift = winrate - static_winrate
        features = classify_board_pattern(flop_cards, turn)
        results.append({
            'turn_card': str(turn),
            'winrate': round(winrate, 1),
            'shift': round(shift, 1),
            'features': features
        })

    # ランキング（上位・下位）
    results_sorted = sorted(results, key=lambda x: x['shift'], reverse=True)
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return top10, bottom10


def simulate_vs_random(my_hand, flop, turn, iterations=20):
    """
    自分の手札とボード（フロップ＋ターン）に対して、
    モンテカルロで勝率を推定（相手はランダム）。
    """
    wins = 0
    ties = 0
    total = 0
    used_cards = my_hand + flop + turn

    for _ in range(iterations):
        deck = eval7.Deck()
        deck.cards = [card for card in deck.cards if str(card) not in [str(c) for c in used_cards]]
        deck.shuffle()

        river = deck.peek(1)
        full_board = flop + turn + river
        opp_hand = deck.peek(3)[1:3]

        my_full = my_hand + full_board
        opp_full = opp_hand + full_board

        my_score = eval7.evaluate(my_full)
        opp_score = eval7.evaluate(opp_full)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1
        total += 1

    return (wins + ties / 2) / total * 100
