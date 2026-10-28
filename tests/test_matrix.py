from spike.matrix import budget_seconds, sets_for_context


def test_haystack_only_runs_in_windows_that_can_hold_it():
    sets = ["hand", "short", "haystack"]
    assert sets_for_context(sets, 2048) == ["hand", "short"]
    assert sets_for_context(sets, 32768) == ["hand", "short"]
    assert sets_for_context(sets, 131072) == sets


def test_larger_models_get_a_longer_time_budget():
    assert budget_seconds({"parameter_size": "3.9B"}) == 90 * 60
    assert budget_seconds({"parameter_size": "11.8B"}) == 240 * 60
    assert budget_seconds({"parameter_size": "800M"}) == 90 * 60
    assert budget_seconds({}) == 90 * 60


def test_the_budget_can_be_overridden():
    assert budget_seconds({"parameter_size": "11.8B"}, override_minutes=10) == 600
