def extract_features_for_flop(flop: list) -> list:
    suits = [card[1] for card in flop]
    ranks = [card[0] for card in flop]

    features = []
    if len(set(suits)) == 1:
        features.append("flush_possible")
    if len(set(ranks)) < 3:
        features.append("pair_or_set")
    if any(r in ranks for r in ['A', 'K', 'Q']):
        features.append("high_card_present")
    if sorted([ord(r) for r in ranks if isinstance(r, str)])[-1] - sorted([ord(r) for r in ranks if isinstance(r, str)])[0] <= 4:
        features.append("straight_possible")
    return features
