import eval7
import random
import copy
import time
import pandas as pd

def generate_all_169_hands():
    ranks = 'AKQJT98765432'
    hands = set()
    for r1 in ranks:
        for r2 in ranks:
            if r1 == r2:
                hands.add(r1 + r2)
            elif ranks.index(r1) < ranks.index(r2):
                hands.add(r2 + r1 + 's')
            else:
                hands.add(r1 + r2 + 'o')
    return sorted(hands)

def hand_str_to_cards_precomputed(hand_str):
    rank1, rank2 = hand_str[0], hand_str[1]
    suited = hand_str[2:] == 's'
    offsuit = hand_str[2:] == 'o'
    if suited:
        return [eval7.Card(rank1 + 's'), eval7.Card(rank2 + 's')]
    elif offsuit:
        return [eval7.Card(rank1 + 's'), eval7.Card(rank2 + 'h')]
    else:
        return [eval7.Card(rank1 + 's'), eval7.Card(rank2 + 'h')]

def monte_carlo_winrate_vs_random_optimized(my_hand, iterations):
    wins, ties = 0, 0
    base_deck = eval7.Deck()
    base_deck.cards = [card for card in base_deck.cards if card not in my_hand]

    for _ in range(iterations):
        deck = copy.copy(base_deck.cards)
        random.shuffle(deck)
        opp_hand = deck[:2]
        board = deck[2:7]

        my_score = eval7.evaluate(my_hand + board)
        opp_score = eval7.evaluate(opp_hand + board)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1

    return round((wins + ties / 2) / iterations * 100, 2)

def calculate_preflop_winrates(trials=100000):
    hands = generate_all_169_hands()
    data = []
    start = time.time()

    for i, hand in enumerate(hands, 1):
        my_hand = hand_str_to_cards_precomputed(hand)
        winrate = monte_carlo_winrate_vs_random_optimized(my_hand, trials)
        data.append({"hand": hand, "winrate": winrate})
        print(f"[{i}/169] {hand}: {winrate}%")

    elapsed = round(time.time() - start, 1)
    print(f"\n✅ 完了：全169ハンド（各{trials}回） → {elapsed} 秒")
    return pd.DataFrame(data)

# ✅ Streamlit進捗表示対応版（別関数）
def calculate_preflop_winrates_streamlit(trials=100000, update_func=None):
    hands = generate_all_169_hands()
    data = []
    start = time.time()

    for i, hand in enumerate(hands, 1):
        my_hand = hand_str_to_cards_precomputed(hand)
        winrate = monte_carlo_winrate_vs_random_optimized(my_hand, trials)
        data.append({"hand": hand, "winrate": winrate})
        if update_func:
            update_func(i, hand, winrate)

    return pd.DataFrame(data)

def calculate_all_winrates_montecarlo(trials=100000):
    df = calculate_preflop_winrates(trials)
    filename = f"preflop_winrates_random_{trials}.csv"
    df.to_csv(filename, index=False)
    print(f"💾 保存先: {filename}")

if __name__ == "__main__":
    calculate_all_winrates_montecarlo(trials=100000)
