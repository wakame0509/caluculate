import eval7
from turn_generator import convert_rank_to_value

def classify_board_pattern(flop, turn):
    """
    フロップ＋ターンの4枚ボードに対してパターンを分類する。
    主な分類例：
    - flush_draw
    - flush_complete
    - straight_draw
    - straight_complete
    - paired_board
    - monotone
    - two_tone
    - rainbow
    """
    board = flop + [turn]
    suits = [card.suit for card in board]
    ranks = [card.rank for card in board]
    rank_vals = sorted([convert_rank_to_value(r) for r in ranks])

    features = []

    # スート分布による分類
    suit_counts = {s: suits.count(s) for s in set(suits)}
    max_suit_count = max(suit_counts.values())

    if max_suit_count == 4:
        features.append("monotone")
    elif max_suit_count == 3:
        features.append("two_tone")
    else:
        features.append("rainbow")

    # フラッシュ完成 or ドロー
    if max_suit_count >= 4:
        features.append("flush_draw")
        if max_suit_count == 4:
            features.append("flush_complete")

    # ストレート完成 or ドロー
    for i in range(2, 11):
        window = set(range(i, i + 5))
        if len(window.intersection(rank_vals)) >= 4:
            features.append("straight_draw")
        if window.issubset(set(rank_vals)):
            features.append("straight_complete")
            break

    # ボードペア
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    if any(count >= 2 for count in rank_counts.values()):
        features.append("paired_board")

    return features
