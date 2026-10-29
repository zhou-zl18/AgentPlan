"""Run AgentPlan from scratch or resume a community checkpoint."""
import argparse
from agentplan.config import DATASETS, EXPERIMENT_DIR, DEFAULT_EXPNAME, experiment_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', choices=DATASETS, default='Huilongguan')
    parser.add_argument('--experiment-dir', default=EXPERIMENT_DIR,
                        help='Root output directory relative to this release (default: experiments).')
    parser.add_argument('--expname', default=DEFAULT_EXPNAME,
                        help='Experiment name within the dataset directory (default: default).')
    parser.add_argument('--resume-community', default=None,
                        help='Load a checkpoint for this community; skip completed communities.')
    args = parser.parse_args()

    from agentplan import llm
    from agentplan.planning import initialize_experiment, resume_experiment, run_planning, save_results
    if not llm.AZURE_API_KEY or not llm.AZURE_ENDPOINT:
        parser.error('Fill in AZURE_API_KEY and AZURE_ENDPOINT in agentplan/config.py before running experiments.')
    exppath = experiment_path(args.dataset, args.expname, args.experiment_dir)
    print(exppath)
    if args.resume_community is None:
        if not exppath.exists():
            print('Create new dir.')
            exppath.mkdir(parents=True)
        state = initialize_experiment(args.dataset, exppath)
    else:
        state = resume_experiment(args.dataset, exppath, args.resume_community)
    planner, residents, environment, records, agentdf, agent_area_dist, evaluation_configs = state
    run_planning(planner, residents, environment, records, agentdf,
                 agent_area_dist, evaluation_configs, exppath)
    save_results(planner, residents, environment, records, exppath)


if __name__ == '__main__':
    main()
