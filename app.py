import streamlit as st
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands
from flop_generator import generate_flops_by_type

st.set_page_config(page_title="統合版 勝率変動分析アプリ", layout="centered")
st.title("♠ 統合版 勝率変動分析アプリ（フロップ→ターン→リバー自動）")

hand_str = st.selectbox("🎴 自分のハンドを選択", all_starting_hands)
flop_type = st.selectbox("🃏 フロップタイプを選択", [
    "high_rainbow", "low_connected", "middle_monotone",
    "paired", "wet", "dry", "random"
])
trials = st.selectbox("🧪 モンテカルロ試行回数", [1000, 5000, 10000])

if st.button("ShiftFlop ➜ ShiftTurn ➜ ShiftRiver を一括実行"):
    with st.spinner("フロップ生成中..."):
        flops = generate_flops_by_type(flop_type, count=20)

    shiftflop_results = []
    shifturn_results = []
    shiftriver_results = []

    for flop_cards in flops:
        with st.spinner(f"フロップ: {' '.join(flop_cards)} 処理中..."):
            static_wr, feature_shifts = run_shift_flop(hand_str, flop_cards, trials)
            shiftflop_results.append((flop_cards, static_wr, feature_shifts))

            top10_turn, bottom10_turn = run_shift_turn(hand_str, flop_cards)
            shifturn_results.append((flop_cards, top10_turn, bottom10_turn))

            for turn_entry in top10_turn[:1]:
                turn_card = turn_entry["turn_card"]
                top10_river, bottom10_river = run_shift_river(hand_str, flop_cards, turn_card)
                shiftriver_results.append((flop_cards, turn_card, top10_river, bottom10_river))

    st.success("計算完了 ✅")

    for i, (flop_cards, static_wr, feature_shifts) in enumerate(shiftflop_results):
        st.markdown(f"## フロップ{i+1}: {' '.join(flop_cards)}")
        st.markdown(f"- プリフロップ勝率: {static_wr:.1f}%")
        st.markdown("### 📘 フロップ特徴量ごとの平均勝率変動")
        for feat, delta in feature_shifts.items():
            st.write(f"  - {feat}: {delta:.2f}%")

        top10_turn = shifturn_results[i][1]
        bottom10_turn = shifturn_results[i][2]
        st.markdown("### 🟢 ShiftTurn: トップ10")
        for item in top10_turn:
            st.write(f"  {item['turn_card']} | {item['shift']}% | {item['features']}")
        st.markdown("### 🔴 ShiftTurn: ワースト10")
        for item in bottom10_turn:
            st.write(f"  {item['turn_card']} | {item['shift']}% | {item['features']}")

        if i < len(shiftriver_results):
            _, turn_card, top10_river, bottom10_river = shiftriver_results[i]
            st.markdown(f"### 🟣 ShiftRiver（ターン: {turn_card}）: トップ10")
            for item in top10_river:
                st.write(f"  {item['river_card']} | {item['shift']}% | {item['features']}")
            st.markdown("### 🟠 ShiftRiver: ワースト10")
            for item in bottom10_river:
                st.write(f"  {item['river_card']} | {item['shift']}% | {item['features']}")
