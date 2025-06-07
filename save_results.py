import csv
import os

def save_shift_results(filename, hand, top10, bottom10):
    """
    勝率変動結果（トップ10・ワースト10）をCSVに保存する。
    """
    os.makedirs("results", exist_ok=True)
    filepath = os.path.join("results", f"{filename}_{hand}.csv")

    with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Rank", "RiverCard", "Winrate", "Shift", "Features", "Type"])

        for i, row in enumerate(top10, 1):
            writer.writerow([i, row['river_card'], row['winrate'], row['shift'], ';'.join(row['features']), "Top"])
        for i, row in enumerate(bottom10, 1):
            writer.writerow([i, row['river_card'], row['winrate'], row['shift'], ';'.join(row['features']), "Bottom"])

    print(f"保存完了: {filepath}")
