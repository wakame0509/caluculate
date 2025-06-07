import streamlit as st
from hand_utils import all_starting_hands
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river

st.title("♠️ 統合版 勝率変動分析アプリ")

st.sidebar.header("設定")
mode = st.sidebar.selectbox("分析ステージを選択", ["ShiftFlop", "ShiftTurn", "ShiftRiver"])
hand = st.sidebar.selectbox("自分のハンドを選択", all_starting_hands)
flop_type = st.sidebar.selectbox("フロップタイプ", ["High Card Rainbow", "Low Card Dry", "Paired Board", "Monotone", "Connected", "Two Tone", "Mixed"])
num_flops = st.sidebar.selectbox("使用するフロップ数", [10, 20, 30])
num_trials = st.sidebar.selectbox("モンテカルロ試行回数", [1000, 10000, 50000, 100000])

if mode == "ShiftFlop":
    st.header("🃏 ShiftFlop：プリフロップ → フロップ 勝率変動")
    if st.button("ShiftFlop を実行"):
        run_shift_flop(hand, flop_type, num_trials)

elif mode == "ShiftTurn":
    st.header("🂱 ShiftTurn：フロップ → ターン 勝率変動")
    if st.button("ShiftTurn を実行"):
        run_shift_turn(hand, flop_type, num_flops)

elif mode == "ShiftRiver":
    st.header("🂡 ShiftRiver：ターン → リバー 勝率変動")
    if st.button("ShiftRiver を実行"):
        run_shift_river(hand, flop_type, num_flops)
