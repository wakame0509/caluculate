import eval7
import csv
import time

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

def hand_str_to_cards(hand_str):
    rank1, rank2 = hand_str[0], hand_str[1]
    suited = hand_str[2:] == 's'
    suits = ['s', 'h', 'd', 'c']
    if suited:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[0])]
    elif 'o' in hand_str:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[1])]
    else:
        return [eval7.Card(rank1 + suits[0]), eval7.Card(rank2 + suits[1])]

def monte_carlo_winrate_vs_random(hand_str, iterations):
    wins, ties, total = 0, 0, 0
    my_hand = hand_str_to_cards(hand_str)

    for _ in range(iterations):
        deck = eval7.Deck()
        for card in my_hand:
            deck.cards.remove(card)

        opp_hand = deck.sample(2)
        for card in opp_hand:
            deck.cards.remove(card)

        board = deck.sample(5)

        my_score = eval7.evaluate(my_hand + board)
        opp_score = eval7.evaluate(opp_hand + board)

        if my_score > opp_score:
            wins += 1
        elif my_score == opp_score:
            ties += 1
        total += 1

    return round((wins + ties / 2) / total * 100, 2)

def calculate_all_winrates_montecarlo(trials=100000):
    hands = generate_all_169_hands()
    results = []
    start_time = time.time()

    for hand in hands:
        winrate = monte_carlo_winrate_vs_random(hand, trials)
        results.append({'hand': hand, 'winrate': winrate})

    elapsed = time.time() - start_time
    filename = f"preflop_winrates_random_{trials}.csv"
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["hand", "winrate"])
        writer.writeheader()
        writer.writerows(results)

    print(f"Completed in {round(elapsed, 2)} seconds")
    print(f"Saved to {filename}")

# 試行回数をここで指定
if __name__ == "__main__":
    calculate_all_winrates_montecarlo(trials=100000)
