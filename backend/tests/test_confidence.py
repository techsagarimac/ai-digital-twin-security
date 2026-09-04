from app.utils.confidence import UNKNOWN, accept, is_known


def test_below_threshold_is_unknown() -> None:
    assert accept("Blue", 0.4, 0.5) == UNKNOWN
    assert not is_known(UNKNOWN)


def test_above_threshold_keeps_value() -> None:
    assert accept("glasses", 0.91, 0.5) == "glasses"
    assert is_known("glasses")
