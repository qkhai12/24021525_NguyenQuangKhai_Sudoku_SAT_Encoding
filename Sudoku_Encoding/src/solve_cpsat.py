import time
from math import isqrt

from ortools.sat.python import cp_model

from sudoku_amo import symbol_to_value


def solve_cpsat(N, puzzle, time_limit=60):
    """Giải Sudoku bằng OR-Tools CP-SAT (một worker, các tham số khác mặc định).

    Trả về (status, t_total, t_build, t_solve); status là SAT / UNSAT / TIMEOUT.
    """
    t0 = time.perf_counter()
    B = isqrt(N)
    model = cp_model.CpModel()

    x = [[model.NewIntVar(0, N - 1, f"x_{r}_{c}") for c in range(N)] for r in range(N)]

    for i in range(N):
        model.AddAllDifferent([x[i][c] for c in range(N)])
        model.AddAllDifferent([x[r][i] for r in range(N)])

    for br in range(B):
        for bc in range(B):
            model.AddAllDifferent([
                x[br * B + i][bc * B + j] for i in range(B) for j in range(B)
            ])

    for r in range(N):
        for c in range(N):
            if puzzle[r][c] != ".":
                model.Add(x[r][c] == symbol_to_value(puzzle[r][c]))

    t_build = time.perf_counter() - t0

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 1

    t1 = time.perf_counter()
    status = solver.Solve(model)
    t_solve = time.perf_counter() - t1
    t_total = time.perf_counter() - t0

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        res = "SAT"
    elif status == cp_model.INFEASIBLE:
        res = "UNSAT"
    else:
        res = "TIMEOUT"

    return res, t_total, t_build, t_solve