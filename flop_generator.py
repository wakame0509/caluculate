import itertools
import eval7

# ランクとスート定義
RANKS = '23456789TJQKA'
SUITS = 'shdc'

# デッキを全て生成
FULL_DECK = [eval7.Card(rank + suit) for rank in RANKS for suit in SUITS]

def generate_all_flops():
    """デッキから重複なしの全てのフロップ（3枚）を生成"""
    return list(itertools.combinations(FULL_DECK, 3))

def classify_flop(flop):
    """
    フロップを分類して、フロップタイプを返す
    - rainbow_high: バラバラのスート + 高ランクカード含む（A, K, Q）
    - monotone: 同スート3枚
    - paired: 同じランクが含まれる
    - low: すべて低ランク（9以下）
    - connected: ストレートになりやすい（連続または間1枚）
    """
    suits = [card.suit for card in flop]
    ranks = sorted([card.rank for card in flop], key=lambda x: RANKS.index(x))
    rank_vals = [RANKS.index(r) for r in ranks]

    if len(set(suits)) == 1:
        return "monotone"
    elif len(set(card.rank for card in flop)) < 3:
        return "paired"
    elif any(r in ranks for r in ['A', 'K', 'Q']) and len(set(suits)) == 3:
        return "rainbow_high"
    elif all(RANKS.index(r) <= 7 for r in ranks):
        return "low"
    elif max(rank_vals) - min(rank_vals) <= 4:
        return "connected"
    else:
        return "other"

def get_flops_by_type(flop_type):
    """指定されたフロップタイプに一致するフロップをすべて返す"""
    all_flops = generate_all_flops()
    filtered = [flop for flop in all_flops if classify_flop(flop) == flop_type]
    return filtered
