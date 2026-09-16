"""Solve LinkedIn's Queens puzzle as a binary integer program."""

from .board import Puzzle, PuzzleError, check_solution
from .solver import NoSolutionError, Solution, count_solutions, solve

__version__ = "1.0.0"

__all__ = [
    "Puzzle",
    "PuzzleError",
    "check_solution",
    "solve",
    "count_solutions",
    "Solution",
    "NoSolutionError",
]
