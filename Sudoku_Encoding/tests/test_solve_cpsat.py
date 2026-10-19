import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "..", "src"))

from solve_cpsat import solve_cpsat
from sudoku_amo import make_puzzle


def test_cpsat_solver():
    N = 9
    holes_ratio = 0.3
    seed = 42

    print(f"--- Bắt đầu test CP-SAT Solver cho Sudoku (N={N}, holes_ratio={holes_ratio}) ---")

    puzzle = make_puzzle(N, holes_ratio, seed)
    print("\nĐề bài Sudoku:")
    for row in puzzle:
        print(" ".join(row))
    print("\n" + "=" * 60)

    print(f"{'Solver':<10} | {'Trạng thái':<10} | {'Encoding(s)':>12} | {'Solve(s)':>10}")
    print("-" * 60)

    status, _, t_build, t_solve = solve_cpsat(N, puzzle, time_limit=60)
    print(f"{'CP-SAT':<10} | {status:<10} | {t_build:12.4f} | {t_solve:10.4f}")

    assert status == "SAT", f"CP-SAT trả về {status} cho một đề Sudoku hợp lệ"


if __name__ == "__main__":
    test_cpsat_solver()
    print("\n=> CP-SAT Solver vượt qua bài test.")