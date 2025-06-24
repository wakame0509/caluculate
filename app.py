import streamlit as st
import pandas as pd
import random
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands, hand_str_to_cards
from flop_generator import generate_flops_by_type
import eval7

st.set_page_config(page_title="統合版 勝率変動分析アプリ", layout="centered")
st.title("♠ 統合版 勝率変動分析アプリ（フロップ→ターン→リバー自動／手動切替）")

mode = st.radio("モードを選択", ["自動生成モード", "手動選択モード"])

hand_str = st.selectbox("🎴 自分のハンドを選択", all_starting_hands)
trials = st.selectbox("🧪 モンテカルロ試行回数", [1000, 5000 , 10000, 100000])

if mode == "自動生成モード":
    flop_type = st.selectbox("🃏 フロップタイプを選択", [
        "high_rainbow", "low_connected", "middle_monotone",
        "paired", "wet", "dry", "random"
    ])
    flop_count = st.selectbox("🃏 使用するフロップの枚数", [5, 10, 20, 30])

    if "shiftflop_results" not in st.session_state:
        st.session_state["shiftflop_results"] = []
        st.session_state["shiftturn_results"] = []
        st.session_state["shiftriver_results"] = []

    if st.button("ShiftFlop ➜ ShiftTurn ➜ ShiftRiver を一括実行"):
        with st.spinner("フロップ生成中..."):
            flops = generate_flops_by_type(flop_type, count=flop_count)

        shiftflop_results = []
        shiftturn_results = []
        shiftriver_results = []

        for idx, flop_cards in enumerate(flops):
            flop_list = list(flop_cards)
            flop_str = ' '.join(flop_list)
            with st.spinner(f"({idx+1}/{len(flops)}) フロップ: {flop_str} 処理中..."):
                static_wr, feature_shifts = run_shift_flop(hand_str, flop_list, trials)
                shiftflop_results.append((flop_list, static_wr, feature_shifts))

                top10_turn, bottom10_turn = run_shift_turn(hand_str, flop_list, trials)
                shiftturn_results.append((flop_list, top10_turn, bottom10_turn))

                if top10_turn:
                    random_turn = random.choice(top10_turn)["turn_card"]
                    top10_river, bottom10_river = run_shift_river(hand_str, flop_list, random_turn, trials)
                    shiftriver_results.append((flop_list, random_turn, top10_river, bottom10_river))

        st.session_state["shiftflop_results"] = shiftflop_results
        st.session_state["shiftturn_results"] = shiftturn_results
        st.session_state["shiftriver_results"] = shiftriver_results
        st.success("計算完了 ✅")

elif mode == "手動選択モード":
    flop_input = st.text_input("🃏 フロップをスペース区切りで入力 (例: Ah Ks Td)")
    turn_input = st.text_input("🃒 ターンカード（任意、1枚だけ）")
    river_input = st.text_input("🃓 リバーカード（任意、1枚だけ）")

    try:
        flop_cards = flop_input.strip().split()
        if len(flop_cards) != 3:
            st.error("フロップは3枚入力してください。例: Ah Ks Td")
        else:
            with st.spinner("ShiftFlop計算中..."):
                static_wr, feature_shifts = run_shift_flop(hand_str, flop_cards, trials)
                st.markdown("### 📘 フロップ特徴量ごとの平均勝率変動")
                for feat, delta in sorted(feature_shifts.items(), key=lambda x: abs(x[1]), reverse=True):
                    st.write(f"  - {feat}: {delta:.2f}%")

            with st.spinner("ShiftTurn計算中..."):
                top10_turn, bottom10_turn = run_shift_turn(hand_str, flop_cards, trials)
                st.markdown("### 🟢 ShiftTurn: トップ10")
                for item in top10_turn:
                    made = next((f for f in item['features'] if f.startswith("made_")), "made_―").replace("made_", "")
                    feats = [f for f in item['features'] if not f.startswith("made_")]
                    st.write(f"  {item['turn_card']} | {item['shift']:.2f}% | {feats} | 役: {made}")

                st.markdown("### 🔴 ShiftTurn: ワースト10")
                for item in bottom10_turn:
                    made = next((f for f in item['features'] if f.startswith("made_")), "made_―").replace("made_", "")
                    feats = [f for f in item['features'] if not f.startswith("made_")]
                    st.write(f"  {item['turn_card']} | {item['shift']:.2f}% | {feats} | 役: {made}")

            if turn_input:
                with st.spinner("ShiftRiver計算中..."):
                    top10_river, bottom10_river = run_shift_river(hand_str, flop_cards, turn_input, trials)
                    st.markdown(f"### 🟣 ShiftRiver（ターン: {turn_input}）: トップ10")
                    for item in top10_river:
                        made = next((f for f in item['features'] if f.startswith("made_")), "made_―").replace("made_", "")
                        feats = [f for f in item['features'] if not f.startswith("made_")]
                        st.write(f"  {item['river_card']} | {item['shift']:.2f}% | {feats} | 役: {made}")

                    st.markdown("### 🟠 ShiftRiver: ワースト10")
                    for item in bottom10_river:
                        made = next((f for f in item['features'] if f.startswith("made_")), "made_―").replace("made_", "")
                        feats = [f for f in item['features'] if not f.startswith("made_")]
                        st.write(f"  {item['river_card']} | {item['shift']:.2f}% | {feats} | 役: {made}")

    except Exception as e:
        st.error(f"入力エラー: {e}")
        # ===== CSV保存 =====
