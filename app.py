import streamlit as st
import pandas as pd
import random
import eval7
from simulate_shift_flop import run_shift_flop  # ホールカード貢献付きバージョン
from simulate_shift_turn import run_shift_turn
from simulate_shift_river import simulate_shift_river_multiple_turns
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

mode = st.radio("モードを選択", ["プリフロップ勝率", "自動生成モード", "手動選択モード"])


# ==== プリフロップ勝率生成モード ====
if mode == "プリフロップ勝率":
    st.header("プリフロップ勝率生成（ランダムハンド vs ランダムハンド）")

    trials_pf = st.selectbox("試行回数", [1000, 2000, 3000, 5000, 10000, 50000, 100000])

    if st.button("プリフロップ勝率を生成して保存"):
        deck_full = [r + s for r in '23456789TJQKA' for s in 'shdc']

        preflop_results = []
        for hand in generate_169_hands():
            win_rate = simulate_preflop_vs_random(hand, trials_pf)
            preflop_results.append({"hand": hand, "win_rate": win_rate})

        df_pf = pd.DataFrame(preflop_results)
        df_pf.to_csv("preflop_winrates_random.csv", index=False, encoding="utf-8-sig")
        st.success("プリフロップ勝率を preflop_winrates_random.csv に保存しました！")
        st.dataframe(df_pf)


