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
                if isinstance(shift_feats, dict) and len(shift_feats) > 0:
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
                else:
                    # 空dictでも1行だけ出力（ShiftFlop結果が失われないように）
                    csv_rows.append({
                        "Stage": "ShiftFlop",
                        "Flop": flop_str,
                        "Turn": "",
                        "Detail": "―",
                        "Shift": "",
                        "Winrate": static_wr_flop,
                        "Features": "",
                        "Role": "",
                        "Hand": hand_str
                    })

                # --- ShiftTurn ---
                turn_entries = []
                if hand_str in auto_turn:
                    tlist = auto_turn[hand_str]
                    if i < len(tlist):
                        turn_entries_raw = tlist[i]
                        if isinstance(turn_entries_raw, dict) and "all" in turn_entries_raw:
                            turn_entries.append(turn_entries_raw)
                        elif isinstance(turn_entries_raw, (list, tuple)):
                            for el in turn_entries_raw:
                                if isinstance(el, tuple) and len(el) == 3:
                                    all_list = el[0] if el[0] else []
                                    turn_entries.append({"turn_card": None, "all": all_list})
                                elif isinstance(el, dict):
                                    turn_entries.append({"turn_card": el.get("turn_card", None), "all": el.get("all", [el])})
                                elif isinstance(el, str):
                                    try:
                                        parsed = ast.literal_eval(el)
                                        if isinstance(parsed, dict):
                                            turn_entries.append(parsed if "all" in parsed else {"turn_card": parsed.get("turn_card"), "all": [parsed]})
                                    except Exception:
                                        continue
                        elif isinstance(turn_entries_raw, str):
                            try:
                                parsed = ast.literal_eval(turn_entries_raw)
                                if isinstance(parsed, dict) and "all" in parsed:
                                    turn_entries.append(parsed)
                                elif isinstance(parsed, list):
                                    for el in parsed:
                                        if isinstance(el, dict):
                                            turn_entries.append({"turn_card": el.get("turn_card"), "all": [el]})
                            except Exception:
                                pass

                seen_turn = set()
                for tentry in turn_entries:
                    all_turns = tentry.get("all") if isinstance(tentry, dict) else tentry
                    if isinstance(all_turns, str):
                        try:
                            all_turns = ast.literal_eval(all_turns)
                        except Exception:
                            all_turns = []
                    if not isinstance(all_turns, list):
                        all_turns = [all_turns]

                    for item in all_turns:
                        if isinstance(item, str):
                            try:
                                item = ast.literal_eval(item)
                            except Exception:
                                continue
                        if not isinstance(item, dict):
                            continue
                        tc = item.get("turn_card", None)
                        if tc in seen_turn:
                            continue
                        seen_turn.add(tc)
                        made = item.get("hand_rank", "―")
                        if made == "high_card":
                            made = "―"
                        feats = [f for f in item.get("features", []) if f.startswith("newmade_")]
                        if not feats:
                            feats = ["―"]
                        wr = item.get("winrate", None)
                        shift = None
                        if wr is not None:
                            try:
                                shift = round(float(wr) - float(static_wr_flop), 2)
                                wr = round(float(wr), 2)
                            except Exception:
                                shift = ""
                        csv_rows.append({
                            "Stage": "ShiftTurn",
                            "Flop": flop_str,
                            "Turn": tc or "―",
                            "Detail": tc or "―",
                            "Shift": shift,
                            "Winrate": wr if wr is not None else "―",
                            "Features": ', '.join(feats),
                            "Role": made,
                            "Hand": hand_str
                        })

                # --- shiftriver ---
                if hand_str in auto_river:
                    rlist = auto_river[hand_str]
                    if i < len(rlist):
                        river_data = rlist[i]
                        # river_data は「ターンごとのリスト」
                        if isinstance(river_data, list):
                            for turn_block in river_data:
                                turn_card = turn_block.get("turn_card", "―")
                                river_items = turn_block.get("all", [])
                                if not isinstance(river_items, list):
                                    continue

                                seen_river = set()
                                for item in river_items:
                                    if not isinstance(item, dict):
                                        continue
                                    rc = item.get("river_card", None)
                                    if rc in seen_river:
                                        continue
                                    seen_river.add(rc)

                                    made = item.get("hand_rank", "―")
                                    if made == "high_card":
                                        made = "―"

                                    feats = [f for f in item.get("features", []) if f.startswith("newmade_")]
                                    if not feats:
                                        feats = ["―"]

                                    wr = item.get("winrate", None)
                                    shift = None
                                    if wr is not None:
                                        try:
                                            shift = round(float(wr) - float(static_wr_flop), 2)
                                            wr = round(float(wr), 2)
                                        except Exception:
                                            shift = ""

                                    csv_rows.append({
                                        "Stage": "ShiftRiver",
                                        "Flop": flop_str,
                                        "Turn": turn_card,
                                        "Detail": rc or "―",
                                        "Shift": shift,
                                        "Winrate": wr if wr is not None else "―",
                                        "Features": ', '.join(feats),
                                        "Role": made,
                                        "Hand": hand_str
                                    })
        # --- 保存処理 ---
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
import streamlit as st
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

