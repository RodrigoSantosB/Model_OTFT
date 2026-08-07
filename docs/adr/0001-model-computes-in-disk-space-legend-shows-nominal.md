# Model computes output curves in disk space; legend shows nominal for Exp, effective for Model

**Context.** Output-curve hysteresis is compensated by a per-curve *effective* gate voltage recovered
from the reference transfer curve, and some technologies (CNT) also carry a *global shift*
(`pre_process_shift_volt_data`, `-1 V`) persisted into the CSVs on disk. The model parameters are
fitted against the transfer curves as stored on disk (post-global-shift), so an output curve must be
computed at its effective voltage **in that same disk frame**.

**Decision.** The model's gate bias (`path_voltages` → `input_voltage` → `create_models_datas`) carries
the **effective voltage in disk space** (e.g. `-3.90 V` for `cnt-4VGS`). The experimental legend shows
the **nominal** voltage (`-4.00 V`) via a *separate* `list_tension` vector; the model legend shows the
effective voltage with the applied shift in parentheses. We removed the previous scheme that discounted
the global shift from the model input (`_adjust_shift_with_preprocess`) and re-added it only for display
(`apply_global_shift_to_output_display`), because for CNT the global shift is the same order as the
operating bias and that scheme silently fit the transfers in disk space while computing the outputs
`1 V` weaker in the same frame (`-2.90 V` instead of `-3.90 V`), a ~24% current error.

**Consequences.** `path_voltages`/`input_voltage` remain the single source of the model bias (nominal is
display-only, derived independently from the CSV/file voltages). On Org1-style data (no global shift) the
behavior is unchanged. The display re-shift helper becomes unnecessary.
