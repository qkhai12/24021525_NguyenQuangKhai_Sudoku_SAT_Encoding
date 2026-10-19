import csv
import os
import sys

import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "..", "src")
results_dir = os.path.join(current_dir, "..", "results")
sys.path.insert(0, src_dir)

from sudoku_amo import AMO_METHODS, build_clauses, make_puzzle

N_VALUES = [9, 16, 25, 36, 49, 64, 81]
REF_HOLE_RATIO = 0.50   # instance mẫu để đếm; số clue ở các hole ratio khác suy ra từ chênh lệch
REF_SEED = 1
BASE_COLS = ["N", "Hole Ratio", "Seed", "Method", "Status",
             "Encoding Time (s)", "Solving Time (s)", "Total Time (s)"]


def num_clues(N, hole_ratio):
    return N * N - int(hole_ratio * N * N)


def compute_model_stats():
    """Trả về (stats_rows, stats_map): số biến và số ràng buộc/clause theo (N, method).

    Số liệu tính cho instance (N, REF_HOLE_RATIO, REF_SEED). Riêng pairwise với N >= 64
    dùng công thức thay vì dựng CNF (hàng chục triệu clause) để tránh tràn RAM.
    """
    stats_rows = []
    stats_map = {}

    def add(N, method, n_vars, n_constraints):
        stats_rows.append([N, method, n_vars, n_constraints])
        stats_map[(N, method)] = (n_vars, n_constraints)

    for N in N_VALUES:
        puzzle = make_puzzle(N, REF_HOLE_RATIO, REF_SEED)
        clues = num_clues(N, REF_HOLE_RATIO)

        for amo_name, amo_fn in AMO_METHODS.items():
            method_name = f"sat_{amo_name}"
            if amo_name == "pairwise" and N >= 64:
                n_vars = N**3
                # 4N^2 nhóm, mỗi nhóm có 1 clause ALO và N(N-1)/2 clause AMO
                n_clauses = 4 * (N**2) * (1 + (N * (N - 1)) // 2) + clues
            else:
                try:
                    clauses = build_clauses(N, puzzle, amo_fn)
                    n_vars = max(abs(l) for cl in clauses for l in cl)
                    n_clauses = len(clauses)
                except Exception as e:
                    print(f"Lỗi khi đếm clause {method_name} (N={N}): {e}")
                    n_vars, n_clauses = 0, 0
            add(N, method_name, n_vars, n_clauses)

        for method_name in ("cplex_mip", "gurobi"):
            add(N, method_name, N**3, 4 * (N**2) + clues)
        for method_name in ("cplex_cp", "cpsat"):
            add(N, method_name, N**2, 3 * N + clues)

    return stats_rows, stats_map


def merge_into_benchmark(benchmark_csv_file, stats_map):
    """Điền cột Vars/Constraints vào cuối benchmark_results.csv.

    Hai cột đặt ở cuối để benchmark.py (ghi 8 cột) vẫn ghi nối được. Số constraint được điều
    chỉnh theo số clue thực tế của từng dòng so với instance mẫu.
    """
    def exact_stats(row):
        N = int(row["N"])
        diff = num_clues(N, float(row["Hole Ratio"])) - num_clues(N, REF_HOLE_RATIO)
        n_vars, n_constraints = stats_map.get((N, str(row["Method"])), (0, 0))
        return pd.Series([n_vars, n_constraints + diff if n_constraints > 0 else 0])

    df = pd.read_csv(benchmark_csv_file)
    df[["Vars", "Constraints"]] = df.apply(exact_stats, axis=1)

    final_cols = BASE_COLS + ["Vars", "Constraints"]
    df = df[[c for c in final_cols if c in df.columns]]
    df.to_csv(benchmark_csv_file, index=False, encoding="utf-8")


def export_and_merge_stats():
    os.makedirs(results_dir, exist_ok=True)
    stats_csv_file = os.path.join(results_dir, "model_statistics.csv")
    benchmark_csv_file = os.path.join(results_dir, "benchmark_results.csv")

    print("Đang tính toán số lượng biến và ràng buộc/mệnh đề...")
    stats_rows, stats_map = compute_model_stats()

    with open(stats_csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["N", "Method", "Vars", "Constraints_Clauses"])
        writer.writerows(stats_rows)
    print(f"=> [Thành công 1/2] Đã xuất bảng thống kê tại: {stats_csv_file}")

    if not os.path.exists(benchmark_csv_file):
        print(f"Chưa thấy file {benchmark_csv_file}, dữ liệu sẽ được dùng khi bạn chạy benchmark.")
        return

    try:
        merge_into_benchmark(benchmark_csv_file, stats_map)
        print(f"=> [Thành công 2/2] Đã điền 2 cột 'Vars' và 'Constraints' vào CUỐI file: {benchmark_csv_file}")
    except Exception as e:
        print(f"Lỗi khi merge: {e}")


if __name__ == "__main__":
    export_and_merge_stats()