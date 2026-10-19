"""Giải Sudoku bằng ILP (biến nhị phân x[r, c, v]) với Gurobi.

Đo riêng thời gian dựng mô hình (encoding) và thời gian giải (solving).
"""
import time
from math import isqrt

import gurobipy as gp
from gurobipy import GRB

from sudoku_amo import symbol_to_value


def solve_gurobi(N, puzzle, time_limit=60, return_grid=False, threads=1, verbose=False):
    """Giải Sudoku bằng Gurobi.

    Trả về (status, t_total, t_build, t_solve), thêm `grid` ở cuối nếu return_grid=True.
    status là một trong SAT / UNSAT / TIMEOUT / ERROR.
    """
    t0 = time.perf_counter()
    B = isqrt(N)

    env = gp.Env(empty=True)
    if not verbose:
        env.setParam("OutputFlag", 0)
    env.start()

    model = gp.Model("Sudoku_Gurobi", env=env)
    model.Params.TimeLimit = time_limit
    model.Params.Threads = threads

    x = model.addVars(N, N, N, vtype=GRB.BINARY, name="x")

    model.addConstrs(
        (x.sum(r, c, "*") == 1 for r in range(N) for c in range(N)), name="cell"
    )
    model.addConstrs(
        (x.sum(r, "*", v) == 1 for r in range(N) for v in range(N)), name="row"
    )
    model.addConstrs(
        (x.sum("*", c, v) == 1 for c in range(N) for v in range(N)), name="col"
    )
    model.addConstrs(
        (
            gp.quicksum(x[br * B + i, bc * B + j, v] for i in range(B) for j in range(B)) == 1
            for br in range(B) for bc in range(B) for v in range(N)
        ),
        name="box",
    )

    for r in range(N):
        for c in range(N):
            if puzzle[r][c] != ".":
                x[r, c, symbol_to_value(puzzle[r][c])].LB = 1.0

    model.update()
    t_build = time.perf_counter() - t0

    t1 = time.perf_counter()
    model.optimize()
    t_solve = time.perf_counter() - t1
    t_total = time.perf_counter() - t0

    if model.Status in (GRB.OPTIMAL, GRB.SUBOPTIMAL):
        res = "SAT"
    elif model.Status == GRB.INFEASIBLE:
        res = "UNSAT"
    elif model.Status == GRB.TIME_LIMIT:
        res = "TIMEOUT"
    else:
        res = "ERROR"

    if not return_grid:
        return res, t_total, t_build, t_solve

    grid = None
    if res == "SAT":
        grid = [
            [next(v for v in range(N) if x[r, c, v].X > 0.5) for c in range(N)]
            for r in range(N)
        ]
    return res, t_total, t_build, t_solve, grid


if __name__ == "__main__":
    from sudoku_amo import make_puzzle

    try:
        from sudoku_check import validate
    except ImportError:
        validate = None

    print(f"{'N':>3s} {'status':6s} {'Encoding(s)':>12s} {'Solve(s)':>10s} {'Total(s)':>10s} {'Check'}")
    print("-" * 55)

    for N in (9, 16, 25, 36):
        puzzle = make_puzzle(N, 0.3, seed=1)
        st, t_tot, t_enc, t_sol, grid = solve_gurobi(N, puzzle, time_limit=60, return_grid=True)
        ok = ""
        if st == "SAT" and validate and grid:
            validate(N, puzzle, grid)
            ok = "đáp án đúng"
        print(f"{N:3d} {st:6s} {t_enc:12.4f} {t_sol:10.4f} {t_tot:10.4f} {ok}")