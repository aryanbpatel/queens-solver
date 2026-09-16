"""Command line interface.

    queens solve puzzles/linkedin-style-8x8.txt
    queens solve my_puzzle.txt --png solved.png --unique
    queens generate 9 --seed 42 -o puzzles/new.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .board import Puzzle, PuzzleError, check_solution
from .render import supports_color, to_png, to_terminal
from .solver import NoSolutionError, count_solutions, solve


def _load(path: str) -> Puzzle:
    if path == "-":
        return Puzzle.from_text(sys.stdin.read())
    return Puzzle.from_file(path)


def cmd_solve(args: argparse.Namespace) -> int:
    puzzle = _load(args.puzzle)
    color = supports_color() and not args.no_color

    loose = puzzle.disconnected_regions()
    if loose:
        print(f"warning: region(s) {', '.join(loose)} are not contiguous - check for typos",
              file=sys.stderr)

    try:
        result = solve(puzzle, time_limit=args.time_limit, verbose=args.verbose)
    except NoSolutionError:
        print(to_terminal(puzzle, color=color))
        print("\nNo solution: these regions can't all hold a queen under the rules.")
        return 1

    # The model should never return an invalid board, but it's cheap to be sure.
    problems = check_solution(puzzle, result.queens)
    if problems:
        print("solver returned an invalid board:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 2

    print(to_terminal(puzzle, result.queens, color=color))
    print()
    print("Queens (row, col): " + "  ".join(f"({r + 1},{c + 1})" for r, c in result.queens))
    s = result.stats
    print(f"{puzzle.size}x{puzzle.size} board | {s['variables']} binary vars, "
          f"{s['constraints']} constraints | solved in {result.seconds * 1000:.0f} ms")

    if args.unique:
        n = count_solutions(puzzle, limit=2)
        print("Solution is unique." if n == 1 else "Heads up: this puzzle has more than one solution.")

    if args.png:
        out = to_png(puzzle, args.png, result.queens)
        print(f"Saved image to {out}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    puzzle = _load(args.puzzle)
    try:
        queens = [tuple(int(v) - 1 for v in pair.split(",")) for pair in args.queens]
    except ValueError:
        print("queens must look like ROW,COL (1-indexed), e.g. 1,3 2,5", file=sys.stderr)
        return 2
    problems = check_solution(puzzle, queens)  # type: ignore[arg-type]
    if problems:
        print("Not valid:\n  " + "\n  ".join(problems))
        return 1
    print("Valid solution.")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    from .generator import generate

    puzzle = generate(args.size, seed=args.seed)
    if args.output:
        Path(args.output).write_text(puzzle.to_text(), encoding="utf-8")
        print(f"Wrote {args.size}x{args.size} puzzle to {args.output}")
    else:
        sys.stdout.write(puzzle.to_text())
    if args.png:
        to_png(puzzle, args.png)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="queens",
        description="Solve LinkedIn-style Queens puzzles with integer programming.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("solve", help="solve a puzzle file")
    p.add_argument("puzzle", help="path to a puzzle .txt file, or - for stdin")
    p.add_argument("--png", metavar="FILE", help="also save the solved board as an image")
    p.add_argument("--unique", action="store_true", help="check that the solution is unique")
    p.add_argument("--time-limit", type=float, default=None, metavar="SEC")
    p.add_argument("--no-color", action="store_true", help="plain text output")
    p.add_argument("-v", "--verbose", action="store_true", help="show CBC solver log")
    p.set_defaults(func=cmd_solve)

    p = sub.add_parser("check", help="check a hand-made solution against the rules")
    p.add_argument("puzzle")
    p.add_argument("queens", nargs="+", metavar="ROW,COL")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("generate", help="make a new random puzzle with a unique solution")
    p.add_argument("size", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("-o", "--output", metavar="FILE")
    p.add_argument("--png", metavar="FILE", help="save the empty board as an image")
    p.set_defaults(func=cmd_generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (PuzzleError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
