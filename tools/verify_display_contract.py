#!/usr/bin/env python3
"""Verify nominal/effective voltage contract for plot legends and model input."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules_otft._model import TFTModel
from modules_otft._read_data import ReadData
from modules_otft import _utils as U

VOLTAGE_RE = re.compile(r"(-?\d+\.\d+)V")


def _load_settings(json_path: Path) -> dict:
    blocks = json.loads(json_path.read_text())
    settings = {"_json_path": str(json_path), "_json_blocks": blocks}
    for block in blocks:
        settings.update(block)
    return settings


def _parse_voltage(label: str) -> float | None:
    match = VOLTAGE_RE.search(label.replace("<b>", ""))
    if not match:
        return None
    return float(match.group(1))


def _run_pipeline(json_path: Path):
    settings = _load_settings(json_path)
    U.settings = settings

    read = ReadData()
    type_curve_plot = U.get_type_plot(settings)
    U.calculate_shift_list(settings)
    effective_voltages = U.get_shift_list(read, settings)
    path_voltages_nominal = read.read_files_experimental(settings["path"])
    path_voltages = U.apply_effective_voltages_to_path(path_voltages_nominal, effective_voltages)
    nominal_voltages = U.extract_nominal_voltages(path_voltages_nominal)

    path_voltages, effective_filtered, nominal_filtered = U.filter_and_load_files(
        read,
        settings,
        path_voltages,
        effective_voltages,
        list_tension_nominal=nominal_voltages,
    )

    Vv, Id, input_voltage, n_points, count_transfer, count_output = read.load_data(
        settings["type_read_data_exp"],
        path_voltages,
        settings["current_typic"],
        settings["experimental_data_scale_transfer"],
        settings["experimental_data_scale_output"],
        type_curve_plot,
    )

    load_parameters = U.load_coefficients(settings)
    _, load_idleak = U.load_idleak_parameters(settings)
    width_t = U.get_transistor_width(settings)
    tp_tst = U.get_transistor_type(settings)
    resistance = U.get_resistance(settings)
    current = U.get_current(settings)

    model = U.instance_model(
        read,
        TFTModel,
        n_points,
        type_curve_plot,
        load_parameters,
        input_voltage,
        Vv,
        load_idleak,
        width_t,
        count_transfer,
        tp_tst,
        settings["experimental_data_scale_transfer"],
        settings["current_typic"],
        resistance,
        current,
        path_voltages=path_voltages,
        settings=settings,
    )
    _, _, out_model_data, out_exp_data = U.load_experimental_data(
        read, count_transfer, Vv, Id, model, count_output
    )

    metadata = settings.get("_shift_metadata", [])
    metadata_by_name = {
        Path(entry["curve_name"]).stem.lower(): entry
        for entry in metadata
        if entry.get("curve_type") == "output"
    }

    output_curves = []
    for path, curve_type, effective in path_voltages:
        if curve_type != 1:
            continue
        stem = Path(path).stem.lower()
        entry = metadata_by_name[stem]
        output_curves.append((stem, float(entry["nominal_voltage"]), float(effective)))

    assert len(input_voltage) == len(path_voltages), "input_voltage length mismatch"
    for index, (_, _, effective) in enumerate(path_voltages):
        assert abs(float(input_voltage[index]) - float(effective)) < 1e-9, (
            f"path_voltages[{index}] effective {effective} != input_voltage {input_voltage[index]}"
        )

    assert len(nominal_filtered) == len(effective_filtered), "nominal/effective list length mismatch"
    for nominal, effective in zip(nominal_filtered, effective_filtered):
        assert abs(float(nominal) + float(effective - nominal) - float(effective)) < 1e-9

    for stem, nominal, effective in output_curves:
        entry = metadata_by_name[stem]
        display_delta = float(entry["display_delta"])
        assert abs(float(entry["nominal_voltage"]) - nominal) < 1e-6, entry
        assert abs(float(entry["effective_voltage"]) - effective) < 1e-6, entry
        assert abs((effective - nominal) - display_delta) < 1e-6, entry
        assert abs(nominal + display_delta - effective) < 1e-6, entry

    import plotly.graph_objects as go

    captured: list = []
    go.Figure.show = lambda self, *args, **kwargs: captured.append(self)

    plot = U.initialize_graphics_plot(settings)
    U.plot_curves(
        "Show output curve",
        plot,
        nominal_filtered,
        effective_filtered,
        count_transfer,
        [],
        out_model_data,
        [],
        out_exp_data,
        settings.get("_shift_metadata", []),
        settings.get("selected_curves", ""),
        settings["current_typic"],
        type_curve_plot,
    )

    exp_labels = []
    model_labels = []
    for figure in captured:
        for trace in figure.data:
            label = (trace.name or "").replace("<b>", "").replace("<b", "")
            if trace.mode and "lines" in trace.mode:
                model_labels.append(label)
            else:
                exp_labels.append(label)

    assert len(exp_labels) == len(output_curves), "experimental legend count mismatch"
    assert len(model_labels) == len(output_curves), "model legend count mismatch"

    for (_, nominal, effective), exp_label, model_label in zip(output_curves, exp_labels, model_labels):
        entry = next(
            value for value in metadata_by_name.values()
            if abs(float(value["nominal_voltage"]) - nominal) < 1e-6
        )
        display_delta = float(entry["display_delta"])

        exp_voltage = _parse_voltage(exp_label)
        model_voltage = _parse_voltage(model_label)
        assert exp_voltage is not None, exp_label
        assert model_voltage is not None, model_label
        assert abs(exp_voltage - nominal) < 0.02, (exp_label, nominal)
        assert abs(model_voltage - effective) < 0.02, (model_label, effective)

        if abs(display_delta) > 1e-6:
            paren_match = re.search(r"\(([+-]?\d+\.\d+)V\)", model_label)
            assert paren_match is not None, model_label
            assert abs(float(paren_match.group(1)) - display_delta) < 0.02, model_label
            assert abs(nominal + display_delta - effective) < 0.02, model_label


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "json_paths",
        nargs="*",
        default=[
            "inputs/tipo p/inputs_Org1_SB.json",
            "inputs/tipo p/inputs_cnts_v2.json",
        ],
    )
    args = parser.parse_args()

    failures = 0
    for raw_path in args.json_paths:
        json_path = Path(raw_path)
        if not json_path.is_absolute():
            json_path = ROOT / json_path
        try:
            _run_pipeline(json_path)
            print(f"OK  {json_path.relative_to(ROOT)}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {json_path.relative_to(ROOT)}: {exc}")
        except Exception as exc:
            failures += 1
            print(f"ERROR {json_path.relative_to(ROOT)}: {exc}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
