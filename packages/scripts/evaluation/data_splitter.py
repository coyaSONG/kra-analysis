"""Temporal data splitter for walk-forward validation."""

from __future__ import annotations


class TemporalDataSplitter:
    """Time-ordered data splitter for train/val/test."""

    def __init__(
        self, train_ratio: float = 0.4, val_ratio: float = 0.4, test_ratio: float = 0.2
    ):
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio

    def split(self, race_files: list[dict]) -> dict[str, list[dict]]:
        """Sort by race_date then split chronologically."""
        if not race_files:
            return {"train": [], "val": [], "test": []}

        sorted_files = sorted(race_files, key=lambda x: x.get("race_date", ""))
        n = len(sorted_files)

        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.val_ratio)

        return {
            "train": sorted_files[:train_end],
            "val": sorted_files[train_end:val_end],
            "test": sorted_files[val_end:],
        }

    def walk_forward_splits(
        self, race_files: list[dict], n_splits: int = 5
    ) -> list[dict[str, list[dict]]]:
        """Generate expanding window walk-forward splits."""
        if not race_files:
            return []

        sorted_files = sorted(race_files, key=lambda x: x.get("race_date", ""))
        n = len(sorted_files)

        if n < n_splits * 3:  # Need at least 3 per split (1 train, 1 val, 1 test)
            return [self.split(race_files)]

        splits = []
        test_size = max(1, n // (n_splits + 1))

        for i in range(n_splits):
            test_start = n - (n_splits - i) * test_size
            test_end = test_start + test_size
            if i == n_splits - 1:
                test_end = n  # Last split gets remainder

            available = sorted_files[:test_start]
            if not available:
                continue

            val_size = max(1, len(available) // 4)
            train_data = available[:-val_size] if len(available) > val_size else available[:1]
            val_data = available[-val_size:] if len(available) > val_size else available[1:]
            test_data = sorted_files[test_start:test_end]

            splits.append({
                "train": train_data,
                "val": val_data,
                "test": test_data,
            })

        return splits
