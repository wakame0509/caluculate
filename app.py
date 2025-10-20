import streamlit as st
import pandas as pd
import random
import eval7
from simulate_shift_flop import run_shift_flop  # ホールカード貢献付きバージョン
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import run_shift_river
from hand_utils import all_starting_hands, hand_str_to_cards
from preflop_winrates_random import get_static_preflop_winrate
from generate_preflop_winrates import calculate_preflop_winrates_streamlit

# --- セッションステートの初期化 ---
if "auto_flop" not in st.session_state:
    st.session_state["auto_flop"] = {}
if "auto_turn" not in st.session_state:
    st.session_state["auto_turn"] = {}
if "auto_river" not in st.session_state:
    st.session_state["auto_river"] = {}

st.set_page_config(page_title="統合 勝率変動分析", layout="centered")
st.title("統合 勝率変動分析アプリ（複数ハンド対応・CSV保存付き）")

mode = st.radio("モードを選択", ["自動生成モード", "手動選択モード", "プリフロップ勝率生成"])

# --- プリフロップ勝率生成モード ---
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

# --- 共通設定 ---
ALL_HANDS = all_starting_hands
selected_hands = st.multiselect("複数ハンドを選択してください", ALL_HANDS, default=[])

# --- 自動生成モード ---
if mode == "自動生成モード":
    trials = st.selectbox("モンテカルロ試行回数", [1000, 10000, 50000, 100000])
    flop_count = st.selectbox("使用するフロップの枚数", [5, 10, 20, 30])
    turn_count = st.selectbox("使用するターンの枚数", [1, 3, 5])

    if st.button("ShiftFlop → ShiftTurn → ShiftRiver を一括実行"):
        deck_full = [r + s for r in '23456789TJQKA' for s in 'hdcs']
        batch_flop, batch_turn, batch_river = {}, {}, {}

        for hand in selected_hands:
            with st.spinner(f"ハンド {hand} を処理中..."):
                # フロップ生成
                flops_str = []
                while len(flops_str) < flop_count:
                    sample = random.sample(deck_full, 3)
                    if sample not in flops_str:
                        flops_str.append(sample)

                flop_results, turn_results, river_results = [], [], []
                static_wr_pf = get_static_preflop_winrate(hand)

                # 進捗表示
                flop_progress = st.progress(0)
                flop_status = st.empty()
                total_flops = len(flops_str)

                for idx, flop_cards_str in enumerate(flops_str):
                    flop_status.text(f"[{idx+1}/{total_flops}] フロップ計算中: {' '.join(flop_cards_str)}")
                    flop_progress.progress((idx + 1) / total_flops)

                    flop_cards = [eval7.Card(c) for c in flop_cards_str]
                    flop_wr, shift_feats = run_shift_flop(hand, flop_cards, trials)

                    # --- ターン・リバー処理（内部記録のみ） ---
                    turn_items, _, _ = run_shift_turn(hand, flop_cards, flop_wr, trials)
                    river_items, _, _ = run_shift_river(hand, flop_cards, flop_wr, trials, turn_count)

                    turn_results.append([{"turn_card": "", "all": turn_items}])
                    river_results.append([{"turn_card": "", "all": river_items}])
                    flop_results.append((flop_cards_str, flop_wr, shift_feats))

                flop_status.text(f"✅ ハンド {hand} のフロップ計算完了")
                flop_progress.progress(1.0)

                batch_flop[hand] = flop_results
                batch_turn[hand] = turn_results
                batch_river[hand] = river_results

        st.session_state["auto_flop"] = batch_flop
        st.session_state["auto_turn"] = batch_turn
        st.session_state["auto_river"] = batch_river

        # --- CSV出力 ---
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("CSV保存（上部）"):
                csv_rows = []
                for hand_str, flop_list in st.session_state.get("auto_flop", {}).items():
                    static_wr_pf = round(get_static_preflop_winrate(hand_str), 2)
                    csv_rows.append({
                        "Stage": "HandInfo", "Flop": "", "Turn": "", "Detail": "",
                        "Shift": "", "Winrate": static_wr_pf, "Features": "",
                        "Role": "", "Hand": hand_str
                    })

                    for i, (flop_cards_str, static_wr_flop, shift_feats) in enumerate(flop_list):
                        flop_str = ' '.join(flop_cards_str)
                        csv_rows.append({
                            "Stage": f"=== Flop {i+1}: {flop_str} ===", "Flop": "", "Turn": "",
                            "Detail": "", "Shift": "", "Winrate": "", "Features": "",
                            "Role": "", "Hand": hand_str
                        })

                        for f, delta in shift_feats.items():
                            csv_rows.append({
                                "Stage": "ShiftFlop", "Flop": flop_str, "Turn": "",
                                "Detail": f, "Shift": round(delta, 2),
                                "Winrate": round(static_wr_pf + delta, 2),
                                "Features": "", "Role": "", "Hand": hand_str
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

# --- 手動選択モード ---
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
            flop_wr, shift_feats = run_shift_flop(selected_hands[0], flop_cards, trials)
            st.session_state["manual"] = {
                "flop_cards_str": flop_cards_str,
                "static_wr": flop_wr,
                "flop_feats": shift_feats,
            }
            st.success("手動計算完了 ✅")

    except Exception as e:
        st.error(f"入力エラー: {e}")

# --- 結果表示（ShiftFlopのみ） ---
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
--- CSV保存処理（このブロックを既存の if st.button("CSV保存"): 以下と置き換えてください） ---
import streamlit as st
import pandas as pd
import ast

if st.button("CSV保存"):
    csv_rows = []

    auto_flop = st.session_state.get("auto_flop", {})
    auto_turn = st.session_state.get("auto_turn", {})
    auto_river = st.session_state.get("auto_river", {})

    for hand_str, flop_list in auto_flop.items():
        static_wr_pf = round(get_static_preflop_winrate(hand_str), 2)

        # --- Hand info row ---
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

        # === 各フロップ ===
        for i, flop_entry in enumerate(flop_list):
            try:
                flop_cards_str, static_wr_flop, shift_feats = flop_entry
            except Exception:
                continue

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

            # --- ShiftFlop ---
            if isinstance(shift_feats, dict):
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

            # --- ShiftTurn 全通り保存 ---
            turn_entries = []
            if hand_str in auto_turn:
                tlist = auto_turn[hand_str]
                if i < len(tlist):
                    raw_turns = tlist[i]
                    if isinstance(raw_turns, dict) and "all" in raw_turns:
                        turn_entries = raw_turns["all"]
                    elif isinstance(raw_turns, (list, tuple)):
                        for el in raw_turns:
                            if isinstance(el, dict) and "all" in el:
                                turn_entries.extend(el["all"])
                            elif isinstance(el, dict):
                                turn_entries.append(el)
                    elif isinstance(raw_turns, str):
                        try:
                            parsed = ast.literal_eval(raw_turns)
                            if isinstance(parsed, list):
                                turn_entries.extend(parsed)
                        except Exception:
                            pass

            turn_wr_dict = {}  # ターンカードごとの勝率を保存（リバーShift用）

            for item in turn_entries:
                if not isinstance(item, dict):
                    continue
                tc = item.get("turn_card", "―")
                wr_t = item.get("winrate", None)
                made = item.get("hand_rank", "―")
                if made == "high_card":
                    made = "―"
                feats = [f for f in item.get("features", []) if f.startswith("newmade_")]
                if not feats:
                    feats = ["―"]
                shift_t = None
                if wr_t is not None:
                    try:
                        shift_t = round(float(wr_t) - float(static_wr_flop), 2)
                        wr_t = round(float(wr_t), 2)
                        turn_wr_dict[tc] = wr_t  # 保存
                    except Exception:
                        shift_t = ""
                csv_rows.append({
                    "Stage": "ShiftTurn",
                    "Flop": flop_str,
                    "Turn": tc,
                    "Detail": tc,
                    "Shift": shift_t,
                    "Winrate": wr_t if wr_t is not None else "―",
                    "Features": ', '.join(feats),
                    "Role": made,
                    "Hand": hand_str
                })

            # --- ShiftRiver 全通り保存 ---
            if hand_str in auto_river:
                rlist = auto_river[hand_str]
                if i < len(rlist):
                    river_raw = rlist[i]

                    river_items = []
                    if isinstance(river_raw, dict) and "all" in river_raw:
                        turn_card = river_raw.get("turn_card", "")
                        river_items = river_raw["all"]
                    elif isinstance(river_raw, (list, tuple)):
                        for el in river_raw:
                            if isinstance(el, dict) and "all" in el:
                                river_items.extend(el["all"])
                            elif isinstance(el, dict):
                                river_items.append(el)
                    elif isinstance(river_raw, str):
                        try:
                            parsed = ast.literal_eval(river_raw)
                            if isinstance(parsed, list):
                                river_items.extend(parsed)
                        except Exception:
                            pass

                    seen_river = set()
                    for item in river_items:
                        if not isinstance(item, dict):
                            continue
                        rc = item.get("river_card", None)
                        if rc in seen_river:
                            continue
                        seen_river.add(rc)
                        turn_card = item.get("turn_card", "")
                        wr_r = item.get("winrate", None)
                        made = item.get("hand_rank", "―")
                        if made == "high_card":
                            made = "―"
                        feats = [f for f in item.get("features", []) if f.startswith("newmade_")]
                        if not feats:
                            feats = ["―"]

                        shift_r = None
                        if wr_r is not None:
                            try:
                                wr_r = round(float(wr_r), 2)
                                # --- ✅ 修正点：ターン基準のShiftRiver計算 ---
                                wr_turn_base = turn_wr_dict.get(turn_card, static_wr_flop)
                                shift_r = round(float(wr_r) - float(wr_turn_base), 2)
                            except Exception:
                                shift_r = ""

                        csv_rows.append({
                            "Stage": "ShiftRiver",
                            "Flop": flop_str,
                            "Turn": turn_card or "―",
                            "Detail": rc or "―",
                            "Shift": shift_r,
                            "Winrate": wr_r if wr_r is not None else "―",
                            "Features": ', '.join(feats),
                            "Role": made,
                            "Hand": hand_str
                        })

    # === 保存処理 ===
    df = pd.DataFrame(csv_rows)
    st.session_state["csv_data"] = df.to_csv(index=False)
    st.success("フロップ・ターン・リバー全通りの結果をCSVに保存しました ✅")

# --- ダウンロードボタン ---
if "csv_data" in st.session_state and st.session_state["csv_data"]:
    st.download_button(
        label="📥 CSVをダウンロード",
        data=st.session_state["csv_data"],
        file_name="shift_results.csv",
        mime="text/csv"
    )
else:
    st.warning("CSVがまだ生成されていません。Shift計算を先に実行してください。")
import pandas as pd
import re

# === 役名一覧（newmade_ が前提） ===
made_roles = [
    "newmade_set", "newmade_straight", "newmade_flush", "newmade_full_house",
    "newmade_two_pair", "newmade_pair", "newmade_quads", "newmade_straight_flush"
]

# === 除外対象の特徴量 ===
excluded_features = {"newmade_rainbow", "newmade_two_tone", "newmade_monotone"}

# === バケット定義（10%刻み、-100〜100%） ===
def make_buckets(start, end, step):
    buckets = []
    for v in range(start, end, step):
        buckets.append(f"{v}%以上〜{v+step}%未満")
    return buckets

BUCKETS_MADE = make_buckets(0, 100, 10) + ["100%以上"]
BUCKETS_NOTMADE = make_buckets(-100, 100, 10) + ["100%以上"]

# === バケット分類関数 ===
def get_bucket(value, is_made):
    if is_made:
        if value < 0:
            return "0%未満"
        elif value >= 100:
            return "100%以上"
        else:
            lower = int(value // 10) * 10
            upper = lower + 10
            return f"{lower}%以上〜{upper}%未満"
    else:
        if value < -100:
            return "-100%未満"
        elif value >= 100:
            return "100%以上"
        else:
            lower = int(value // 10) * 10
            upper = lower + 10
            return f"{lower}%以上〜{upper}%未満"

# === 特徴量の統計処理（hc0, hc1を別役として扱う） ===
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

            # hcを含むfeatをそのまま使い、made判定はhc除外で行う
            base_match = re.match(r"(newmade_[a-z_]+)", feat)
            feat_base = base_match.group(1) if base_match else feat
            is_made = feat_base in made_roles

            bucket = get_bucket(shift, is_made)
            record = {
                "feature": feat,   # hc付きで集計
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

    # === 集計・統計（hc付きfeatureごと） ===
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

# === Streamlit UI ===
st.title("特徴量別 勝率シフト度数分布＋統計（役あり／役なし分離・hc別集計対応）")

uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    df_all = pd.concat([pd.read_csv(file) for file in uploaded_files], ignore_index=True)
    st.success(f"{len(uploaded_files)} ファイルを読み込みました。合計 {len(df_all)} 行のデータがあります。")

    summary_made, summary_notmade = analyze_features(df_all)

    if not summary_made.empty:
        st.subheader("🟩 役が完成した特徴量（made, hc区別あり）")
        st.dataframe(summary_made)
        csv_made = summary_made.to_csv(index=True, encoding="utf-8-sig")
        st.download_button("📥 made特徴量をCSV保存", data=csv_made, file_name="summary_made.csv", mime="text/csv")

    if not summary_notmade.empty:
        st.subheader("🟦 役が未完成の特徴量（not made, hc区別あり）")
        st.dataframe(summary_notmade)
        csv_notmade = summary_notmade.to_csv(index=True, encoding="utf-8-sig")
        st.download_button("📥 not made特徴量をCSV保存", data=csv_notmade, file_name="summary_notmade.csv", mime="text/csv")
