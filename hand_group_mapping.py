def classify_hand_group(hand_str):
    """
    与えられたスターティングハンドを12の代表的なグループに分類する。
    """
    pairs = ['AA', 'KK', 'QQ', 'JJ', 'TT', '99', '88', '77', '66', '55', '44', '33', '22']
    broadways = ['A', 'K', 'Q', 'J', 'T']
    suited = hand_str.endswith('s')
    offsuit = hand_str.endswith('o')
    ranks = hand_str[:2]

    rank1 = ranks[0]
    rank2 = ranks[1]
    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                   '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11,
                   'Q': 12, 'K': 13, 'A': 14}

    r1_val = rank_values[rank1]
    r2_val = rank_values[rank2]
    gap = abs(r1_val - r2_val)

    if ranks == 'AA':
        return "High Pair"
    elif hand_str in ['KK', 'QQ', 'JJ']:
        return "High Pair"
    elif hand_str in ['TT', '99']:
        return "Middle Pair"
    elif hand_str in ['88', '77', '66', '55', '44', '33', '22']:
        return "Low Pair"
    elif suited and rank1 == 'A' and r2_val <= 9:
        return "Suited Ace-x"
    elif suited and rank1 in broadways and rank2 in broadways:
        return "Broadway Suited"
    elif offsuit and rank1 in broadways and rank2 in broadways:
        return "Broadway Offsuit"
    elif suited and gap == 1 and r1_val < 12:
        return "Suited Connectors"
    elif offsuit and gap == 1 and r1_val < 12:
        return "Offsuit Connectors"
    elif suited and gap == 2 and r1_val < 11:
        return "Suited One-Gappers"
    elif suited:
        return "Other Suited"
    else:
        return "Other Offsuit"

def generate_all_169_hands():
    """
    169通りのスターティングハンドを生成（スーテッド・オフスート・ペア）
    """
    ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
    hands = []
    for i in range(len(ranks)):
        for j in range(len(ranks)):
            if i < j:
                hands.append(ranks[i] + ranks[j] + 's')
                hands.append(ranks[i] + ranks[j] + 'o')
            elif i == j:
                hands.append(ranks[i] + ranks[j])
    return hands

# 実行してマッピングを辞書として得る
hand_group_dict = {}
for hand in generate_all_169_hands():
    hand_group_dict[hand] = classify_hand_group(hand)

# 必要に応じて出力確認
if __name__ == "__main__":
    import pprint
    pprint.pprint(hand_group_dict)
