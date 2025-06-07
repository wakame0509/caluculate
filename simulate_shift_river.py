import eval7
from extract_features import extract_features_for_flop
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def simulate_shift_river_exhaustive(hand_str, flop_cards, turn_card, trials_per_river=20):
    """
    指定ハンド・フロップ・ターンに対して、すべてのリバーカードを考慮して
    勝率変動と特徴量を集計し、ランキング化する。
    """
    hole_cards = list(hand_str_to_cards(hand_str))
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
    """
    自分のハンド＋フロップ＋ターンを除いた45枚から、リバー候補を生成
    """
    used = set(str(c) for c in hole_cards + flop + [turn])
    deck = eval7.Deck()
    rivers = [card for card in deck.cards if str(card) not in used]
    return rivers


def simulate_vs_random(my_hand, board4, river_card, iterations=20):
    """
    自分のハンドとボード（4枚 or 5枚）に対して、
    相手ランダム手札を用いた勝率を推定。
    """
    wins = 0
    ties = 0
    total = 0
    used_cards = my_hand + board4 + river_card

    for _ in range(iterations):
        deck = eval7.Deck()
        deck.cards = [card for card in deck.cards if str(card) not in [str(c) for c in used_cards]]
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
