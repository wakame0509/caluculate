# analyze_shift_data.py

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from hand_group_dict import hand_group_mapping

# CSVファイル読み込み
df = pd.read_csv("shift_results.csv")

# ハンドグループ付与
df['HandGroup'] = df['Flop'].apply(lambda x: hand_group_mapping.get(x.split()[0], 'Other'))

# 特徴量がある行のみ（ShiftTurn / ShiftRiver 対象）
df_feat = df[df['Features'].notna()].copy()

# 複数特徴がある場合は分割
df_feat['Features'] = df_feat['Features'].str.split(', ')
df_exploded = df_feat.explode('Features')

# グループ × 特徴量ごとに平均勝率変動を計算
pivot = df_exploded.pivot_table(index='HandGroup', columns='Features', values='Shift', aggfunc='mean')

# ヒートマップ描画
plt.figure(figsize=(12, 6))
sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn", center=0)
plt.title("HandGroup × Feature 平均勝率変動（Shift）")
plt.tight_layout()
plt.savefig("summary_heatmap.png")
plt.show()
