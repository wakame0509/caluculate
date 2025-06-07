def extract_features_for_flop(flop: list) -> list:
    suits = [card[1] for card in flop]
    ranks = [card[0] for card in flop]
    values = sorted([convert_rank_to_value(r) for r in ranks])

    features = []

    # フラッシュ関連（モノボード or 2枚同スート）
    suit_counts = {s: suits.count(s) for s in set(suits)}
    max_suit = max(suit_counts.values())
    if max_suit == 3:
        features.append("monoboard")
    elif max_suit == 2:
        features.append("2_flush_draw")

    # ペア・セット
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    count_values = list(rank_counts.values())
    if 3 in count_values:
        features.append("flop_set")
    elif count_values.count(2) == 1:
        features.append("flop_pair")
    elif count_values.count(2) == 2:
        features.append("two_pair")

    # ストレート関連（3枚連続 or ガットショット）
    if values[2] - values[0] <= 4 and len(set(values)) == 3:
        features.append("straight_draw_possible")

    # ハイカード（A, K, Q）
    if any(r in ranks for r in ['A', 'K', 'Q']):
        features.append("high_card_present")

    # ミドルカードボード
    if all(6 <= v <= 10 for v in values):
        features.append("middle_board")

    # ローボード（全部10以下）
    if all(v <= 10 for v in values):
        features.append("low_board")

    # ボードのドライ／ウェット
    if "monoboard" not in features and "2_flush_draw" not in features and "straight_draw_possible" not in features:
        features.append("dry_board")
    else:
        features.append("wet_board")

    return features


def convert_rank_to_value(rank_char: str) -> int:
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5,
        '6': 6, '7': 7, '8': 8, '9': 9,
        'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    return rank_map.get(rank_char.upper(), 0)
