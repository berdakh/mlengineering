"""Same config + seed -> same numbers. A different seed must actually reach the split."""


def test_two_runs_with_the_same_config_give_identical_metrics(cli, workdir, base_config, base_run):
    again = cli.train(workdir, base_config)
    assert again.json("metrics.json") == base_run.json("metrics.json")
    assert again.json("config.json") == base_run.json("config.json")


def test_seed_from_config_controls_the_split(cli, workdir, base_config, base_run):
    splits = {tuple(base_run.json("metrics.json")["test_units"])}
    for seed in (3, 11, 23):
        run = cli.train(workdir, base_config, "--set", f"split.seed={seed}")
        splits.add(tuple(run.json("metrics.json")["test_units"]))
    assert len(splits) >= 2, "changing split.seed never changed the held-out units: is the seed threaded through?"
