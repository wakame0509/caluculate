import streamlit as st
import pandas as pd
import random
import eval7
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands, hand_str_to_cards
from flop_generator import generate_flops_by_type
from preflop_winrates_random import get_static_preflop_winrate
from generate_preflop_winrates import calculate_preflop_winrates
from generate_preflop_winrates import calculate_preflop_winrates_streamlit 
st.set_page_config(page_title="統合 勝率変動分析", layout="centered")
st.title("統合 勝率変動分析アプリ（自動・手動切替＋CSV保存）")
mode = st.radio("モードを選択", ["自動生成モード", "手動選択モード", "プリフロップ勝率生成"])
if mode == "プリフロップ勝率生成":
    st.header("プリフロップ勝率生成（ランダム相手）")
    trials_pf = st.selectbox("試行回数", [100000, 200000, 500000, 1000000])
    if st.button("計算開始（CSV保存）"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(i, hand, winrate):
            progress_bar.progress(i / 169)
            status_text.text(f"[{i}/169] {hand}: {winrate:.2f}%")

        with st.spinner(f"{trials_pf:,}回のモンテカルロ計算中..."):
            result_df = calculate_preflop_winrates_streamlit(
                trials=trials_pf,
                update_func=update_progress
            )

        st.success("計算完了 ✅")
        st.download_button("CSVダウンロード", result_df.to_csv(index=False), "preflop_winrates.csv", "text/csv")
    st.stop()
if mode in ["自動生成モード", "手動選択モード"]:
        ALL_HANDS = all_starting_hands 
        hand_str = st.selectbox("自分のハンドを選択してください", ALL_HANDS)
# 自動モード
if mode == "自動生成モード":
    trials = st.selectbox("モンテカルロ試行回数", [1000, 10000, 50000, 100000])
    flop_count = st.selectbox("使用するフロップの枚数", [5, 10, 20, 30])

    if st.button("ShiftFlop → ShiftTurn → ShiftRiver を一括実行"):
        with st.spinner("ランダムフロップ生成中..."):
            deck = [r + s for r in '23456789TJQKA' for s in 'hdcs']
            flops_str = []

            while len(flops_str) < flop_count:
                sample = random.sample(deck, 3)
                if sample not in flops_str:
                    flops_str.append(sample)
        flop_results, turn_results, river_results = [], [], []

        for idx, flop_cards_str in enumerate(flops_str):
            flop_cards = [eval7.Card(c) for c in flop_cards_str]
            flop_str = ' '.join(flop_cards_str)

            with st.spinner(f"({idx+1}/{len(flops_str)}) フロップ: {flop_str} 処理中..."):
                static_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
                all_t, top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, trials)

       # 完全ランダムにターンカードを選び、その1枚でリバー計算を実行
                used_cards = flop_cards_str + [c.__str__() for c in hand_str_to_cards(hand_str)]
                deck = [r + s for r in '23456789TJQKA' for s in 'hdcs']
                remaining = [c for c in deck if c not in used_cards]
                random_turn = random.choice(remaining)
                all_t, top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, random_turn, trials)
                flop_results.append((flop_cards_str, static_wr, shift_feats))
                turn_results.append((flop_cards_str, top10_t, bottom10_t, all_t))
                river_results.append((flop_cards_str, random_turn, top10_r, bottom10_r, all_t))

        st.session_state["auto_flop"] = flop_results
        st.session_state["auto_turn"] = turn_results
        st.session_state["auto_river"] = river_results
        st.success("自動計算完了 ✅")

