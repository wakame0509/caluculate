import eval7

def get_169_starting_hands():
    """
    169通りのスターティングハンドを返す。
    例: 'AKs', 'KQo', '77' など。
    """
    ranks = 'AKQJT98765432'
    hands = []
    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i < j:
                hands.append(f"{r1}{r2}s")
                hands.append(f"{r1}{r2}o")
            elif i == j:
                hands.append(f"{r1}{r2}")
    return hands

# ✅ これを追加することで ImportError を回避可能
all_starting_hands = get_169_starting_hands()


def hand_str_to_cards(hand_str):
    """
    'AKs' -> [eval7.Card('As'), eval7.Card('Ks')]
    'QJo' -> [eval7.Card('Qh'), eval7.Card('Jd')]（異スート）
    '99'  -> [eval7.Card('9h'), eval7.Card('9d')]（異スート）
    """
    rank1 = hand_str[0]
    rank2 = hand_str[1]
    suited = len(hand_str) == 3 and hand_str[2] == 's'
    offsuit = len(hand_str) == 3 and hand_str[2] == 'o'

    if rank1 == rank2:
        return [eval7.Card(rank1 + 'h'), eval7.Card(rank2 + 'd')]
    elif suited:
        return [eval7.Card(rank1 + 's'), eval7.Card(rank2 + 's')]
    elif offsuit:
        return [eval7.Card(rank1 + 'h'), eval7.Card(rank2 + 'd')]
    else:
        raise ValueError(f"Invalid hand string: {hand_str}")
