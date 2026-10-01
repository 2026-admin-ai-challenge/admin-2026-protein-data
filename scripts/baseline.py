"""CPU baseline: public sequence/shape features -> scaled Logistic Regression.
Works both in this repository and inside the downloaded starter kit.
"""
from pathlib import Path
import argparse
import time
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from threadpoolctl import threadpool_limits

def default_data_dir():
    here = Path(__file__).resolve().parent
    repository_data = here.parent / "data/public"
    return repository_data if here.name == "scripts" and repository_data.is_dir() else here

def load_inputs(data_dir):
    data_dir = Path(data_dir)
    required = ["train.csv", "example_input.csv", "train_features.csv", "example_features.csv", "validation_split.csv"]
    if any(not (data_dir / name).is_file() for name in required):
        raise FileNotFoundError("학습 데이터가 없습니다. 대회 시작 후 Starter Kit을 받아 압축을 풀고 실행하세요. 다른 폴더에 있다면 --data-dir로 지정하세요.")
    train = pd.read_csv(data_dir / "train.csv", dtype=str)
    example = pd.read_csv(data_dir / "example_input.csv", dtype=str)
    features = pd.read_csv(data_dir / "train_features.csv")
    example_features = pd.read_csv(data_dir / "example_features.csv")
    folds = pd.read_csv(data_dir / "validation_split.csv", dtype=str)
    columns = features.columns.drop("id").tolist()
    if list(example_features.columns) != list(features.columns): raise ValueError("Feature columns disagree")
    for ids, frame in [(train.id, features), (example.id, example_features), (train.id, folds)]:
        if not frame.id.is_unique or set(ids) != set(frame.id): raise ValueError("Missing or duplicate input IDs")
    x = features.set_index("id").loc[train.id, columns]
    xt = example_features.set_index("id").loc[example.id, columns]
    fold = folds.set_index("id").loc[train.id, "fold"].to_numpy()
    if set(fold) != {"fit", "validation"}: raise ValueError("Invalid validation folds")
    return train, example, x, xt, fold

def run(output=Path("example_prediction.csv"), data_dir=None):
    started = time.monotonic()
    train, example, x, xt, fold = load_inputs(data_dir or default_data_dir())
    model = make_pipeline(StandardScaler(), LogisticRegression(
        max_iter=2000, C=1.0, class_weight="balanced", random_state=42))
    # Fit scaler only on the fit subset. H-superfamilies never cross validation folds.
    with threadpool_limits(limits=2):
        model.fit(x.iloc[fold == "fit"], train.label[fold == "fit"])
        score = f1_score(train.label[fold == "validation"], model.predict(x.iloc[fold == "validation"]),
                         labels=sorted(train.label.unique()), average="macro", zero_division=0)
        print(f"H-group holdout validation Macro F1: {score:.5f}")
        print("The example rows come from training; this output only demonstrates the inference format.")
        model.fit(x, train.label)
        prediction = model.predict(xt)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"id": example.id, "label": prediction}).to_csv(output, index=False)
    print(f"Wrote {len(example)} example predictions to {output}; elapsed {time.monotonic() - started:.1f}s")
    return score

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="example_prediction.csv")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    args = parser.parse_args()
    run(args.output, args.data_dir)