if st.button("📥 結果をCSVで保存"):
    csv_rows = []

    # 自動モードの結果
    for i, (flop_cards, static_wr, feature_shifts) in enumerate(st.session_state.get("shiftflop_results", [])):
        flop_str = ' '.join(flop_cards)
        for feat, delta in feature_shifts.items():
            csv_rows.append({
                'Stage': 'ShiftFlop',
                'Flop': flop_str,
                'Turn': '',
                'Detail': feat,
                'Shift': round(delta, 2),
                'Features': '',
                'Role': ''
            })

        top10_turn = st.session_state["shiftturn_results"][i][1]
        bottom10_turn = st.session_state["shiftturn_results"][i][2]
        for item in top10_turn + bottom10_turn:
            made = next((f for f in item['features'] if f.startswith("made_")), "―").replace("made_", "")
            feats = [f for f in item['features'] if not f.startswith("made_")]
            csv_rows.append({
                'Stage': 'ShiftTurn',
                'Flop': flop_str,
                'Turn': '',
                'Detail': item['turn_card'],
                'Shift': round(item['shift'], 2),
                'Features': ', '.join(feats),
                'Role': made
            })

        if i < len(st.session_state["shiftriver_results"]):
            _, turn_card, top10_river, bottom10_river = st.session_state["shiftriver_results"][i]
            for item in top10_river + bottom10_river:
                made = next((f for f in item['features'] if f.startswith("made_")), "―").replace("made_", "")
                feats = [f for f in item['features'] if not f.startswith("made_")]
                csv_rows.append({
                    'Stage': 'ShiftRiver',
                    'Flop': flop_str,
                    'Turn': turn_card,
                    'Detail': item['river_card'],
                    'Shift': round(item['shift'], 2),
                    'Features': ', '.join(feats),
                    'Role': made
                })

    # 手動モードの結果（あれば）
    if st.session_state.get("manual_shiftflop_result"):
        flop_cards, static_wr, feature_shifts = st.session_state["manual_shiftflop_result"]
        flop_str = ' '.join(flop_cards)
        for feat, delta in feature_shifts.items():
            csv_rows.append({
                'Stage': 'ShiftFlop (Manual)',
                'Flop': flop_str,
                'Turn': '',
                'Detail': feat,
                'Shift': round(delta, 2),
                'Features': '',
                'Role': ''
            })

    if st.session_state.get("manual_shiftturn_result"):
        flop_cards, top10_turn, bottom10_turn = st.session_state["manual_shiftturn_result"]
        flop_str = ' '.join(flop_cards)
        for item in top10_turn + bottom10_turn:
            made = next((f for f in item['features'] if f.startswith("made_")), "―").replace("made_", "")
            feats = [f for f in item['features'] if not f.startswith("made_")]
            csv_rows.append({
                'Stage': 'ShiftTurn (Manual)',
                'Flop': flop_str,
                'Turn': '',
                'Detail': item['turn_card'],
                'Shift': round(item['shift'], 2),
                'Features': ', '.join(feats),
                'Role': made
            })

    if st.session_state.get("manual_shiftriver_result"):
        flop_cards, turn_card, top10_river, bottom10_river = st.session_state["manual_shiftriver_result"]
        flop_str = ' '.join(flop_cards)
        for item in top10_river + bottom10_river:
            made = next((f for f in item['features'] if f.startswith("made_")), "―").replace("made_", "")
            feats = [f for f in item['features'] if not f.startswith("made_")]
            csv_rows.append({
                'Stage': 'ShiftRiver (Manual)',
                'Flop': flop_str,
                'Turn': turn_card,
                'Detail': item['river_card'],
                'Shift': round(item['shift'], 2),
                'Features': ', '.join(feats),
                'Role': made
            })

    df = pd.DataFrame(csv_rows)
    csv = df.to_csv(index=False)
    st.download_button("📄 CSVファイルをダウンロード", csv, file_name="shift_results.csv", mime="text/csv")
