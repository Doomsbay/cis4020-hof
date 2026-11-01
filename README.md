# Predicting Baseball Hall of Fame Induction: Performance vs. Honours

CIS4020 course project, University of Guelph, Fall 2026.

## About

How well can a player's career performance (batting and pitching statistics and position) predict whether they will be inducted into the Baseball Hall of Fame, and how much do honours voted on during their career (awards and All-Star selections) add? Where does the model disagree with the voters, and why?

We compare three models (performance only, honours only, and combined) using PR AUC on a held-out test set.

**Data:** [Lahman Baseball Database](https://sabr.org/lahman-database), 2025 release, published by SABR (CC BY-SA 3.0). It's included in the repo as `data/raw/lahman_2025.zip`.

## Setup

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone git@github.com:Doomsbay/cis4020-hof.git
cd cis4020-hof
docker build -t cis4020-hof .
docker run --rm -v "$PWD":/project cis4020-hof python src/data_prep.py
docker run --rm -p 8888:8888 -v "$PWD":/project cis4020-hof
```

Then open http://localhost:8888/lab?token=cis4020. On Windows PowerShell, use `${PWD}` instead of `"$PWD"`.

## Repository layout

| Folder | What's in it |
|---|---|
| `data/` | Raw Lahman data (zipped) and the processed table the pipeline builds |
| `src/` | The data pipeline: extract, clean, join |
| `notebooks/` | One notebook per pipeline stage |
| `reports/` | Figures for the report and slides |

## Team

| Member | Responsibility | Also supports |
|---|---|---|
| Yaye Song | Data acquisition, cleaning and joins (pipeline and repository setup) | Reproducibility (README, environment file) |
| Lemi Miyu | Exploratory analysis and visualizations | Feature engineering |
| Felix Nguyen | Modelling (baselines, logistic regression, tree models) | Threshold tuning |
| Wyatt Lee | Evaluation (bootstrap, error analysis), ethics and limitations | Demo notebook |

## AI use disclosure

We used Claude (Anthropic) to explore candidate datasets and test whether they could support the project, discuss possible approaches, assist with programming, and write detailed documentation for the project. All members review, understand and can explain every part of the submitted work.