# ==== 自動生成モード（ShiftFlop→ShiftTurn→ShiftRiver） ====
elif mode == "自動生成モード":
    st.header("プリフロップ → フロップ → ターン → リバー 勝率変動 自動生成")

    # === ハンド選択 ===
    st.subheader("スターティングハンドを選択")

    ranks = 'AKQJT98765432'  # A系→K系→Q系…の順で整理
    all_hands = []

    # --- 全169ハンド生成（スート差なし）---
    for i, r1 in enumerate(ranks[::-1]):  # 一応逆順生成（安定動作用）
        for j, r2 in enumerate(ranks[::-1]):
            if i < j:
                all_hands.append(r2 + r1 + "s")  # スーテッド
                all_hands.append(r2 + r1 + "o")  # オフスート
            elif i == j:
                all_hands.append(r1 + r2)  # ペア

    # --- カスタムソート関数 ---
    def hand_sort_key(hand):
        rank_order = {r: i for i, r in enumerate(ranks)}
        main_rank = hand[0]  # 先頭のランク（A系, K系, Q系...）
        secondary_rank = hand[1]

        # グループ順: A→K→Q→J→...、同グループ内はペア→スーテッド→オフスート
        primary_idx = rank_order.get(main_rank, 99)
        secondary_idx = rank_order.get(secondary_rank, 99)
        suited = 0 if hand.endswith("s") else 1
        pair = 0 if hand[0] == hand[1] else 1

        return (primary_idx, pair, secondary_idx, suited)

    # --- ソート適用 ---
    all_hands_sorted = sorted(all_hands, key=hand_sort_key)

    # --- Streamlit選択 ---
    selected_hands = st.multiselect(
        "対象ハンドを選択（複数可）",
        all_hands_sorted,
        default=["AKs"]
    )  
    # === プリフロップ勝率表示 ===
    st.subheader("プリフロップ勝率（ランダム相手）")
    if selected_hands:
        pf_data = []
        for hand in selected_hands:
            pf_winrate = get_static_preflop_winrate(hand)
            pf_data.append({"ハンド": hand, "プリフロップ勝率": f"{pf_winrate:.2f}%"})
        st.table(pf_data)

    # === 自動生成設定 ===
    st.subheader("自動生成パラメータ設定")
    trials = st.selectbox("試行回数", [1000, 2000, 3000, 5000, 10000, 50000, 100000])
    flop_count = st.selectbox("フロップ枚数", [5, 10, 20, 30])
    turn_count = st.selectbox("ターンカード枚数", [5, 10, 20, 30])

    # === 実行ボタン ===
    if st.button("ShiftFlop → ShiftTurn → ShiftRiver を一括実行"):
        # --- 念のため再初期化 ---
        for key in ["auto_flop", "auto_turn", "auto_river"]:
            if key not in st.session_state:
                st.session_state[key] = {}

        deck_full = [r + s for r in '23456789TJQKA' for s in 'hdcs']
        batch_flop, batch_turn, batch_river = {}, {}, {}

        for hand in selected_hands:
            with st.spinner(f"ハンド {hand} を処理中..."):
                # --- フロップ生成 ---
                flops_str = []
                while len(flops_str) < flop_count:
                    sample = random.sample(deck_full, 3)
                    if sample not in flops_str:
                        flops_str.append(sample)

                flop_results, turn_results, river_results = [], [], []
                static_wr_pf = get_static_preflop_winrate(hand)

                # --- 進捗バー ---
                flop_progress = st.progress(0)
                flop_status = st.empty()
                total_flops = len(flops_str)

                for idx, flop_cards_str in enumerate(flops_str):
                    flop_status.text(f"[{idx+1}/{total_flops}] フロップ計算中: {' '.join(flop_cards_str)}")
                    flop_progress.progress((idx + 1) / total_flops)

                    flop_cards = [eval7.Card(c) for c in flop_cards_str]
                    flop_wr, shift_feats = run_shift_flop(hand, flop_cards, trials)

                                        # --- ターン・リバー処理 ---
                    turn_all_items, turn_top10, turn_bottom10 = run_shift_turn(
                        hand, flop_cards, flop_wr, trials
                    )

                    # ターンカード一覧を抽出
                    if isinstance(turn_all_items, list) and len(turn_all_items) > 0:
                        all_turn_cards = [t["turn_card"] for t in turn_all_items if "turn_card" in t]
                    else:
                        all_turn_cards = []

                    # 指定枚数だけサンプリング（ターン数より少なければ全使用）
                    if len(all_turn_cards) > 0:
                        sampled_turn_cards = random.sample(
                            all_turn_cards, min(turn_count, len(all_turn_cards))
                        )
                    else:
                        sampled_turn_cards = []

                    # --- ターン結果を格納 ---
                    turn_results.append(turn_all_items)

                    # --- フロップごとに、ターン×リバー構造で保持 ---
                    river_result_per_flop = []  # 各ターンごとのリバー結果リスト

                    # 各ターンに対してリバー全探索を実行
                    for t_card in sampled_turn_cards:
                        turn_wr = next(
                            (t["winrate"] for t in turn_all_items if t.get("turn_card") == t_card),
                            flop_wr
                        )

                        # 各ターンごとにリバー全探索
                        river_items, _, _ = simulate_shift_river_multiple_turns(
                            hand,
                            flop_cards + [eval7.Card(t_card)],
                            turn_wr,
                            turn_count=turn_count,   # UIで指定したターン数をそのまま反映
                            trials_per_river=trials
                        )

                        # ターンカードとリバー結果を1セットとして保存
                        river_result_per_flop.append({
                            "turn_card": t_card,
                            "all": river_items
                        })

                    # --- フロップ単位でまとめて保存 ---
                    river_results.append(river_result_per_flop)
                    flop_results.append((flop_cards_str, flop_wr, shift_feats))

                # --- 各ハンド処理完了 ---
                flop_status.text(f"✅ ハンド {hand} のフロップ計算完了")
                flop_progress.progress(1.0)

                # --- セッションステートに格納 ---
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

