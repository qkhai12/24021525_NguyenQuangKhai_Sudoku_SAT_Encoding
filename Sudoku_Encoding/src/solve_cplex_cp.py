"""Giải Sudoku bằng CPLEX CP Optimizer (qua docplex.cp).

Mô hình: N^2 biến nguyên y[r, c] thuộc {0..N-1} và ràng buộc toàn cục all_diff.
Đo riêng thời gian dựng mô hình (t_build) và thời gian giải (t_solve).
"""
import os
import sys
import time
from math import isqrt

from docplex.cp.config import context
from docplex.cp.model import CpoModel, all_diff

from sudoku_amo import symbol_to_value

CPO_BIN_DIR = r"C:\Program Files\IBM\ILOG\CPLEX_Studio222\cpoptimizer\bin\x64_win64"
CPO_EXEC = os.path.join(CPO_BIN_DIR, "cpoptimizer.exe")

# Nạp engine local bản đầy đủ từ CPLEX Studio thay vì bản community của gói pip.
if os.path.exists(CPO_EXEC):
    context.solver.agent = "local"
    context.solver.local.exec_path = CPO_EXEC
    os.environ["PATH"] = CPO_BIN_DIR + os.pathsep + os.environ["PATH"]
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(CPO_BIN_DIR)
        except Exception:
            pass


def solve_cplex_cp(N, puzzle, time_limit=60, return_grid=False, threads=1, verbose=False):
    """Giải Sudoku bằng CPLEX CP Optimizer.

    Trả về (status, t_total, t_build, t_solve), thêm `grid` ở cuối nếu return_grid=True.
    status là SAT / UNSAT / TIMEOUT.
    """
    t0 = time.perf_counter()
    B = isqrt(N)

    mdl = CpoModel(name="Sudoku_CPLEX_CP")
    y = {
        (r, c): mdl.integer_var(min=0, max=N - 1, name=f"y_{r}_{c}")
        for r in range(N) for c in range(N)
    }

    for r in range(N):
        mdl.add(all_diff([y[r, c] for c in range(N)]))
    for c in range(N):
        mdl.add(all_diff([y[r, c] for r in range(N)]))
    for br in range(B):
        for bc in range(B):
            mdl.add(all_diff([y[br * B + i, bc * B + j] for i in range(B) for j in range(B)]))

    for r in range(N):
        for c in range(N):
            if puzzle[r][c] != ".":
                mdl.add(y[r, c] == symbol_to_value(puzzle[r][c]))

    t_build = time.perf_counter() - t0

    t1 = time.perf_counter()
    sol = mdl.solve(
        TimeLimit=time_limit,
        Workers=threads,
        log_output=sys.stdout if verbose else None,
    )
    t_solve = time.perf_counter() - t1
    t_total = time.perf_counter() - t0

    if sol and sol.is_solution():
        res = "SAT"
    elif sol and sol.get_solve_status() == "Infeasible":
        res = "UNSAT"
    else:
        res = "TIMEOUT" if t_solve >= time_limit else "UNSAT"

    if not return_grid:
        return res, t_total, t_build, t_solve

    grid = None
    if res == "SAT":
        grid = [[int(sol.get_value(y[r, c])) for c in range(N)] for r in range(N)]
    return res, t_total, t_build, t_solve, grid


if __name__ == "__main__":
    from sudoku_amo import make_puzzle

    try:
        from sudoku_check import validate
    except ImportError:
        validate = None

    print(f"{'N':>3s} {'status':6s} {'Encoding(s)':>12s} {'Solve(s)':>10s} {'Total(s)':>10s} {'Check'}")
    print("-" * 55)

    for N in (9, 16, 25):
        puzzle = make_puzzle(N, 0.3, seed=1)
        st, t_tot, t_enc, t_sol, grid = solve_cplex_cp(N, puzzle, time_limit=60, return_grid=True)
        ok = ""
        if st == "SAT" and validate and grid:
            validate(N, puzzle, grid)
            ok = "đáp án đúng"
        print(f"{N:3d} {st:6s} {t_enc:12.4f} {t_sol:10.4f} {t_tot:10.4f} {ok}")