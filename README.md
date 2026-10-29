# AgentPlan

This is the official implementation of paper "Agentic urban renewal planning with large language models".

## Layout

```text
AgentPlan/
├── run_experiment.py       # New experiment or checkpoint resume
├── evaluate.py             # Evaluate a saved plan
├── requirements.txt
├── agentplan/
│   ├── config.py           # Project paths and experiment defaults
│   ├── data.py             # Map/profile loading and distance matrices
│   ├── landuse.py          # Facility categories and area requirements
│   ├── spatial.py          # Shared geometry and direction helpers
│   ├── constraints.py      # Requirement and feasibility checks
│   ├── metrics.py          # Shared evaluation metrics
│   ├── feedback.py         # Textual plan descriptions and evaluations
│   ├── prompts.py          # Planner and resident prompt templates
│   ├── llm.py              # Azure calls, multiprocessing, token usage
│   ├── agents.py           # Planner and Resident
│   ├── environment.py      # Plan state and update history
│   └── planning.py         # Community division and planning workflow
├── data/
│   ├── Huilongguan/
│   ├── UK_Stockwell/
│   ├── US_Atlanta/
│   ├── Qinghe/
│   └── Nancun/
└── experiments/            # Outputs: {dataset}/{expname}/; excluded from Git
```

Each dataset directory contains three input files:

- `basemap.geojson`: projected planning geometries, area IDs, area sizes,
  original facility categories, and area types. UK_Stockwell, US_Atlanta, and
  Nancun also provide facility categories after actual renewal.
- `Agent_Profile_1000.xlsx`: resident profiles, facility needs, and coordinates.
- `basemap_proj.jpg`: planning map sent to the planner.

| Dataset argument | Data directory |
| --- | --- |
| `Huilongguan` (default) | `data/Huilongguan` |
| `UK_Stockwell` | `data/UK_Stockwell` |
| `US_Atlanta` | `data/US_Atlanta` |
| `Qinghe` | `data/Qinghe` |
| `Nancun` | `data/Nancun` |

## Installation

Use Python 3.11 on Linux. From this directory:

```bash
pip install -r requirements.txt
```

## LLM configuration

Experiments use Azure OpenAI, with `gpt-4o` for the planner and `gpt-4o-mini` for
residents. The model-to-deployment mapping is in `agentplan/llm.py`.
Configure Azure deployments with those names, or adapt the deployment mapping to
your own deployment names before running.

Open `agentplan/config.py` and fill in `AZURE_API_KEY` and `AZURE_ENDPOINT`:

```python
AZURE_API_KEY = ""
AZURE_ENDPOINT = ""
AZURE_API_VERSION = ""
```

## Run an experiment

```bash
python run_experiment.py --dataset Huilongguan
```

The default run starts from scratch with experiment name `default`. Outputs are organized as `experiments/{dataset}/{expname}/`, so this
command writes to `experiments/Huilongguan/default/`. Experiment and evaluation
use the same directory structure. 

To select a name for another experiment:

```bash
python run_experiment.py --dataset UK_Stockwell --expname run1
```

This writes to `experiments/UK_Stockwell/run1/`.

## Resume a checkpoint

Resume a run from community `5`:

```bash
python run_experiment.py --dataset Huilongguan --expname run1 --resume-community 5
```

## Evaluate a plan

```bash
python evaluate.py --dataset Huilongguan --expname run1
```

This evaluate the plan `experiments/Huilongguan/run1/plan.geojson`. 

The script prints requirement violations and feasible additions, followed by
seven evaluation metrics. Each metric is printed once, on a separate line as
`Walk score: 0.123`.

| Metric | Meaning |
| --- | --- |
| Walk score | Mean walk score across residents and facility categories |
| Service | Mean accessibility to five public-service categories |
| Satisfaction | Overall facility-need satisfaction |
| Inclusion | Facility-need satisfaction for special groups |
| Walk score equality | 1 minus the resident-level walk-score Gini |
| Service equality | 1 minus the resident-level service-access Gini |
| Satisfaction equality | 1 minus the resident-level satisfaction Gini |

Higher values indicate better performance for all seven metrics.

## Output files

Within `experiments/{dataset}/{expname}/`, a completed experiment produces:

- `plan.geojson`: final plan.
- `planner_messages.json`: planner chat history.
- `records.json`: planning records.
- `planner.pkl`, `residents.pkl`, `environment.pkl`: final saved state.

Each completed community also saves `records_community<id>.json`,
`planner_community<id>.pkl`, `residents_community<id>.pkl`, and
`environment_community<id>.pkl` for checkpoint recovery.

`community2areas.geojson` contains a JSON dictionary mapping
community IDs to area IDs. Despite the filename extension, it is not a GeoJSON
feature collection.
