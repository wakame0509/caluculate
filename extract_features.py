def extract_features_for_flop(flop: list) -> list:
    suits = [card[1] for card in flop]
    ranks = [card[0] for card in flop]

    features = []

    # フラッシュの可能性（スートが全部同じ）
    if len(set(suits)) == 1:
        features.append("flush_possible")

    # ペア・セット・フルハウスの可能性（重複ランク）
    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    if 3 in rank_counts.values():
        features.append("set")
    elif 2 in rank_counts.values():
        features.append("pair")

    # ストレートの可能性（連続ランク）
    rank_values = sorted([convert_rank_to_value(r) for r in ranks])
    if rank_values[-1] - rank_values[0] <= 4 and len(set(rank_values)) == 3:
        features.append("straight_possible")

    # ハイカード出現（A, K, Q）
    if any(r in ranks for r in ['A', 'K', 'Q']):
        features.append("high_card_present")

    return features


def convert_rank_to_value(rank_char: str) -> int:
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    return rank_map.get(rank_char.upper(), 0)
