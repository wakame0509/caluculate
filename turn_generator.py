import eval7

RANKS = '23456789TJQKA'
SUITS = 'shdc'

def generate_turn_cards(flop, used_cards=None):
    """
    指定されたフロップに対して使用可能なターンカード（1枚ずつ）を全て返す。
    used_cards: フロップ＋自分のハンドなど（eval7.Card型）
    """
    if used_cards is None:
        used_cards = set(flop)
    else:
        used_cards = set(flop) | set(used_cards)

    full_deck = [eval7.Card(r + s) for r in RANKS for s in SUITS]
    turn_cards = [card for card in full_deck if card not in used_cards]
    return turn_cards

# 関数名の互換性維持のためのエイリアス
generate_turns_for_flop = generate_turn_cards

def classify_turn_card(flop, turn):
    """
    ターンカードの特徴を返す（リストで複数可能性あり）:
    - flush_complete（フラッシュ完成）
    - straight_complete（ストレート完成）
    - paired_board（ボードペア）
    - overcard（フロップの最高ランクより高いカード）
    """
    features = []
    suits = [card.suit for card in flop + [turn]]
    ranks = [card.rank for card in flop + [turn]]
    rank_vals = sorted([convert_rank_to_value(r) for r in ranks])

    # フラッシュ完成
    for suit in 'shdc':
        if suits.count(suit) >= 4:
            features.append("flush_complete")
            break

    # ストレート完成
    for i in range(2, 11):
        seq = set(range(i, i + 5))
        if seq.issubset(set(rank_vals)):
            features.append("straight_complete")
            break

    # ボードペア
    rank_counts = {r: ranks.count(r) for r in ranks}
    if any(count >= 2 for count in rank_counts.values()):
        features.append("paired_board")

    # オーバーカード
    flop_ranks = [convert_rank_to_value(c.rank) for c in flop]
    if convert_rank_to_value(turn.rank) > max(flop_ranks):
        features.append("overcard")

    return features

def convert_rank_to_value(rank_char: str) -> int:
    """ランク文字を数値に変換（例: A=14, K=13）"""
    rank_map = {
        '2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
        '7': 7, '8': 8, '9': 9, 'T': 10,
        'J': 11, 'Q': 12, 'K': 13, 'A': 14
    }
    return rank_map.get(rank_char.upper(), 0)