# 手動モード
elif mode == "手動選択モード":
    trials = st.selectbox("モンテカルロ試行回数", [1000, 10000, 50000, 100000])
    flop_input = st.text_input("フロップ（例: Ah Ks Td）")
    turn_input = st.text_input("ターンカード（任意）")
    river_input = st.text_input("リバーカード（任意）")

    try:
        flop_cards_str = flop_input.strip().split()
        if len(flop_cards_str) != 3:
            st.error("フロップは3枚指定してください（例: Ah Ks Td）")
        else:
            flop_cards = [eval7.Card(c) for c in flop_cards_str]
            static_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
            top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, trials)

            if turn_input:
                turn_card = turn_input.strip()
                top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, turn_card, trials)
            else:
                turn_card, top10_r, bottom10_r = "", [], []

            st.session_state["manual"] = {
                "flop_cards_str": flop_cards_str,
                "static_wr": static_wr,
                "flop_feats": shift_feats,
                "turn_top": top10_t,
                "turn_bottom": bottom10_t,
                "turn_card": turn_card,
                "river_top": top10_r,
                "river_bottom": bottom10_r
            }

            st.success("手動計算完了 ✅")

    except Exception as e:
        st.error(f"入力エラー: {e}")

# 手動モード表示
if "manual" in st.session_state:
    d = st.session_state["manual"]
    flop_str = ' '.join(d["flop_cards_str"])

    st.subheader(f"勝率表示（{hand_str}）")
    st.markdown(f"- プリフロップ勝率: **{get_static_preflop_winrate(hand_str):.1f}%**")
    st.markdown(f"- フロップ勝率（モンテカルロ）: **{d['static_wr']:.1f}%**")

    st.subheader("ShiftTurn：勝率上昇 Top10")
    for item in d["turn_top"]:
        sign = "+" if item["shift"] > 0 else ""
        st.markdown(f"{item['turn_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")

    st.subheader("ShiftTurn：勝率下降 Worst10")
    for item in d["turn_bottom"]:
        sign = "+" if item["shift"] > 0 else ""
        st.markdown(f"{item['turn_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")

    if d["river_top"]:
        st.subheader("ShiftRiver：勝率上昇 Top10")
        for item in d["river_top"]:
            sign = "+" if item["shift"] > 0 else ""
            st.markdown(f"{item['river_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")

    if d["river_bottom"]:
        st.subheader("ShiftRiver：勝率下降 Worst10")
        for item in d["river_bottom"]:
            sign = "+" if item["shift"] > 0 else ""
            st.markdown(f"{item['river_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")

# 自動モード結果表示
if "auto_flop" in st.session_state:
    st.subheader("自動生成モードの結果表示")
    for i, (flop_cards_str, static_wr, shift_feats) in enumerate(st.session_state["auto_flop"]):
        flop_str = ' '.join(flop_cards_str)
        st.markdown(f"【{i+1}】フロップ: **{flop_str}**")
        st.markdown(f"- プリフロップ勝率: **{get_static_preflop_winrate(hand_str):.1f}%**")
        st.markdown(f"- フロップ勝率（モンテカルロ）: **{static_wr:.1f}%**")

        st.markdown("- ShiftFlop 特徴:")
        for f, delta in shift_feats.items():
            st.markdown(f"　・{f}: {round(delta,2)}%")

        top10_t = st.session_state["auto_turn"][i][1]
        bottom10_t = st.session_state["auto_turn"][i][2]
        st.markdown("- ShiftTurn Top10:")
        for item in top10_t:
            sign = "+" if item["shift"] > 0 else ""
            st.markdown(f"　・{item['turn_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")
        st.markdown("- ShiftTurn Worst10:")
        for item in bottom10_t:
            sign = "+" if item["shift"] > 0 else ""
            st.markdown(f"　・{item['turn_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")

        turn_card = st.session_state["auto_river"][i][1]
        top10_r = st.session_state["auto_river"][i][2]
        bottom10_r = st.session_state["auto_river"][i][3]
        if top10_r:
            st.markdown(f"- ShiftRiver Top10（ターン: {turn_card}）:")
            for item in top10_r:
                sign = "+" if item["shift"] > 0 else ""
                st.markdown(f"　・{item['river_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")
        if bottom10_r:
            st.markdown(f"- ShiftRiver Worst10（ターン: {turn_card}）:")
            for item in bottom10_r:
                sign = "+" if item["shift"] > 0 else ""
                st.markdown(f"　・{item['river_card']}：{sign}{item['shift']:.2f}% ({', '.join(item['features'])})")

