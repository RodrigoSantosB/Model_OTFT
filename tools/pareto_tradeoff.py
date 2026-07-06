#!/usr/bin/env python3
"""Pareto trade-off scan: transfer_curve_weight vs transfer/output RMSE."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules_otft._model import TFTModel
from modules_otft._read_data import ReadData
from modules_otft import _utils as U

DEFAULT_JSON = ROOT / "inputs/tipo p/inputs_cnts_v2.json"


def _load_settings(json_path: Path):
    blocks = json.loads(json_path.read_text())
    settings = {"_json_path": str(json_path), "_json_blocks": blocks}
    for block in blocks:
        settings.update(block)
    return settings


def _prepare_data(settings):
    read = ReadData()
    type_curve_plot = U.get_type_plot(settings)
    U.calculate_shift_list(settings)
    effective = U.get_shift_list(read, settings)
    nominal_path = read.read_files_experimental(settings["path"])
    path_voltages = U.apply_effective_voltages_to_path(nominal_path, effective)
    path_voltages, effective, nominal = U.filter_and_load_files(
        read, settings, path_voltages, effective,
        list_tension_nominal=U.extract_nominal_voltages(nominal_path),
    )
    Vv, Id, input_voltage, n_points, count_transfer, count_output = read.load_data(
        settings["type_read_data_exp"],
        path_voltages,
        settings["current_typic"],
        settings["experimental_data_scale_transfer"],
        settings["experimental_data_scale_output"],
        type_curve_plot,
    )
    return read, path_voltages, type_curve_plot, Vv, Id, input_voltage, n_points, count_transfer, count_output


def _aggregate_rmse(model, coeff, Vv, Id, count_transfer):
    id_matrix = np.asarray(Id, dtype=float)
    vv_matrix = np.asarray(Vv, dtype=float)
    n_points, n_curves = id_matrix.shape
    pred_matrix = np.asarray(model.calc_model(vv_matrix.ravel(), *coeff), dtype=float).reshape(
        n_points, n_curves
    )

    transfer_rmses = []
    output_rmses = []
    per_curve = []
    for idx in range(n_curves):
        residual = pred_matrix[:, idx] - id_matrix[:, idx]
        rmse = float(np.sqrt(np.mean(np.square(residual))))
        per_curve.append(rmse)
        if idx < count_transfer:
            transfer_rmses.append(rmse)
        else:
            output_rmses.append(rmse)

    transfer_agg = float(np.sqrt(np.mean(np.square(transfer_rmses)))) if transfer_rmses else np.nan
    output_agg = float(np.sqrt(np.mean(np.square(output_rmses)))) if output_rmses else np.nan
    return transfer_agg, output_agg, per_curve


def _knee_index(transfer_rmses, output_rmses):
    x = np.asarray(transfer_rmses, dtype=float)
    y = np.asarray(output_rmses, dtype=float)
    if x.size < 3:
        return 0
    x_norm = (x - x.min()) / max(x.max() - x.min(), 1e-12)
    y_norm = (y - y.min()) / max(y.max() - y.min(), 1e-12)
    distances = np.sqrt(x_norm ** 2 + y_norm ** 2)
    return int(np.argmin(distances))


def _weight_grid(min_weight, max_weight, n_points):
    return np.geomspace(min_weight, max_weight, n_points)


def run_scan(json_path: Path, min_weight=0.5, max_weight=20.0, n_points=10, out_dir=None):
    settings = _load_settings(json_path)
    read, path_voltages, type_curve_plot, Vv, Id, input_voltage, n_points_data, count_transfer, _ = (
        _prepare_data(settings)
    )

    load_parameters = U.load_coefficients(settings)
    mode_idleak, load_idleak = U.load_idleak_parameters(settings)
    width_t = U.get_transistor_width(settings)
    tp_tst = U.get_transistor_type(settings)
    resistance = U.get_resistance(settings)
    current = U.get_current(settings)

    model_id = U.create_model_opt(
        TFTModel,
        input_voltage,
        n_points_data,
        type_curve_plot,
        settings["current_typic"],
        settings["experimental_data_scale_transfer"],
        load_idleak,
        mode_idleak,
        count_transfer,
        resistance,
        current,
        width_t,
        tp_tst,
        path_voltages=path_voltages,
        read=read,
        settings=settings,
    )

    optimizer = U.create_optimizer(settings, path_voltages, type_curve_plot)
    original_loss_mode = settings.get("loss_mode", "fixed")
    settings["loss_mode"] = "fixed"
    U.configure_optimizer(optimizer, settings)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = out_dir or (ROOT / "artefatos" / f"pareto_{timestamp}")
    out_root.mkdir(parents=True, exist_ok=True)

    rows = []
    weights = _weight_grid(min_weight, max_weight, n_points)
    for weight in weights:
        optimizer.transfer_curve_weight = float(weight)
        coeff_opt, _, verbose = U.optimize_model(
            optimizer, model_id, load_parameters, *path_voltages, settings=settings
        )
        transfer_rmse, output_rmse, per_curve = _aggregate_rmse(
            model_id, coeff_opt, Vv, Id, count_transfer
        )
        rows.append(
            {
                "transfer_curve_weight": float(weight),
                "transfer_rmse": transfer_rmse,
                "output_rmse": output_rmse,
                "per_curve_rmse": per_curve,
                "verbose_tail": "\n".join(verbose.splitlines()[-3:]),
            }
        )
        print(
            f"weight={weight:6.2f}  transfer_rmse={transfer_rmse:.4e}  output_rmse={output_rmse:.4e}"
        )

    settings["loss_mode"] = original_loss_mode

    csv_path = out_root / "pareto_scan.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["transfer_curve_weight", "transfer_rmse", "output_rmse", "per_curve_rmse"]
        )
        for row in rows:
            writer.writerow(
                [
                    row["transfer_curve_weight"],
                    row["transfer_rmse"],
                    row["output_rmse"],
                    json.dumps(row["per_curve_rmse"]),
                ]
            )

    transfer_vals = [row["transfer_rmse"] for row in rows]
    output_vals = [row["output_rmse"] for row in rows]
    knee_idx = _knee_index(transfer_vals, output_vals)
    knee_row = rows[knee_idx]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(transfer_vals, output_vals, "o-", label="Pareto scan")
    ax.scatter(
        [knee_row["transfer_rmse"]],
        [knee_row["output_rmse"]],
        color="red",
        s=80,
        zorder=5,
        label=f"knee (w={knee_row['transfer_curve_weight']:.2f})",
    )
    for row in rows:
        ax.annotate(
            f"{row['transfer_curve_weight']:.1f}",
            (row["transfer_rmse"], row["output_rmse"]),
            textcoords="offset points",
            xytext=(4, 4),
            fontsize=8,
        )
    ax.set_xlabel("Aggregate transfer RMSE (dec, log10)")
    ax.set_ylabel("Aggregate output RMSE (uA scale)")
    ax.set_title("Transfer weight Pareto trade-off")
    ax.grid(True, alpha=0.3)
    ax.legend()
    png_path = out_root / "pareto_frontier.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

    summary_path = out_root / "pareto_summary.txt"
    summary_path.write_text(
        "\n".join(
            [
                f"json={json_path}",
                f"knee_weight={knee_row['transfer_curve_weight']}",
                f"knee_transfer_rmse={knee_row['transfer_rmse']}",
                f"knee_output_rmse={knee_row['output_rmse']}",
                f"csv={csv_path}",
                f"plot={png_path}",
            ]
        )
    )

    print(f"\nKnee point: transfer_curve_weight={knee_row['transfer_curve_weight']:.2f}")
    print(f"Artifacts saved to {out_root}")
    return rows, knee_row, out_root


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", nargs="?", default=str(DEFAULT_JSON))
    parser.add_argument("--min-weight", type=float, default=0.5)
    parser.add_argument("--max-weight", type=float, default=20.0)
    parser.add_argument("--n-points", type=int, default=10)
    parser.add_argument("--out-dir", type=str, default=None)
    args = parser.parse_args()

    run_scan(
        Path(args.json_path),
        min_weight=args.min_weight,
        max_weight=args.max_weight,
        n_points=args.n_points,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
