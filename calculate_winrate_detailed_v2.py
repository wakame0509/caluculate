import eval7
import random
from extract_features import extract_features_for_flop, extract_features_for_turn, extract_features_for_river
from preflop_winrate_dict import get_static_preflop_winrate
from hand_utils import detect_made_hand  # ★ 追加

def calculate_equity(hero, board, opp_hands, iters=1000):
    hero_wins = 0
    for _ in range(iters):
        deck = eval7.Deck()
        used = hero + board
        for card in used:
            deck.cards.remove(card)
        opp_hand = random.choice(opp_hands)
        for card in opp_hand:
            deck.cards.remove(card)
        remaining = 5 - len(board)
        board_sample = list(board)
        board_sample += deck.sample(remaining)
        hero_score = eval7.evaluate(hero + board_sample)
        opp_score = eval7.evaluate(opp_hand + board_sample)
        if hero_score > opp_score:
            hero_wins += 1
        elif hero_score == opp_score:
            hero_wins += 0.5
    return hero_wins / iters * 100

def simulate_shift_flop(hand_str, flop_list, opp_hands, iters=1000):
    hero = [eval7.Card(hand_str[0:2]), eval7.Card(hand_str[2:4])]
    preflop = get_static_preflop_winrate(hand_str)
    total_shift = 0
    features_count = {}
    for flop in flop_list:
        flop_cards = [eval7.Card(c) for c in flop]
        equity = calculate_equity(hero, flop_cards, opp_hands, iters)
        shift = equity - preflop
        total_shift += shift
        features = extract_features_for_flop(flop)
        for feat in features:
            features_count[feat] = features_count.get(feat, []) + [shift]
    avg_shift = total_shift / len(flop_list)
    avg_features = {feat: sum(vals)/len(vals) for feat, vals in features_count.items()}
    return avg_shift, avg_features

def simulate_shift_turn_with_ranking(hand_str, flop_list, opp_hands, iters=1000):
    hero = [eval7.Card(hand_str[0:2]), eval7.Card(hand_str[2:4])]
    total_shift = 0
    all_turns = []
    for flop in flop_list:
        flop_cards = [eval7.Card(c) for c in flop]
        deck = eval7.Deck()
        used = hero + flop_cards
        for card in used:
            deck.cards.remove(card)
        turn_shifts = []
        for turn in deck:
            board = flop_cards + [turn]
            equity = calculate_equity(hero, board, opp_hands, iters)
            shift = equity - calculate_equity(hero, flop_cards, opp_hands, iters)
            features = extract_features_for_turn(board)
            turn_shifts.append((str(turn), shift, features))
        all_turns += turn_shifts
    all_turns.sort(key=lambda x: x[1], reverse=True)
    top10 = all_turns[:10]
    worst10 = all_turns[-10:]
    avg_total = sum([s[1] for s in all_turns]) / len(all_turns)
    return avg_total, top10, worst10

def simulate_shift_river_with_ranking(hand_str, flop_list, opp_hands, iters=1000):
    hero = [eval7.Card(hand_str[0:2]), eval7.Card(hand_str[2:4])]
    total_shift = 0
    all_rivers = []
    for flop in flop_list:
        flop_cards = [eval7.Card(c) for c in flop]
        deck = eval7.Deck()
        used = hero + flop_cards
        for card in used:
            deck.cards.remove(card)
        turn = random.choice(deck)
        used.append(turn)
        for card in used:
            deck.cards.remove(card)
        for river in deck:
            board = flop_cards + [turn, river]
            equity = calculate_equity(hero, board, opp_hands, iters)
            shift = equity - calculate_equity(hero, flop_cards + [turn], opp_hands, iters)
            features = extract_features_for_river(board)
            made_hand = detect_made_hand(hero, board)  # ★ 役を検出
            all_rivers.append((str(river), shift, features, made_hand[0]))  # ★ 役も追加
    all_rivers.sort(key=lambda x: x[1], reverse=True)
    top10 = all_rivers[:10]
    worst10 = all_rivers[-10:]
    avg_total = sum([s[1] for s in all_rivers]) / len(all_rivers)
    return avg_total, top10, worst10