# === 169ハンド集合（AA, AKo, AKs 形式） ===
def all_starting_hands_169():
    ranks = "AKQJT98765432"
    hands = set()
    for i, r1 in enumerate(ranks):
        for j, r2 in enumerate(ranks):
            if i == j:
                hands.add(r1 + r2)          # ペア
            elif i < j:
                # 上位文字を先に：例 AKs, AKo
                hands.add(r1 + r2 + "s")
                hands.add(r1 + r2 + "o")
            # i > j は既に追加済み
    return hands

EXPECTED_169 = all_starting_hands_169()

# === 役と特徴を分離して集計（役は hc0/hc1/hc2 を保持、特徴は hc なし） ===
_role_pat = re.compile(r"^(newmade_[a-z_]+?)(?:_hc([012]))?$")

def analyze_roles_and_features(df_all):
    role_recs = []     # 役（hc保持）
    feat_recs = []     # 特徴（hcなし）

    for _, row in df_all.iterrows():
        shift = row["Shift"]
        winrate = row["Winrate"]
        features = str(row["Features"]).split(", ")

        for tok in features:
            tok = tok.strip()
            if not tok.startswith("newmade_") or tok in excluded_features:
                continue

            m = _role_pat.match(tok)
            base = m.group(1) if m else tok
            hc = m.group(2)  # '0','1','2' or None

            if base in made_roles:
                # 役：hc をそのまま保持（無ければベース名のまま）
                name = f"{base}_hc{hc}" if hc is not None else base
                bucket = get_bucket(shift, True)
                role_recs.append({
                    "name": name, "bucket": bucket,
                    "shift": shift, "winrate": winrate
                })
            else:
                # 特徴：hc は存在しない想定 → ベース名で集計
                name = base
                bucket = get_bucket(shift, False)
                feat_recs.append({
                    "name": name, "bucket": bucket,
                    "shift": shift, "winrate": winrate
                })

    df_roles = pd.DataFrame(role_recs)
    df_feats = pd.DataFrame(feat_recs)

    # 役の集計（役は上昇側バケット定義を使う）
    summary_roles = (
        df_roles.groupby(["name", "bucket"]).size().unstack(fill_value=0)
        if not df_roles.empty else pd.DataFrame()
    )
    if not df_roles.empty:
        summary_roles["平均Shift"] = df_roles.groupby("name")["shift"].mean().round(2)
        summary_roles["標準偏差"] = df_roles.groupby("name")["shift"].std().round(2)
        summary_roles["平均Winrate"] = df_roles.groupby("name")["winrate"].mean().round(2)
        cols = [c for c in BUCKETS_MADE if c in summary_roles.columns]
        summary_roles = summary_roles.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary_roles = summary_roles.sort_values("平均Shift", ascending=False)

    # 特徴の集計（特徴は上下対称バケット定義を使う）
    summary_feats = (
        df_feats.groupby(["name", "bucket"]).size().unstack(fill_value=0)
        if not df_feats.empty else pd.DataFrame()
    )
    if not df_feats.empty:
        summary_feats["平均Shift"] = df_feats.groupby("name")["shift"].mean().round(2)
        summary_feats["標準偏差"] = df_feats.groupby("name")["shift"].std().round(2)
        summary_feats["平均Winrate"] = df_feats.groupby("name")["winrate"].mean().round(2)
        cols = [c for c in BUCKETS_NOTMADE if c in summary_feats.columns]
        summary_feats = summary_feats.reindex(columns=cols + ["平均Shift", "標準偏差", "平均Winrate"])
        summary_feats = summary_feats.sort_values("平均Shift", ascending=False)

    return summary_roles, summary_feats

