import csv
import multiprocessing as mp
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, "..", "src"))
results_dir = os.path.abspath(os.path.join(current_dir, "..", "results"))
sys.path.insert(0, src_dir)

from sudoku_amo import AMO_METHODS, make_puzzle, solve

try:
    from solve_cplex_cp import solve_cplex_cp
    from solve_cplex_mip import solve_cplex
    from solve_cpsat import solve_cpsat
    from solve_gurobi import solve_gurobi
except ImportError as e:
    print(f"Canh bao: Thieu module solver - {e}")

TIME_LIMIT = 300
SEEDS = [1, 2, 3]
N_VALUES = [9, 16, 25, 36, 49, 64, 81]
HOLE_RATIOS_BY_N = {
    9: [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90],
    16: [0.30, 0.40, 0.50, 0.60, 0.70, 0.80],
    25: [0.30, 0.40, 0.50, 0.60],
    36: [0.20, 0.30, 0.40, 0.50],
    49: [0.20, 0.30, 0.40],
    64: [0.10, 0.20, 0.30, 0.40],
    81: [0.10, 0.20, 0.30, 0.40],
}
METHODS = [f"sat_{name}" for name in AMO_METHODS] + ["cplex_cp", "cplex_mip", "cpsat", "gurobi"]
CSV_HEADER = ["N", "Hole Ratio", "Seed", "Method", "Status",
              "Encoding Time (s)", "Solving Time (s)", "Total Time (s)"]


def normalize_status(status):
    """SAT -> solved, UNSAT -> unsolved; các trạng thái khác giữ nguyên (chữ hoa)."""
    status = status.strip().upper()
    if status == "SAT":
        return "solved"
    if status == "UNSAT":
        return "unsolved"
    return status


def is_valid_result(method, status, t_enc):
    """Một kết quả được tính là đã chạy xong nếu không lỗi và không phải cpsat với t_enc = 0."""
    return status != "ERROR" and not (method == "cpsat" and t_enc == 0.0)


def update_existing_results(csv_file):
    """Chuẩn hóa cột Status của CSV đã có (SAT/UNSAT -> solved/unsolved)."""
    if not os.path.exists(csv_file):
        print("Chua co file ket qua cu de cap nhat.")
        return

    with open(csv_file, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames or "Status" not in fieldnames:
            print("Canh bao: CSV khong co cot Status.")
            return
        rows = list(reader)

    changed = 0
    for row in rows:
        old_status = row.get("Status", "")
        new_status = normalize_status(old_status)
        if new_status != old_status:
            row["Status"] = new_status
            changed += 1

    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Da chuan hoa va cap nhat thanh cong ({changed} dong duoc doi moi).")


def _sat_worker(N, puzzle, amo_name, result_queue):
    """Chạy một lượt SAT trong tiến trình riêng để có thể dừng khi quá giờ."""
    try:
        ok, _, _, _, t_enc, t_solve = solve(N, puzzle, amo_name)
        result_queue.put(("SAT" if ok else "UNSAT", t_enc, t_solve))
    except Exception:
        result_queue.put(("ERROR", 0.0, 0.0))


def solve_sat_with_timeout(N, puzzle, amo_name, time_limit=TIME_LIMIT):
    """Giải SAT với giới hạn thời gian thực; quá giờ ghi (TIMEOUT, time_limit, 0.0)."""
    result_queue = mp.Queue()
    process = mp.Process(target=_sat_worker, args=(N, puzzle, amo_name, result_queue))
    process.start()
    process.join(timeout=time_limit)

    if process.is_alive():
        process.terminate()
        process.join()
        return "TIMEOUT", float(time_limit), 0.0

    if not result_queue.empty():
        return result_queue.get()
    return "ERROR", 0.0, 0.0


def get_completed_tasks(csv_file):
    """Đọc CSV cũ và trả về tập (seed, N, hole, method) đã chạy hợp lệ."""
    completed = set()
    if not os.path.exists(csv_file):
        return completed

    try:
        with open(csv_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) < 8:
                    continue
                N = int(row[0])
                hole = round(float(row[1]), 4)
                seed = int(row[2])
                method, status, t_enc = row[3], row[4], float(row[5])
                if is_valid_result(method, status, t_enc):
                    completed.add((seed, N, hole, method))
    except Exception as e:
        print(f"Loi khi doc CSV lich su: {e}")

    return completed


def run_method(method, N, puzzle, time_limit):
    """Chạy một phương pháp, trả về (status, t_enc, t_solve)."""
    if method.startswith("sat_"):
        return solve_sat_with_timeout(N, puzzle, method.replace("sat_", ""), time_limit)

    solvers = {
        "cplex_cp": solve_cplex_cp,
        "cplex_mip": solve_cplex,
        "cpsat": solve_cpsat,
        "gurobi": solve_gurobi,
    }
    status, _, t_enc, t_solve = solvers[method](N, puzzle, time_limit=time_limit)
    return status, t_enc, t_solve


def run_benchmarks():
    os.makedirs(results_dir, exist_ok=True)
    csv_file = os.path.join(results_dir, "benchmark_results.csv")

    update_existing_results(csv_file)
    completed_tasks = get_completed_tasks(csv_file)
    if completed_tasks:
        print(f"Da tim thay {len(completed_tasks)} ket qua hop le. Dang chuan bi chay tiep...")

    file_exists = os.path.exists(csv_file)

    with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADER)

        for seed in SEEDS:
            for N in N_VALUES:
                for hole in HOLE_RATIOS_BY_N.get(N, [0.10, 0.20, 0.30]):
                    hole = round(hole, 4)
                    puzzle = None

                    for method in METHODS:
                        if (seed, N, hole, method) in completed_tasks:
                            print(f"[Bo qua] {method} (N={N}, Hole={hole}, Seed={seed}) da co ket qua.")
                            continue

                        if puzzle is None:
                            print(f"\nDang tao Sudoku N={N}, Hole={hole}, Seed={seed}...")
                            puzzle = make_puzzle(N, hole, seed)

                        print(f"  -> Dang giai bang {method}...")

                        try:
                            status, t_enc, t_solve = run_method(method, N, puzzle, TIME_LIMIT)
                        except Exception as e:
                            print(f"      [Loi] {method}: {e}")
                            status, t_enc, t_solve = "ERROR", 0.0, 0.0

                        status = normalize_status(status)
                        writer.writerow([N, hole, seed, method, status,
                                         round(t_enc, 4), round(t_solve, 4),
                                         round(t_enc + t_solve, 4)])
                        f.flush()

                        if is_valid_result(method, status, t_enc):
                            completed_tasks.add((seed, N, hole, method))

    print(f"\n=> Benchmark hoan tat! Ket qua luu tai: {csv_file}")


if __name__ == "__main__":
    run_benchmarks()