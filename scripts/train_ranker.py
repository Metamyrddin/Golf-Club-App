#!/usr/bin/env python3
"""Optional check: can a shallow tree recover the rule-based flex label?

The tree is NOT used to recommend clubs. It is a regression test you can
read — if importances ignore age or the squat ratio, the labels or the
features are wrong. Requires scikit-learn (see requirements-ml.txt).

    python scripts/generate_synthetic.py --n 8000
    python scripts/train_ranker.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> None:
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.tree import DecisionTreeClassifier
    except ImportError:
        raise SystemExit("scikit-learn is not installed. pip install -r requirements-ml.txt")

    path = ROOT / "data" / "synthetic_profiles.jsonl"
    if not path.exists():
        raise SystemExit(f"Missing {path}. Run scripts/generate_synthetic.py first.")

    features = []
    labels = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            profile = row["profile"]
            weight = profile.get("weight_kg") or 0
            squat = profile.get("squat_kg") or 0
            features.append(
                [
                    profile["age"],
                    profile["height_cm"],
                    1 if profile["gender"] == "male" else 0,
                    1 if profile["gender"] == "female" else 0,
                    weight,
                    (squat / weight) if weight and squat else 0,
                    profile.get("handicap") or -1,
                    profile.get("fitness_level") or 0,
                    1 if "back" in (profile.get("medical_flags") or []) else 0,
                    1 if "low_bone_density" in (profile.get("medical_flags") or []) else 0,
                ]
            )
            labels.append(row["label"]["flex"])

    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=7
    )
    tree = DecisionTreeClassifier(max_depth=6, random_state=7)
    tree.fit(x_train, y_train)
    accuracy = tree.score(x_test, y_test)
    names = [
        "age",
        "height",
        "male",
        "female",
        "weight",
        "squat_ratio",
        "handicap",
        "fitness",
        "back",
        "low_bone_density",
    ]
    ranked = sorted(zip(names, tree.feature_importances_), key=lambda item: -item[1])
    print(f"Holdout accuracy recovering rule-based flex: {accuracy:.3f}")
    print("Importances:")
    for name, value in ranked:
        print(f"  {name:18} {value:.3f}")
    print("The rule engine remains the source of truth. This tree is only a sanity check.")


if __name__ == "__main__":
    main()
