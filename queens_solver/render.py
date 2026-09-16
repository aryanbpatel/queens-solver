"""Drawing boards in the terminal and as PNG images."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .board import Cell, Puzzle

# Soft pastels close to the ones the LinkedIn game uses, plus a few extras
# so boards up to 12x12 still get distinct colors.
PALETTE = [
    "#BBA3E2",  # lavender
    "#FFC992",  # peach
    "#96BEFF",  # sky blue
    "#B3DFA0",  # sage
    "#DFDFDF",  # light gray
    "#FF7B60",  # coral
    "#E6F388",  # lime
    "#B9B29E",  # taupe
    "#DFA0BF",  # rose
    "#A3D2D8",  # teal
    "#62EFEA",  # aqua
    "#FF93F3",  # pink
]

QUEEN = "♛"  # black chess queen


def region_colors(puzzle: Puzzle) -> dict[str, str]:
    return {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(puzzle.labels)}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def supports_color(stream=sys.stdout) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def to_terminal(puzzle: Puzzle, queens: list[Cell] | None = None, color: bool = True) -> str:
    """Render the board as text. With color on, each region gets a truecolor background."""
    queens_set = set(queens or [])
    colors = region_colors(puzzle)
    lines = []

    for r, row in enumerate(puzzle.grid):
        parts = []
        for c, label in enumerate(row):
            mark = QUEEN if (r, c) in queens_set else " "
            if color:
                red, green, blue = _hex_to_rgb(colors[label])
                parts.append(f"\x1b[48;2;{red};{green};{blue}m\x1b[38;2;20;20;20m {mark} \x1b[0m")
            else:
                parts.append(f" {'Q' if mark != ' ' else label.lower()} ")
        lines.append("".join(parts))

    return "\n".join(lines)


def to_png(
    puzzle: Puzzle,
    path: str | Path,
    queens: list[Cell] | None = None,
    cell_px: int = 64,
) -> Path:
    """Save the board as a PNG. Needs matplotlib (pip install matplotlib)."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise RuntimeError("PNG output needs matplotlib: pip install matplotlib") from exc

    n = puzzle.size
    colors = region_colors(puzzle)
    queens_set = set(queens or [])
    dpi = 100
    size_in = n * cell_px / dpi

    fig, ax = plt.subplots(figsize=(size_in, size_in), dpi=dpi)
    ax.set_xlim(0, n)
    ax.set_ylim(n, 0)
    ax.set_aspect("equal")
    ax.axis("off")

    for r in range(n):
        for c in range(n):
            ax.add_patch(
                Rectangle((c, r), 1, 1, facecolor=colors[puzzle.grid[r][c]], edgecolor="#555555", linewidth=0.5)
            )
            if (r, c) in queens_set:
                ax.text(c + 0.5, r + 0.54, QUEEN, ha="center", va="center",
                        fontsize=cell_px * 0.45, color="#1d1d1d")

    # Thicker lines where two regions meet, like the real game board.
    for r in range(n):
        for c in range(n):
            here = puzzle.grid[r][c]
            if c + 1 < n and puzzle.grid[r][c + 1] != here:
                ax.plot([c + 1, c + 1], [r, r + 1], color="#1d1d1d", linewidth=2.2, solid_capstyle="round")
            if r + 1 < n and puzzle.grid[r + 1][c] != here:
                ax.plot([c, c + 1], [r + 1, r + 1], color="#1d1d1d", linewidth=2.2, solid_capstyle="round")
    ax.add_patch(Rectangle((0, 0), n, n, fill=False, edgecolor="#1d1d1d", linewidth=3))

    path = Path(path)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return path
