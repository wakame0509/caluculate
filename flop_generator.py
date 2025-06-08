import itertools
import random

ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
suits = ['h', 'd', 'c', 's']

def convert_rank_to_value(rank_char: str) -> int:
    """ランク文字を数値に変換（例: A=14, K=13）"""
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    return rank_map.get(rank_char.upper(), 0)

def generate_all_flops():
    """52枚から3枚の全フロップを生成"""
    deck = [r + s for r in ranks for s in suits]
    return list(itertools.combinations(deck, 3))

def classify_flop(flop):
    """フロップを7つのカテゴリに分類"""
    suits = [card[1] for card in flop]
    ranks_only = [card[0] for card in flop]
    unique_suits = len(set(suits))
    unique_ranks = len(set(ranks_only))
    rank_vals = sorted([convert_rank_to_value(r) for r in ranks_only])
    rank_set = set(rank_vals)

    if unique_suits == 1:
        return "middle_monotone"
    elif unique_ranks < 3:
        return "paired"
    elif max(rank_vals) >= 11 and unique_suits == 3:
        return "high_rainbow"
    elif rank_vals[2] - rank_vals[0] <= 3 and max(rank_vals) <= 9:
        return "low_connected"
    elif unique_suits == 3 and rank_vals[2] - rank_vals[0] >= 6:
        return "dry"
    elif unique_suits <= 2 and any(
        set(range(x, x + 3)).issubset(rank_set) for x in range(2, 12)
    ):
        return "wet"
    else:
        return "random"

def generate_flops_by_type(flop_type, count=10):
    """
    指定したフロップタイプに一致するものから最大 count 個のフロップを返す
    """
    all_flops = generate_all_flops()
    matched = [f for f in all_flops if classify_flop(f) == flop_type]

    if not matched:
        raise ValueError(f"No flops matched type: {flop_type}")

    return random.sample(matched, min(count, len(matched)))
