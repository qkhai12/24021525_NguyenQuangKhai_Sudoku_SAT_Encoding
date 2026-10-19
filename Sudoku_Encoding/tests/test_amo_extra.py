import os
import sys
from itertools import product as iproduct

from pysat.solvers import Glucose3

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, "..", "src"))

from amo_extra import amo_commander, amo_product


def check_amo_method(amo_func, n):
    """Kiểm tra vét cạn: với mọi phép gán của n biến, công thức SAT khi và chỉ khi có tối đa 1 biến đúng."""
    vs = list(range(1, n + 1))
    clauses, _ = amo_func(vs, n)

    solver = Glucose3(bootstrap_with=clauses)
    for bits in iproduct([0, 1], repeat=n):
        assumptions = [v if b else -v for v, b in zip(vs, bits)]
        is_sat = solver.solve(assumptions=assumptions)
        assert is_sat == (sum(bits) <= 1), f"Lỗi ở n={n}, bits={bits}. SAT trả về {is_sat}"
    solver.delete()


if __name__ == "__main__":
    from sudoku_amo import AMO_METHODS

    for name, func in AMO_METHODS.items():
        print(f"Đang kiểm tra {name} Encoding...")
        for n in range(2, 15):
            check_amo_method(func, n)
        print(f"=> {name} OK cho n = 2..14\n")