import eval7
import random
import pandas as pd
import itertools
from collections import Counter
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

# -----------------------------
# Utility functions
# -----------------------------
def convert_rank_to_value(rank):
    rank_map = {'2':2,'3':3,'4':4,'5':5,'6':6,
                '7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    if isinstance(rank, int):
        return rank
    return rank_map[str(rank)]

def generate_turns(flop_cards, hole_cards, n_turns=None):
    used_str = {str(c) for c in flop_cards + hole_cards}
    deck = [c for c in eval7.Deck() if str(c) not in used_str]
    if n_turns is None or n_turns >= len(deck):
        return deck
    random.shuffle(deck)
    return deck[:n_turns]

def generate_rivers(board4, hole_cards):
    used_str = {str(c) for c in board4 + hole_cards}
    return [c for c in eval7.Deck() if str(c) not in used_str]

def simulate_vs_random(my_hand, board_full, iterations=1000):
    wins = ties = 0
    deck = eval7.Deck()
    used = {str(c) for c in my_hand + board_full}
    deck = [c for c in deck if str(c) not in used]

    for _ in range(iterations):
        random.shuffle(deck)
        opp_hand = deck[:2]
        my_score = eval7.evaluate(my_hand + board_full)
        opp_score = eval7.evaluate(opp_hand + board_full)
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    return (wins + ties / 2) / iterations * 100

# ============================================================
# ★ ここから：ベスト5枚ベースの厳密な役判定ロジック ★
# ============================================================

def best5_from_seven(cards7):
    """7枚から eval7 スコア最大の5枚を返す（安定・確実）"""
    best = None
    best_score = -1
    for comb in itertools.combinations(cards7, 5):
        sc = eval7.evaluate(list(comb))
        if sc > best_score:
            best_score = sc
            best = list(comb)
    return best  # list[eval7.Card] (必ず5枚)

def _values(card_list, unique=False, sort_desc=True):
    vals = [convert_rank_to_value(c.rank) for c in card_list]
    if unique:
        vals = sorted(set(vals), reverse=sort_desc)
    else:
        vals = sorted(vals, reverse=sort_desc)
    return vals

def _is_straight_from_values(values_unique_desc):
    """降順ユニーク値でストレート判定（5連続 or A-5ホイール）"""
    # 5連番
    for i in range(len(values_unique_desc) - 4):
        window = values_unique_desc[i:i+5]
        if window[0] - window[4] == 4 and len(set(window)) == 5:
            return True
    # A-5 (wheel)
    s = set(values_unique_desc)
    return {14,5,4,3,2}.issubset(s)

def classify5(cards5):
    """5枚固定からテキサスホールデムの役名を返す（文字列）"""
    vals = _values(cards5, unique=False)          # 重複含む
    uvals = _values(cards5, unique=True)          # ユニーク
    ranks = [c.rank for c in cards5]
    suits = [c.suit for c in cards5]
    rc = Counter(ranks)                            # 各ランクの個数
    sc = Counter(suits)                            # 各スートの個数

    is_flush = any(cnt >= 5 for cnt in sc.values())
    is_straight = _is_straight_from_values(uvals)

    # 同スート5枚を抽出してストフラ判定
    if is_flush:
        flush_suit = max(sc, key=lambda k: sc[k])
        suited = [c for c in cards5 if c.suit == flush_suit]
        su = _values(suited, unique=True)
        if _is_straight_from_values(su):
            return "straight_flush"

    # カウントパターンで役を決定
    counts_sorted = sorted(rc.values(), reverse=True)
    if counts_sorted[0] == 4:
        return "quads"
    if counts_sorted[0] == 3 and counts_sorted[1] == 2:
        return "full_house"
    if is_flush:
        return "flush"
    if is_straight:
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
    7枚からベスト5枚を取り出し、その5枚を厳密に分類して役名を返す。
    これにより「実際に完成していない役」を返すことがなくなる。
    """
    seven = hole_cards + board_cards
    best5 = best5_from_seven(seven)
    hand_name = classify5(best5)
    return [hand_name]  # 互換のためリストで返す

def count_holecards_in_made_hand(hole_cards, board_cards, hand_name):
    """
    完成役にホールカードが何枚“ベスト5の中で”関与しているかを数える。
    役名は detect_made_hand() の結果に合わせる。
    """
    seven = hole_cards + board_cards
    best5 = best5_from_seven(seven)
    best5_set = set(best5)

    # ベスト5に入っているホールカード何枚か？
    hc_in_best5 = sum(1 for c in hole_cards if c in best5_set)

    # 役の性質に応じて、ベスト5内の寄与を厳密にカウント
    if hand_name in ["straight", "straight_flush"]:
        # ベスト5はまさにストレート(or ストフラ)の5枚なので、in_best5そのまま（最大2）
        return min(hc_in_best5, 2)
    if hand_name == "flush":
        return min(hc_in_best5, 2)
    if hand_name in ["pair", "two_pair", "set", "full_house", "quads"]:
        # ベスト5内で同ランク役を作っているかで数える
        ranks_best5 = [c.rank for c in best5]
        rc = Counter(ranks_best5)
        contrib = 0
        for hc in hole_cards:
            if rc[hc.rank] >= 2:  # 同ランクが2枚以上なら、そのHCは役に関与
                contrib += 1
        return min(contrib, 2)
    return 0

# -----------------------------
# Helper functions
# -----------------------------
def is_overcard_river(hole_cards, river_card):
    if hole_cards[0].rank != hole_cards[1].rank:
        return False
    pair_rank = convert_rank_to_value(hole_cards[0].rank)
    river_rank = convert_rank_to_value(river_card.rank)
    return river_rank > pair_rank

# -----------------------------
# Main simulation (unchanged except calling new detectors)
# -----------------------------

def enumerate_vs_all(my_hand, board_full):
    used_str = {str(c) for c in my_hand + board_full}
    remaining = [c for c in eval7.Deck() if str(c) not in used_str]

    wins = ties = 0
    total = 0
    my_score = eval7.evaluate(my_hand + board_full)  # ループ外でOK

    for opp_pair in itertools.combinations(remaining, 2):
        total += 1
        opp_hand = list(opp_pair)
        opp_score = eval7.evaluate(opp_hand + board_full)
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    if total == 0:
        return 0.0
    return (wins + ties / 2) / total * 100.0

def simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate, turn_count=1, trials_per_river=1000):
    try:
        static_turn_winrate = float(static_turn_winrate)
    except:
        static_turn_winrate = 0.0

    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(c) if isinstance(c, str) else c for c in flop_cards_str]
    turn_candidates = generate_turns(flop_cards, hole_cards, n_turns=turn_count)
    all_results = []

    for turn_card in turn_candidates:
        board4 = flop_cards + [turn_card]
        feats_before = classify_flop_turn_pattern(flop_cards, turn_card)
        made_before = detect_made_hand(hole_cards, board4)
        river_candidates = generate_rivers(board4, hole_cards)

        for river in river_candidates:
            full_board = board4 + [river]
            river_winrate = enumerate_vs_all(hole_cards, full_board)
            shift = round(river_winrate - static_turn_winrate, 2)

            made_after = detect_made_hand(hole_cards, full_board)
            hole_involved = count_holecards_in_made_hand(hole_cards, full_board, made_after[0])

            features = []
            if made_after[0] != made_before[0] and made_after[0] != "high_card":
                features.append(f"newmade_{made_after[0]}_hc{hole_involved}")
            else:
                feats_after = classify_flop_turn_pattern(flop_cards, turn_card, river)
                new_feats = [f for f in feats_after if f not in feats_before]
                features.extend([f"newmade_{f}" for f in new_feats])
                if is_overcard_river(hole_cards, river):
                    features.append("newmade_overcard")

            all_results.append({
                'turn_card': str(turn_card),
                'river_card': str(river),
                'winrate': round(river_winrate, 2),
                'shift': shift,
                'features': features,
                'hand_rank': made_after[0],
                'hole_involved': hole_involved
            })

    df = pd.DataFrame(all_results)
    df_sorted = df.sort_values(by='shift', ascending=False)
    df_sorted.to_csv(f'results_river_multiple_turns_{hand_str}.csv', index=False)

    results_sorted = df_sorted.to_dict(orient='records')
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return results_sorted, top10, bottom10

def run_shift_river(hand_str, flop_cards_str, static_turn_winrate, turn_count=1, trials_per_river=1000):
    results_sorted, top10, bottom10 = simulate_shift_river_multiple_turns(
        hand_str, flop_cards_str, static_turn_winrate, turn_count, trials_per_river
    )
    return results_sorted, top10, bottom10
