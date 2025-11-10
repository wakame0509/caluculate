import eval7
import pandas as pd
import random
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def convert_rank_to_value(rank):
    rank_dict = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                 '7': 7, '8': 8, '9': 9, 'T': 10,
                 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    if isinstance(rank, int):
        return rank
    return rank_dict[str(rank)]

def is_overcard_turn(hole_cards, turn_card):
    if hole_cards[0].rank != hole_cards[1].rank:
        return False
    pair_rank = convert_rank_to_value(hole_cards[0].rank)
    turn_rank = convert_rank_to_value(turn_card.rank)
    return turn_rank > pair_rank

def generate_turns(flop, hole_cards):
    used = set(flop + hole_cards)
    deck = list(eval7.Deck())
    return [card for card in deck if card not in used]

def simulate_vs_random(my_hand, flop_cards, turn_cards, iterations=1000):
    used_cards = set(my_hand + flop_cards + turn_cards)
    wins = ties = 0
    full_board_base = flop_cards + turn_cards

    for _ in range(iterations):
        deck = [card for card in eval7.Deck() if card not in used_cards]
        random.shuffle(deck)
        opp_hand = deck[:2]
        remaining_board = deck[2: 2 + (5 - len(full_board_base))]
        full_board = full_board_base + remaining_board

        my_score = eval7.evaluate(my_hand + full_board)
        opp_score = eval7.evaluate(opp_hand + full_board)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    return (wins + ties / 2) / iterations * 100

# ===== ここから：役判定のみ刷新 =====
def _has_straight_from_values(values_iterable):
    """値の集合（int）からストレートの有無を厳密判定。Aは14扱い、A-5ストレートにも対応。"""
    u = sorted(set(int(v) for v in values_iterable))
    if not u:
        return False
    # A(14) を 1 としても扱う（5ハイストレート）
    if 14 in u:
        u_with_wheel = u + [1]
    else:
        u_with_wheel = u[:]

    # 連続5個をチェック（昇順）
    streak = 1
    for i in range(1, len(u_with_wheel)):
        if u_with_wheel[i] == u_with_wheel[i-1] + 1:
            streak += 1
            if streak >= 5:
                return True
        elif u_with_wheel[i] == u_with_wheel[i-1]:
            continue
        else:
            streak = 1
    return False

def detect_made_hand(hole_cards, board_cards):
    """7枚（2+5）から実際の役を厳密に判定して、文字列を1要素リストで返す。"""
    all_cards = hole_cards + board_cards

    # ランク/スーツの集計
    ranks = [c.rank for c in all_cards]
    suits = [c.suit for c in all_cards]
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1
    suit_counts = {}
    for s in suits:
        suit_counts[s] = suit_counts.get(s, 0) + 1

    # 値（A=14）一覧
    all_values = [convert_rank_to_value(c.rank) for c in all_cards]

    # --- ストレートフラッシュ ---
    for s, cnt in suit_counts.items():
        if cnt >= 5:
            suited_vals = [convert_rank_to_value(c.rank) for c in all_cards if c.suit == s]
            if _has_straight_from_values(suited_vals):
                return ["straight_flush"]

    # --- フォーカード ---
    if any(c == 4 for c in rank_counts.values()):
        return ["quads"]

    # --- フルハウス（トリップス2種 or トリップス+別ランクのペア） ---
    trips = [r for r, c in rank_counts.items() if c >= 3]
    pairs = [r for r, c in rank_counts.items() if c >= 2]
    if trips and (len(trips) >= 2 or any(r != trips[0] for r in pairs)):
        return ["full_house"]

    # --- フラッシュ ---
    if any(cnt >= 5 for cnt in suit_counts.values()):
        return ["flush"]

    # --- ストレート ---
    if _has_straight_from_values(all_values):
        return ["straight"]

    # --- セット ---
    if any(c >= 3 for c in rank_counts.values()):
        return ["set"]

    # --- ツーペア（ペア以上のランクが2種類以上。上位役は既に除外済み） ---
    if len([r for r, c in rank_counts.items() if c >= 2]) >= 2:
        return ["two_pair"]

    # --- ペア ---
    if any(c >= 2 for c in rank_counts.values()):
        return ["pair"]

    return ["high_card"]
# ===== ここまで：役判定のみ刷新 =====

# （is_straight は使わなくなりましたが、他所で参照していないため残しても動作に影響はありません）
def is_straight(values):
    # 互換のため残置（未使用）。厳密判定は detect_made_hand 内の _has_straight_from_values を使用。
    return _has_straight_from_values(values)

