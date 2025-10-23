import eval7
import random
import pandas as pd
import itertools
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
    """フロップ＋ホールカード以外からターン候補を生成"""
    used_str = {str(c) for c in flop_cards + hole_cards}
    deck = [c for c in eval7.Deck() if str(c) not in used_str]
    if n_turns is None or n_turns >= len(deck):
        return deck
    random.shuffle(deck)
    return deck[:n_turns]

def generate_rivers(board4, hole_cards):
    """ターン＋フロップ＋ホールカード以外からリバー候補を生成"""
    used_str = {str(c) for c in board4 + hole_cards}
    return [c for c in eval7.Deck() if str(c) not in used_str]

# -----------------------------
# Monte Carlo Simulation
# -----------------------------
def simulate_vs_random(my_hand, board_full, iterations=1000):
    """指定ボードでの自分の勝率をモンテカルロで算出"""
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

# -----------------------------
# Hand Detection
# -----------------------------
def detect_made_hand(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    ranks = [c.rank for c in all_cards]
    suits = [c.suit for c in all_cards]
    values = sorted([convert_rank_to_value(c.rank) for c in all_cards], reverse=True)
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    suit_counts = {s: suits.count(s) for s in set(suits)}
    counts = list(rank_counts.values())

    for suit in suit_counts:
        suited_cards = [c for c in all_cards if c.suit == suit]
        suited_values = sorted(set(convert_rank_to_value(c.rank) for c in suited_cards), reverse=True)
        if is_straight(suited_values):
            return ["straight_flush"]

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

def count_holecards_in_made_hand(hole_cards, board_cards, hand_name):
    """完成役にホールカードが何枚関与しているかを数える"""
    all_cards = hole_cards + board_cards
    ranks = [c.rank for c in all_cards]
    rank_counts = {r: ranks.count(r) for r in set(ranks)}

    if hand_name in ["pair", "two_pair", "set", "full_house", "quads"]:
        hole_ranks = [c.rank for c in hole_cards]
        count = sum(min(rank_counts[r], hole_ranks.count(r)) for r in hole_ranks)
        return min(count, 2)
    elif hand_name in ["straight", "straight_flush"]:
        values = sorted(set([convert_rank_to_value(c.rank) for c in all_cards]))
        hole_values = set(convert_rank_to_value(c.rank) for c in hole_cards)
        for i in range(len(values) - 4):
            window = set(values[i:i + 5])
            cnt = len(hole_values.intersection(window))
            if cnt > 0:
                return min(cnt, 2)
        wheel = {14, 2, 3, 4, 5}
        cnt = len(hole_values.intersection(wheel)) if wheel.issubset(set(values)) else 0
        return min(cnt, 2)
    elif hand_name == "flush":
        suit_groups = {}
        for c in all_cards:
            suit_groups.setdefault(c.suit, []).append(c)
        flush_suit = None
        for s, clist in suit_groups.items():
            if len(clist) >= 5:
                flush_suit = s
                break
        if flush_suit:
            cnt = sum(1 for c in hole_cards if c.suit == flush_suit)
            return min(cnt, 2)
        return 0
    return 0

# -----------------------------
# Helper functions
# -----------------------------
def is_overcard_river(hole_cards, river_card):
    """リバーでペアハンドを上回るカードが出たかを判定"""
    if hole_cards[0].rank != hole_cards[1].rank:
        return False
    pair_rank = convert_rank_to_value(hole_cards[0].rank)
    river_rank = convert_rank_to_value(river_card.rank)
    return river_rank > pair_rank

def is_straight(values):
    unique_values = sorted(set(values), reverse=True)
    for i in range(len(unique_values) - 4):
        if unique_values[i] - unique_values[i + 4] == 4:
            return True
    if {14, 2, 3, 4, 5}.issubset(set(values)):
        return True
    return False

# -----------------------------
# Main simulation
# -----------------------------
def simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate, turn_count=1, trials_per_river=1000):
    """複数ターン × 全リバー の勝率変動を計算して保存"""
    try:
        static_turn_winrate = float(static_turn_winrate)
    except:
        static_turn_winrate = 0.0

    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(c) if isinstance(c, str) else c for c in flop_cards_str]
    turn_candidates = generate_turns(flop_cards, hole_cards, n_turns=turn_count)
    all_results = []

    # --- 各ターンごとにリバー全探索 ---
    import itertools

# --- 追加ヘルパー：相手ハンドを全列挙して正確な勝率を計算 ---
def enumerate_vs_all(my_hand, board_full):
    """
    my_hand: list of eval7.Card (自分のホール2枚)
    board_full: list of eval7.Card (フロップ+ターン+リバー の5枚固定)
    return: winrate% (float)
    """
    used_str = {str(c) for c in my_hand + board_full}
    # 残りデッキ（Card オブジェクトのリスト）
    remaining = [c for c in eval7.Deck() if str(c) not in used_str]

    wins = ties = 0
    total = 0

    # 全組合せで相手ハンドを列挙
    for opp_pair in itertools.combinations(remaining, 2):
        total += 1
        opp_hand = list(opp_pair)
        my_score = eval7.evaluate(my_hand + board_full)
        opp_score = eval7.evaluate(opp_hand + board_full)
        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    if total == 0:
        return 0.0
    return (wins + ties / 2) / total * 100.0

# --- 修正版メイン関数（リバーは全列挙で評価） ---
def simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate, turn_count=1, trials_per_river=1000):
    """
    役の命名（hc付け）や出力形式は既存と同じに保つ。
    この関数では各指定ターンに対してリバー全通り（ターン+フロップ+ホールを除いた残り）を列挙して、
    相手ハンドを全組合せで評価してリバ―勝率を求めます（モンテカルロは使いません）。
    """
    # --- 型統一 ---
    try:
        static_turn_winrate = float(static_turn_winrate)
    except:
        static_turn_winrate = 0.0

    hole_cards = hand_str_to_cards(hand_str)
    flop_cards = [eval7.Card(c) if isinstance(c, str) else c for c in flop_cards_str]
    turn_candidates = generate_turns(flop_cards, hole_cards, n_turns=turn_count)
    all_results = []

    # 各ターンごとにリバー全探索（リバーは相手ハンド全列挙で評価）
    for turn_card in turn_candidates:
        board4 = flop_cards + [turn_card]
        feats_before = classify_flop_turn_pattern(flop_cards, turn_card)
        made_before = detect_made_hand(hole_cards, board4)
        river_candidates = generate_rivers(board4, hole_cards)

        for river in river_candidates:
            full_board = board4 + [river]

            # ← ここをモンテカルロではなく全列挙で正確に評価
            river_winrate = enumerate_vs_all(hole_cards, full_board)

            # shift はフロップ基準との差にするなら static_turn_winrate との差分
            # （ご希望に合わせてターン基準 or フロップ基準に変更可能）
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
    return simulate_shift_river_multiple_turns(hand_str, flop_cards_str, static_turn_winrate, turn_count, trials_per_river)
