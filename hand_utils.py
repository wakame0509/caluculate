import eval7

# 169通りの全スターティングハンド
def get_169_starting_hands():
    ranks = "AKQJT98765432"
    hands = []

    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i < j:
                hands.append(f"{r1}{r2}s")  # スーテッド
            elif i > j:
                hands.append(f"{r2}{r1}o")  # オフスート
            else:
                hands.append(f"{r1}{r2}")   # ペア
    return hands


def convert_hand_to_cards(hand_str):
    """
    文字列から eval7.Card オブジェクトのリストに変換する

    例:
    'AKs' -> [eval7.Card('As'), eval7.Card('Ks')]
    'QJo' -> [eval7.Card('Qs'), eval7.Card('Jh')]
    '99'  -> [eval7.Card('9h'), eval7.Card('9d')]
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
