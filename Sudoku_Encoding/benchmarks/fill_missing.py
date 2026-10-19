"""Chạy bù các dòng còn thiếu trong benchmark_results.csv (không chạy lại thứ đã có).

Đặt cùng thư mục với benchmark.py (thư mục benchmarks/).

    python fill_missing.py --dry-run          # chỉ liệt kê việc sẽ chạy (nên làm bước này trước)
    python fill_missing.py                    # chạy bù, ghi nối vào CSV; bị ngắt thì chạy lại là tiếp tục
    python fill_missing.py --include-single   # chạy cả instance mới chỉ có 1 phương pháp (rất lâu)
    python fill_missing.py --csv duong_dan/file.csv

Tập instance là mọi (N, hole, seed) đã có trong CSV. Với mỗi instance, phương pháp nào chưa có
dòng hợp lệ (không tính ERROR) thì chạy bù bằng các hàm solver trong benchmark.py, giới hạn 300 s.
"""
import argparse
import csv
import os
import sys

import pandas as pd

METHODS = ["sat_pairwise", "sat_seqcounter", "sat_bitwise", "sat_product", "sat_commander",
           "cplex_cp", "cplex_mip", "cpsat", "gurobi"]
HERE = os.path.dirname(os.path.abspath(__file__))


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=None)
    ap.add_argument("--tl", type=float, default=300.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--include-single", action="store_true",
                    help="chạy cả các instance mới chỉ có 1 phương pháp (thiếu 8 phương pháp)")
    return ap.parse_args()


def find_csv(explicit):
    candidates = [explicit] if explicit else [
        os.path.join(HERE, "..", "results", "benchmark_results.csv"),
        os.path.join(HERE, "benchmark_results.csv"),
        os.path.join(os.getcwd(), "results", "benchmark_results.csv"),
        os.path.join(os.getcwd(), "benchmark_results.csv"),
    ]
    path = next((p for p in candidates if p and os.path.exists(p)), None)
    if path is None:
        print("Không tìm thấy CSV. Đã tìm ở:")
        for p in candidates:
            print("  ", os.path.abspath(p))
        sys.exit(1)
    return os.path.abspath(path)


def plan_missing(d, include_single):
    """Trả về (todo, single): các lần chạy bù cần làm và các instance chỉ có 1 phương pháp."""
    valid = d[d["Status"] != "ERROR"]
    have = set(zip(valid["N"].astype(int), valid["Hole Ratio"].astype(float),
                   valid["Seed"].astype(int), valid["Method"]))
    instances = sorted(set(zip(d["N"].astype(int), d["Hole Ratio"].astype(float),
                               d["Seed"].astype(int))))

    todo = []
    for N, h, s in instances:
        missing = [m for m in METHODS if (N, h, s, m) not in have]
        if len(missing) == len(METHODS) - 1 and not include_single:
            continue
        todo.extend((N, h, s, m) for m in missing)

    single = [(N, h, s) for N, h, s in instances
              if sum((N, h, s, m) in have for m in METHODS) == 1]
    return instances, todo, single


def to_label(status, elapsed, time_limit, ok_label):
    """Quy trạng thái của solver về nhãn trong CSV."""
    if status in ("SAT", "SOLVED"):
        return ok_label
    if status == "TIMEOUT":
        return "TIMEOUT"
    if status == "UNSAT" and elapsed >= time_limit - 1:  # cplex_mip hay báo nhầm timeout thành UNSAT
        return "TIMEOUT"
    return status


def run_one(b, method, N, puzzle, time_limit):
    """Chạy một phương pháp bằng các hàm solver của benchmark.py, trả về (status, t_enc, t_solve)."""
    if method.startswith("sat_"):
        return b.solve_sat_with_timeout(N, puzzle, method.replace("sat_", ""), time_limit=time_limit)
    solver = {"cplex_cp": b.solve_cplex_cp, "cplex_mip": b.solve_cplex,
              "cpsat": b.solve_cpsat, "gurobi": b.solve_gurobi}[method]
    status, _, t_enc, t_solve = solver(N, puzzle, time_limit=time_limit)
    return status, t_enc, t_solve


def run_missing(path, header, todo, time_limit, ok_label):
    sys.path.insert(0, HERE)
    import benchmark as b

    puzzle_cache = {}  # chỉ giữ instance hiện tại để tiết kiệm bộ nhớ
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for i, (N, h, s, m) in enumerate(todo, 1):
            key = (N, h, s)
            if key not in puzzle_cache:
                puzzle_cache = {key: b.make_puzzle(N, h, s)}
            print(f"[{i}/{len(todo)}] {m} N={N} hole={h} seed={s} ...", flush=True)

            try:
                status, t_enc, t_solve = run_one(b, m, N, puzzle_cache[key], time_limit)
            except Exception as e:
                print("   [Lỗi]", repr(e)[:200])
                continue

            label = to_label(status, t_enc + t_solve, time_limit, ok_label)
            if label == "ERROR":
                print("   status ERROR, không ghi vào CSV")
                continue

            row = {"N": N, "Hole Ratio": h, "Seed": s, "Method": m, "Status": label,
                   "Encoding Time (s)": round(t_enc, 4), "Solving Time (s)": round(t_solve, 4),
                   "Total Time (s)": round(t_enc + t_solve, 4)}
            writer.writerow([row.get(c, "") for c in header])
            f.flush()
            print(f"   -> {label}  enc={t_enc:.3f}s solve={t_solve:.3f}s")


def main():
    a = parse_args()
    path = find_csv(a.csv)
    print("CSV:", path)

    d = pd.read_csv(path)
    d["Hole Ratio"] = d["Hole Ratio"].round(4)
    ok_label = "SOLVED" if "SOLVED" in set(d["Status"]) else "SAT"
    print(f"Nhãn thành công trong CSV: {ok_label}")

    instances, todo, single = plan_missing(d, a.include_single)
    print(f"\nSố instance trong CSV: {len(instances)}")
    print(f"Số lần chạy bù cần làm: {len(todo)}")

    by_method = {}
    for N, h, s, m in todo:
        by_method.setdefault(m, []).append((N, h, s))
    for m, items in by_method.items():
        print(f"  {m}: {len(items)} lần  ví dụ {items[:3]}")
    if single and not a.include_single:
        print(f"\nBỏ qua {len(single)} instance chỉ có 1 phương pháp "
              f"(dùng --include-single nếu muốn chạy): {single}")

    if a.dry_run or not todo:
        print("\n(dry-run / không có việc gì) -> không chạy solver.")
        return

    run_missing(path, list(d.columns), todo, a.tl, ok_label)
    print("\nXong. Chạy lại với --dry-run để kiểm tra còn thiếu gì.")


if __name__ == "__main__":
    main()