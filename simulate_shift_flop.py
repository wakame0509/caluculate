import random
import eval7
import itertools
from collections import Counter
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

# ============================================================
# ★ 厳密な役判定（ベスト5枚方式）＋ hc カウント
# ============================================================

def best5_from_seven(cards7):
    """7枚から eval7 スコア最大の5枚を返す"""
    best = None
    best_score = -1
    for comb in itertools.combinations(cards7, 5):
        sc = eval7.evaluate(list(comb))
        if sc > best_score:
            best_score = sc
            best = list(comb)
    return best

def _values(card_list, unique=False, sort_desc=True):
    vals = [convert_rank_to_value(c.rank) for c in card_list]
    if unique:
        vals = sorted(set(vals), reverse=sort_desc)
    else:
        vals = sorted(vals, reverse=sort_desc)
    return vals

def _is_straight_from_values(values_unique_desc):
    # 5連番
    for i in range(len(values_unique_desc) - 4):
        window = values_unique_desc[i:i+5]
        if window[0] - window[4] == 4 and len(set(window)) == 5:
            return True
    # A-5 (wheel)
    s = set(values_unique_desc)
    return {14,5,4,3,2}.issubset(s)

def classify5(cards5):
    """5枚固定から役名を返す"""
    ranks = [c.rank for c in cards5]
    suits = [c.suit for c in cards5]
    rc = Counter(ranks)
    sc = Counter(suits)

    is_flush = any(cnt >= 5 for cnt in sc.values())  # 5枚なので==5と同義
    uvals = _values(cards5, unique=True)

    # ストレートフラッシュ
    if is_flush:
        flush_suit = max(sc, key=lambda k: sc[k])
        suited = [c for c in cards5 if c.suit == flush_suit]
        su = _values(suited, unique=True)
        if _is_straight_from_values(su):
            return "straight_flush"

    counts_sorted = sorted(rc.values(), reverse=True)
    if counts_sorted[0] == 4:
        return "quads"
    if counts_sorted[0] == 3 and counts_sorted[1] == 2:
        return "full_house"
    if is_flush:
        return "flush"
    if _is_straight_from_values(uvals):
        return "straight"
    if counts_sorted[0] == 3:
        return "set"
    if counts_sorted[0] == 2 and counts_sorted[1] == 2:
        return "two_pair"
    if counts_sorted[0] == 2:
        return "pair"
    return "high_card"

def detect_made_hand(hole_cards, board_cards):
    """
    ベスト5枚で厳密に役を判定し、そのベスト5内に何枚ホールが入っているかで hc を数える。
    戻り値は (hand_name, hole_contrib) で、既存の呼び出しに互換。
    """
    seven = hole_cards + board_cards
    best5 = best5_from_seven(seven)
    hand_name = classify5(best5)

    # hc 枚数（ベスト5内に含まれるホールカード枚数）
    best5_set = set(best5)
    hole_contrib = sum(1 for c in hole_cards if c in best5_set)
    hole_contrib = min(hole_contrib, 2)
    return hand_name, hole_contrib

# ============================================================
# シフトフロップ本体（インターフェイスは現状維持）
# ============================================================

def is_straight(values):  # 互換用（外部で使っていないが念のため残す）
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
        made_preflop, _ = detect_made_hand(hole_cards, [])
        made_flop, hole_contrib = detect_made_hand(hole_cards, flop)

        if made_flop != made_preflop and made_flop != "high_card":
            features.append(f"newmade_{made_flop}_hc{hole_contrib}")
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
        made_preflop, _ = detect_made_hand(hole_cards, [])
        made_flop, hole_contrib = detect_made_hand(hole_cards, flop)

        if made_flop != made_preflop and made_flop != "high_card":
            features.append(f"newmade_{made_flop}_hc{hole_contrib}")
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
