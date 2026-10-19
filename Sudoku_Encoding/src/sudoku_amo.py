import random
import time
from math import isqrt

from pysat.card import CardEnc, EncType
from pysat.solvers import Glucose3

from amo_extra import amo_commander, amo_product

SYMBOLS = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()-_=+[{]}<>"


def amo_pysat(enc_type):
    """Bọc một encoding AMO của PySAT thành hàm (vs, top) -> (clauses, new_top).

    `top` là số hiệu biến lớn nhất đã dùng, để biến phụ không bị trùng.
    """
    def f(vs, top):
        cnf = CardEnc.atmost(lits=vs, bound=1, top_id=top, encoding=enc_type)
        new_top = max([top] + [abs(l) for cl in cnf.clauses for l in cl])
        return cnf.clauses, new_top
    return f


AMO_METHODS = {
    "pairwise":   amo_pysat(EncType.pairwise),
    "seqcounter": amo_pysat(EncType.seqcounter),
    "bitwise":    amo_pysat(EncType.bitwise),
    "product":    amo_product,
    "commander":  amo_commander,
}


def symbol_to_value(ch):
    """'1' -> 0, '9' -> 8, 'A' -> 9, ..."""
    return SYMBOLS.index(ch)


def make_var(N):
    """Trả về hàm var(r, c, v) đánh số biến x[r][c][v] từ 1 đến N^3."""
    def var(r, c, v):
        return r * N * N + c * N + v + 1
    return var


def build_clauses(N, puzzle, amo_fn):
    """Sinh CNF: exactly-one (ALO + AMO) cho ô, hàng, cột, subgrid, cộng các clue."""
    B = isqrt(N)
    var = make_var(N)
    top = N**3
    clauses = []

    def exactly_one(vs):
        nonlocal top
        clauses.append(list(vs))
        amo, top = amo_fn(list(vs), top)
        clauses.extend(amo)

    for r in range(N):
        for c in range(N):
            exactly_one([var(r, c, v) for v in range(N)])
    for r in range(N):
        for v in range(N):
            exactly_one([var(r, c, v) for c in range(N)])
    for c in range(N):
        for v in range(N):
            exactly_one([var(r, c, v) for r in range(N)])
    for br in range(B):
        for bc in range(B):
            for v in range(N):
                exactly_one([var(br * B + i, bc * B + j, v)
                             for i in range(B) for j in range(B)])

    for r in range(N):
        for c in range(N):
            if puzzle[r][c] != '.':
                clauses.append([var(r, c, symbol_to_value(puzzle[r][c]))])
    return clauses


def make_puzzle(N, holes_ratio, seed):
    """Sinh instance: lưới đầy đủ hợp lệ rồi xóa int(holes_ratio * N^2) ô ngẫu nhiên."""
    rnd = random.Random(seed)
    B = isqrt(N)
    base = [[(B * (r % B) + r // B + c) % N for c in range(N)] for r in range(N)]
    vals = list(range(N))
    rnd.shuffle(vals)

    def shuffled_axis():
        bands = list(range(B))
        rnd.shuffle(bands)
        axis = []
        for b in bands:
            inner = list(range(B))
            rnd.shuffle(inner)
            axis += [b * B + i for i in inner]
        return axis

    rows, cols = shuffled_axis(), shuffled_axis()
    grid = [[vals[base[rows[r]][cols[c]]] for c in range(N)] for r in range(N)]

    cells = [(r, c) for r in range(N) for c in range(N)]
    rnd.shuffle(cells)
    holes = set(cells[:int(holes_ratio * N * N)])
    return ["".join('.' if (r, c) in holes else SYMBOLS[grid[r][c]] for c in range(N))
            for r in range(N)]


def solve(N, puzzle, amo_name):
    """Trả về (sat, model, n_clauses, n_vars, t_build, t_solve)."""
    t0 = time.perf_counter()
    clauses = build_clauses(N, puzzle, AMO_METHODS[amo_name])
    t_build = time.perf_counter() - t0
    n_vars = max(abs(l) for cl in clauses for l in cl)

    solver = Glucose3()
    for cl in clauses:
        solver.add_clause(cl)

    t1 = time.perf_counter()
    ok = solver.solve()
    t_solve = time.perf_counter() - t1
    model = {x for x in solver.get_model() if x > 0} if ok else None
    return ok, model, len(clauses), n_vars, t_build, t_solve


if __name__ == "__main__":
    print(f"{'N':>3s} {'encoding':11s} {'sat':5s} {'bien':>7s} {'menh de':>9s} {'solve(s)':>9s}")
    for N in (9, 16, 25):
        puzzle = make_puzzle(N, 0.5, seed=1)
        for name in AMO_METHODS:
            ok, model, nc, nv, tb, ts = solve(N, puzzle, name)
            print(f"{N:3d} {name:11s} {str(ok):5s} {nv:7d} {nc:9d} {ts:9.4f}")