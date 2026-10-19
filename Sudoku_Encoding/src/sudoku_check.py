"""Giải mã và kiểm tra đáp án Sudoku, dùng chung cho mọi solver."""
from math import isqrt

from sudoku_amo import make_var, symbol_to_value


def decode_sat(N, model):
    """Từ model của SAT solver (danh sách literal) -> lưới N x N các giá trị 0..N-1."""
    var = make_var(N)
    true_vars = {x for x in model if x > 0}
    grid = []
    for r in range(N):
        row = []
        for c in range(N):
            vals = [v for v in range(N) if var(r, c, v) in true_vars]
            if len(vals) != 1:
                raise ValueError(f"ô ({r},{c}) có {len(vals)} giá trị: {vals}")
            row.append(vals[0])
        grid.append(row)
    return grid


def validate(N, puzzle, grid):
    """Kiểm tra lưới đúng luật Sudoku và khớp các ô cho sẵn. Sai thì raise ValueError."""
    B = isqrt(N)
    full = set(range(N))
    for i in range(N):
        if set(grid[i]) != full:
            raise ValueError(f"hàng {i} sai")
        if {grid[r][i] for r in range(N)} != full:
            raise ValueError(f"cột {i} sai")
    for br in range(B):
        for bc in range(B):
            blk = {grid[br * B + i][bc * B + j] for i in range(B) for j in range(B)}
            if blk != full:
                raise ValueError(f"khối ({br},{bc}) sai")
    for r in range(N):
        for c in range(N):
            if puzzle[r][c] != '.' and grid[r][c] != symbol_to_value(puzzle[r][c]):
                raise ValueError(f"ô cho sẵn ({r},{c}) bị đổi")
    return True
