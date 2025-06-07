import eval7
import random
from preflop_winrates_random import get_static_preflop_winrate
from extract_features import extract_features_for_flop
from turn_generator import generate_turns_for_flop
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards
from flop_generator import generate_flops_by_type

def simulate_shift_turn_exhaustive(hand_str, flop_cards, trials_per_turn=20):
    """
    指定ハンド＆フロップに対して、すべてのターンカードを考慮して
    勝率変動と特徴量を集計し、ランキング化する。
    """
    hole_cards = list(hand_str_to_cards(hand_str))
    static_winrate = simulate_vs_random(hole_cards, list(flop_cards), [], trials_per_turn)
    turn_cards = generate_turns_for_flop(flop_cards, hole_cards)

    results = []

    for turn in turn_cards:
        board = list(flop_cards) + [turn]
        winrate = simulate_vs_random(hole_cards, list(flop_cards), [turn], trials_per_turn)
        shift = winrate - static_winrate
        features = classify_flop_turn_pattern(flop_cards, turn)
        results.append({
            'turn_card': str(turn),
            'winrate': round(winrate, 1),
            'shift': round(shift, 1),
            'features': features
        })

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
    used_cards = my_hand + list(flop) + list(turn)

    for _ in range(iterations):
        deck = eval7.Deck()
        deck.cards = [card for card in deck.cards if str(card) not in [str(c) for c in used_cards]]
        deck.shuffle()
        river = deck.peek(1)
        full_board = list(flop) + list(turn) + river
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

def run_shift_turn(hand_str, trials_per_turn=20, flop_type="high_rainbow", flop_count=20):
    """
    指定ハンドに対して、フロップタイプから複数フロップを生成し、
    各フロップごとに全ターンカードで勝率変動を調査し、平均化して返す。
    """
    all_top10 = []
    all_bottom10 = []

    flop_list = generate_flops_by_type(flop_type, count=flop_count)

    for flop in flop_list:
        flop_cards = [eval7.Card(card) for card in flop]
        top10, bottom10 = simulate_shift_turn_exhaustive(hand_str, flop_cards, trials_per_turn)
        all_top10.extend(top10)
        all_bottom10.extend(bottom10)

    # 勝率変動でソート
    all_top10 = sorted(all_top10, key=lambda x: x['shift'], reverse=True)[:10]
    all_bottom10 = sorted(all_bottom10, key=lambda x: x['shift'])[:10]

    return all_top10, all_bottom10
