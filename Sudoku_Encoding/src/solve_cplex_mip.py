"""Giải Sudoku bằng ILP (biến nhị phân x[r, c, v]) qua cplex.exe của CPLEX Studio.

Gọi trực tiếp cplex.exe để tránh giới hạn 1000 biến của gói pip.
Đo riêng thời gian dựng mô hình (t_build) và thời gian giải (t_solve).
"""
import os
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from math import isqrt

from docplex.mp.model import Model

from sudoku_amo import symbol_to_value

CPLEX_EXEC = r"C:\Program Files\IBM\ILOG\CPLEX_Studio222\cplex\bin\x64_win64\cplex.exe"


def solve_cplex(N, puzzle, time_limit=60, return_grid=False, threads=1, verbose=False):
    """Giải Sudoku bằng cplex.exe trên file LP xuất từ docplex.

    Trả về (status, t_total, t_build, t_solve), thêm `grid` ở cuối nếu return_grid=True.
    status là SAT / UNSAT / TIMEOUT; SAT khi cplex.exe ghi ra file nghiệm.
    """
    t0 = time.perf_counter()
    B = isqrt(N)

    mdl = Model(name="Sudoku_CPLEX")
    x = {
        (r, c, v): mdl.binary_var(name=f"x_{r}_{c}_{v}")
        for r in range(N) for c in range(N) for v in range(N)
    }

    for r in range(N):
        for c in range(N):
            mdl.add_constraint(mdl.sum(x[r, c, v] for v in range(N)) == 1)
    for r in range(N):
        for v in range(N):
            mdl.add_constraint(mdl.sum(x[r, c, v] for c in range(N)) == 1)
    for c in range(N):
        for v in range(N):
            mdl.add_constraint(mdl.sum(x[r, c, v] for r in range(N)) == 1)
    for br in range(B):
        for bc in range(B):
            for v in range(N):
                mdl.add_constraint(
                    mdl.sum(x[br * B + i, bc * B + j, v] for i in range(B) for j in range(B)) == 1
                )

    for r in range(N):
        for c in range(N):
            if puzzle[r][c] != ".":
                mdl.add_constraint(x[r, c, symbol_to_value(puzzle[r][c])] == 1)

    with tempfile.TemporaryDirectory() as tmpdir:
        lp_path = os.path.join(tmpdir, "sudoku.lp")
        sol_path = os.path.join(tmpdir, "sudoku.sol")
        cmd_path = os.path.join(tmpdir, "cplex_cmds.txt")

        mdl.export_as_lp(lp_path)
        t_build = time.perf_counter() - t0

        t1 = time.perf_counter()
        cmd_script = (
            f'read "{lp_path}"\n'
            f"set threads {threads}\n"
            f"set timelimit {time_limit}\n"
            f"optimize\n"
            f'write "{sol_path}"\n'
            f"quit\n"
        )
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(cmd_script)

        if not os.path.exists(CPLEX_EXEC):
            raise FileNotFoundError(f"Không tìm thấy file cplex.exe tại: {CPLEX_EXEC}")

        try:
            subprocess.run(
                [CPLEX_EXEC, "-f", cmd_path],
                capture_output=not verbose,
                text=True,
                timeout=time_limit + 10,
            )
            t_solve = time.perf_counter() - t1
        except subprocess.TimeoutExpired:
            t_solve = time.perf_counter() - t1
            t_total = time.perf_counter() - t0
            if return_grid:
                return "TIMEOUT", t_total, t_build, t_solve, None
            return "TIMEOUT", t_total, t_build, t_solve

        t_total = time.perf_counter() - t0

        res = "SAT" if os.path.exists(sol_path) else "UNSAT"

        grid = None
        if res == "SAT" and return_grid:
            chosen = {
                var.attrib.get("name")
                for var in ET.parse(sol_path).getroot().iter("variable")
                if float(var.attrib.get("value", 0)) > 0.5
                and var.attrib.get("name").startswith("x_")
            }
            grid = [
                [next((v for v in range(N) if f"x_{r}_{c}_{v}" in chosen), 0) for c in range(N)]
                for r in range(N)
            ]

        if return_grid:
            return res, t_total, t_build, t_solve, grid
        return res, t_total, t_build, t_solve


if __name__ == "__main__":
    from sudoku_amo import make_puzzle

    print(f"{'N':>3s} {'status':6s} {'Encoding(s)':>12s} {'Solve(s)':>10s} {'Total(s)':>10s}")
    print("-" * 50)

    for N in (9, 16, 25):
        puzzle = make_puzzle(N, 0.3, seed=1)
        st, t_tot, t_enc, t_sol = solve_cplex(N, puzzle, time_limit=60)
        print(f"{N:3d} {st:6s} {t_enc:12.4f} {t_sol:10.4f} {t_tot:10.4f}")