if st.button("CSV保存"):
    import ast
    csv_rows = []

    auto_flop = st.session_state.get("auto_flop", {})
    auto_turn = st.session_state.get("auto_turn", {})
    auto_river = st.session_state.get("auto_river", {})

    for hand_str, flop_list in auto_flop.items():
        static_wr_pf = round(get_static_preflop_winrate(hand_str), 2)

        # Hand info row
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

        # ==========================================================
        # Flop loop
        # ==========================================================
        for i, flop_entry in enumerate(flop_list):
            try:
                flop_cards_str, static_wr_flop, shift_feats = flop_entry
            except Exception:
                continue

            flop_str = ' '.join(flop_cards_str)

            # Flop header row
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

            # ==========================================================
            # ShiftFlop（特徴は Detail 列）
            # ==========================================================
            if isinstance(shift_feats, dict) and shift_feats:
                for f, delta in sorted(shift_feats.items(), key=lambda x: float(x[1])):
                    d = float(delta)
                    csv_rows.append({
                        "Stage": "ShiftFlop",
                        "Flop": flop_str,
                        "Turn": "",
                        "Detail": str(f),
                        "Shift": round(d, 2),
                        "Winrate": round(float(static_wr_pf) + d, 2),
                        "Features": "",
                        "Role": "",
                        "Hand": hand_str
                    })
            else:
                csv_rows.append({
                    "Stage": "ShiftFlop",
                    "Flop": flop_str,
                    "Turn": "",
                    "Detail": "―",
                    "Shift": "",
                    "Winrate": round(float(static_wr_flop), 2),
                    "Features": "",
                    "Role": "",
                    "Hand": hand_str
                })

            # ==========================================================
            # ShiftTurn
            # ==========================================================
            turn_wr_dict = {}   # { 'Tc': 96.05, ... }

            if hand_str in auto_turn and i < len(auto_turn[hand_str]):
                turn_items = auto_turn[hand_str][i] or []

                for t in turn_items:
                    if not isinstance(t, dict):
                        continue

                    tc = t.get("turn_card")
                    wr = t.get("winrate")
                    if tc is None or wr is None:
                        continue

                    turn_wr_dict[str(tc)] = float(wr)

                    made = t.get("hand_rank", "―")
                    if made == "high_card":
                        made = "―"

                    feats = [fx for fx in t.get("features", []) if str(fx).startswith("newmade_")]
                    if not feats:
                        feats = ["―"]

                    try:
                        shift_t = round(float(wr) - float(static_wr_flop), 2)
                        wr_out = round(float(wr), 2)
                    except Exception:
                        shift_t, wr_out = "", wr

                    csv_rows.append({
                        "Stage": "ShiftTurn",
                        "Flop": flop_str,
                        "Turn": str(tc),
                        "Detail": str(tc),
                        "Shift": shift_t,
                        "Winrate": wr_out,
                        "Features": ", ".join(feats),
                        "Role": made,
                        "Hand": hand_str
                    })

            # ==========================================================
            # ShiftRiver（ターン勝率基準）
            # ==========================================================
            if hand_str in auto_river and i < len(auto_river[hand_str]):
                river_blocks = auto_river[hand_str][i] or []

                for block in river_blocks:
                    if not isinstance(block, dict):
                        continue

                    turn_card = str(block.get("turn_card", "―"))
                    river_items = block.get("all", []) or []

                    # ターン基準（無ければフロップ勝率でフォールバック）
                    baseline_turn_wr = turn_wr_dict.get(turn_card, float(static_wr_flop))

                    seen_rivers = set()
                    for item in river_items:
                        if not isinstance(item, dict):
                            continue

                        rc = item.get("river_card")
                        if rc is None:
                            continue
                        rc = str(rc)

                        if rc in seen_rivers:
                            continue
                        seen_rivers.add(rc)

                        made = item.get("hand_rank", "―")
                        if made == "high_card":
                            made = "―"

                        feats = [fx for fx in item.get("features", []) if str(fx).startswith("newmade_")]
                        if not feats:
                            feats = ["―"]

                        wr = item.get("winrate")
                        if wr is not None:
                            try:
                                wr_out = round(float(wr), 2)
                                # ★ ShiftRiver は「リバー勝率 − ターン勝率」
                                shift_r = round(float(wr) - float(baseline_turn_wr), 2)
                            except Exception:
                                wr_out, shift_r = wr, ""
                        else:
                            wr_out, shift_r = "―", ""

                        csv_rows.append({
                            "Stage": "ShiftRiver",
                            "Flop": flop_str,
                            "Turn": turn_card,
                            "Detail": rc,
                            "Shift": shift_r,
                            "Winrate": wr_out,
                            "Features": ", ".join(feats),
                            "Role": made,
                            "Hand": hand_str
                        })

    # 保存
    df = pd.DataFrame(csv_rows)
    st.session_state["csv_data"] = df.to_csv(index=False)
    st.success("CSVをセッションに保存しました")

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
# analyze_shift_features.py
import re
import pandas as pd
import streamlit as st

# ====== 定義 ======
MADE_ROLES = {
    "newmade_set", "newmade_straight", "newmade_flush", "newmade_full_house",
    "newmade_two_pair", "newmade_pair", "newmade_quads", "newmade_straight_flush",
}
EXCLUDED_FEATURES = {"newmade_rainbow", "newmade_two_tone", "newmade_monotone"}
ROLE_RE = re.compile(r'^(newmade_[a-z_]+?)(?:_hc([0-2]))?$')

