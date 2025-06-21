import eval7

def extract_features_for_flop(flop: list) -> list:
    """
    フロップから特徴量を抽出する関数。
    入力は eval7.Card のリストまたは str のリストでも可。
    """
    flop = [eval7.Card(c) if isinstance(c, str) else c for c in flop]

    suits = [card.suit for card in flop]
    ranks = [card.rank for card in flop]  # これは int です（2〜14）
    values = sorted(ranks)

    features = []

    # フラッシュ関連
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

    # ストレートドロー
    if values[2] - values[0] <= 4 and len(set(values)) == 3:
        features.append("straight_draw_possible")

    # ハイカード
    if any(v in values for v in [14, 13, 12]):  # A, K, Q
        features.append("high_card_present")

    # ミドルカードボード
    if all(6 <= v <= 10 for v in values):
        features.append("middle_board")

    # ローボード（全て10以下）
    if all(v <= 10 for v in values):
        features.append("low_board")

    # ドライ／ウェット
    if "monoboard" not in features and "2_flush_draw" not in features and "straight_draw_possible" not in features:
        features.append("dry_board")
    else:
        features.append("wet_board")

    return features
