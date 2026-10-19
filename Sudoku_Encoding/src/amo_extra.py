import math
from itertools import combinations


def _pairwise(lits):
    """Các mệnh đề xung đột ¬x ∨ ¬y cho mọi cặp trong `lits`."""
    return [[-x, -y] for x, y in combinations(lits, 2)]


def amo_commander(lits, top, g=3):
    """Commander encoding (Klieber & Kwon 2007), chỉ một chiều x -> commander.

    Trả về (clauses, new_top); `top` là số hiệu biến lớn nhất đã dùng.
    """
    if len(lits) <= 4:
        return _pairwise(lits), top

    clauses = []
    commanders = []

    for i in range(0, len(lits), g):
        group = lits[i:i + g]
        clauses.extend(_pairwise(group))

        top += 1
        commanders.append(top)
        clauses.extend([-x, top] for x in group)

    sub_clauses, top = amo_commander(commanders, top, g)
    clauses.extend(sub_clauses)
    return clauses, top


def amo_product(lits, top):
    """Product encoding (Chen 2010): lưới p x q, một biến phụ cho mỗi hàng và cột.

    Trả về (clauses, new_top); `top` là số hiệu biến lớn nhất đã dùng.
    """
    k = len(lits)
    if k <= 4:
        return _pairwise(lits), top

    p = math.isqrt(k - 1) + 1
    q = (k + p - 1) // p

    rows = [top + i + 1 for i in range(p)]
    cols = [top + p + j + 1 for j in range(q)]
    top += p + q

    clauses = []
    for idx, x in enumerate(lits):
        i, j = divmod(idx, q)
        clauses.append([-x, rows[i]])
        clauses.append([-x, cols[j]])

    row_clauses, top = amo_product(rows, top)
    col_clauses, top = amo_product(cols, top)
    clauses.extend(row_clauses)
    clauses.extend(col_clauses)
    return clauses, top