def make_buckets(start: int, end: int, step: int):
    return [f"{v}%以上〜{v+step}%未満" for v in range(start, end, step)]

BUCKETS = ["-100%未満"] + make_buckets(-100, 100, 10) + ["100%以上"]

def get_bucket(v) -> str | None:
    try:
        x = float(v)
    except Exception:
        return None
    if pd.isna(x): return None
    if x < -100:  return "-100%未満"
    if x >= 100:  return "100%以上"
    lo = int(x // 10) * 10
    return f"{lo}%以上〜{lo+10}%未満"

# ---- Features と Detail の両方から newmade_* を吸い上げる ----
def _split_items(cell) -> list[str]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    s = str(cell).strip()
    if not s or s == "―":
        return []
    s = s.strip("[]")
    return [x.strip() for x in s.split(",") if x.strip()]

def collect_newmade_items(row) -> list[str]:
    items = []
    if "Features" in row: items += _split_items(row["Features"])
    if "Detail"   in row: items += _split_items(row["Detail"])  # 👈 ShiftFlopがDetailに出る旧CSV救済
    return [it for it in items if str(it).startswith("newmade_")]

# ====== 集計 ======
def analyze_roles_and_features(df: pd.DataFrame):
    role_rows, feat_rows = [], []

    # 列名ゆらぎを一応吸収
    if "Shift" not in df.columns or "Winrate" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    for _, row in df.iterrows():
        bucket = get_bucket(row.get("Shift"))
        if bucket is None:
            continue
        try:
            shift = float(row.get("Shift"))
            winrate = float(row.get("Winrate"))
        except Exception:
            continue

        items = collect_newmade_items(row)
        if not items:
            continue

        for item in items:
            if item in EXCLUDED_FEATURES:
                continue
            m = ROLE_RE.match(item)
            if not m:
                continue
            base, hc = m.group(1), m.group(2)  # hc は '0'|'1'|'2' or None

            if base in MADE_ROLES:
                # “新規にペア完成”で hc2 は理論上不整合なので除外
                if base == "newmade_pair" and hc == "2":
                    continue
                role_key = f"{base}_hc{hc}" if hc is not None else f"{base}_hcnone"
                role_rows.append(
                    {"role_key": role_key, "role_base": base, "hc": ("none" if hc is None else hc),
                     "bucket": bucket, "shift": shift, "winrate": winrate}
                )
            else:
                feat_rows.append(
                    {"feature": base, "bucket": bucket, "shift": shift, "winrate": winrate}
                )

    df_role = pd.DataFrame(role_rows)
    df_feat = pd.DataFrame(feat_rows)

    # 役（hc別）
    if not df_role.empty:
        summary_roles = df_role.groupby(["role_key", "bucket"]).size().unstack(fill_value=0)
        summary_roles["平均Shift"]   = df_role.groupby("role_key")["shift"].mean().round(2)
        summary_roles["標準偏差"]    = df_role.groupby("role_key")["shift"].std().round(2)
        summary_roles["平均Winrate"] = df_role.groupby("role_key")["winrate"].mean().round(2)
        cols = [c for c in BUCKETS if c in summary_roles.columns]
        summary_roles = summary_roles.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary_roles = summary_roles.sort_values("平均Shift", ascending=False)
    else:
        summary_roles = pd.DataFrame()

    # 特徴（hcなし）
    if not df_feat.empty:
        summary_feats = df_feat.groupby(["feature", "bucket"]).size().unstack(fill_value=0)
        summary_feats["平均Shift"]   = df_feat.groupby("feature")["shift"].mean().round(2)
        summary_feats["標準偏差"]    = df_feat.groupby("feature")["shift"].std().round(2)
        summary_feats["平均Winrate"] = df_feat.groupby("feature")["winrate"].mean().round(2)
        cols = [c for c in BUCKETS if c in summary_feats.columns]
        summary_feats = summary_feats.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary_feats = summary_feats.sort_values("平均Shift", ascending=False)
    else:
        summary_feats = pd.DataFrame()

    return summary_roles, summary_feats

# ====== UI ======
st.title("特徴量別 勝率シフト集計（Features or Detail の newmade_* を集計）")

files = st.file_uploader("Shift結果のCSVをアップロード（複数可）", type="csv", accept_multiple_files=True)

if files:
    df_all = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    st.success(f"{len(files)} ファイル, 合計 {len(df_all)} 行を読み込みました。")

    roles, feats = analyze_roles_and_features(df_all)

    if not roles.empty:
        st.subheader("🟩 役（hc別）")
        st.dataframe(roles)
        st.download_button(
            "📥 役（hc別）CSVを保存",
            data=roles.to_csv(index=True, encoding="utf-8-sig"),
            file_name="summary_roles_hc.csv",
            mime="text/csv",
        )

    if not feats.empty:
        st.subheader("🟦 特徴（hcなし）")
        st.dataframe(feats)
        st.download_button(
            "📥 特徴CSVを保存",
            data=feats.to_csv(index=True, encoding="utf-8-sig"),
            file_name="summary_features.csv",
            mime="text/csv",
        )

    if roles.empty and feats.empty:
        st.info("newmade_* が見つかりませんでした（Features/Detailのどちらにも存在しない可能性があります）。")
else:
    st.caption("※ ShiftFlopで特徴が Detail 列に入っている古いCSVでも、そのまま集計できます。")
# ============================================================
#   役を hc0 / hc1 / hc2 の 3 グループに分けて集計する
# ============================================================

def analyze_by_hc_groups(df: pd.DataFrame):
    """
    役(newmade_*)をHCごとに3つに完全分割して集計する。
    hc0 = hc0 + hcnone
    hc1 = hc1
    hc2 = hc2
    """
    hc_groups = {
        "hc0": [],
        "hc1": [],
        "hc2": [],
    }

    for _, row in df.iterrows():
        bucket = get_bucket(row.get("Shift"))
        if bucket is None:
            continue
        try:
            shift = float(row.get("Shift"))
            winrate = float(row.get("Winrate"))
        except Exception:
            continue

        # 役や特徴を抽出（Features + Detail）
        items = collect_newmade_items(row)
        if not items:
            continue

        for item in items:
            if item in EXCLUDED_FEATURES:
                continue
            m = ROLE_RE.match(item)
            if not m:
                continue

            base, hc = m.group(1), m.group(2)

            # 役だけ対象（特徴は無視）
            if base not in MADE_ROLES:
                continue

            # ペアの hc2 は理論上不正 → 除外
            if base == "newmade_pair" and hc == "2":
                continue

            # hc をカテゴリへ振り分け
            if hc is None:
                group = "hc0"      # ← hcnone は hc0 として扱う（あなたの要望）
            elif hc == "0":
                group = "hc0"
            elif hc == "1":
                group = "hc1"
            else:
                group = "hc2"

            hc_groups[group].append({
                "role": base,
                "bucket": bucket,
                "shift": shift,
                "winrate": winrate,
            })

    # --- 各 hc グループを度数分布に変換 ---
    summaries = {}
    for key, rows in hc_groups.items():
        if not rows:
            summaries[key] = pd.DataFrame()
            continue

        df_hc = pd.DataFrame(rows)
        summary = df_hc.groupby(["role", "bucket"]).size().unstack(fill_value=0)
        summary["平均Shift"]   = df_hc.groupby("role")["shift"].mean().round(2)
        summary["標準偏差"]    = df_hc.groupby("role")["shift"].std().round(2)
        summary["平均Winrate"] = df_hc.groupby("role")["winrate"].mean().round(2)

        cols = [c for c in BUCKETS if c in summary.columns]
        summary = summary.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary = summary.sort_values("平均Shift", ascending=False)

        summaries[key] = summary

    return summaries
    # ====== 追加：HC別分析結果の表示 ======
st.header("HC 別集計（役のみを hc0 / hc1 / hc2 に分離）")

hc_summaries = analyze_by_hc_groups(df_all)

for hc_key, df_hc in hc_summaries.items():
    st.subheader(f"◎ {hc_key} の役集計")
    if df_hc.empty:
        st.info(f"{hc_key} のデータがありません。")
        continue

    st.dataframe(df_hc)
    st.download_button(
        f"📥 {hc_key} のCSV保存",
        data=df_hc.to_csv(index=True, encoding='utf-8-sig'),
        file_name=f"summary_roles_{hc_key}.csv",
        mime="text/csv",
    )
