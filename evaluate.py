"""Evaluate a saved AgentPlan plan."""
import argparse
from agentplan.config import DATASETS, EXPERIMENT_DIR, DEFAULT_EXPNAME, data_path, experiment_path, evaluation_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=DATASETS, default='Huilongguan')
    parser.add_argument('--experiment-dir', default=EXPERIMENT_DIR,
                        help='Root plan directory relative to this release (default: experiments).')
    parser.add_argument('--expname', default=DEFAULT_EXPNAME,
                        help='Experiment name within the dataset directory (default: default).')
    args = parser.parse_args()

    import geopandas as gp
    from agentplan.constraints import evaluate_all_requirements, check_feasible_areas
    from agentplan.data import load_evaluation_data
    from agentplan.metrics import evaluate
    exppath = experiment_path(args.dataset, args.expname, args.experiment_dir)
    print(exppath)
    assert exppath.exists()
    _, agentdf, agent_area_dist = load_evaluation_data(data_path(args.dataset))
    gdf = gp.read_file(exppath / 'plan.geojson')
    print('Requirement violation:', evaluate_all_requirements(gdf))
    print('Feasible areas:', check_feasible_areas(gdf))
    evaluate(gdf, agentdf, agent_area_dist, evaluation_config(args.dataset))


if __name__ == '__main__':
    main()
