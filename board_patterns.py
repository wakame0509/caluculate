import eval7

# ランク（A〜K）を数値に変換する関数
def convert_rank_to_value(rank):
    rank_order = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    return rank_order.get(rank.upper(), 0)

def classify_flop_turn_pattern(flop, turn, river=None):
    board = flop + [turn]
    if river is not None:
        board.append(river)

    suits = [str(card)[1] for card in board]
    ranks = [card.rank for card in board]
    rank_vals = sorted([convert_rank_to_value(r) for r in ranks])
    unique_vals = sorted(set(rank_vals))

    features = []

    # --- スート系分類 ---
    suit_counts = {s: suits.count(s) for s in set(suits)}
    max_suit_count = max(suit_counts.values())

    if max_suit_count == 5:
        features.append("monotone")
    elif max_suit_count == 4:
        features.append("two_tone")
    else:
        features.append("rainbow")

    if max_suit_count >= 3:
        features.append("three_flush")
    if max_suit_count >= 4:
        features.append("flush_draw")
    if max_suit_count == 5:
        features.append("flush_complete")

    # --- ストレートドロー・完成 ---
    for i in range(2, 11):
        window = set(range(i, i + 5))
        overlap = window.intersection(rank_vals)
        if len(overlap) >= 4:
            features.append("straight_draw")
        if window.issubset(set(rank_vals)):
            features.append("straight_complete")
            break

    # --- 1枚足りない4連ガットショット ---
    for i in range(len(unique_vals) - 3):
        subset = unique_vals[i:i+4]
        if subset[-1] - subset[0] == 4 and len(subset) == 4:
            features.append("gutshot_draw_4")

    # --- 3連番チェック ---
    for i in range(len(unique_vals) - 2):
        if unique_vals[i+1] == unique_vals[i]+1 and unique_vals[i+2] == unique_vals[i]+2:
            features.append("three_straight")
            break

    # --- ボードペア ---
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    if any(count >= 2 for count in rank_counts.values()):
        features.append("paired_board")

    return features
