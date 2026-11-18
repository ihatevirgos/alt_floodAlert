import pytest

from flood_alert.core import Classifier


@pytest.fixture
def c():
    return Classifier()


@pytest.mark.parametrize(
    "h, prev, expected",
    [
        # First reading: band only
        (14.2, None, "D"),
        (15.3, None, "L1"),
        (16.5, None, "L2"),
        (18.0, None, "L3"),
        # Below 15 m: direction only
        (14.6, 14.2, "L0"),
        (14.2, 14.2, "D"),
        (14.0, 14.2, "D"),
        # Band boundaries
        (15.0, 14.8, "L1"),
        (15.99, 15.8, "L1"),
        (16.0, 15.8, "L2"),
        (17.99, 17.8, "L2"),
        (18.0, 17.8, "L3"),
        # Rapid rise beats the band (priority L3 > R > L2 > L1)
        (15.6, 15.0, "R"),
        (15.5, 15.0, "R"),
        (16.4, 15.9, "R"),  # float trap: 16.4 - 15.9 = 0.4999999...
        (17.4, 16.8, "R"),
        (15.4, 15.0, "L1"),
        (18.6, 17.9, "L3"),  # L3 beats R
        (15.2, 14.5, "R"),  # jump from below 15 m into the rapid-rise band
        # Falling within the bands
        (15.5, 17.4, "L1"),
        (17.4, 18.1, "L2"),
    ],
)
def test_classify(c, h, prev, expected):
    assert c.classify(h, prev) == expected


def test_rejects_negative_level(c):
    with pytest.raises(ValueError):
        c.classify(-1.0, None)


def test_thresholds_must_be_ordered():
    with pytest.raises(ValueError):
        Classifier(prep_level_m=16, evac_level_m=15, forced_level_m=18)
