import streamlit as st
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands

st.set_page_config(page_title="統合版 勝率変動分析アプリ", layout="centered")

st.title("♠ 統合版 勝率変動分析アプリ")

mode = st.sidebar.selectbox("分析モードを選択", ["ShiftFlop", "ShiftTurn", "ShiftRiver"])

st.markdown("## 🎴 自分のハンドを選択")
hand_str = st.selectbox("169通りから選択", all_starting_hands)

if mode == "ShiftFlop":
    st.header("🟦 ShiftFlop：プリフロップ ➜ フロップ 勝率変動")

    flop_type = st.selectbox("フロップタイプを選択", ["high_rainbow", "low_connected", "middle_monotone", "paired", "wet", "dry", "random"])
    trials = st.selectbox("モンテカルロ試行回数", [1000, 5000, 10000])

    if st.button("ShiftFlop を実行"):
        with st.spinner("計算中..."):
            static_wr, feature_shifts = run_shift_flop(hand_str, flop_type, trials)
        st.success(f"プリフロップ勝率: {static_wr:.1f}%")
        st.markdown("### フロップ特徴量ごとの平均勝率変動")
        for feat, delta in feature_shifts.items():
            st.write(f"- {feat} : {delta:.2f}%")

elif mode == "ShiftTurn":
    st.header("🟩 ShiftTurn：フロップ ➜ ターン 勝率変動")

    flop_input = st.text_input("フロップを入力（例: Ah 7d 2c）", "")
    if flop_input:
        flop_cards = flop_input.strip().split()
        if len(flop_cards) != 3:
            st.error("フロップは3枚入力してください")
        else:
            if st.button("ShiftTurn を実行"):
                with st.spinner("計算中..."):
                    top10, bottom10 = run_shift_turn(hand_str, flop_cards)
                st.markdown("### 📈 トップ10")
                for item in top10:
                    st.write(f"{item['turn_card']} | {item['shift']}% | {item['features']}")
                st.markdown("### 📉 ワースト10")
                for item in bottom10:
                    st.write(f"{item['turn_card']} | {item['shift']}% | {item['features']}")

elif mode == "ShiftRiver":
    st.header("🟥 ShiftRiver：ターン ➜ リバー 勝率変動")

    flop_input = st.text_input("フロップを入力（例: Ah 7d 2c）", "")
    turn_input = st.text_input("ターンカードを入力（例: Qs）", "")

    if flop_input and turn_input:
        flop_cards = flop_input.strip().split()
        turn_card = turn_input.strip()
        if len(flop_cards) != 3 or len(turn_card) != 2:
            st.error("正しい形式で入力してください")
        else:
            if st.button("ShiftRiver を実行"):
                with st.spinner("計算中..."):
                    top10, bottom10 = run_shift_river(hand_str, flop_cards, turn_card)
                st.markdown("### 📈 トップ10")
                for item in top10:
                    st.write(f"{item['river_card']} | {item['shift']}% | {item['features']}")
                st.markdown("### 📉 ワースト10")
                for item in bottom10:
                    st.write(f"{item['river_card']} | {item['shift']}% | {item['features']}")
