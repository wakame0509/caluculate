import eval7
import pandas as pd
from board_patterns import classify_flop_turn_pattern
from hand_utils import hand_str_to_cards

def convert_rank_to_value(rank):
    rank_dict = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6,
                 '7': 7, '8': 8, '9': 9, 'T': 10,
                 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    if isinstance(rank, int):
        return rank
    return rank_dict[str(rank)]

def simulate_shift_turn_exhaustive(hand_str, flop_cards, trials_per_turn=20):
    hole_cards = [eval7.Card(str(c)) for c in hand_str_to_cards(hand_str)]
    flop_cards = [eval7.Card(str(c)) for c in flop_cards]

    static_winrate = simulate_vs_random(hole_cards, flop_cards, [], trials_per_turn)
    turn_candidates = generate_turns(flop_cards, hole_cards)

    results = []
    for turn in turn_candidates:
        board4 = flop_cards + [turn]
        winrate = simulate_vs_random(hole_cards, flop_cards, [turn], trials_per_turn)
        shift = winrate - static_winrate
        features = classify_flop_turn_pattern(flop_cards, turn)
        made_hand = detect_made_hand(hole_cards, board4)
        features.append(f"made_{made_hand[0]}" if made_hand else "made_―")

        # Overcard 判定
        if detect_overcard(hole_cards, board4):
            features.append("overcard")

        results.append({
            'turn_card': str(turn),
            'winrate': round(winrate, 2),
            'shift': round(shift, 2),
            'features': features
        })

    df = pd.DataFrame(results)
    df_sorted = df.sort_values(by='shift', ascending=False)
    df_sorted.to_csv(f'results_turn_{hand_str}.csv', index=False)

    results_sorted = df_sorted.to_dict(orient='records')
    top10 = results_sorted[:10]
    bottom10 = results_sorted[-10:]
    results_sorted = df_sorted.to_dict(orient='records')
top10 = results_sorted[:10]
bottom10 = results_sorted[-10:]

# ✅ ここを修正
    return results_sorted, top10, bottom10

def generate_turns(flop, hole_cards):
    used_ids = set(str(c) for c in flop + hole_cards)
    deck = eval7.Deck()
    return [card for card in deck.cards if str(card) not in used_ids]

def simulate_vs_random(my_hand, flop_cards, turn_cards, iterations=20):
    my_hand = [eval7.Card(str(c)) for c in my_hand]
    flop_cards = [eval7.Card(str(c)) for c in flop_cards]
    turn_cards = [eval7.Card(str(c)) for c in turn_cards]

    used_ids = set(str(c) for c in my_hand + flop_cards + turn_cards)

    wins = ties = total = 0

    for _ in range(iterations):
        deck = eval7.Deck()
        deck.cards = [c for c in deck.cards if str(c) not in used_ids]
        deck.shuffle()
        opp_hand = deck.sample(2)

        my_score = eval7.evaluate(my_hand + flop_cards + turn_cards)
        opp_score = eval7.evaluate(opp_hand + flop_cards + turn_cards)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1
        total += 1

    return (wins + ties / 2) / total * 100

def detect_made_hand(hole_cards, board_cards):
    all_cards = hole_cards + board_cards
    ranks = [card.rank for card in all_cards]
    suits = [card.suit for card in all_cards]
    values = sorted([convert_rank_to_value(card.rank) for card in all_cards], reverse=True)

    rank_counts = {r: ranks.count(r) for r in set(ranks)}
    suit_counts = {s: suits.count(s) for s in set(suits)}
    counts = list(rank_counts.values())

    for suit in suit_counts:
        suited_cards = [card for card in all_cards if card.suit == suit]
        suited_values = sorted(set(convert_rank_to_value(card.rank) for card in suited_cards), reverse=True)
        if is_straight(suited_values):
            return ["straight_flush"]
    if 4 in counts:
        return ["quads"]
    if 3 in counts and 2 in counts:
        return ["full_house"]
    if max(suit_counts.values()) >= 5:
        return ["flush"]
    if is_straight(values):
        return ["straight"]
    if 3 in counts:
        return ["set"]
    if counts.count(2) >= 2:
        return ["two_pair"]
    if 2 in counts:
        return ["pair"]
    return ["high_card"]

def is_straight(values):
    unique_values = sorted(set(values), reverse=True)
    for i in range(len(unique_values) - 4):
        window = unique_values[i:i+5]
        if window[0] - window[4] == 4:
            return True
    if set([14, 2, 3, 4, 5]).issubset(set(values)):
        return True
    return False

def detect_overcard(hole_cards, board_cards):
    values = [convert_rank_to_value(c.rank) for c in hole_cards]
    board_values = [convert_rank_to_value(c.rank) for c in board_cards]
    if values[0] == values[1]:  # ペア
        pair_rank = values[0]
        return any(v > pair_rank for v in board_values)
    return False

def run_shift_turn(hand_str, flop_cards, trials_per_turn=20):
    return simulate_shift_turn_exhaustive(hand_str, flop_cards, trials_per_turn)
