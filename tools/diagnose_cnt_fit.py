#!/usr/bin/env python3
"""Deep diagnostic of the CNT TRF fit: residual location, parameter
sensitivity, and model capacity (transfers-only fit)."""

from __future__ import annotations

import json
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


def _param_names(settings):
    return U.get_parameter_keys(settings=settings)


def _load_settings():
    blocks = json.loads(JSON_PATH.read_text())
    settings = {"_json_path": str(JSON_PATH), "_json_blocks": blocks}
    for block in blocks:
        settings.update(block)
    return settings


def main() -> int:
    settings = _load_settings()
    read = ReadData()
    type_curve_plot = U.get_type_plot(settings)
    U.calculate_shift_list(settings)
    effective = U.get_shift_list(read, settings)
    nominal_path = read.read_files_experimental(settings["path"])
    path_voltages = U.apply_effective_voltages_to_path(nominal_path, effective)
    path_voltages, effective, nominal = U.filter_and_load_files(
        read, settings, path_voltages, effective,
        list_tension_nominal=U.extract_nominal_voltages(nominal_path))
    Vv, Id, input_voltage, n_points, count_transfer, count_output = read.load_data(
        settings["type_read_data_exp"], path_voltages, settings["current_typic"],
        settings["experimental_data_scale_transfer"],
        settings["experimental_data_scale_output"], type_curve_plot)

    load_parameters = U.load_coefficients(settings)
    mode_idleak, load_idleak = U.load_idleak_parameters(settings)
    width_t = U.get_transistor_width(settings)
    tp_tst = U.get_transistor_type(settings)
    resistance = U.get_resistance(settings)
    current = U.get_current(settings)

    model_id = U.create_model_opt(
        TFTModel, input_voltage, n_points, type_curve_plot, settings["current_typic"],
        settings["experimental_data_scale_transfer"], load_idleak, mode_idleak,
        count_transfer, resistance, current, width_t, tp_tst,
        path_voltages=path_voltages, read=read, settings=settings)

    optimizer = U.create_optimizer(settings, path_voltages, type_curve_plot)
    U.configure_optimizer(optimizer, settings)

    id_matrix = np.asarray(Id, dtype=float)
    vv_matrix = np.asarray(Vv, dtype=float)
    vv_flat = vv_matrix.ravel()
    id_flat = id_matrix.ravel()
    n_pts, n_curves = id_matrix.shape
    weights = optimizer._combine_residual_weights(id_matrix, vv_flat, count_transfer)

    curve_labels = []
    for idx in range(n_curves):
        kind = "transfer" if idx < count_transfer else "output"
        curve_labels.append(f"{kind}[{idx}] (V={input_voltage[idx]:+.2f})")

    # ---- full compromise fit (same path as notebook) ----
    coeff_opt, _, verbose = U.optimize_model(
        optimizer, model_id, load_parameters, *path_voltages, settings=settings)
    coeff_opt = np.asarray(coeff_opt, dtype=float)
    pred_flat = model_id.calc_model(vv_flat, *coeff_opt)
    full_rmse = optimizer._weighted_rmse(pred_flat - id_flat, weights)

    print("\n================ 1) LOCALIZACAO DO RESIDUO ================")
    param_names = _param_names(settings)
    print(f"coeff_opt: {dict(zip(param_names, np.round(coeff_opt, 4)))}")
    print(f"weighted RMSE global: {full_rmse:.4e}\n")
    pred_matrix = pred_flat.reshape(n_pts, n_curves)
    regions = [(-6.0, -2.0, "on/strong"), (-2.0, -0.5, "subthreshold"), (-0.5, 0.5, "off/leak")]
    for idx in range(n_curves):
        col_res = pred_matrix[:, idx] - id_matrix[:, idx]
        col_v = vv_matrix[:, idx]
        unit = "dec(log10)" if idx < count_transfer else "uA"
        line = f"  {curve_labels[idx]:32s} rmse={np.sqrt(np.mean(col_res**2)):.3e} {unit}"
        if idx < count_transfer:
            parts = []
            for lo, hi, name in regions:
                mask = (col_v >= lo) & (col_v < hi)
                if np.any(mask):
                    parts.append(f"{name}={np.sqrt(np.mean(col_res[mask]**2)):.3f}")
            line += "  [" + ", ".join(parts) + "]"
        print(line)

    # ---- 2) sensibilidade dos parametros no otimo ----
    print("\n================ 2) SENSIBILIDADE (delta RMSE p/ +5% do span) ================")
    lw_bounds, up_bounds = U.get_bounds(settings)
    lb = np.asarray(lw_bounds, dtype=float)
    ub = np.asarray(up_bounds, dtype=float)
    span = ub - lb
    for i, name in enumerate(param_names):
        trial = coeff_opt.copy()
        step = 0.05 * span[i]
        trial[i] = np.clip(trial[i] + step, lb[i], ub[i])
        if np.isclose(trial[i], coeff_opt[i]):
            trial[i] = np.clip(coeff_opt[i] - step, lb[i], ub[i])
        try:
            trial_pred = model_id.calc_model(vv_flat, *trial)
            delta = optimizer._weighted_rmse(trial_pred - id_flat, weights) - full_rmse
            print(f"  {name:8s} {coeff_opt[i]:>12.4g}  delta_rmse={delta:+.4e}")
        except Exception as exc:
            print(f"  {name:8s} {coeff_opt[i]:>12.4g}  ERRO: {exc}")

    # ---- 3) capacidade: ajustar SO as transfers (peso zero nas saidas) ----
    print("\n================ 3) CAPACIDADE DO MODELO (transfers-only) ================")
    transfer_weights = np.zeros_like(id_matrix)
    transfer_weights[:, :count_transfer] = 1.0
    tw_flat = transfer_weights.ravel()
    sigma_t = np.where(tw_flat > 0, 0.7, 1e6)
    try:
        coeff_t, _, _ = optimizer._fit_once(
            model_id.calc_model, vv_flat, id_flat, coeff_opt, lb, ub, "trf", sigma_t)
        pred_t = model_id.calc_model(vv_flat, *coeff_t).reshape(n_pts, n_curves)
        print(f"  coeff transfers-only: {dict(zip(param_names, np.round(coeff_t, 4)))}")
        for idx in range(count_transfer):
            res_full = pred_matrix[:, idx] - id_matrix[:, idx]
            res_only = pred_t[:, idx] - id_matrix[:, idx]
            print(
                f"  {curve_labels[idx]:32s} rmse compromisso={np.sqrt(np.mean(res_full**2)):.3f}"
                f"  -> transfers-only={np.sqrt(np.mean(res_only**2)):.3f} dec"
            )
    except Exception as exc:
        print(f"  fit transfers-only falhou: {exc}")

    print("\n================ verbose (tail) ================")
    print("\n".join(verbose.splitlines()[-6:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
