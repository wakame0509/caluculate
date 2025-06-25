import streamlit as st
import pandas as pd
import random
import eval7
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands
from flop_generator import generate_flops_by_type

st.set_page_config(page_title="統合 勝率変動分析", layout="centered")
st.title("♠ 統合 勝率変動分析アプリ（自動・手動切替＋CSV保存）")

mode = st.radio("モードを選択", ["自動生成モード", "手動選択モード"])
hand_str = st.selectbox("🎴 自分のハンドを選択", all_starting_hands)
trials = st.selectbox("🧪 モンテカルロ試行回数", [1000, 5000, 10000, 100000])

if mode == "自動生成モード":
    flop_type = st.selectbox("🃏 フロップタイプを選択", [
        "high_rainbow", "low_connected", "middle_monotone",
        "paired", "wet", "dry", "random"
    ])
    flop_count = st.selectbox("🃏 使用するフロップの枚数", [5, 10, 20, 30])

    if st.button("ShiftFlop ➜ ShiftTurn ➜ ShiftRiver を一括実行"):
        with st.spinner("フロップ生成中..."):
            flops_str = generate_flops_by_type(flop_type, count=flop_count)

        flop_results, turn_results, river_results = [], [], []

        for idx, flop_cards_str in enumerate(flops_str):
            flop_cards = [eval7.Card(c) for c in flop_cards_str]
            flop_str = ' '.join(flop_cards_str)

            with st.spinner(f"({idx+1}/{len(flops_str)}) フロップ: {flop_str} 処理中..."):
                static_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
                top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, trials)

                if top10_t:
                    random_turn = random.choice(top10_t)["turn_card"]
                    top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, random_turn, trials)
                else:
                    random_turn, top10_r, bottom10_r = "", [], []

                flop_results.append((flop_cards_str, static_wr, shift_feats))
                turn_results.append((flop_cards_str, top10_t, bottom10_t))
                river_results.append((flop_cards_str, random_turn, top10_r, bottom10_r))

        st.session_state["auto_flop"] = flop_results
        st.session_state["auto_turn"] = turn_results
        st.session_state["auto_river"] = river_results
        st.success("自動計算完了 ✅")

elif mode == "手動選択モード":
    flop_input = st.text_input("🃏 フロップ (例: Ah Ks Td)")
    turn_input = st.text_input("🃒 ターンカード（任意）")
    river_input = st.text_input("🃓 リバーカード（任意）")

    try:
        flop_cards_str = flop_input.strip().split()
        if len(flop_cards_str) != 3:
            st.error("フロップは3枚指定してください。例: Ah Ks Td")
        else:
            flop_cards = [eval7.Card(c) for c in flop_cards_str]
            static_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
            top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, trials)

            if turn_input:
                top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, turn_input.strip(), trials)
            else:
                top10_r, bottom10_r = [], []

            st.session_state["manual"] = {
                "flop_cards_str": flop_cards_str,
                "static_wr": static_wr,
                "flop_feats": shift_feats,
                "turn_top": top10_t,
                "turn_bottom": bottom10_t,
                "turn_card": turn_input.strip(),
                "river_top": top10_r,
                "river_bottom": bottom10_r,
            }

            st.success("手動計算完了 ✅")

    except Exception as e:
        st.error(f"入力エラー: {e}")

# CSV保存ボタン
if st.button("📅 CSV保存"):
    csv_rows = []

    for i, (flop_cards_str, static_wr, shift_feats) in enumerate(st.session_state.get("auto_flop", [])):
        flop_str = ' '.join(flop_cards_str)
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

        top10_t = st.session_state["auto_turn"][i][1]
        bottom10_t = st.session_state["auto_turn"][i][2]
        for item in top10_t + bottom10_t:
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

        if i < len(st.session_state["auto_river"]):
            turn_card = st.session_state["auto_river"][i][1]
            top10_r = st.session_state["auto_river"][i][2]
            bottom10_r = st.session_state["auto_river"][i][3]
            for item in top10_r + bottom10_r:
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
    st.download_button("📄 CSVダウンロード", df.to_csv(index=False), "shift_results.csv", "text/csv")
