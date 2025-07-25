import streamlit as st
import pandas as pd
import random
import eval7
from simulate_shift_flop import run_shift_flop
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands, hand_str_to_cards
from preflop_winrates_random import get_static_preflop_winrate
from generate_preflop_winrates import calculate_preflop_winrates_streamlit

st.set_page_config(page_title="統合 勝率変動分析", layout="centered")
st.title("統合 勝率変動分析アプリ（複数ハンド対応・CSV保存付き）")

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
            result_df = calculate_preflop_winrates_streamlit(trials=trials_pf, update_func=update_progress)
        st.success("計算完了 ✅")
        st.download_button("CSVダウンロード", result_df.to_csv(index=False), "preflop_winrates.csv", "text/csv")
    st.stop()
ALL_HANDS = all_starting_hands

# 複数ハンドを自由に選択できるように表示（初期選択なし）
selected_hands = st.multiselect("複数ハンドを選択してください", ALL_HANDS, default=[])

if mode == "自動生成モード":
    trials = st.selectbox("モンテカルロ試行回数", [1000, 10000, 50000, 100000])
    flop_count = st.selectbox("使用するフロップの枚数", [5, 10, 20, 30])
    if st.button("ShiftFlop → ShiftTurn → ShiftRiver を一括実行"):
        deck_full = [r + s for r in '23456789TJQKA' for s in 'hdcs']
        batch_flop = {}
        batch_turn = {}
        batch_river = {}

        for hand in selected_hands:
            with st.spinner(f"ハンド {hand} を処理中..."):
                # フロップを生成
                flops_str = []
                while len(flops_str) < flop_count:
                    sample = random.sample(deck_full, 3)
                    if sample not in flops_str:
                        flops_str.append(sample)

                flop_results, turn_results, river_results = [], [], []
                static_wr_pf = get_static_preflop_winrate(hand)

                for idx, flop_cards_str in enumerate(flops_str):
                    flop_cards = [eval7.Card(c) for c in flop_cards_str]
                    flop_wr, shift_feats = run_shift_flop(hand, flop_cards, trials)
                    all_t, top10_t, bottom10_t = run_shift_turn(hand, flop_cards, flop_wr, trials)

                    used_cards = flop_cards_str + [c.__str__() for c in hand_str_to_cards(hand)]
                    remaining = [c for c in deck_full if c not in used_cards]
                    random_turn = random.choice(remaining)
                    turn_wr = next((item['winrate'] for item in all_t if item['turn_card'] == random_turn), flop_wr)
                    all_r, top10_r, bottom10_r = run_shift_river(hand, flop_cards, random_turn, turn_wr, trials)

                    flop_results.append((flop_cards_str, flop_wr, shift_feats))
                    turn_results.append((flop_cards_str, all_t, top10_t, bottom10_t))
                    river_results.append((flop_cards_str, random_turn, all_r, top10_r, bottom10_r))

                batch_flop[hand] = flop_results
                batch_turn[hand] = turn_results
                batch_river[hand] = river_results

        st.session_state["auto_flop"] = batch_flop
        st.session_state["auto_turn"] = batch_turn
        st.session_state["auto_river"] = batch_river
        # 実行ボタンの下に保存・ダウンロードボタンを追加
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("CSV保存（上部）"):
                csv_rows = []

                for hand_str, flop_list in st.session_state.get("auto_flop", {}).items():
                    static_wr_pf = round(get_static_preflop_winrate(hand_str), 2)

                    csv_rows.append({
                        "Stage": "HandInfo",
                        "Flop": "",
                        "Turn": "",
                        "Detail": "",
                        "Shift": "",
                        "Winrate": static_wr_pf,
                        "Features": "",
                        "Role": "",
                        "Hand": hand_str
                    })

                    for i, (flop_cards_str, static_wr_flop, shift_feats) in enumerate(flop_list):
                        flop_str = ' '.join(flop_cards_str)

                        csv_rows.append({
                            "Stage": f"=== Flop {i+1}: {flop_str} ===",
                            "Flop": "",
                            "Turn": "",
                            "Detail": "",
                            "Shift": "",
                            "Winrate": "",
                            "Features": "",
                            "Role": "",
                            "Hand": hand_str
                        })

                        # ShiftFlop
                        for f, delta in shift_feats.items():
                            csv_rows.append({
                                "Stage": "ShiftFlop",
                                "Flop": flop_str,
                                "Turn": "",
                                "Detail": f,
                                "Shift": round(delta, 2),
                                "Winrate": round(static_wr_pf + delta, 2),
                                "Features": "",
                                "Role": "",
                                "Hand": hand_str
                            })

                        # ShiftTurn
                        turn_data = st.session_state["auto_turn"][hand_str][i]
                        turn_items = turn_data[1]
                        seen_turn = set()
                        for item in turn_items:
                            tc = item["turn_card"]
                            if tc in seen_turn:
                                continue
                            seen_turn.add(tc)
                            made = item["hand_rank"] if item["hand_rank"] != "high_card" else "―"
                            feats = [f for f in item["features"] if f.startswith("newmade_")]
                            if not feats:
                                feats = ["―"]
                            shift = round(item["winrate"] - static_wr_flop, 2)
                            csv_rows.append({
                                "Stage": "ShiftTurn",
                                "Flop": flop_str,
                                "Turn": tc,
                                "Detail": tc,
                                "Shift": shift,
                                "Winrate": round(item["winrate"], 2),
                                "Features": ', '.join(feats),
                                "Role": made,
                                "Hand": hand_str
                            })

                        # ShiftRiver
                        river_data = st.session_state["auto_river"][hand_str][i]
                        turn_card = river_data[1]
                        river_items = river_data[2]
                        turn_wr = next((t["winrate"] for t in turn_items if t["turn_card"] == turn_card), static_wr_flop)
                        seen_river = set()
                        for item in river_items:
                            rc = item["river_card"]
                            if rc in seen_river:
                                continue
                            seen_river.add(rc)
                            made = item["hand_rank"] if item["hand_rank"] != "high_card" else "―"
                            feats = [f for f in item["features"] if f.startswith("newmade_")]
                            if not feats:
                                feats = ["―"]
                            shift = round(item["winrate"] - turn_wr, 2)
                            csv_rows.append({
                                "Stage": "ShiftRiver",
                                "Flop": flop_str,
                                "Turn": turn_card,
                                "Detail": rc,
                                "Shift": shift,
                                "Winrate": round(item["winrate"], 2),
                                "Features": ', '.join(feats),
                                "Role": made,
                                "Hand": hand_str
                            })

                df = pd.DataFrame(csv_rows)
                st.session_state["csv_data"] = df.to_csv(index=False)
                st.success("CSVをセッションに保存しました")

        with col2:
            if "csv_data" in st.session_state:
                st.download_button(
                    label="📥 ダウンロード（上部）",
                    data=st.session_state["csv_data"],
                    file_name="shift_results.csv",
                    mime="text/csv"
                )    
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
            flop_wr, shift_feats = run_shift_flop(hand_str, flop_cards, trials)
            top10_t, bottom10_t = run_shift_turn(hand_str, flop_cards, flop_wr, trials)

            if turn_input:
                turn_card = turn_input.strip()
                turn_wr = next((item['winrate'] for item in top10_t + bottom10_t if item['turn_card'] == turn_card), flop_wr)
                top10_r, bottom10_r = run_shift_river(hand_str, flop_cards, turn_card, turn_wr, trials)
            else:
                turn_card, top10_r, bottom10_r = "", [], []

            st.session_state["manual"] = {
                "flop_cards_str": flop_cards_str,
                "static_wr": flop_wr,
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
if "auto_flop" in st.session_state:
    st.subheader("自動生成モードの結果表示")

    for hand_str, flop_list in st.session_state["auto_flop"].items():
        static_wr_pf = round(get_static_preflop_winrate(hand_str), 2)
        st.markdown(f"### 💠 ハンド: **{hand_str}**")
        for i, (flop_cards_str, static_wr_flop, shift_feats) in enumerate(flop_list):
            flop_str = ' '.join(flop_cards_str)
            st.markdown(f"【{i+1}】フロップ: **{flop_str}**")
            st.markdown(f"- プリフロップ勝率: **{static_wr_pf:.1f}%**")
            st.markdown(f"- フロップ勝率: **{static_wr_flop:.1f}%**")

            st.markdown("- ShiftFlop 特徴:")
            for f, delta in shift_feats.items():
                st.markdown(f"　・{f}: {round(delta,2)}%")

            # ShiftTurn 表示
            turn_data = st.session_state["auto_turn"][hand_str][i]
            top10_t = turn_data[2]
            bottom10_t = turn_data[3]
            st.markdown("- ShiftTurn Top10:")
            for item in top10_t:
                shift_val = item["winrate"] - static_wr_flop
                sign = "+" if shift_val > 0 else ""
                st.markdown(f"　・{item['turn_card']}：{sign}{shift_val:.2f}% ({', '.join(item['features'])})")

            st.markdown("- ShiftTurn Worst10:")
            for item in bottom10_t:
                shift_val = item["winrate"] - static_wr_flop
                sign = "+" if shift_val > 0 else ""
                st.markdown(f"　・{item['turn_card']}：{sign}{shift_val:.2f}% ({', '.join(item['features'])})")

            # ShiftRiver 表示
            river_data = st.session_state["auto_river"][hand_str][i]
            turn_card = river_data[1]
            top10_r = river_data[2]
            bottom10_r = river_data[3]

            if top10_r:
                turn_wr = next((t["winrate"] for t in st.session_state["auto_turn"][hand_str][i][1] if t["turn_card"] == turn_card), static_wr_flop)
                st.markdown(f"- ShiftRiver Top10（ターン: {turn_card}）:")
                for item in top10_r:
                    shift_val = item["winrate"] - turn_wr
                    sign = "+" if shift_val > 0 else ""
                    st.markdown(f"　・{item['river_card']}：{sign}{shift_val:.2f}% ({', '.join(item['features'])})")

            if bottom10_r:
                turn_wr = next((t["winrate"] for t in st.session_state["auto_turn"][hand_str][i][1] if t["turn_card"] == turn_card), static_wr_flop)
                st.markdown(f"- ShiftRiver Worst10（ターン: {turn_card}）:")
                for item in bottom10_r:
                    shift_val = item["winrate"] - turn_wr
                    sign = "+" if shift_val > 0 else ""
                    st.markdown(f"　・{item['river_card']}：{sign}{shift_val:.2f}% ({', '.join(item['features'])})")
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

if st.button("CSV保存"):
    csv_rows = []

    for hand_str, flop_list in st.session_state.get("auto_flop", {}).items():
        static_wr_pf = round(get_static_preflop_winrate(hand_str), 2)

        csv_rows.append({
            "Stage": "HandInfo",
            "Flop": "",
            "Turn": "",
            "Detail": "",
            "Shift": "",
            "Winrate": static_wr_pf,
            "Features": "",
            "Role": "",
            "Hand": hand_str
        })

        for i, (flop_cards_str, static_wr_flop, shift_feats) in enumerate(flop_list):
            flop_str = ' '.join(flop_cards_str)

            csv_rows.append({
                "Stage": f"=== Flop {i+1}: {flop_str} ===",
                "Flop": "",
                "Turn": "",
                "Detail": "",
                "Shift": "",
                "Winrate": "",
                "Features": "",
                "Role": "",
                "Hand": hand_str
            })

            # ShiftFlop
            for f, delta in shift_feats.items():
                csv_rows.append({
                    "Stage": "ShiftFlop",
                    "Flop": flop_str,
                    "Turn": "",
                    "Detail": f,
                    "Shift": round(delta, 2),
                    "Winrate": round(static_wr_pf + delta, 2),
                    "Features": "",
                    "Role": "",
                    "Hand": hand_str
                })

            # ShiftTurn
            turn_data = st.session_state["auto_turn"][hand_str][i]
            turn_items = turn_data[1]
            seen_turn = set()
            for item in turn_items:
                tc = item["turn_card"]
                if tc in seen_turn:
                    continue
                seen_turn.add(tc)
                made = item["hand_rank"] if item["hand_rank"] != "high_card" else "―"
                feats = [f for f in item["features"] if f.startswith("newmade_")]
                if not feats:
                    feats = ["―"]
                shift = round(item["winrate"] - static_wr_flop, 2)
                csv_rows.append({
                    "Stage": "ShiftTurn",
                    "Flop": flop_str,
                    "Turn": tc,
                    "Detail": tc,
                    "Shift": shift,
                    "Winrate": round(item["winrate"], 2),
                    "Features": ', '.join(feats),
                    "Role": made,
                    "Hand": hand_str
                })

            # ShiftRiver
            river_data = st.session_state["auto_river"][hand_str][i]
            turn_card = river_data[1]
            river_items = river_data[2]
            turn_wr = next((t["winrate"] for t in turn_items if t["turn_card"] == turn_card), static_wr_flop)
            seen_river = set()
            for item in river_items:
                rc = item["river_card"]
                if rc in seen_river:
                    continue
                seen_river.add(rc)
                made = item["hand_rank"] if item["hand_rank"] != "high_card" else "―"
                feats = [f for f in item["features"] if f.startswith("newmade_")]
                if not feats:
                    feats = ["―"]
                shift = round(item["winrate"] - turn_wr, 2)
                csv_rows.append({
                    "Stage": "ShiftRiver",
                    "Flop": flop_str,
                    "Turn": turn_card,
                    "Detail": rc,
                    "Shift": shift,
                    "Winrate": round(item["winrate"], 2),
                    "Features": ', '.join(feats),
                    "Role": made,
                    "Hand": hand_str
                })

    df = pd.DataFrame(csv_rows)
    st.session_state["csv_data"] = df.to_csv(index=False)

if "csv_data" in st.session_state:
    st.download_button(
        label="📥 結果をCSVでダウンロード",
        data=st.session_state["csv_data"],
        file_name="shift_results.csv",
        mime="text/csv"
    )
import streamlit as st
import pandas as pd

# 役名一覧（newmade_ が前提）
made_roles = [
    "newmade_set", "newmade_straight", "newmade_flush", "newmade_full_house",
    "newmade_two_pair", "newmade_pair", "newmade_quads", "newmade_straight_flush"
]

# 除外対象の特徴量（スート系など）
excluded_features = {"newmade_rainbow", "newmade_two_tone", "newmade_monotone"}

# 表示順を固定するためのバケット（全て「以上〜未満」形式・半角マイナス）
BUCKETS_MADE = [
    "0%未満", "0%以上〜5%未満", "5%以上〜10%未満", "10%以上〜15%未満",
    "15%以上〜20%未満", "20%以上〜25%未満", "25%以上〜30%未満", "30%以上"
]
BUCKETS_NOTMADE = [
    "-15%未満", "-15%以上〜-10%未満", "-10%以上〜-5%未満", "-5%以上〜0%未満",
    "0%以上〜5%未満", "5%以上〜10%未満", "10%以上〜15%未満", "15%以上"
]

# バケット分類関数
def get_bucket(value, is_made):
    if is_made:
        if value < 0:
            return "0%未満"
        elif value >= 30:
            return "30%以上"
        else:
            lower = int(value // 5) * 5
            upper = lower + 5
            return f"{lower}%以上〜{upper}%未満"
    else:
        if value < -15:
            return "-15%未満"
        elif value >= 15:
            return "15%以上"
        else:
            lower = int(value // 5) * 5
            upper = lower + 5
            return f"{lower}%以上〜{upper}%未満"

# 特徴量の統計処理
def analyze_features(df_all):
    records_made = []
    records_notmade = []

    for _, row in df_all.iterrows():
        shift = row["Shift"]
        winrate = row["Winrate"]
        features = str(row["Features"]).split(", ")
        for feat in features:
            if not feat.startswith("newmade_") or feat in excluded_features:
                continue
            is_made = feat in made_roles
            bucket = get_bucket(shift, is_made)
            record = {
                "feature": feat,
                "shift": shift,
                "winrate": winrate,
                "bucket": bucket
            }
            if is_made:
                records_made.append(record)
            else:
                records_notmade.append(record)

    df_made = pd.DataFrame(records_made)
    df_notmade = pd.DataFrame(records_notmade)

    summary_made = (
        df_made.groupby(["feature", "bucket"]).size().unstack(fill_value=0)
        if not df_made.empty else pd.DataFrame()
    )
    summary_notmade = (
        df_notmade.groupby(["feature", "bucket"]).size().unstack(fill_value=0)
        if not df_notmade.empty else pd.DataFrame()
    )

    if not df_made.empty:
        summary_made["平均Shift"] = df_made.groupby("feature")["shift"].mean().round(2)
        summary_made["標準偏差"] = df_made.groupby("feature")["shift"].std().round(2)
        summary_made["平均Winrate"] = df_made.groupby("feature")["winrate"].mean().round(2)
        cols = [col for col in BUCKETS_MADE if col in summary_made.columns]
        summary_made = summary_made.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary_made = summary_made.sort_values("平均Shift", ascending=False)

    if not df_notmade.empty:
        summary_notmade["平均Shift"] = df_notmade.groupby("feature")["shift"].mean().round(2)
        summary_notmade["標準偏差"] = df_notmade.groupby("feature")["shift"].std().round(2)
        summary_notmade["平均Winrate"] = df_notmade.groupby("feature")["winrate"].mean().round(2)
        cols = [col for col in BUCKETS_NOTMADE if col in summary_notmade.columns]
        summary_notmade = summary_notmade.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary_notmade = summary_notmade.sort_values("平均Shift", ascending=False)

    return summary_made, summary_notmade

# Streamlit UI
st.title("特徴量別 勝率シフト度数分布＋統計（役あり／役なし分離）")

uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    df_all = pd.concat([pd.read_csv(file) for file in uploaded_files], ignore_index=True)
    st.success(f"{len(uploaded_files)} ファイルを読み込みました。合計 {len(df_all)} 行のデータがあります。")

    summary_made, summary_notmade = analyze_features(df_all)

    if not summary_made.empty:
        st.subheader("🟩 役が完成した特徴量（made）の統計")
        st.dataframe(summary_made)
        csv_made = summary_made.to_csv(index=True, encoding="utf-8-sig")
        st.download_button("📥 made特徴量をCSV保存", data=csv_made, file_name="summary_made.csv", mime="text/csv")

    if not summary_notmade.empty:
        st.subheader("🟦 役が未完成の特徴量（not made）の統計")
        st.dataframe(summary_notmade)
        csv_notmade = summary_notmade.to_csv(index=True, encoding="utf-8-sig")
        st.download_button("📥 not made特徴量をCSV保存", data=csv_notmade, file_name="summary_notmade.csv", mime="text/csv")
