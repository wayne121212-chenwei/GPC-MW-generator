import math

from gpc_calculator import (
    DataPoint,
    baseline_correct,
    calculate_mw_mn_pdi,
    clip_with_interpolation,
    read_csv_data,
)


def test_two_point_baseline_correction():
    raw = [
        DataPoint(19, 10),
        DataPoint(20, 15),
        DataPoint(21, 13),
        DataPoint(22, 11),
        DataPoint(23, 10),
    ]
    corrected = baseline_correct(raw)
    assert corrected[0].intensity == 0
    assert corrected[-1].intensity == 0
    assert corrected[1].intensity > 0


def test_clip_with_interpolation():
    raw = [
        DataPoint(18, 1),
        DataPoint(20, 5),
        DataPoint(22, 1),
    ]
    clipped = clip_with_interpolation(raw, 19, 21)
    assert math.isclose(clipped[0].time, 19)
    assert math.isclose(clipped[-1].time, 21)


def test_molecular_weight_outputs_positive():
    corrected = [
        DataPoint(19, 1),
        DataPoint(20, 3),
        DataPoint(21, 1),
    ]
    mw, mn, pdi = calculate_mw_mn_pdi(corrected, "-0.5*t + 12")
    assert mw > 0
    assert mn > 0
    assert pdi >= 1


def test_read_two_column_whitespace_text(tmp_path):
    f = tmp_path / "gpc.txt"
    f.write_text(
        "0.0000   -0.1606\n0.0017   -0.1606\n0.0033   -0.1611\n",
        encoding="utf-8",
    )

    points = read_csv_data(str(f), "time", "intensity")
    assert len(points) == 3
    assert math.isclose(points[0].time, 0.0)
    assert math.isclose(points[1].intensity, -0.1606)
