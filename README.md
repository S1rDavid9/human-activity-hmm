# Human Activity Recognition with HMM

Decoding standing / walking / jumping / still from smartphone accelerometer +
gyroscope signals using a Gaussian HMM (Baum-Welch training, Viterbi decoding).

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Contents

```
human-activity-hmm/
├── README.md
├── requirements.txt
├── notebook.ipynb          full pipeline notebook (see below)
├── report.docx             written report (background, methods, results, discussion)
├── recording_log.csv       activity/split/source/duration/notes per recording
├── manifest.csv            recording -> activity/split/index mapping used to build data/
├── manifest_template.csv   template for the manifest above
├── data/
│   ├── train/              48 labelled training recordings (accel + gyro CSVs)
│   └── test/                12 labelled test recordings (accel + gyro CSVs)
├── outputs/                 everything the notebook generates:
│   ├── evaluation_results.csv
│   ├── sample_raw_signals.png
│   ├── baum_welch_convergence.png
│   ├── transition_matrix_heatmap.png
│   ├── emission_means_heatmap.png
│   ├── feature_distributions_by_state.png
│   └── decoded_sequence_example.png
├── scripts/
│   └── organize_recordings.py   builds data/ from raw Sensor Logger exports + a manifest
└── raw_exports/              drop zone for raw Sensor Logger exports (not tracked)
```

`notebook.ipynb` runs the full pipeline: load & align raw sensor CSVs, window,
extract features, normalize, fit a Gaussian HMM, decode with Viterbi, and
evaluate on the held-out test set — writing every figure/metric into
`outputs/`. `scripts/organize_recordings.py` is only needed if you're
rebuilding `data/` from scratch; it's not required to view results.

## Re-running the notebook

```
source .venv/bin/activate
jupyter nbconvert --to notebook --execute --inplace notebook.ipynb
```

## Recording workflow (for reference / re-collecting data)

1. Record clips with Sensor Logger (accelerometer + gyroscope, same sampling
   rate for both, CSV export).
2. Export/unzip each recording into `raw_exports/` (or point
   `--raw-dir` at wherever they land, e.g. `~/Downloads`).
3. Copy `manifest_template.csv` to `manifest.csv` and fill in one row per
   recording: which raw export it is, which activity, train or test, and an
   index number.
4. Run:
   ```
   python scripts/organize_recordings.py --raw-dir <dir> --manifest manifest.csv
   ```
   This copies each recording's Accelerometer.csv/Gyroscope.csv into
   `data/train/` or `data/test/` with clear names (e.g.
   `walking_train_03_accel.csv`) and builds `recording_log.csv` with the
   actual recorded duration per file, pulled from the timestamp column.

## Actual recording counts (this dataset)

| Activity | Train clips | Test clips | Total duration (train+test) |
|---|---|---|---|
| Standing | 12 | 3 | 115.8s |
| Walking  | 12 | 3 | 115.4s |
| Jumping  | 12 | 3 | 110.7s |
| Still    | 12 | 3 | 113.1s |

Training recorded indoors, phone held in hand. Test recorded outdoors with the
phone in a pocket (still: different surface) — a deliberate domain shift to
make the test set genuinely unseen.

## Headline results

Test-set decoding accuracy: ~67%. Jumping and still are decoded perfectly
(both very distinct in feature space); standing and walking are the
confusable pair, and walking is frequently decoded as jumping under the
outdoor/pocket test conditions (higher-amplitude motion than the indoor
hand-held training data). See `outputs/evaluation_results.csv` and
`outputs/confusion_matrix_test.png` for details, and the notebook's markdown
for the full reasoning, including a documented HMM-initialization issue
(Baum-Welch's EM converged to a degenerate 3-activity solution under random
initialization, fixed via informed initialization from per-activity class
means). `report.docx` is the full written report.