if st.button("CSV保存"):
    csv_rows = []

    for i, (flop_cards_str, static_wr, shift_feats) in enumerate(st.session_state.get("auto_flop", [])):
        flop_str = ' '.join(flop_cards_str)

        # ShiftFlop
        for f, delta in shift_feats.items():
            csv_rows.append({
                "Stage": "ShiftFlop",
                "Flop": flop_str,
                "Turn": "",
                "Detail": f,
                "Shift": round(delta, 2),
                "Features": "",
                "Role": ""
            })

         # ShiftTurn 全件出力（results_sortedから）
all_turn_items = st.session_state["auto_turn"][i][0]
seen_turn_cards = set()
for item in all_turn_items:
    if item["turn_card"] in seen_turn_cards:
        continue  # 重複回避
    seen_turn_cards.add(item["turn_card"])
    made = next((f for f in item["features"] if f.startswith("made_")), "―").replace("made_", "")
    feats = [f for f in item["features"] if not f.startswith("made_")]
    csv_rows.append({
        "Stage": "ShiftTurn",
        "Flop": flop_str,
        "Turn": "",
        "Detail": item["turn_card"],
        "Shift": round(item["shift"], 2),
        "Features": ', '.join(feats),
        "Role": made
    })

        # ShiftRiver 全件出力
if i < len(st.session_state["auto_river"]):
    turn_card = st.session_state["auto_river"][i][1]
    all_river_items = st.session_state["auto_river"][i][0]  # ← 修正ここ
    seen_river_cards = set()
    for item in all_river_items:
        if item["river_card"] in seen_river_cards:
            continue  # 重複回避
        seen_river_cards.add(item["river_card"])
        made = next((f for f in item["features"] if f.startswith("made_")), "―").replace("made_", "")
        feats = [f for f in item["features"] if not f.startswith("made_")]
        csv_rows.append({
            "Stage": "ShiftRiver",
            "Flop": flop_str,
            "Turn": turn_card,
            "Detail": item["river_card"],
            "Shift": round(item["shift"], 2),
            "Features": ', '.join(feats),
            "Role": made
        })
    # 手動モード（Top10/Bottom10のみ）
    if "manual" in st.session_state:
        d = st.session_state["manual"]
        flop_str = ' '.join(d["flop_cards_str"])

        for f, delta in d["flop_feats"].items():
            csv_rows.append({
                "Stage": "ShiftFlop (Manual)",
                "Flop": flop_str,
                "Turn": "",
                "Detail": f,
                "Shift": round(delta, 2),
                "Features": "",
                "Role": ""
            })

        for item in d["turn_top"] + d["turn_bottom"]:
            made = next((f for f in item["features"] if f.startswith("made_")), "―").replace("made_", "")
            feats = [f for f in item["features"] if not f.startswith("made_")]
            csv_rows.append({
                "Stage": "ShiftTurn (Manual)",
                "Flop": flop_str,
                "Turn": "",
                "Detail": item["turn_card"],
                "Shift": round(item["shift"], 2),
                "Features": ', '.join(feats),
                "Role": made
            })

        for item in d["river_top"] + d["river_bottom"]:
            made = next((f for f in item["features"] if f.startswith("made_")), "―").replace("made_", "")
            feats = [f for f in item["features"] if not f.startswith("made_")]
            csv_rows.append({
                "Stage": "ShiftRiver (Manual)",
                "Flop": flop_str,
                "Turn": d["turn_card"],
                "Detail": item["river_card"],
                "Shift": round(item["shift"], 2),
                "Features": ', '.join(feats),
                "Role": made
            })

    df = pd.DataFrame(csv_rows)
    df.sort_values(by=["Stage", "Flop", "Shift"], ascending=[True, True, False], inplace=True)
    st.download_button("CSVダウンロード", df.to_csv(index=False), "shift_results.csv", "text/csv")
