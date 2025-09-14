import eval7
from turn_generator import convert_rank_to_value

def classify_flop_turn_pattern(flop, turn, river=None):
    board = flop + [turn]
    if river is not None:
        board.append(river)

    if any(card is None for card in board):
        return []

    suits = [str(card)[1] for card in board]
    ranks = [str(card)[0] for card in board]
    rank_vals = sorted([convert_rank_to_value(r) for r in ranks])
    rank_set = set(rank_vals)
    unique_vals = sorted(rank_set)

    features = []

    # --- スート系 ---
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
    # flush_complete は削除

    # --- ストレートドロー（4連番のみ） ---
    for i in range(len(unique_vals) - 3):
        subset = unique_vals[i:i+4]
        if subset[-1] - subset[0] == 3:  # 4連番
            features.append("straight_draw")

    # --- ガットショット4枚 ---
    for i in range(len(unique_vals) - 3):
        subset = unique_vals[i:i+4]
        if subset[-1] - subset[0] == 4:
            features.append("gutshot_draw_4")

    # --- 3連番チェック ---
    for i in range(len(unique_vals) - 2):
        if unique_vals[i+1] == unique_vals[i]+1 and unique_vals[i+2] == unique_vals[i]+2:
            features.append("three_straight")
            break

    return features  # ペアボード判定は完全削除
