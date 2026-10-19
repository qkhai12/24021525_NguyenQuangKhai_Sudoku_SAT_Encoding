import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "..", "src"))

from solve_cplex_cp import solve_cplex_cp
from sudoku_amo import make_puzzle


def test_cplex_cp_solver():
    N = 9
    holes_ratio = 0.3
    seed = 42

    print(f"--- Bắt đầu test CPLEX CP Optimizer cho Sudoku (N={N}, holes_ratio={holes_ratio}) ---")

    puzzle = make_puzzle(N, holes_ratio, seed)
    print("\nĐề bài Sudoku:")
    for row in puzzle:
        print(" ".join(row))
    print("\n" + "=" * 75)

    print(f"{'Solver':<12} | {'Trạng thái':<10} | {'Encoding(s)':>12} | {'Solve(s)':>10} | {'Total(s)':>10}")
    print("-" * 75)

    status, t_tot, t_build, t_solve, grid = solve_cplex_cp(
        N, puzzle, time_limit=60, return_grid=True
    )
    print(f"{'CPLEX CP':<12} | {status:<10} | {t_build:12.4f} | {t_solve:10.4f} | {t_tot:10.4f}")

    assert status == "SAT", f"CPLEX CP trả về {status} cho một đề Sudoku hợp lệ"


if __name__ == "__main__":
    test_cplex_cp_solver()
    print("\n=> CPLEX CP Solver vượt qua bài test.")