import streamlit as st
import pandas as pd
import random
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands
from flop_generator import generate_flops_by_type

st.set_page_config(page_title="統合 勝率変動分析", layout="centered")
st.title("\u2660 \u7d71\u5408 \u52dd\u7387\u5909\u52d5\u5206\u6790\u30a2\u30d7\u30ea（\u81ea\u52d5・\u624b\u52d5\u5207\u66ff\uff0bCSV\u4fdd\u5b58）")

mode = st.radio("\u30e2\u30fc\u30c9\u3092\u9078\u629e", ["\u81ea\u52d5\u751f\u6210\u30e2\u30fc\u30c9", "\u624b\u52d5\u9078\u629e\u30e2\u30fc\u30c9"])
hand_str = st.selectbox("\ud83c\udfb4 \u81ea\u5206\u306e\u30cf\u30f3\u30c9\u3092\u9078\u629e", all_starting_hands)
trials = st.selectbox("\ud83e\uddea \u30e2\u30f3\u30c6\u30ab\u30eb\u30ed\u8a66\u884c\u56de\u6570", [1000, 5000, 10000, 100000])

if mode == "\u81ea\u52d5\u751f\u6210\u30e2\u30fc\u30c9":
    flop_type = st.selectbox("\ud83c\udccf \u30d5\u30ed\u30c3\u30d7\u30bf\u30a4\u30d7\u3092\u9078\u629e", [
        "high_rainbow", "low_connected", "middle_monotone",
        "paired", "wet", "dry", "random"
    ])
    flop_count = st.selectbox("\ud83c\udccf \u4f7f\u7528\u3059\u308b\u30d5\u30ed\u30c3\u30d7\u306e\u679a\u6570", [5, 10, 20, 30])

    if st.button("ShiftFlop \u2794 ShiftTurn \u2794 ShiftRiver \u3092\u4e00\u62ec\u5b9f\u884c"):
        with st.spinner("\u30d5\u30ed\u30c3\u30d7\u751f\u6210\u4e2d..."):
            flops = generate_flops_by_type(flop_type, count=flop_count)

        flop_results, turn_results, river_results = [], [], []

        for idx, flop_cards in enumerate(flops):
            flop_str = ' '.join(flop_cards)
            with st.spinner(f"({idx+1}/{len(flops)}) \u30d5\u30ed\u30c3\u30d7: {flop_str} \u51e6\u7406\u4e2d..."):
                static_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
                top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, trials)

                if top10_t:
                    random_turn = random.choice(top10_t)["turn_card"]
                    top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, random_turn, trials)
                else:
                    random_turn, top10_r, bottom10_r = "", [], []

                flop_results.append((flop_cards, static_wr, shift_feats))
                turn_results.append((flop_cards, top10_t, bottom10_t))
                river_results.append((flop_cards, random_turn, top10_r, bottom10_r))

        st.session_state["auto_flop"] = flop_results
        st.session_state["auto_turn"] = turn_results
        st.session_state["auto_river"] = river_results
        st.success("\u81ea\u52d5\u8a08\u7b97\u5b8c\u4e86 \u2705")

elif mode == "\u624b\u52d5\u9078\u629e\u30e2\u30fc\u30c9":
    flop_input = st.text_input("\ud83c\udccf \u30d5\u30ed\u30c3\u30d7 (\u4f8b: Ah Ks Td)")
    turn_input = st.text_input("\ud83c\udcb2 \u30bf\u30fc\u30f3\u30ab\u30fc\u30c9（\u4efb\u610f）")
    river_input = st.text_input("\ud83c\udcb3 \u30ea\u30d0\u30fc\u30ab\u30fc\u30c9（\u4efb\u610f）")

    try:
        flop_cards = list(flop_input.strip().split())
        if len(flop_cards) != 3:
            st.error("\u30d5\u30ed\u30c3\u30d7\u306f3\u679a\u6307\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002\u4f8b: Ah Ks Td")
        else:
            static_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
            top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, trials)
            if turn_input:
                top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, turn_input, trials)
            else:
                top10_r, bottom10_r = [], []

            st.session_state["manual"] = {
                "flop_cards": flop_cards,
                "static_wr": static_wr,
                "flop_feats": shift_feats,
                "turn_top": top10_t,
                "turn_bottom": bottom10_t,
                "turn_card": turn_input,
                "river_top": top10_r,
                "river_bottom": bottom10_r,
            }

            st.success("\u624b\u52d5\u8a08\u7b97\u5b8c\u4e86 \u2705")

    except Exception as e:
        st.error(f"\u5165\u529b\u30a8\u30e9\u30fc: {e}")

# CSV\u4fdd\u5b58\u6a5f\u80fd
if st.button("\ud83d\udcc5 CSV\u4fdd\u5b58"):
    csv_rows = []

    for i, (flop_cards, static_wr, shift_feats) in enumerate(st.session_state.get("auto_flop", [])):
        flop_str = ' '.join(flop_cards)
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
        flop_str = ' '.join(d["flop_cards"])
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
    st.download_button("\ud83d\udcc4 CSV\u30c0\u30a6\u30f3\u30ed\u30fc\u30c9", df.to_csv(index=False), "shift_results.csv", "text/csv")