# --- 役に何枚ホールカードが絡んでいるかを判定（そのまま） ---
def count_holecard_involvement(hole_cards, hand_rank, board_cards):
    hc_vals = [convert_rank_to_value(c.rank) for c in hole_cards]
    all_vals = [convert_rank_to_value(c.rank) for c in (hole_cards + board_cards)]
    rank_counts_vals = {}
    for v in all_vals:
        rank_counts_vals[v] = rank_counts_vals.get(v, 0) + 1

    if hand_rank == "pair":
        return sum(rank_counts_vals.get(v, 0) >= 2 for v in hc_vals)
    if hand_rank == "two_pair":
        return sum(rank_counts_vals.get(v, 0) >= 2 for v in hc_vals)
    if hand_rank == "set":
        return sum(rank_counts_vals.get(v, 0) >= 3 for v in hc_vals)
    if hand_rank == "quads":
        return sum(rank_counts_vals.get(v, 0) == 4 for v in hc_vals)
    if hand_rank == "full_house":
        return sum(rank_counts_vals.get(v, 0) >= 2 for v in hc_vals)
    if hand_rank in ["straight", "straight_flush"]:
        uniq = sorted(set(all_vals))
        windows = []
        # Aを1として扱う
        if 14 in uniq:
            uniq_with_wheel = sorted(set(uniq + [1]))
        else:
            uniq_with_wheel = uniq[:]
        # 連続窓を列挙して HC 関与数を見る
        for i in range(len(uniq_with_wheel) - 4):
            if uniq_with_wheel[i+4] - uniq_with_wheel[i] == 4 and len(set(uniq_with_wheel[i:i+5])) == 5:
                windows.append(set(uniq_with_wheel[i:i+5]))
        if windows:
            return max(sum(v in w for v in hc_vals) for w in windows)
        return 0
    if hand_rank in ["flush", "straight_flush"]:
        suits = [c.suit for c in (hole_cards + board_cards)]
        for s in set(suits):
            suited = [convert_rank_to_value(c.rank) for c in (hole_cards + board_cards) if c.suit == s]
            if len(suited) >= 5:
                return sum(c.suit == s for c in hole_cards)
    return 0

def simulate_shift_turn_exhaustive(hand_str, flop_cards, static_winrate, trials_per_turn=1000):
    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(str(c)) for c in flop_cards]
    turn_candidates = generate_turns(flop_cards, hole_cards)

    # フロップ時点の役・特徴を取得
    made_before = detect_made_hand(hole_cards, flop_cards)
    feats_before = classify_flop_turn_pattern(flop_cards, turn=None)

    results = []
    for turn in turn_candidates:
        # --- ターンカードをリスト化（複数対応）---
        if isinstance(turn, list):
            turn_list = [eval7.Card(str(t)) for t in turn]
        else:
            turn_list = [turn]

        board4 = flop_cards + turn_list
        winrate = simulate_vs_random(hole_cards, flop_cards, turn_list, trials_per_turn)
        shift = winrate - static_winrate

        features = []
        made_after = detect_made_hand(hole_cards, board4)

        # --- 役が進化した場合 ---
        if made_after[0] != made_before[0] and made_after[0] != "high_card":
            hc_count = count_holecard_involvement(hole_cards, made_after[0], board4)
            features.append(f"newmade_{made_after[0]}_hc{hc_count}")

        # --- 役が進化しなかった場合：ボード特徴を比較 ---
        else:
            feats_after = classify_flop_turn_pattern(flop_cards, turn_list[-1])
            new_feats = [f for f in feats_after if f not in feats_before]

            # --- newmade_形式で特徴を記録（役が進化しなかった時のみ） ---
            if new_feats:
                for f in new_feats:
                    features.append(f"newmade_{f}")

            # --- Overcard 判定 ---
            for t in turn_list:
                if is_overcard_turn(hole_cards, t):
                    features.append("newmade_overcard")
                    break

        # --- 結果を記録 ---
        results.append({
            'turn_card': ','.join([str(t) for t in turn_list]),
            'winrate': round(winrate, 2),
            'shift': round(shift, 2),
            'features': features if features else ["none"],
            'hand_rank': made_after[0] if made_after else '―'
        })

    # --- 結果をソート・保存 ---
    df = pd.DataFrame(results)
    df_sorted = df.sort_values(by='shift', ascending=False)
    df_sorted.to_csv(f'results_turn_{hand_str}.csv', index=False)

    results_sorted = df_sorted.to_dict(orient='records')
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    return results_sorted, top10, bottom10

def run_shift_turn(hand_str, flop_cards, static_winrate, trials_per_turn=1000):
    return simulate_shift_turn_exhaustive(hand_str, flop_cards, static_winrate, trials_per_turn)
