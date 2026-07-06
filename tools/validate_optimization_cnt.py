#!/usr/bin/env python3
"""Short CNT optimization smoke test with per-curve RMSE comparison."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules_otft._model import TFTModel
from modules_otft._read_data import ReadData
from modules_otft import _utils as U

JSON_PATH = ROOT / "inputs/tipo p/inputs_cnts_v2.json"


def _load_settings():
    blocks = json.loads(JSON_PATH.read_text())
    settings = {"_json_path": str(JSON_PATH), "_json_blocks": blocks}
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
        read, settings, path_voltages, effective, list_tension_nominal=U.extract_nominal_voltages(nominal_path)
    )
    Vv, Id, input_voltage, n_points, count_transfer, count_output = read.load_data(
        settings["type_read_data_exp"],
        path_voltages,
        settings["current_typic"],
        settings["experimental_data_scale_transfer"],
        settings["experimental_data_scale_output"],
        type_curve_plot,
    )
    return read, settings, path_voltages, type_curve_plot, Vv, Id, input_voltage, n_points, count_transfer, count_output


def _global_weighted_rmse(optimizer, model, coeff, Vv, Id, count_transfer=None):
    id_matrix = np.asarray(Id, dtype=float)
    vv_matrix = np.asarray(Vv, dtype=float)
    vv_flat = vv_matrix.ravel()
    id_flat = id_matrix.ravel()
    pred = model.calc_model(vv_flat, *coeff)
    weights = optimizer._combine_residual_weights(id_matrix, vv_flat, count_transfer)
    return float(optimizer._weighted_rmse(pred - id_flat, weights))


def _per_curve_rmse(model, coeff, Vv, Id, count_transfer):
    id_matrix = np.asarray(Id, dtype=float)
    vv_matrix = np.asarray(Vv, dtype=float)
    n_points, n_curves = id_matrix.shape
    # calc_model segments the flat vector internally per curve, so predict on
    # the full flattened input and reshape instead of feeding isolated columns.
    pred_matrix = np.asarray(
        model.calc_model(vv_matrix.ravel(), *coeff), dtype=float
    ).reshape(n_points, n_curves)
    labels = []
    rmses = []
    for index in range(n_curves):
        residual = pred_matrix[:, index] - id_matrix[:, index]
        rmse = float(np.sqrt(np.mean(np.square(residual))))
        curve_type = "transfer" if index < count_transfer else "output"
        labels.append(f"{curve_type}[{index}]")
        rmses.append(rmse)
    return labels, rmses


def main() -> int:
    print("=== verify_display_contract ===")
    verify = subprocess.run(
        [sys.executable, str(ROOT / "tools/verify_display_contract.py"), str(JSON_PATH)],
        cwd=str(ROOT),
        check=False,
    )
    if verify.returncode != 0:
        print("verify_display_contract failed")
        return verify.returncode

    settings = _load_settings()
    read, settings, path_voltages, type_curve_plot, Vv, Id, input_voltage, n_points, count_transfer, count_output = _prepare_data(settings)

    load_parameters = U.load_coefficients(settings)
    mode_idleak, load_idleak = U.load_idleak_parameters(settings)
    width_t = U.get_transistor_width(settings)
    tp_tst = U.get_transistor_type(settings)
    resistance = U.get_resistance(settings)
    current = U.get_current(settings)

    model_id = U.create_model_opt(
        TFTModel, input_voltage, n_points, type_curve_plot, settings["current_typic"],
        settings["experimental_data_scale_transfer"], load_idleak, mode_idleak, count_transfer,
        resistance, current, width_t, tp_tst, path_voltages=path_voltages, read=read,
        settings=settings,
    )

    optimizer = U.create_optimizer(settings, path_voltages, type_curve_plot)
    U.configure_optimizer(optimizer, settings)

    init_weighted = _global_weighted_rmse(optimizer, model_id, load_parameters, Vv, Id, count_transfer)
    print(f"\nGlobal weighted RMSE (initial): {init_weighted:.6e}")

    init_labels, init_rmses = _per_curve_rmse(model_id, load_parameters, Vv, Id, count_transfer)
    print("\n=== per-curve RMSE (initial guess) ===")
    for label, value in zip(init_labels, init_rmses):
        print(f"  {label}: {value:.6e}")

    coeff_opt, coeff_error, text_verbose = U.optimize_model(
        optimizer, model_id, load_parameters, *path_voltages, settings=settings
    )

    opt_weighted = _global_weighted_rmse(optimizer, model_id, coeff_opt, Vv, Id, count_transfer)
    print(f"\nGlobal weighted RMSE (optimized): {opt_weighted:.6e} (delta={opt_weighted - init_weighted:+.6e})")

    opt_labels, opt_rmses = _per_curve_rmse(model_id, coeff_opt, Vv, Id, count_transfer)
    print("\n=== per-curve RMSE (optimized) ===")
    improved = 0
    for label, before, after in zip(opt_labels, init_rmses, opt_rmses):
        delta = after - before
        status = "better" if after < before else "worse/same"
        if after < before:
            improved += 1
        print(f"  {label}: {after:.6e} ({status}, delta={delta:+.6e})")

    print(f"\nImproved curves: {improved}/{len(opt_rmses)}")
    print("\n=== optimizer verbose (tail) ===")
    print("\n".join(text_verbose.splitlines()[-12:]))

    if opt_weighted >= init_weighted:
        print("WARNING: global weighted RMSE did not improve in short smoke test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
