#!/usr/bin/env python3
"""GPC molecular weight calculator with two-point baseline correction."""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class DataPoint:
    time: float
    intensity: float


def _parse_two_column_text(content: str) -> List[DataPoint]:
    points: List[DataPoint] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Accept separators: whitespace, comma, semicolon, tab
        pieces = [p for p in re.split(r"[\s,;]+", line) if p]
        if len(pieces) < 2:
            continue

        try:
            t = float(pieces[0])
            inten = float(pieces[1])
        except ValueError:
            # Ignore non-numeric line (header / comments)
            continue

        points.append(DataPoint(t, inten))

    return points


def read_csv_data(path: str, time_col: str, intensity_col: str) -> List[DataPoint]:
    """Read GPC data from either:
    1) CSV with header columns (default mode), or
    2) two-column text without header (time intensity).
    """
    file_path = Path(path)
    content = file_path.read_text(encoding="utf-8-sig")

    points: List[DataPoint] = []
    # First try regular CSV header format.
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        if time_col in fieldnames and intensity_col in fieldnames:
            for row in reader:
                try:
                    t = float(row[time_col])
                    inten = float(row[intensity_col])
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"資料列包含非數值內容: {row}") from exc
                points.append(DataPoint(t, inten))

    # Fallback: no matching header columns -> parse two-column numeric text.
    if not points:
        points = _parse_two_column_text(content)

    if not points:
        raise ValueError(
            "找不到可解析的資料。請使用 CSV 欄位格式(time/intensity)或兩欄數值格式(time intensity)。"
        )

    points.sort(key=lambda p: p.time)
    return points


def _linear_interpolate(p1: DataPoint, p2: DataPoint, time_target: float) -> DataPoint:
    if p2.time == p1.time:
        raise ValueError("時間資料有重複點，無法內插。")
    ratio = (time_target - p1.time) / (p2.time - p1.time)
    intensity_target = p1.intensity + ratio * (p2.intensity - p1.intensity)
    return DataPoint(time_target, intensity_target)


def clip_with_interpolation(
    points: List[DataPoint], t_start: float, t_end: float
) -> List[DataPoint]:
    if t_start >= t_end:
        raise ValueError("積分範圍需滿足 start < end。")
    if t_start < points[0].time or t_end > points[-1].time:
        raise ValueError(
            f"積分範圍超出資料時間區間 [{points[0].time}, {points[-1].time}]。"
        )

    clipped: List[DataPoint] = []

    for i in range(len(points) - 1):
        left = points[i]
        right = points[i + 1]

        if left.time <= t_start <= right.time:
            clipped.append(_linear_interpolate(left, right, t_start))

        if t_start <= right.time <= t_end:
            if right.time == t_start and clipped and clipped[-1].time == t_start:
                continue
            clipped.append(right)

        if left.time <= t_end <= right.time:
            if not clipped or clipped[-1].time != t_end:
                clipped.append(_linear_interpolate(left, right, t_end))
            break

    if len(clipped) < 2:
        raise ValueError("積分範圍內有效資料不足。")

    if clipped[0].time != t_start:
        for p in points:
            if p.time == t_start:
                clipped.insert(0, p)
                break

    if clipped[-1].time != t_end:
        for p in reversed(points):
            if p.time == t_end:
                clipped.append(p)
                break

    return clipped


def baseline_correct(points: List[DataPoint]) -> List[DataPoint]:
    start = points[0]
    end = points[-1]
    duration = end.time - start.time
    if duration <= 0:
        raise ValueError("積分範圍時間錯誤。")

    corrected: List[DataPoint] = []
    for p in points:
        frac = (p.time - start.time) / duration
        baseline = start.intensity + frac * (end.intensity - start.intensity)
        value = p.intensity - baseline
        corrected.append(DataPoint(p.time, max(0.0, value)))
    return corrected


def parse_calibration_formula(formula: str):
    """Return function f(t)->log10(M). Supports forms like:
    - "-0.45*t + 12.3"
    - "logM = -0.45*t + 12.3"
    """

    expr = formula.strip()
    if "=" in expr:
        _, expr = expr.split("=", 1)
    expr = expr.strip()

    if not expr:
        raise ValueError("檢量線公式不可為空。")

    allowed_pattern = r"^[0-9eE\+\-\*/\(\)\. tlogmath]+$"
    if not re.match(allowed_pattern, expr):
        raise ValueError("檢量線公式包含不允許字元。")

    def log_m(t: float) -> float:
        safe_scope = {
            "t": t,
            "math": math,
            "log": math.log10,
        }
        try:
            return float(eval(expr, {"__builtins__": {}}, safe_scope))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"無法解析檢量線公式: {formula}") from exc

    return log_m


def calculate_mw_mn_pdi(points: List[DataPoint], formula: str) -> Tuple[float, float, float]:
    log_m = parse_calibration_formula(formula)

    total_w = 0.0
    total_w_over_m = 0.0
    total_w_times_m = 0.0

    for p in points:
        if p.intensity <= 0:
            continue
        m = 10 ** log_m(p.time)
        if m <= 0:
            continue
        w = p.intensity
        total_w += w
        total_w_over_m += w / m
        total_w_times_m += w * m

    if total_w <= 0 or total_w_over_m <= 0:
        raise ValueError("修正後訊號不足，無法計算分子量。")

    mn = total_w / total_w_over_m
    mw = total_w_times_m / total_w
    pdi = mw / mn

    return mw, mn, pdi


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GPC 圖譜分子量計算程式")
    parser.add_argument("--data", required=True, help="資料檔路徑 (CSV或兩欄純文字)")
    parser.add_argument("--formula", required=True, help="檢量線公式，例如 'logM=-0.45*t+12.3'")
    parser.add_argument("--range", nargs=2, type=float, metavar=("START", "END"), required=True, help="積分範圍 (分鐘)")
    parser.add_argument("--time-col", default="time", help="時間欄位名稱 (預設: time)")
    parser.add_argument("--intensity-col", default="intensity", help="強度欄位名稱 (預設: intensity)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw = read_csv_data(args.data, args.time_col, args.intensity_col)
    clipped = clip_with_interpolation(raw, args.range[0], args.range[1])
    corrected = baseline_correct(clipped)
    mw, mn, pdi = calculate_mw_mn_pdi(corrected, args.formula)

    print(f"Mw: {mw:.6g}")
    print(f"Mn: {mn:.6g}")
    print(f"PDI: {pdi:.6g}")


if __name__ == "__main__":
    main()
