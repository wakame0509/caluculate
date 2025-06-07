import random
import eval7
from preflop_winrates_random import get_static_preflop_winrate
from extract_features import extract_features_for_flop
from flop_generator import generate_flops_by_type
from hand_utils import get_169_starting_hands

def simulate_shift_flop_montecarlo(hand_str, flop_type, trials=10000):
    """
    指定ハンドに対して、指定フロップタイプの下での
    プリフロップ→フロップの勝率変動をモンテカルロ法でシミュレーション。
    特徴量別に平均勝率変動を集計して返す。
    """
    deck = [str(card) for card in eval7.Deck()]
    hole_cards = list(hand_str_to_cards(hand_str))
    static_winrate = get_static_preflop_winrate(hand_str)
    feature_shifts = {}

    # 対象となるフロップ候補（事前に1回だけ抽出）
    candidate_flops = generate_flops_by_type(flop_type)

    for _ in range(trials):
        flop = list(random.choice(candidate_flops))

        used = set(hole_cards + flop)
        deck_remaining = [c for c in deck if c not in used]

        opp_hand = random.sample(deck_remaining, 2)
        board = flop

        winrate = simulate_vs_random(hole_cards, opp_hand, board, iterations=20)
        shift = winrate - static_winrate

        features = extract_features_for_flop(flop)
        for feat in features:
            if feat not in feature_shifts:
                feature_shifts[feat] = []
            feature_shifts[feat].append(shift)

    # 平均変動を算出
    avg_feature_shift = {
        feat: sum(shifts)/len(shifts)
        for feat, shifts in feature_shifts.items()
    }
    return static_winrate, avg_feature_shift


def simulate_vs_random(my_hand, opp_hand, board, iterations=20):
    """
    自分と相手の手札、ボードを指定してモンテカルロで勝率を推定。
    """
    wins = 0
    ties = 0
    total = 0

    for _ in range(iterations):
        deck = eval7.Deck()
        used = my_hand + opp_hand + board
        deck.cards = [card for card in deck.cards if str(card) not in [str(c) for c in used]]

        deck.shuffle()
        remaining_board = deck.peek(5 - len(board))
        full_board = board + remaining_board

        my_hand_combined = my_hand + full_board
        opp_hand_combined = opp_hand + full_board

        my_val = eval7.evaluate(my_hand_combined)
        opp_val = eval7.evaluate(opp_hand_combined)

        if my_val > opp_val:
            wins += 1
        elif my_val == opp_val:
            ties += 1
        total += 1

    return (wins + ties / 2) / total * 100


def hand_str_to_cards(hand_str):
    """
    例: 'AKs' → ['As', 'Ks']
        'AKo' → ['As', 'Kd']
        'TT'  → ['Tc', 'Td']
    """
    rank1, rank2 = hand_str[0], hand_str[1]
    suited = hand_str[2:] == 's'
    offsuit = hand_str[2:] == 'o'

    suits = ['s', 'h', 'd', 'c']

    if suited:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[0])]
    elif offsuit:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[1])]
    else:
        # ペア
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[1])]
