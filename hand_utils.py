import eval7

# 169通りの全スターティングハンド
all_starting_hands = [
    f"{r1}{r2}s" if i < j else f"{r2}{r1}o" if i > j else f"{r1}{r2}"
    for i, r1 in enumerate("AKQJT98765432")
    for j, r2 in enumerate("AKQJT98765432")
    if i <= j
]

def convert_hand_to_cards(hand_str):
    """
    'AKs' -> [eval7.Card('As'), eval7.Card('Ks')]
    'QJo' -> [eval7.Card('Qs'), eval7.Card('Jh')]（スートは異なる）
    '99'  -> [eval7.Card('9h'), eval7.Card('9d')]（ペアは異なるスートで）
    """
    rank1 = hand_str[0]
    rank2 = hand_str[1]
    suited = len(hand_str) == 3 and hand_str[2] == 's'
    offsuit = len(hand_str) == 3 and hand_str[2] == 'o'

    if rank1 == rank2:
        # ペア（異なるスート）
        return [eval7.Card(rank1 + 'h'), eval7.Card(rank2 + 'd')]
    elif suited:
        return [eval7.Card(rank1 + 's'), eval7.Card(rank2 + 's')]
    elif offsuit:
        return [eval7.Card(rank1 + 'h'), eval7.Card(rank2 + 'd')]
    else:
        raise ValueError(f"Invalid hand string: {hand_str}")
