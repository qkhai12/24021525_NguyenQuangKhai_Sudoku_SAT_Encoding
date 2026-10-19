import os
import shutil

import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
results_dir = os.path.abspath(os.path.join(current_dir, "..", "results"))
csv_file = os.path.join(results_dir, "benchmark_results.csv")
backup_file = os.path.join(results_dir, "benchmark_results.backup.csv")

KEY = ["N", "Hole Ratio", "Seed"]


def clean_benchmark_results():
    """Xóa dòng trùng (giữ dòng cuối) và các instance không đủ mọi method.

    File gốc được sao lưu một lần sang benchmark_results.backup.csv trước khi ghi đè.
    """
    if not os.path.exists(csv_file):
        print(f"Không tìm thấy file kết quả tại: {csv_file}")
        return

    df = pd.read_csv(csv_file)
    initial_count = len(df)

    df = df.drop_duplicates(subset=KEY + ["Method"], keep="last")
    after_dup = len(df)

    n_methods = df["Method"].nunique()
    group_size = df.groupby(KEY)["Method"].transform("size")
    incomplete = df[group_size != n_methods]
    df = df[group_size == n_methods]

    if len(df) == initial_count:
        print("Dữ liệu đã sạch, không có gì để xóa.")
        return

    if not os.path.exists(backup_file):
        shutil.copy2(csv_file, backup_file)

    if len(incomplete):
        print("Các dòng thuộc nhóm không đủ method sẽ bị xóa:")
        print(incomplete[KEY + ["Method", "Status"]].to_string(index=False))

    df.to_csv(csv_file, index=False, encoding="utf-8")

    print("\nĐã làm sạch file thành công!")
    print(f"- Số dòng ban đầu: {initial_count}")
    print(f"- Số dòng trùng lặp đã xóa: {initial_count - after_dup}")
    print(f"- Số dòng thuộc nhóm thiếu method đã xóa: {len(incomplete)}")
    print(f"- Số dòng sau khi chuẩn hóa: {len(df)}")
    print(f"- File sao lưu: {backup_file}")


if __name__ == "__main__":
    clean_benchmark_results()