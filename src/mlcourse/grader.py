"""In-notebook grading for the 12-week course.

Students write an answer in a cell, then run the grader cell below it::

    from mlcourse.grader import grade, quiz
    grade("w02.count_orders", query)        # a SQL string, a function, a DataFrame, a number...
    quiz("w02.q1", "b")                      # a multiple-choice self-check

Tests live in ``mlcourse/graders/wNN.py``. Each exercise is a function decorated with
``@exercise("wNN.name", hint="...")`` that receives the student's answer and raises
``AssertionError("plain-language reason")`` when something is wrong. Tests must check behaviour on
several inputs (not one exact implementation), and must never reveal the solution in a message.

Every result is appended to the file named by ``MLCOURSE_GRADE_LOG`` (if set), which is how
``tools/verify_notebooks.py`` proves that solved notebooks pass and blank ones fail.
"""
from __future__ import annotations

import importlib
import json
import os
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable

_EXERCISES: dict[str, "Exercise"] = {}
_QUIZZES: dict[str, "Quiz"] = {}


@dataclass
class Exercise:
    key: str
    test: Callable[[Any], None]
    hint: str = ""


@dataclass
class Quiz:
    key: str
    answer: str
    explanation: str
    wrong: dict[str, str] = field(default_factory=dict)


def exercise(key: str, hint: str = "") -> Callable:
    """Register a test for an exercise."""
    def wrap(fn: Callable[[Any], None]) -> Callable[[Any], None]:
        _EXERCISES[key] = Exercise(key, fn, hint)
        return fn
    return wrap


def register_quiz(key: str, answer: str, explanation: str, wrong: dict[str, str] | None = None) -> None:
    """Register a multiple-choice question: correct letter, why it is right, and why each wrong letter is wrong."""
    _QUIZZES[key] = Quiz(key, answer.lower(), explanation, wrong or {})


def _load(key: str) -> None:
    module = key.split(".")[0]
    importlib.import_module(f"mlcourse.graders.{module}")


def _log(kind: str, key: str, passed: bool, detail: str = "") -> None:
    path = os.environ.get("MLCOURSE_GRADE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"kind": kind, "key": key, "passed": passed, "detail": detail[:300]}) + "\n")


class _Result:
    """Shown nicely as the last value of a cell; truthy when the exercise passed."""

    def __init__(self, passed: bool, text: str):
        self.passed, self.text = passed, text

    def __bool__(self) -> bool:
        return self.passed

    def __repr__(self) -> str:
        return self.text

    def _repr_markdown_(self) -> str:
        return self.text.replace("\n", "  \n")


def grade(key: str, answer: Any) -> _Result:
    """Run the tests for exercise `key` on `answer` and report in plain language."""
    _load(key)
    if key not in _EXERCISES:
        raise KeyError(f"no exercise called {key!r}")
    ex = _EXERCISES[key]
    try:
        if answer is None or (isinstance(answer, str) and ("YOUR" in answer and "HERE" in answer)):
            raise NotImplementedError
        ex.test(answer)
    except NotImplementedError:
        _log("exercise", key, False, "not attempted")
        return _Result(False, f"⏳ {key}: not attempted yet. Replace the `# YOUR CODE HERE` part and run again.")
    except AssertionError as err:
        msg = str(err) or "the answer does not behave as required"
        _log("exercise", key, False, msg)
        hint = f"\nHint: {ex.hint}" if ex.hint else ""
        return _Result(False, f"❌ {key}: {msg}{hint}")
    except Exception as err:  # the student's code crashed: show the error, not a grader stack trace
        last = traceback.format_exception_only(type(err), err)[-1].strip()
        _log("exercise", key, False, last)
        return _Result(False, f"❌ {key}: your code raised an error: {last}")
    _log("exercise", key, True)
    return _Result(True, f"✅ {key}: all tests passed.")


def quiz(key: str, choice: str) -> _Result:
    """Check a multiple-choice answer and explain it."""
    _load(key)
    q = _QUIZZES[key]
    choice = (choice or "").strip().lower()
    if not choice or choice == "?":
        _log("quiz", key, False, "not attempted")
        return _Result(False, f"⏳ {key}: put your letter between the quotes and run again.")
    if choice == q.answer:
        _log("quiz", key, True)
        return _Result(True, f"✅ {key}: correct. {q.explanation}")
    _log("quiz", key, False, choice)
    why = q.wrong.get(choice, "")
    return _Result(False, f"❌ {key}: not quite. {why} Think again, then re-run.".replace("  ", " "))


def exercise_keys(module: str) -> list[str]:
    """All exercise keys registered by a grader module (used by tests and the verifier)."""
    importlib.import_module(f"mlcourse.graders.{module}")
    return sorted(k for k in _EXERCISES if k.startswith(module + "."))
