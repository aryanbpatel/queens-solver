"""Puzzle representation, parsing, and rule checking.

A puzzle is an N x N grid where every cell belongs to one of N colored
regions. In the text format each region is a single character:

    # 5x5 example
    AABBB
    AABCB
    DDCCC
    DECCE
    EEEEE

Blank lines and lines starting with '#' are ignored. Spaces between
characters are allowed, so "A A B B B" also works.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

Cell = tuple[int, int]


class PuzzleError(ValueError):
    """Raised when a puzzle definition is malformed."""


@dataclass(frozen=True)
class Puzzle:
    grid: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        n = len(self.grid)
        if n == 0:
            raise PuzzleError("puzzle is empty")
        for i, row in enumerate(self.grid, start=1):
            if len(row) != n:
                raise PuzzleError(
                    f"row {i} has {len(row)} cells but the grid has {n} rows (it must be square)"
                )
        if len(self.labels) != n:
            raise PuzzleError(
                f"a {n}x{n} puzzle needs exactly {n} regions, found {len(self.labels)}"
            )

    # --- construction -------------------------------------------------

    @classmethod
    def from_rows(cls, rows: list[str] | list[list[str]]) -> "Puzzle":
        return cls(tuple(tuple(r) for r in rows))

    @classmethod
    def from_text(cls, text: str) -> "Puzzle":
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(line.replace(" ", ""))
        return cls.from_rows(rows)

    @classmethod
    def from_file(cls, path: str | Path) -> "Puzzle":
        return cls.from_text(Path(path).read_text(encoding="utf-8"))

    def to_text(self) -> str:
        return "\n".join("".join(row) for row in self.grid) + "\n"

    # --- helpers ------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self.grid)

    @property
    def labels(self) -> list[str]:
        """Region labels in order of first appearance (reading order)."""
        seen: dict[str, None] = {}
        for row in self.grid:
            for ch in row:
                seen.setdefault(ch, None)
        return list(seen)

    def region_of(self, cell: Cell) -> str:
        r, c = cell
        return self.grid[r][c]

    def cells(self):
        n = self.size
        return ((r, c) for r in range(n) for c in range(n))

    def region_cells(self) -> dict[str, list[Cell]]:
        out: dict[str, list[Cell]] = {label: [] for label in self.labels}
        for cell in self.cells():
            out[self.region_of(cell)].append(cell)
        return out

    def disconnected_regions(self) -> list[str]:
        """Regions whose cells are not one orthogonally connected blob.

        The official puzzles always use contiguous regions. The solver
        doesn't need this, but it's a useful sanity check when typing a
        puzzle in by hand.
        """
        bad = []
        for label, cells in self.region_cells().items():
            remaining = set(cells)
            stack = [cells[0]]
            remaining.discard(cells[0])
            while stack:
                r, c = stack.pop()
                for nb in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                    if nb in remaining:
                        remaining.discard(nb)
                        stack.append(nb)
            if remaining:
                bad.append(label)
        return bad


def check_solution(puzzle: Puzzle, queens: list[Cell]) -> list[str]:
    """Return a list of rule violations. An empty list means the placement is valid.

    `queens` uses 0-indexed (row, col) pairs; messages are 1-indexed so they
    match what a person sees on the board.

    Rules (same as LinkedIn's Queens):
      1. exactly one queen in every row
      2. exactly one queen in every column
      3. exactly one queen in every color region
      4. no two queens touch, including diagonally
    """
    n = puzzle.size
    problems: list[str] = []

    if len(set(queens)) != len(queens):
        problems.append("duplicate queen positions")
    for r, c in queens:
        if not (0 <= r < n and 0 <= c < n):
            problems.append(f"queen at ({r + 1},{c + 1}) is off the board")
            return problems

    if len(queens) != n:
        problems.append(f"expected {n} queens, got {len(queens)}")

    def count(key) -> dict:
        tally: dict = {}
        for q in queens:
            tally[key(q)] = tally.get(key(q), 0) + 1
        return tally

    rows = count(lambda q: q[0])
    cols = count(lambda q: q[1])
    regions = count(puzzle.region_of)

    for i in range(n):
        if rows.get(i, 0) != 1:
            problems.append(f"row {i + 1} has {rows.get(i, 0)} queens")
    for i in range(n):
        if cols.get(i, 0) != 1:
            problems.append(f"column {i + 1} has {cols.get(i, 0)} queens")
    for label in puzzle.labels:
        if regions.get(label, 0) != 1:
            problems.append(f"region '{label}' has {regions.get(label, 0)} queens")

    placed = sorted(set(queens))
    for i, (r1, c1) in enumerate(placed):
        for r2, c2 in placed[i + 1 :]:
            if abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                problems.append(f"queens at ({r1 + 1},{c1 + 1}) and ({r2 + 1},{c2 + 1}) touch")

    return problems
