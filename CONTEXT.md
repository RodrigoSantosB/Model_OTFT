# OTFT/CNT Modeling — Voltage, Shift & Legend Context

This context governs how gate/drain biases are labeled, shifted, and displayed when
comparing experimental curves against the fitted (optimized) TFT model. It exists
because the same numeric "tension" has been overloaded to mean three different
things (measured bias, model bias, legend label), which produced a silent error on
the CNT technology.

## Language

**Tensão nominal** (nominal voltage):
The bias at which the experimental curve was physically measured (e.g. `-4 V` for `cnt-4VGS`).
_Avoid_: tensão medida bruta, tensão do arquivo.

**Tensão efetiva** (effective voltage):
The bias that reproduces the current observed on the reference transfer curve; it absorbs
the hysteresis/threshold offset. It is defined on the transfer axis exactly as that axis is
stored on disk (see **espaço do disco**).
_Avoid_: tensão ajustada, tensão corrigida.

**Shift global** (global shift):
A single horizontal voltage offset (`pre_process_shift_volt_data`, `-1 V` for CNT) applied to
every curve. When `pre_process_global_shift_persisted = yes` it is already baked into the CSVs
on disk, so the runtime pipeline must not re-apply it to the data — only reason about it.
_Avoid_: deslocamento, offset genérico.

**Shift automático** (automatic/local output shift):
The per-output-curve shift computed by `estimate_output_shifts`: it matches the output current
at the reference VDS back onto the reference transfer curve to recover the **tensão efetiva**.
_Avoid_: shift local (ambíguo com `apply_local_output_shift`).

**Espaço do disco** (disk space):
The voltage frame in which the CSVs are stored *after* the **shift global** has been persisted.
The model parameters are fitted against the transfer curves in this frame.

**Espaço medido** (measured space):
The original voltage frame *before* the persisted **shift global** (disk space minus the global shift).

**Contrato de legenda** (legend contract):
The experimental trace legend shows the **tensão nominal**; the model trace legend shows the
**tensão efetiva**, with the applied shift in parentheses (e.g. `Model -3.90V (-1.10V)` vs `Exp -4.00V`).

## Relationships

- A **curva de saída** (output curve) carries exactly one **tensão nominal** and one **tensão efetiva**.
- The **tensão efetiva** lives in the **espaço do disco** — the same frame in which model parameters are fitted.
- The **shift global** relates the two frames: `espaço do disco = espaço medido + shift global`.
- The model must compute an output curve at its **tensão efetiva** (disk space); the experimental points are read straight from the CSV and are independent of any tension label.

## Flagged ambiguities (resolved)

- `list_tension_shift` was used to mean **both** the model's input bias (fed to the model via
  `path_voltages` → `input_voltage`) **and** the display base that the legend re-shifts.
  **Resolved (ADR 0001):** these are distinct — `list_tension_shift` / `input_voltage` carry the
  **tensão efetiva** in **espaço do disco** for the model; `list_tension` carries the **tensão nominal**
  for the experimental legend only.
- The old `_adjust_shift_with_preprocess` discounted the **shift global** from the model input while
  `apply_global_shift_to_output_display` re-added it only for display. **Removed:** automatic shifts are
  computed and applied in **espaço do disco**; the model receives the effective voltage as found on the
  reference transfer (e.g. `-3.90 V` for `cnt-4VGS`, not `-2.90 V`).
- For CNT the **shift global** (`-1 V`) is the same order of magnitude as the operating bias (`0.1–4 V`),
  so discounting it from the model input caused a ~24% current error; for Org1 (biases `-20…-50 V`, no
  global shift) the same defect was invisible.
