import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "..", "src"))

from sudoku_amo import AMO_METHODS, make_puzzle, solve


def test_sudoku_sat_solver():
    """Mọi AMO encoding phải giải được (SAT) một instance sinh từ make_puzzle."""
    N = 9
    holes_ratio = 0.3
    seed = 42

    print(f"--- Bắt đầu test SAT Solver cho Sudoku (N={N}, holes_ratio={holes_ratio}) ---")

    puzzle = make_puzzle(N, holes_ratio, seed)
    print("\nĐề bài Sudoku:")
    for row in puzzle:
        print(" ".join(row))
    print("\n" + "=" * 70)

    print(f"{'Phương pháp':<12} | {'Trạng thái':<10} | {'Số biến':>8} | {'Mệnh đề':>9} | {'Solve(s)':>10}")
    print("-" * 70)

    for amo_name in AMO_METHODS:
        ok, model, nc, nv, tb, ts = solve(N, puzzle, amo_name)
        status = "SAT" if ok else "UNSAT"
        print(f"{amo_name:<12} | {status:<10} | {nv:8d} | {nc:9d} | {ts:10.4f}")

        # make_puzzle xóa ô từ một lưới hợp lệ nên instance luôn giải được
        assert ok is True, f"Lỗi: Phương pháp {amo_name} trả về UNSAT cho một bài toán hợp lệ!"


if __name__ == "__main__":
    test_sudoku_sat_solver()
    print("\n=> Tất cả các phương pháp mã hóa đều vượt qua bài test.")