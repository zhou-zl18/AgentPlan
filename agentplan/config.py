"""Project paths, experiment settings, and Azure configuration.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / 'data'
EXPERIMENT_DIR = 'experiments'
DEFAULT_EXPNAME = 'default'
DATASETS = ('Huilongguan', 'UK_Stockwell', 'US_Atlanta', 'Qinghe', 'Nancun')
DATASET_FOLDERS = {name: name for name in DATASETS}
PLANNER_MODEL = 'gpt-4o'
RESIDENTS_MODEL = 'gpt-4o-mini'
MAX_ROUND = 50

# Fill in your Azure OpenAI credentials here before running experiments.
AZURE_API_KEY = "<your_azure_api_key>"
AZURE_ENDPOINT = "<your_azure_endpoint>"
AZURE_API_VERSION = "<your_azure_api_version>"


def data_path(dataset):
    return DATA_ROOT / DATASET_FOLDERS[dataset]


def experiment_path(dataset, expname=DEFAULT_EXPNAME, directory=EXPERIMENT_DIR):
    path = Path(directory)
    if path.is_absolute():
        raise ValueError('Use a relative experiment directory within AgentPlan.')
    return ROOT / path / dataset / expname


def evaluation_config(dataset):
    return {
        'distance_15min': 300 if dataset == 'UK_Stockwell' else 500,
        'walkscore_min_dist': 100,
        'walkscore_max_dist': 500,
    }
