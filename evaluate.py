"""Cost-Sensitive Rule Engine evaluator and test suite for T20 (Last-Mile Logistics).

Usage:
    uv run python evaluate.py
    uv run pytest
    uv run ruff check .
    uv run mypy evaluate.py
"""

from __future__ import annotations

import csv
import pathlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Literal

SubsetName = Literal["entrenamiento", "prueba"]
BinaryLabel = Literal[0, 1]

DEFAULT_CSV_PATH: Final[pathlib.Path] = (
    pathlib.Path(__file__).resolve().parent / "datos" / "T20.csv"
)
DEFAULT_MIN_FAILURES: Final[int] = 3


@dataclass(frozen=True)
class DeliveryCase:
    """Represents a single scheduled last-mile delivery record from T20.csv."""

    case_id: int
    subset: SubsetName
    prior_failures: int
    whatsapp_confirmed: BinaryLabel
    time_slot: BinaryLabel  # 0 = morning, 1 = afternoon
    actual_absent: BinaryLabel


@dataclass(frozen=True)
class ConfusionMatrix:
    """Binary confusion matrix counts and derived evaluation metrics."""

    vp: int
    fn: int
    fp: int
    vn: int

    @property
    def total(self) -> int:
        return self.vp + self.fn + self.fp + self.vn

    @property
    def accuracy(self) -> float:
        return (self.vp + self.vn) / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        denom = self.vp + self.fp
        return self.vp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.vp + self.fn
        return self.vp / denom if denom else 0.0

    @property
    def specificity(self) -> float:
        denom = self.vn + self.fp
        return self.vn / denom if denom else 0.0


def _parse_subset(raw: str) -> SubsetName:
    """Validate and narrow dataset split name without type: ignore."""
    cleaned = raw.strip()
    if cleaned == "entrenamiento":
        return "entrenamiento"
    if cleaned == "prueba":
        return "prueba"
    msg = f"Unexpected subset value: {raw!r}"
    raise ValueError(msg)


def _parse_binary(raw: str) -> BinaryLabel:
    """Validate and narrow a 0/1 CSV column into a strict BinaryLabel."""
    val = int(raw)
    if val == 0:
        return 0
    if val == 1:
        return 1
    msg = f"Expected binary value (0 or 1), got {raw!r}"
    raise ValueError(msg)


def predict_absent(
    prior_failures: int,
    whatsapp_confirmed: int,
    time_slot: int,
    *,
    min_failures: int = DEFAULT_MIN_FAILURES,
) -> BinaryLabel:
    """Predict whether a delivery fails due to recipient absence (1 = YES, 0 = NO)."""
    if (
        whatsapp_confirmed == 0
        and time_slot == 0
        and prior_failures >= min_failures
    ):
        return 1
    return 0


def load_cases(csv_path: pathlib.Path = DEFAULT_CSV_PATH) -> list[DeliveryCase]:
    """Load and parse all 20 delivery cases from T20.csv."""
    cases: list[DeliveryCase] = []
    with csv_path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            cases.append(
                DeliveryCase(
                    case_id=int(row["caso"]),
                    subset=_parse_subset(row["conjunto"]),
                    prior_failures=int(row["Entregas fallidas previas (del cliente)"]),
                    whatsapp_confirmed=_parse_binary(
                        row["Respondió el aviso por WhatsApp (0 = no, 1 = sí)"]
                    ),
                    time_slot=_parse_binary(
                        row["Franja horaria (0 = mañana, 1 = tarde)"]
                    ),
                    actual_absent=_parse_binary(row["resultado_real"]),
                )
            )
    return cases


def evaluate_subset(
    cases: Iterable[DeliveryCase],
    *,
    min_failures: int = DEFAULT_MIN_FAILURES,
) -> ConfusionMatrix:
    """Compute the confusion matrix for a collection of delivery cases."""
    vp = fn = fp = vn = 0
    for item in cases:
        pred = predict_absent(
            item.prior_failures,
            item.whatsapp_confirmed,
            item.time_slot,
            min_failures=min_failures,
        )
        if item.actual_absent == 1 and pred == 1:
            vp += 1
        elif item.actual_absent == 1 and pred == 0:
            fn += 1
        elif item.actual_absent == 0 and pred == 1:
            fp += 1
        else:
            vn += 1
    return ConfusionMatrix(vp=vp, fn=fn, fp=fp, vn=vn)


def run_self_tests(csv_path: pathlib.Path = DEFAULT_CSV_PATH) -> None:
    """Verify train/test matrices and threshold sensitivity on T20.csv."""
    all_cases = load_cases(csv_path)
    assert len(all_cases) == 20

    train_cases = [c for c in all_cases if c.subset == "entrenamiento"]
    test_cases = [c for c in all_cases if c.subset == "prueba"]
    assert len(train_cases) == 14
    assert len(test_cases) == 6

    # Threshold = 3 (selected cost-sensitive threshold)
    assert evaluate_subset(train_cases, min_failures=3) == ConfusionMatrix(2, 0, 0, 12)
    assert evaluate_subset(test_cases, min_failures=3) == ConfusionMatrix(1, 0, 0, 5)

    # Threshold = 4 (same 20/20 on dataset, but predicts 0 on gray-zone case (3, 0, 0))
    assert evaluate_subset(train_cases, min_failures=4) == ConfusionMatrix(2, 0, 0, 12)
    assert evaluate_subset(test_cases, min_failures=4) == ConfusionMatrix(1, 0, 0, 5)
    assert predict_absent(3, 0, 0, min_failures=3) == 1
    assert predict_absent(3, 0, 0, min_failures=4) == 0

    # Threshold = 2 (flips Case 5 in training from VN to FP -> 13/14 accuracy)
    assert evaluate_subset(train_cases, min_failures=2) == ConfusionMatrix(2, 0, 1, 11)
    case_5 = next(c for c in train_cases if c.case_id == 5)
    assert (
        predict_absent(
            case_5.prior_failures,
            case_5.whatsapp_confirmed,
            case_5.time_slot,
            min_failures=2,
        )
        == 1
    )


def test_cost_sensitive_rule_engine() -> None:
    """Pytest entry point."""
    run_self_tests()


if __name__ == "__main__":
    run_self_tests()
    dataset = load_cases()
    for split_name in ("entrenamiento", "prueba"):
        subset = [c for c in dataset if c.subset == split_name]
        cm = evaluate_subset(subset)
        print(
            f"[{split_name.upper()}] VP={cm.vp} FN={cm.fn} FP={cm.fp} VN={cm.vn} | "
            f"Acc={cm.accuracy:.1%} Prec={cm.precision:.1%} "
            f"Sens={cm.recall:.1%} Spec={cm.specificity:.1%}"
        )
