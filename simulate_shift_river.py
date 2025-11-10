import eval7
import random
import pandas as pd
import itertools
from collections import Counter
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

# =============================
# Utility
# =============================

def convert_rank_to_value(rank):
    rank_map = {'2':2,'3':3,'4':4,'5':5,'6':6,
                '7':7,'8':8,'9':9,'T':10,'J':11,'Q':12,'K':13,'A':14}
    if isinstance(rank, int):
        return rank
    return rank_map[str(rank)]

def ensure_card(c):
    """文字列でもCardでも安全に eval7.Card を返す"""
    if isinstance(c, eval7.Card):
        return c
    return eval7.Card(str(c))

def generate_turns(flop_cards, hole_cards, n_turns=None):
    used = {str(c) for c in flop_cards + hole_cards}
    deck = [c for c in eval7.Deck() if str(c) not in used]
    if n_turns is None or n_turns >= len(deck):
        return deck
    random.shuffle(deck)
    return deck[:n_turns]

def generate_rivers(board4, hole_cards):
    used = {str(c) for c in board4 + hole_cards}
    return [c for c in eval7.Deck() if str(c) not in used]


# =============================
# 役判定（あなたのそのまま）
# =============================

def best5_from_seven(cards7):
    best = None
    best_score = -1
    for comb in itertools.combinations(cards7, 5):
        sc = eval7.evaluate(list(comb))
        if sc > best_score:
            best_score = sc
            best = list(comb)
    return best

def _values(cards, unique=False):
    vals = [convert_rank_to_value(c.rank) for c in cards]
    if unique:
        vals = sorted(set(vals), reverse=True)
    else:
        vals = sorted(vals, reverse=True)
    return vals

def _is_straight_from_values(uniq_vals):
    for i in range(len(uniq_vals) - 4):
        w = uniq_vals[i:i+5]
        if w[0] - w[4] == 4 and len(set(w)) == 5:
            return True
    return {14,5,4,3,2}.issubset(set(uniq_vals))

def classify5(cards5):
    ranks = [c.rank for c in cards5]
    suits = [c.suit for c in cards5]
    rc = Counter(ranks)
    sc = Counter(suits)
    uniq_vals = _values(cards5, unique=True)

    is_flush = any(v >= 5 for v in sc.values())
    is_straight = _is_straight_from_values(uniq_vals)

    if is_flush:
        for s in sc:
            if sc[s] >= 5:
                suited = [c for c in cards5 if c.suit == s]
                su = _values(suited, unique=True)
                if _is_straight_from_values(su):
                    return "straight_flush"

    counts = sorted(rc.values(), reverse=True)
    if counts[0] == 4:
        return "quads"
    if counts[0] == 3 and counts[1] == 2:
        return "full_house"
    if is_flush:
        return "flush"
    if is_straight:
        return "straight"
    if counts[0] == 3:
        return "set"
    if counts[0] == 2 and counts[1] == 2:
        return "two_pair"
    if counts[0] == 2:
        return "pair"
    return "high_card"

def detect_made_hand(hole_cards, board_cards):
    seven = hole_cards + board_cards
    best5 = best5_from_seven(seven)
    return [classify5(best5)]

def count_holecards_in_made_hand(hole, board, hand_name):
    seven = hole + board
    best5 = set(best5_from_seven(seven))
    return min(sum(1 for c in hole if c in best5), 2)


# =============================
# Overcard
# =============================
def is_overcard_river(hole_cards, river):
    if hole_cards[0].rank != hole_cards[1].rank:
        return False
    pair_rank = convert_rank_to_value(hole_cards[0].rank)
    return convert_rank_to_value(river.rank) > pair_rank


# =============================
# 全列挙
# =============================
def enumerate_vs_all(my_hand, board):
    used = {str(c) for c in my_hand + board}
    remaining = [c for c in eval7.Deck() if str(c) not in used]
    my_score = eval7.evaluate(my_hand + board)
    wins = ties = total = 0

    for opp in itertools.combinations(remaining, 2):
        total += 1
        opp_score = eval7.evaluate(list(opp) + board)
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    return (wins + ties / 2) / total * 100


# =============================
# ✅ Main Shift River（修正済）
# =============================
def simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate,
                                        turn_count=1, trials_per_river=1000):

    try:
        static_turn_winrate = float(static_turn_winrate)
    except:
        static_turn_winrate = 0.0

    hole = hand_str_to_cards(hand_str)

    # ✅ Card / str 混在を完全吸収
    flop = [ensure_card(c) for c in flop_cards_str]

    turns = generate_turns(flop, hole, n_turns=turn_count)

    all_rows = []

    for turn in turns:
        board4 = flop + [turn]
        before = detect_made_hand(hole, board4)
        feats_before = classify_flop_turn_pattern(flop, turn)

        rivers = generate_rivers(board4, hole)

        for river in rivers:
            full_board = board4 + [river]

            wr = enumerate_vs_all(hole, full_board)
            shift = round(wr - static_turn_winrate, 2)

            after = detect_made_hand(hole, full_board)
            hc = count_holecards_in_made_hand(hole, full_board, after[0])

            features = []
            if after[0] != before[0] and after[0] != "high_card":
                features.append(f"newmade_{after[0]}_hc{hc}")
            else:
                feats_after = classify_flop_turn_pattern(flop, turn, river)
                new_feats = [f for f in feats_after if f not in feats_before]
                features.extend([f"newmade_{f}" for f in new_feats])

                if is_overcard_river(hole, river):
                    features.append("newmade_overcard")

            all_rows.append({
                "turn_card": str(turn),
                "river_card": str(river),
                "winrate": round(wr, 2),
                "shift": shift,
                "features": features,
                "hand_rank": after[0],
                "hole_involved": hc
            })

    df = pd.DataFrame(all_rows)
    df_sorted = df.sort_values("shift", ascending=False)
    df_sorted.to_csv(f"results_river_multiple_turns_{hand_str}.csv", index=False)

    rows = df_sorted.to_dict("records")
    return rows, rows[:10], rows[-10:]


def run_shift_river(hand_str, flop_cards_str, static_turn_winrate,
                    turn_count=1, trials_per_river=100):
    return simulate_shift_river_multiple_turns(
        hand_str, flop_cards_str, static_turn_winrate,
        turn_count, trials_per_river
    )
