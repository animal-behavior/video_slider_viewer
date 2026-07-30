"""Statistical outlier filter for coordinate CSVs.

Reads a CSV with columns `frame, <joint>_x, <joint>_y, ...`, runs a cascade of
detectors (Hampel, velocity z-score, bone-length consistency), and writes a
filtered CSV plus an outlier report.
"""

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAD_SCALE = 1.4826  # MAD-to-sigma assuming Gaussian noise
DEFAULT_CHAIN = ["iliac_crest", "hip", "knee", "ankle", "mtp", "toe"]


def normalize_label(name: str) -> tuple[str, str | None]:
    """Return (joint_key, axis) where axis is 'x', 'y', or None for non-coordinate columns."""
    s = name.strip().lower()
    m = re.match(r'^(.+?)[ _]?([xy])\s*$', s)
    if not m:
        return s, None
    base = re.sub(r'\s+', '_', m.group(1).strip().rstrip('_').strip())
    return base, m.group(2)


def extract_joints(df: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """Map joint_key -> (x_column_name, y_column_name) for complete pairs only."""
    pending: dict[str, dict[str, str]] = {}
    for col in df.columns:
        if col == "frame":
            continue
        joint, axis = normalize_label(col)
        if axis is None:
            continue
        pending.setdefault(joint, {})[axis] = col
    return {j: (a["x"], a["y"]) for j, a in pending.items() if "x" in a and "y" in a}


def _rolling_mad(series: pd.Series, window: int) -> pd.Series:
    """Rolling MAD; centered window with at least window//2+1 valid samples."""
    def _mad(x: np.ndarray) -> float:
        x = x[~np.isnan(x)]
        if x.size == 0:
            return np.nan
        return float(np.median(np.abs(x - np.median(x))))
    return series.rolling(window=window, center=True, min_periods=window // 2 + 1).apply(_mad, raw=True)


def hampel_mask(series: pd.Series, window: int, k: float) -> np.ndarray:
    """Per-axis Hampel filter. True at indices the filter considers outliers."""
    if window < 3 or len(series) < window:
        return np.zeros(len(series), dtype=bool)
    med = series.rolling(window=window, center=True, min_periods=window // 2 + 1).median()
    sigma = (MAD_SCALE * _rolling_mad(series, window)).replace(0, np.nan)
    deviation = (series - med).abs() / sigma
    return deviation.gt(k).fillna(False).to_numpy()


def velocity_mask(x: pd.Series, y: pd.Series, k: float) -> np.ndarray:
    """Per-joint velocity outlier. Flags both endpoints of an anomalous jump."""
    dx = x.diff()
    dy = y.diff()
    speed = (dx * dx + dy * dy).pow(0.5)
    valid = speed.dropna().to_numpy()
    if valid.size == 0:
        return np.zeros(len(x), dtype=bool)
    med = float(np.median(valid))
    m = float(np.median(np.abs(valid - med)))
    if m == 0:
        return np.zeros(len(x), dtype=bool)
    z = (speed - med).abs() / (MAD_SCALE * m)
    flagged = z.gt(k).fillna(False).to_numpy()
    out = flagged.copy()
    if len(out) > 1:
        # An anomalous Δ at frame i implicates frames i-1 and i.
        out[:-1] |= flagged[1:]
    return out


def per_joint_speed(df: pd.DataFrame, xc: str, yc: str) -> np.ndarray:
    sx = df[xc].to_numpy(dtype=float)
    sy = df[yc].to_numpy(dtype=float)
    dx = np.diff(sx, prepend=sx[0])
    dy = np.diff(sy, prepend=sy[0])
    return np.sqrt(dx * dx + dy * dy)


def bone_length_outliers(
    df: pd.DataFrame,
    joints: dict[str, tuple[str, str]],
    chain: list[str],
    window: int,
    k: float,
) -> dict[str, np.ndarray]:
    """Per-joint outlier masks from bone-length consistency along the chain."""
    n = len(df)
    flags: dict[str, np.ndarray] = {j: np.zeros(n, dtype=bool) for j in joints}
    present = [j for j in chain if j in joints]
    if len(present) < 2:
        return flags

    speeds = {j: per_joint_speed(df, *joints[j]) for j in present}

    bone_flags: list[tuple[str, str, np.ndarray]] = []
    for a, b in zip(present, present[1:]):
        xa, ya = joints[a]
        xb, yb = joints[b]
        length = ((df[xa] - df[xb]) ** 2 + (df[ya] - df[yb]) ** 2).pow(0.5)
        med = length.rolling(window=window, center=True, min_periods=window // 2 + 1).median()
        sigma = (MAD_SCALE * _rolling_mad(length, window)).replace(0, np.nan)
        z = (length - med).abs() / sigma
        anomalous = z.gt(k).fillna(False).to_numpy()
        bone_flags.append((a, b, anomalous))

    # Each anomalous bone is attributed to the joint moving faster in that frame.
    for a, b, anomalous in bone_flags:
        if not anomalous.any():
            continue
        for i in np.where(anomalous)[0]:
            target = a if speeds[a][i] >= speeds[b][i] else b
            flags[target][i] = True

    # If both adjacent bones for a joint flag the same frame, mark that joint regardless.
    for idx, j in enumerate(present):
        prev_bone = bone_flags[idx - 1][2] if idx > 0 else None
        next_bone = bone_flags[idx][2] if idx < len(bone_flags) else None
        if prev_bone is not None and next_bone is not None:
            flags[j] |= prev_bone & next_bone

    return flags


def main() -> int:
    ap = argparse.ArgumentParser(description="Statistical outlier filter for coordinate CSVs.")
    ap.add_argument("input", help="Input CSV (frame, joint_x, joint_y, ...)")
    ap.add_argument("--output", help="Filtered CSV path (default: <input>_filtered.csv)")
    ap.add_argument("--report", help="Outlier report CSV path (default: <input>_outliers.csv)")
    ap.add_argument("--replace", choices=["interpolate", "zero", "nan"], default="interpolate")
    ap.add_argument("--mask-zeros", action="store_true",
                    help="Treat (0, 0) coordinate pairs in input as missing data.")
    ap.add_argument("--hampel-window", type=int, default=7)
    ap.add_argument("--hampel-k", type=float, default=3.0)
    ap.add_argument("--velocity-k", type=float, default=5.0)
    ap.add_argument("--bone-length-k", type=float, default=5.0)
    ap.add_argument("--bone-length-window", type=int, default=15)
    ap.add_argument("--chain", default=",".join(DEFAULT_CHAIN),
                    help="Anatomical joint chain (comma-separated)")
    ap.add_argument("--skip-hampel", action="store_true")
    ap.add_argument("--skip-velocity", action="store_true")
    ap.add_argument("--skip-bone-length", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"error: input file not found: {input_path}", file=sys.stderr)
        return 2

    df_raw = pd.read_csv(input_path)
    if "frame" not in df_raw.columns:
        print("error: input CSV must contain a 'frame' column.", file=sys.stderr)
        return 2

    joints = extract_joints(df_raw)
    if not joints:
        print("error: no (x, y) coordinate columns found.", file=sys.stderr)
        return 2

    chain = [c.strip() for c in args.chain.split(",") if c.strip()]
    n = len(df_raw)
    original = df_raw.copy()
    df = df_raw.copy()

    # Mark invalid input as NaN so detectors do not see them as data.
    for j, (xc, yc) in joints.items():
        xs = df[xc].astype(float)
        ys = df[yc].astype(float)
        invalid = xs.isna() | ys.isna()
        if args.mask_zeros:
            invalid |= (xs == 0) & (ys == 0)
        df.loc[invalid, xc] = np.nan
        df.loc[invalid, yc] = np.nan

    # frame_idx -> joint -> set of reasons (both axes get the same reasons)
    outlier_idx: dict[str, np.ndarray] = {j: np.zeros(n, dtype=bool) for j in joints}
    reasons: dict[tuple[str, int], list[str]] = {}

    def record(joint: str, frame_idx: int, reason: str) -> None:
        outlier_idx[joint][frame_idx] = True
        key = (joint, frame_idx)
        lst = reasons.setdefault(key, [])
        if reason not in lst:
            lst.append(reason)

    # 1. Hampel — per axis
    if not args.skip_hampel:
        if n < args.hampel_window:
            if not args.quiet:
                print(
                    f"warning: input too short ({n} rows) for Hampel window "
                    f"{args.hampel_window}; skipped.",
                    file=sys.stderr,
                )
        else:
            for j, (xc, yc) in joints.items():
                for col in (xc, yc):
                    mask = hampel_mask(df[col], args.hampel_window, args.hampel_k)
                    for i in np.where(mask)[0]:
                        record(j, int(i), "hampel")

    # 2. Velocity — per joint
    if not args.skip_velocity:
        for j, (xc, yc) in joints.items():
            mask = velocity_mask(df[xc], df[yc], args.velocity_k)
            for i in np.where(mask)[0]:
                record(j, int(i), "velocity")

    # 3. Bone length — chain-aware
    if not args.skip_bone_length:
        if n < args.bone_length_window:
            if not args.quiet:
                print(
                    f"warning: input too short ({n} rows) for bone-length window "
                    f"{args.bone_length_window}; skipped.",
                    file=sys.stderr,
                )
        else:
            bl_flags = bone_length_outliers(
                df, joints, chain,
                window=args.bone_length_window, k=args.bone_length_k,
            )
            for j, mask in bl_flags.items():
                for i in np.where(mask)[0]:
                    record(j, int(i), "bone_length")

    # Apply outlier mask: both x and y go to NaN for any flagged frame.
    for j, (xc, yc) in joints.items():
        m = outlier_idx[j]
        df.loc[m, xc] = np.nan
        df.loc[m, yc] = np.nan

    # Replacement strategy
    coord_cols = [c for pair in joints.values() for c in pair]
    if args.replace == "interpolate":
        for col in coord_cols:
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
    elif args.replace == "zero":
        for col in coord_cols:
            df[col] = df[col].fillna(0)
    # 'nan' — leave as is.

    # Build outlier report rows (one row per axis per flagged frame)
    report_rows: list[dict] = []
    for (joint, frame_idx), why in reasons.items():
        for axis, col in zip(("x", "y"), joints[joint]):
            original_val = original.at[frame_idx, col]
            replacement_val = df.at[frame_idx, col]
            report_rows.append({
                "frame": original.at[frame_idx, "frame"],
                "joint": joint,
                "axis": axis,
                "original_value": original_val,
                "replacement": replacement_val,
                "reason": "|".join(why),
            })
    report_rows.sort(key=lambda r: (r["frame"], r["joint"], r["axis"]))

    out_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_filtered.csv")
    report_path = Path(args.report) if args.report else input_path.with_name(input_path.stem + "_outliers.csv")

    df.to_csv(out_path, index=False)
    pd.DataFrame(
        report_rows,
        columns=["frame", "joint", "axis", "original_value", "replacement", "reason"],
    ).to_csv(report_path, index=False)

    if not args.quiet:
        print(f"Filtered: {out_path}")
        print(f"Report:   {report_path}")
        print()
        per_joint = {j: {"hampel": 0, "velocity": 0, "bone_length": 0} for j in joints}
        flagged_frames = {j: set() for j in joints}
        for (joint, frame_idx), why in reasons.items():
            flagged_frames[joint].add(frame_idx)
            for r in why:
                per_joint[joint][r] += 1
        for joint, counts in per_joint.items():
            uniq = len(flagged_frames[joint])
            pct = (uniq / n * 100.0) if n else 0.0
            print(
                f"  {joint:14s}: {uniq:5d} outlier frames ({pct:5.2f}%) — "
                f"hampel:{counts['hampel']}, velocity:{counts['velocity']}, "
                f"bone_length:{counts['bone_length']}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