# === Streamlit UI ===
st.title("特徴量別 勝率シフト度数分布＋統計（役と特徴を別集計／役はhc保持）")

uploaded_files = st.file_uploader("CSVファイルをアップロード（複数可）", type="csv", accept_multiple_files=True)

if uploaded_files:
    df_all = pd.concat([pd.read_csv(file) for file in uploaded_files], ignore_index=True)
    st.success(f"{len(uploaded_files)} ファイルを読み込みました。合計 {len(df_all)} 行のデータがあります。")

    # === 169ハンド網羅 & 重複チェック ===
    possible_cols = [c for c in ["Hand", "hand", "ハンド"] if c in df_all.columns]
    if possible_cols:
        hand_col = possible_cols[0]
        if "Stage" in df_all.columns:
            hand_rows = df_all[df_all["Stage"] == "HandInfo"]
            basis_note = "Stage=='HandInfo' 行を基準に判定"
        else:
            hand_rows = df_all
            basis_note = "Hand列全体を基準に判定（参考）"

        counts = hand_rows[hand_col].astype(str).value_counts(dropna=False)
        present_set = set(counts.index)
        missing = sorted(EXPECTED_169 - present_set)
        duplicates = sorted([h for h, n in counts.items() if n > 1])
        unexpected = sorted(present_set - EXPECTED_169)

        st.subheader("🃏 169ハンド網羅性・重複チェック")
        st.caption(f"基準: {basis_note}")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("検出ハンド数", len(present_set))
        with c2:
            st.metric("欠落ハンド数", len(missing))
        with c3:
            st.metric("重複ハンド数", len(duplicates))

        if missing:
            st.error(f"欠落ハンド（{len(missing)}）: {', '.join(missing)}")
        else:
            st.success("欠落ハンドはありません。")

        if duplicates:
            st.warning(f"重複ハンド（{len(duplicates)}）: {', '.join(duplicates)}")
        else:
            st.info("重複ハンドは検出されませんでした。")

        if unexpected:
            st.warning(f"想定外の表記（{len(unexpected)}）: {', '.join(unexpected)}")
    else:
        st.warning("⚠️ Hand列（Hand/hand/ハンド）が見つかりませんでした。ハンドの存在・重複チェックをスキップします。")

    # === 集計（役と特徴を別々に表示） ===
    summary_roles, summary_feats = analyze_roles_and_features(df_all)

    if not summary_roles.empty:
        st.subheader("🟥 役（hc0/hc1/hc2を保持）")
        st.dataframe(summary_roles)
        csv_roles = summary_roles.to_csv(index=True, encoding="utf-8-sig")
        st.download_button("📥 役の集計をCSV保存", data=csv_roles, file_name="summary_roles.csv", mime="text/csv")

    if not summary_feats.empty:
        st.subheader("🟦 特徴（hcなし）")
        st.dataframe(summary_feats)
        csv_feats = summary_feats.to_csv(index=True, encoding="utf-8-sig")
        st.download_button("📥 特徴の集計をCSV保存", data=csv_feats, file_name="summary_features.csv", mime="text/csv")
