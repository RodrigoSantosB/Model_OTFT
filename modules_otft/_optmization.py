from ._imports import *
from ._read_data import ReadData

LEGACY_PARAM_KEYS = ["VTHO", "DELTA", "N", "L", "LAMBDA", "VGCRIT", "JTH", "RS"]


class ModelOptmization(ReadData):
    """
    Class for optimizing models based on experimental data.

    Args:
        current_typic (str): Type of current.
        scale_transfer (float): Transfer scale.
        scale_output (float): Output scale.
        type_read (str): Type of reading.
        type_curve (str, optional): Curve type (default is 'log').
        method (str, optional): Optimization method (default is 'trf').
        bounds (tuple, optional): Bounds for optimization (default is empty).

    Attributes:
        __DEFAULT_BOUNDS (bool): Flag to use default bounds.
        __MAX_ITER (int): Maximum number of iterations.
        __FTOL_VALUE (float): Tolerance value.

    Methods:
        set_default_bounds(opt):
            Set whether default bounds should be used during optimization.
        set_num_iterations(iterations):
            Set the maximum number of iterations.
        set_ftol_param(ftol):
            Set the tolerance value.
        optimize_all(Model, coeff, *args):
            Optimize the model with the given initial coefficients and data.
    """

    __DEFAULT_BOUNDS = True
    __MAX_ITER = 20000
    __FTOL_VALUE = 0

    def __init__(self, current_typic, scale_transfer, scale_output, type_read, 
                 path_voltages, type_curve='log', method='trf', bounds=()):
        super().__init__()
        self.current_typic = current_typic
        self.scale_transfer = scale_transfer
        self.scale_output = scale_output
        self.type_read = type_read
        self.path_voltages = path_voltages
        self.type_curve = type_curve
        self.method = method
        self.bounds = bounds
        self.optimization_strategy = "curve_fit"
        self.enable_optuna = False
        self.optuna_trials = 30
        self.n_starts = 8
        self.random_seed = None
        self.maxfev = self.__MAX_ITER
        self.hysteresis_weight_mode = "none"
        self.hysteresis_weight_factor = 1.0
        self.hysteresis_weight_windows = []
        self.transfer_curve_weight = 1.0
        self.loss_mode = "fixed"
        self.adaptive_iterations = 5
        self.adaptive_beta = 1.0
        self.point_loss = "linear"
        self.f_scale = 0.1
        self.fixed_parameters = []
        self.ga_population = 60
        self.ga_generations = 150
        self.ga_mutation_rate = 0.1
        self.ga_crossover_rate = 0.8
        self.ga_elitism = 2
        self.ga_stall_generations = 30
        self.ga_seed = None

    def set_default_bounds(self, opt):
        """
        Set whether default bounds should be used during optimization.

        Args:
            opt (str): Option to use or not use default bounds ('yes' or 'no').

        Example:
            >>> set_default_bounds('yes')
            # Set to use default bounds during optimization.
        """
        self.__DEFAULT_BOUNDS = opt.lower() == "yes"

    def set_num_iterations(self, iterations):
        """
        Set the maximum number of iterations for optimization.

        Args:
            iterations (int): Number of iterations.
        """
        if isinstance(iterations, int) and iterations > 0:
            self.__MAX_ITER = iterations
            self.maxfev = iterations
        else:
            print("Invalid number of iterations.")

    def set_ftol_param(self, ftol):
        """
        Set the tolerance value for optimization convergence.

        Args:
            ftol (float): Tolerance value.
        """
        if isinstance(ftol, (int, float)):
            self.__FTOL_VALUE = float(ftol)
        else:
            print("Invalid tolerance value.")

    def set_hybrid_config(self, config):
        """
        Configure hybrid optimization parameters.
        """
        if not isinstance(config, dict):
            return

        method_cfg = str(config.get("optimization_method", self.method)).strip().lower()
        legacy_strategy_ga = self._to_bool(config.get("legacy_strategy_ga", False))
        if legacy_strategy_ga and method_cfg != "ga":
            print(
                "Legacy config detected: optimization_strategy='ga' is ignored for method selection. "
                "Use optimization_method='ga' to run genetic optimization."
            )

        strategy = str(config.get("optimization_strategy", self.optimization_strategy)).strip().lower()
        self.optimization_strategy = strategy if strategy in {"curve_fit", "hybrid"} else "curve_fit"
        self.enable_optuna = self._to_bool(config.get("enable_optuna", self.enable_optuna))
        self.optuna_trials = self._safe_int(config.get("optuna_trials", self.optuna_trials), self.optuna_trials)
        self.n_starts = self._safe_int(config.get("n_starts", self.n_starts), self.n_starts)
        if self.n_starts < 1:
            self.n_starts = 1
        self.random_seed = self._safe_int(config.get("random_seed", self.random_seed), self.random_seed, allow_none=True)
        self.maxfev = self._safe_int(config.get("maxfev", self.maxfev), self.maxfev)
        if self.maxfev and self.maxfev > 0:
            self.__MAX_ITER = self.maxfev

        mode = str(config.get("hysteresis_weight_mode", self.hysteresis_weight_mode)).strip().lower()
        self.hysteresis_weight_mode = mode if mode in {"none", "global", "windows"} else "none"
        factor = config.get("hysteresis_weight_factor", self.hysteresis_weight_factor)
        try:
            self.hysteresis_weight_factor = max(1.0, float(factor))
        except (TypeError, ValueError):
            self.hysteresis_weight_factor = 1.0

        self.hysteresis_weight_windows = self._parse_windows(config.get("hysteresis_weight_windows", []))
        transfer_weight = self._safe_float(
            config.get("transfer_curve_weight", self.transfer_curve_weight), self.transfer_curve_weight
        )
        self.transfer_curve_weight = transfer_weight if transfer_weight > 0 else 1.0

        loss_mode = str(config.get("loss_mode", self.loss_mode)).strip().lower()
        self.loss_mode = loss_mode if loss_mode in {"fixed", "adaptive_curve"} else "fixed"
        self.adaptive_iterations = max(1, self._safe_int(
            config.get("adaptive_iterations", self.adaptive_iterations), self.adaptive_iterations
        ))
        self.adaptive_beta = max(0.01, self._safe_float(
            config.get("adaptive_beta", self.adaptive_beta), self.adaptive_beta
        ))
        point_loss = str(config.get("point_loss", self.point_loss)).strip().lower()
        self.point_loss = point_loss if point_loss in {"linear", "soft_l1", "huber", "cauchy", "arctan"} else "linear"
        self.f_scale = max(1e-12, self._safe_float(config.get("f_scale", self.f_scale), self.f_scale))
        self.fixed_parameters = self._parse_fixed_parameter_names(config.get("fixed_parameters", []))

        self.ga_population = max(4, self._safe_int(config.get("ga_population", self.ga_population), self.ga_population))
        self.ga_generations = max(1, self._safe_int(config.get("ga_generations", self.ga_generations), self.ga_generations))
        self.ga_mutation_rate = min(1.0, max(0.0, self._safe_float(config.get("ga_mutation_rate", self.ga_mutation_rate), self.ga_mutation_rate)))
        self.ga_crossover_rate = min(1.0, max(0.0, self._safe_float(config.get("ga_crossover_rate", self.ga_crossover_rate), self.ga_crossover_rate)))
        self.ga_elitism = max(1, self._safe_int(config.get("ga_elitism", self.ga_elitism), self.ga_elitism))
        self.ga_stall_generations = max(1, self._safe_int(config.get("ga_stall_generations", self.ga_stall_generations), self.ga_stall_generations))
        self.ga_seed = self._safe_int(config.get("ga_seed", self.ga_seed), self.ga_seed, allow_none=True)

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y", "sim", "on"}

    def _safe_int(self, value, default, allow_none=False):
        if allow_none and value in (None, "", "none"):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _safe_float(self, value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _parse_windows(self, raw_windows):
        if raw_windows in (None, "", []):
            return []

        parsed_windows = raw_windows
        if isinstance(raw_windows, str):
            try:
                parsed_windows = eval(raw_windows, {"__builtins__": {}}, {})
            except Exception:
                return []

        if not isinstance(parsed_windows, (list, tuple)):
            return []

        normalized = []
        for entry in parsed_windows:
            if isinstance(entry, dict):
                min_v = entry.get("min", entry.get("start"))
                max_v = entry.get("max", entry.get("end"))
                weight = entry.get("weight", self.hysteresis_weight_factor)
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                min_v = entry[0]
                max_v = entry[1]
                weight = entry[2] if len(entry) >= 3 else self.hysteresis_weight_factor
            else:
                continue

            try:
                min_v = float(min_v)
                max_v = float(max_v)
                weight = max(1.0, float(weight))
            except (TypeError, ValueError):
                continue

            low, high = (min_v, max_v) if min_v <= max_v else (max_v, min_v)
            normalized.append({"min": low, "max": high, "weight": weight})

        return normalized

    def _resolve_bounds(self, coeff, ub_max):
        if self.__DEFAULT_BOUNDS:
            if len(coeff) >= 11:
                lb = np.array([0.0, 0.01, 10.0, 1.0, 1e2, 1.0, 1e-6, 0.0, 1.0, 2.0, 2e3], dtype=float)
                ub = np.array([ub_max, 0.10, 1e2, 4.0, 1e6, ub_max, 1e2, 1e2, 5.0, 8.0, 6e3], dtype=float)
            else:
                lb = np.array([0.0, 0, 1.0, 0, 10.0, 1.0, 1e-9, 0e7], dtype=float)
                ub = np.array([ub_max, 1, 999, 4, 20000, ub_max, 1e4, 1e7], dtype=float)
        else:
            lb = np.array(self.bounds[0], dtype=float) if self.bounds and self.bounds[0] else np.zeros(len(coeff), dtype=float)
            ub = np.array(self.bounds[1], dtype=float) if self.bounds and self.bounds[1] else np.full(len(coeff), ub_max, dtype=float)

        if len(lb) != len(coeff) or len(ub) != len(coeff):
            lb = np.resize(lb, len(coeff))
            ub = np.resize(ub, len(coeff))

        ub = np.maximum(ub, lb + 1e-15)
        return lb, ub

    def _param_names(self, count):
        if count <= len(LEGACY_PARAM_KEYS):
            return LEGACY_PARAM_KEYS[:count]
        extra = [f"p{idx}" for idx in range(len(LEGACY_PARAM_KEYS), count)]
        return LEGACY_PARAM_KEYS + extra

    def _parse_fixed_parameter_names(self, raw_fixed, n_params=None):
        if raw_fixed in (None, "", []):
            return []

        entries = raw_fixed
        if isinstance(raw_fixed, str):
            entries = [part.strip() for part in raw_fixed.split(",") if part.strip()]

        if not isinstance(entries, (list, tuple)):
            return []

        if n_params is None:
            return [str(entry).strip().upper() for entry in entries if str(entry).strip()]

        names = self._param_names(n_params)
        name_to_idx = {name.upper(): idx for idx, name in enumerate(names)}
        fixed_indices = []
        for entry in entries:
            key = str(entry).strip().upper()
            if key in name_to_idx:
                fixed_indices.append(name_to_idx[key])
        return sorted(set(fixed_indices))

    def _resolve_fixed_indices(self, coeff):
        if not self.fixed_parameters:
            return []
        if all(isinstance(item, int) for item in self.fixed_parameters):
            return sorted(set(int(i) for i in self.fixed_parameters if 0 <= int(i) < len(coeff)))
        return self._parse_fixed_parameter_names(self.fixed_parameters, len(coeff))

    def _reduce_coeff_space(self, coeff, lb, ub, fixed_indices):
        if not fixed_indices:
            return np.asarray(coeff, dtype=float), np.asarray(lb, dtype=float), np.asarray(ub, dtype=float), []

        fixed_set = set(fixed_indices)
        free_indices = [idx for idx in range(len(coeff)) if idx not in fixed_set]
        coeff_arr = np.asarray(coeff, dtype=float)
        lb_arr = np.asarray(lb, dtype=float)
        ub_arr = np.asarray(ub, dtype=float)
        return coeff_arr[free_indices], lb_arr[free_indices], ub_arr[free_indices], free_indices

    def _merge_free_coeffs(self, free_coeff, template_coeff, free_indices):
        result = np.asarray(template_coeff, dtype=float).copy()
        free_coeff = np.asarray(free_coeff, dtype=float)
        for idx, param_idx in enumerate(free_indices):
            result[param_idx] = free_coeff[idx]
        return result

    def _wrap_model_fixed_params(self, model_fn, template_coeff, fixed_indices, free_indices):
        if not fixed_indices:
            return model_fn

        template_coeff = np.asarray(template_coeff, dtype=float)

        def wrapped(vv_flat, *free_coeff):
            full_coeff = self._merge_free_coeffs(free_coeff, template_coeff, free_indices)
            return model_fn(vv_flat, *full_coeff)

        return wrapped

    def _expand_fit_result(self, free_coeff, free_errors, template_coeff, fixed_indices, free_indices):
        full_coeff = self._merge_free_coeffs(free_coeff, template_coeff, free_indices)
        full_errors = np.full(len(template_coeff), np.nan, dtype=float)
        if free_errors is not None:
            free_errors = np.asarray(free_errors, dtype=float)
            if free_errors.size == len(free_indices):
                for idx, param_idx in enumerate(free_indices):
                    full_errors[param_idx] = free_errors[idx]
        return full_coeff, full_errors

    def _compute_per_curve_rmse(self, pred_matrix, id_matrix):
        pred_matrix = np.asarray(pred_matrix, dtype=float)
        id_matrix = np.asarray(id_matrix, dtype=float)
        if pred_matrix.ndim != 2 or id_matrix.ndim != 2:
            return np.array([], dtype=float)

        n_curves = pred_matrix.shape[1]
        rmses = []
        for curve_index in range(n_curves):
            residual = pred_matrix[:, curve_index] - id_matrix[:, curve_index]
            rmses.append(float(np.sqrt(np.mean(np.square(residual)))))
        return np.asarray(rmses, dtype=float)

    def _build_weights_with_curve_multipliers(self, id_matrix, vv_flat, count_transfer, curve_multipliers):
        id_matrix = np.asarray(id_matrix, dtype=float)
        n_points, n_curves = id_matrix.shape
        base_flat = self._build_curve_balance_weights(id_matrix, count_transfer)
        base_2d = base_flat.reshape(n_points, n_curves)
        multipliers = np.asarray(curve_multipliers, dtype=float)
        if multipliers.size != n_curves:
            multipliers = np.ones(n_curves, dtype=float)
        weighted_2d = base_2d * multipliers[np.newaxis, :]
        weighted_flat = weighted_2d.ravel()

        transfer_mask = None
        if count_transfer is not None:
            transfer_mask = (np.arange(id_matrix.size) % n_curves) < count_transfer
        hysteresis_weights = self._build_hysteresis_weights(vv_flat, transfer_mask)
        combined = weighted_flat * hysteresis_weights
        mean_weight = float(np.mean(combined))
        if mean_weight > 0:
            combined /= mean_weight
        return combined

    def _update_curve_multipliers(self, curve_multipliers, curve_rmses, beta):
        multipliers = np.asarray(curve_multipliers, dtype=float)
        rmses = np.asarray(curve_rmses, dtype=float)
        if multipliers.size != rmses.size or rmses.size == 0:
            return multipliers

        mean_rmse = float(np.mean(rmses))
        if mean_rmse <= 0:
            return multipliers

        updated = multipliers * np.power(rmses / mean_rmse, beta)
        total = float(np.sum(updated))
        if total > 0:
            updated *= len(updated) / total
        return updated

    def _format_curve_rmse_report(self, curve_rmses, count_transfer=None):
        lines = []
        for idx, rmse in enumerate(curve_rmses):
            kind = "transfer" if count_transfer is not None and idx < count_transfer else "output"
            lines.append(f"  {kind}[{idx}] rmse={float(rmse):.6e}")
        return "\n".join(lines)

    def _build_curve_balance_weights(self, id_matrix, count_transfer=None):
        """
        Per-curve weights so transfer (log) and output (linear) contribute comparably.
        Transfer curves can be emphasized via `transfer_curve_weight`.
        """
        id_matrix = np.asarray(id_matrix, dtype=float)
        if id_matrix.ndim != 2:
            return np.ones(id_matrix.size, dtype=float)

        n_points, n_curves = id_matrix.shape
        weights_2d = np.zeros_like(id_matrix, dtype=float)
        for curve_index in range(n_curves):
            column = id_matrix[:, curve_index]
            scale = float(np.sqrt(np.mean(np.square(column))))
            scale = max(scale, 1e-12)
            weights_2d[:, curve_index] = 1.0 / (n_curves * n_points * scale * scale)
            if count_transfer is not None and curve_index < count_transfer:
                weights_2d[:, curve_index] *= self.transfer_curve_weight

        weights_flat = weights_2d.ravel()
        total = float(np.sum(weights_flat))
        if total > 0:
            weights_flat *= len(weights_flat) / total
        return weights_flat

    def _build_hysteresis_weights(self, vv_flat, transfer_mask=None):
        """
        Voltage-window weights. Windows target the transfer-curve VGS axis, so
        when `transfer_mask` is given, output points (whose axis is VDS and
        overlaps the same numeric range) are excluded from window boosting.
        """
        weights = np.ones_like(vv_flat, dtype=float)
        mode = self.hysteresis_weight_mode

        if mode == "global":
            weights *= self.hysteresis_weight_factor
            return weights

        if mode == "windows":
            for window in self.hysteresis_weight_windows:
                mask = (vv_flat >= window["min"]) & (vv_flat <= window["max"])
                if transfer_mask is not None:
                    mask &= transfer_mask
                weights[mask] *= window["weight"]
            return weights

        return weights

    def _combine_residual_weights(self, id_matrix, vv_flat, count_transfer=None):
        transfer_mask = None
        if count_transfer is not None:
            id_matrix_arr = np.asarray(id_matrix, dtype=float)
            if id_matrix_arr.ndim == 2:
                n_curves = id_matrix_arr.shape[1]
                # Row-major ravel of (n_points, n_curves): column = flat_index % n_curves.
                transfer_mask = (np.arange(id_matrix_arr.size) % n_curves) < count_transfer
        curve_weights = self._build_curve_balance_weights(id_matrix, count_transfer)
        hysteresis_weights = self._build_hysteresis_weights(vv_flat, transfer_mask)
        combined = curve_weights * hysteresis_weights
        mean_weight = float(np.mean(combined))
        if mean_weight > 0:
            combined /= mean_weight
        return combined

    def _format_saturated_bounds_report(self, coeff, lb, ub):
        lines = []
        names = self._param_names(len(coeff))
        for name, value, lower, upper in zip(names, coeff, lb, ub):
            span = float(upper - lower)
            if span <= 0:
                continue
            relative_lower = abs(float(value) - float(lower)) / span
            relative_upper = abs(float(value) - float(upper)) / span
            if relative_lower <= 0.01:
                lines.append(
                    f"WARNING: {name}={float(value):.6g} saturated at lower bound ({float(lower):.6g})"
                )
            if relative_upper <= 0.01:
                lines.append(
                    f"WARNING: {name}={float(value):.6g} saturated at upper bound ({float(upper):.6g})"
                )
        if not lines:
            return "No parameters within 1% of optimization bounds."
        return "\n".join(lines)

    def _coeff_errors_from_covariance(self, mat_covar, coeff_size):
        if mat_covar is None:
            return np.full(coeff_size, np.nan)
        mat_covar = np.asarray(mat_covar, dtype=float)
        if mat_covar.ndim != 2:
            return np.full(coeff_size, np.nan)
        diag = np.diag(mat_covar)
        diag = np.where(diag >= 0, diag, np.nan)
        if diag.size != coeff_size:
            return np.full(coeff_size, np.nan)
        return np.sqrt(diag)

    def _weighted_rmse(self, residuals, weights):
        safe_weights = np.clip(weights, 1e-12, np.inf)
        mse = np.average(np.square(residuals), weights=safe_weights)
        return float(np.sqrt(mse))

    def _is_feasible(self, coeff, lb, ub):
        return bool(np.all(coeff >= lb) and np.all(coeff <= ub))

    def _build_multistart_candidates(self, coeff, lb, ub):
        coeff = np.array(coeff, dtype=float)
        candidates = [np.clip(coeff, lb, ub)]

        if self.optimization_strategy != "hybrid":
            return candidates

        rng = np.random.default_rng(self.random_seed)
        n_extra = max(0, self.n_starts - 1)
        span = np.maximum(ub - lb, 1e-12)
        local_scale = 0.2 * span

        for _ in range(n_extra):
            if rng.random() < 0.5:
                trial = rng.uniform(lb, ub)
            else:
                trial = coeff + rng.normal(0.0, local_scale)
            candidates.append(np.clip(trial, lb, ub))

        return candidates

    def _build_optuna_candidates(self, model, vv_flat, id_flat, lb, ub, weights):
        if not self.enable_optuna:
            return [], ["Optuna disabled by configuration."]

        try:
            import optuna
        except Exception as exc:
            return [], [f"Optuna unavailable. Falling back to multi-start. Reason: {exc}"]

        optuna.logging.set_verbosity(optuna.logging.WARNING)
        sampler = optuna.samplers.TPESampler(seed=self.random_seed)
        study = optuna.create_study(direction="minimize", sampler=sampler)
        bounds = list(zip(lb, ub))

        def objective(trial):
            trial_coeff = []
            for idx, (min_v, max_v) in enumerate(bounds):
                trial_coeff.append(trial.suggest_float(f"p{idx}", float(min_v), float(max_v)))

            pred = model(vv_flat, *trial_coeff)
            residuals = pred - id_flat
            return self._weighted_rmse(residuals, weights)

        try:
            study.optimize(objective, n_trials=max(1, int(self.optuna_trials)))
        except Exception as exc:
            return [], [f"Optuna search failed. Falling back to multi-start. Reason: {exc}"]

        candidates = []
        completed_trials = [t for t in study.trials if t.value is not None and np.isfinite(t.value)]
        ranked = sorted(completed_trials, key=lambda trial: trial.value)
        for trial in ranked[: min(5, len(ranked))]:
            ordered = [trial.params.get(f"p{idx}") for idx in range(len(bounds))]
            if None in ordered:
                continue
            candidates.append(np.array(ordered, dtype=float))

        log = [f"Optuna completed {len(completed_trials)} valid trials."]
        return candidates, log

    def _fit_once(self, model, vv_flat, id_flat, coeff, lb, ub, method, sigma):
        output_verbose = io.StringIO()
        maxfev = self.maxfev if isinstance(self.maxfev, int) and self.maxfev > 0 else None
        fit_kwargs = {}
        if maxfev is not None:
            if method in {"trf", "dogbox"}:
                fit_kwargs["max_nfev"] = maxfev
            else:
                fit_kwargs["maxfev"] = maxfev
        if method in {"trf", "dogbox"}:
            # Parameters span several orders of magnitude; scale each one so the
            # trust region treats them comparably (improves TRF conditioning).
            span = np.asarray(ub, dtype=float) - np.asarray(lb, dtype=float)
            span = np.where(np.isfinite(span) & (span > 0), span, 1.0)
            x_scale = np.maximum(np.abs(np.asarray(coeff, dtype=float)), 1e-3 * span)
            fit_kwargs["x_scale"] = x_scale
            if self.point_loss != "linear":
                fit_kwargs["loss"] = self.point_loss
                fit_kwargs["f_scale"] = self.f_scale
        with contextlib.redirect_stdout(output_verbose):
            coeff_opt, mat_covar = curve_fit(
                model,
                vv_flat,
                id_flat,
                p0=coeff,
                bounds=(lb, ub),
                method=method,
                ftol=self.__FTOL_VALUE,
                gtol=self.__FTOL_VALUE,
                sigma=sigma,
                verbose=True,
                absolute_sigma=True,
                **fit_kwargs,
            )
        return coeff_opt, mat_covar, output_verbose.getvalue()

    def _prepare_optimization_space(self, model_fn, coeff, lb, ub):
        template_coeff = np.asarray(coeff, dtype=float)
        fixed_indices = self._resolve_fixed_indices(template_coeff)
        free_coeff, free_lb, free_ub, free_indices = self._reduce_coeff_space(
            template_coeff, lb, ub, fixed_indices
        )
        wrapped_model = self._wrap_model_fixed_params(
            model_fn, template_coeff, fixed_indices, free_indices
        )
        return wrapped_model, template_coeff, fixed_indices, free_indices, free_coeff, free_lb, free_ub

    def _finalize_optimization_result(self, free_coeff, free_errors, template_coeff, fixed_indices, free_indices, lb, ub):
        full_coeff, full_errors = self._expand_fit_result(
            free_coeff, free_errors, template_coeff, fixed_indices, free_indices
        )
        bounds_report = self._format_saturated_bounds_report(full_coeff, lb, ub)
        return full_coeff, full_errors, bounds_report

    def _run_multistart_fit(
        self,
        model_fn,
        vv_flat,
        id_flat,
        coeff,
        lb,
        ub,
        sigma,
        weights,
        id_matrix,
        count_transfer,
    ):
        wrapped_model, template_coeff, fixed_indices, free_indices, free_coeff, free_lb, free_ub = (
            self._prepare_optimization_space(model_fn, coeff, lb, ub)
        )

        candidate_logs = []
        if fixed_indices:
            fixed_names = [self._param_names(len(template_coeff))[idx] for idx in fixed_indices]
            candidate_logs.append(f"Fixed parameters: {', '.join(fixed_names)}")

        candidates = self._build_multistart_candidates(free_coeff, free_lb, free_ub)
        optuna_candidates, optuna_logs = self._build_optuna_candidates(
            wrapped_model, vv_flat, id_flat, free_lb, free_ub, weights
        )
        candidate_logs.extend(optuna_logs)
        candidates.extend(optuna_candidates)

        unique_candidates = []
        seen = set()
        for candidate in candidates:
            key = tuple(np.round(candidate, 12))
            if key in seen:
                continue
            seen.add(key)
            unique_candidates.append(candidate)

        best_fit = None
        best_score = np.inf
        best_fallback = None
        best_fallback_score = np.inf

        for idx, p0 in enumerate(unique_candidates):
            if not self._is_feasible(p0, free_lb, free_ub):
                candidate_logs.append(f"Candidate {idx + 1}: infeasible p0 discarded.")
                continue

            try:
                preview = wrapped_model(vv_flat, *p0)
                preview_score = self._weighted_rmse(preview - id_flat, weights)
                if preview_score < best_fallback_score:
                    best_fallback_score = preview_score
                    best_fallback = p0.copy()
            except Exception as exc:
                candidate_logs.append(f"Candidate {idx + 1}: preview failed ({exc}).")
                continue

            try:
                coeff_opt, mat_covar, text_verbose = self._fit_once(
                    wrapped_model, vv_flat, id_flat, p0, free_lb, free_ub, self.method, sigma
                )
                fit_pred = wrapped_model(vv_flat, *coeff_opt)
                score = self._weighted_rmse(fit_pred - id_flat, weights)
                candidate_logs.append(
                    f"Candidate {idx + 1}: success, weighted_rmse={score:.6e}."
                )

                if score < best_score:
                    best_score = score
                    best_fit = {
                        "free_coeff": np.array(coeff_opt, dtype=float),
                        "mat_covar": np.array(mat_covar, dtype=float) if mat_covar is not None else None,
                        "text_verbose": text_verbose,
                    }
            except (ValueError, RuntimeError) as exc:
                candidate_logs.append(f"Candidate {idx + 1}: fit failed ({exc}).")
            except Exception as exc:
                candidate_logs.append(f"Candidate {idx + 1}: unexpected fit error ({exc}).")

        if best_fit is not None:
            free_errors = self._coeff_errors_from_covariance(best_fit["mat_covar"], len(free_indices))
            full_coeff, full_errors, bounds_report = self._finalize_optimization_result(
                best_fit["free_coeff"],
                free_errors,
                template_coeff,
                fixed_indices,
                free_indices,
                lb,
                ub,
            )
            text_verbose = (
                best_fit["text_verbose"]
                + "\n"
                + "\n".join(candidate_logs)
                + "\n"
                + bounds_report
            )
            return full_coeff, full_errors, text_verbose, best_score

        if best_fallback is not None:
            full_coeff, full_errors, bounds_report = self._finalize_optimization_result(
                best_fallback,
                np.full(len(free_indices), np.nan),
                template_coeff,
                fixed_indices,
                free_indices,
                lb,
                ub,
            )
            fallback_log = "\n".join(
                candidate_logs + ["All curve_fit attempts failed. Returning best feasible preview candidate.", bounds_report]
            )
            return full_coeff, full_errors, fallback_log, best_fallback_score

        fail_free = np.clip(free_coeff, free_lb, free_ub)
        full_coeff, full_errors, bounds_report = self._finalize_optimization_result(
            fail_free,
            np.full(len(free_indices), np.nan),
            template_coeff,
            fixed_indices,
            free_indices,
            lb,
            ub,
        )
        fail_log = "\n".join(
            candidate_logs + ["No valid candidate generated. Returning clipped initial coefficients.", bounds_report]
        )
        return full_coeff, full_errors, fail_log, np.inf

    def _optimize_adaptive(
        self,
        model_fn,
        vv_flat,
        id_flat,
        coeff,
        lb,
        ub,
        sigma,
        id_matrix,
        count_transfer,
    ):
        n_points, n_curves = id_matrix.shape
        curve_multipliers = np.ones(n_curves, dtype=float)
        logs = [
            "ADAPTIVE CURVE LOSS (min-max reweighting)",
            f"iterations={self.adaptive_iterations}, beta={self.adaptive_beta}",
        ]

        best_result = None
        best_max_rmse = np.inf
        current_p0 = np.array(coeff, dtype=float)

        for iteration in range(self.adaptive_iterations):
            weights = self._build_weights_with_curve_multipliers(
                id_matrix, vv_flat, count_transfer, curve_multipliers
            )
            iter_sigma = sigma

            full_coeff, full_errors, text_verbose, score = self._run_multistart_fit(
                model_fn,
                vv_flat,
                id_flat,
                current_p0,
                lb,
                ub,
                iter_sigma,
                weights,
                id_matrix,
                count_transfer,
            )

            pred_matrix = model_fn(vv_flat, *full_coeff).reshape(n_points, n_curves)
            curve_rmses = self._compute_per_curve_rmse(pred_matrix, id_matrix)
            max_rmse = float(np.max(curve_rmses)) if curve_rmses.size else np.inf

            logs.append(f"Iteration {iteration + 1}: weighted_rmse={score:.6e}, max_curve_rmse={max_rmse:.6e}")
            logs.append(self._format_curve_rmse_report(curve_rmses, count_transfer))

            if max_rmse < best_max_rmse:
                best_max_rmse = max_rmse
                best_result = {
                    "coeff": full_coeff,
                    "errors": full_errors,
                    "verbose": text_verbose,
                    "curve_rmses": curve_rmses,
                }

            current_p0 = full_coeff
            if iteration + 1 < self.adaptive_iterations:
                curve_multipliers = self._update_curve_multipliers(
                    curve_multipliers, curve_rmses, self.adaptive_beta
                )

        if best_result is None:
            return current_p0, np.full(len(current_p0), np.nan), "\n".join(logs)

        logs.append(f"Selected solution with min max_curve_rmse={best_max_rmse:.6e}")
        verbose = "\n".join(logs) + "\n" + best_result["verbose"]
        return best_result["coeff"], best_result["errors"], verbose

    def _run_genetic_optimization(self, model, vv_flat, id_flat, coeff, lb, ub, weights):
        rng_seed = self.ga_seed if self.ga_seed is not None else self.random_seed
        rng = np.random.default_rng(rng_seed)
        dim = len(coeff)
        span = np.maximum(ub - lb, 1e-12)

        pop_size = max(4, int(self.ga_population))
        n_generations = max(1, int(self.ga_generations))
        elitism = min(max(1, int(self.ga_elitism)), pop_size)
        mutation_rate = float(np.clip(self.ga_mutation_rate, 0.0, 1.0))
        crossover_rate = float(np.clip(self.ga_crossover_rate, 0.0, 1.0))
        stall_limit = max(1, int(self.ga_stall_generations))

        population = rng.uniform(lb, ub, size=(pop_size, dim))
        population[0] = np.clip(np.array(coeff, dtype=float), lb, ub)

        def evaluate(individual):
            try:
                pred = model(vv_flat, *individual)
                score = self._weighted_rmse(pred - id_flat, weights)
                if np.isfinite(score):
                    return score
            except Exception:
                pass
            return np.inf

        fitness = np.array([evaluate(ind) for ind in population], dtype=float)
        logs = [f"GA initialized with population={pop_size}, generations={n_generations}."]

        best_idx = int(np.argmin(fitness))
        best_coeff = population[best_idx].copy()
        best_score = float(fitness[best_idx])
        stall_count = 0

        def tournament_select():
            k = min(3, pop_size)
            pool_idx = rng.integers(0, pop_size, size=k)
            pool_scores = fitness[pool_idx]
            return population[int(pool_idx[int(np.argmin(pool_scores))])]

        for generation in range(n_generations):
            order = np.argsort(fitness)
            population = population[order]
            fitness = fitness[order]

            if fitness[0] < best_score:
                best_score = float(fitness[0])
                best_coeff = population[0].copy()
                stall_count = 0
            else:
                stall_count += 1

            if generation == 0 or (generation + 1) % 10 == 0:
                logs.append(f"GA generation {generation + 1}: best weighted_rmse={best_score:.6e}")

            if stall_count >= stall_limit:
                logs.append(f"GA early stop after {generation + 1} generations (stall limit reached).")
                break

            next_population = [population[i].copy() for i in range(elitism)]
            while len(next_population) < pop_size:
                parent_a = tournament_select()
                parent_b = tournament_select()

                if rng.random() < crossover_rate:
                    alpha = rng.random(dim)
                    child_1 = alpha * parent_a + (1.0 - alpha) * parent_b
                    child_2 = alpha * parent_b + (1.0 - alpha) * parent_a
                else:
                    child_1 = parent_a.copy()
                    child_2 = parent_b.copy()

                for child in (child_1, child_2):
                    mutation_mask = rng.random(dim) < mutation_rate
                    if np.any(mutation_mask):
                        child[mutation_mask] += rng.normal(0.0, 0.1 * span[mutation_mask])
                    next_population.append(np.clip(child, lb, ub))
                    if len(next_population) >= pop_size:
                        break

            population = np.array(next_population[:pop_size], dtype=float)
            fitness = np.array([evaluate(ind) for ind in population], dtype=float)

        if not np.isfinite(best_score):
            fallback = np.clip(np.array(coeff, dtype=float), lb, ub)
            fallback_score = evaluate(fallback)
            logs.append("GA could not evaluate a valid individual. Returning clipped initial coefficients.")
            return fallback, float(fallback_score), logs

        logs.append(f"GA finished with best weighted_rmse={best_score:.6e}.")
        return best_coeff, best_score, logs

    def optimize_all(self, Model, coeff, *args):
        """
        Optimize the Model with the given initial coefficients,
        using the data from the *args arguments.

        Args:
            Model (object): Instance of the model to be optimized.
            coeff (array-like): Array with the initial coefficients for optimization.
            *args: List of parameters to be optimized.

        Returns:
            tuple: A tuple containing the optimized coefficients and their respective errors.
        """

        # Load experimental data
        Vv, Id, voltages, _, count_transfer, _ = super().load_data(
            self.type_read, self.path_voltages, self.current_typic,
            self.scale_transfer, self.scale_output, self.type_curve)

        id_matrix = np.asarray(Id, dtype=float)
        vv_matrix = np.asarray(Vv, dtype=float)
        Vv_flat = vv_matrix.ravel()
        Id_flat = id_matrix.ravel()

        # Determine maximum absolute voltage
        vv_max = np.max(abs(Vv_flat))

        # Number of data points
        npoints = len(Vv_flat)

        # Initial error estimation
        error_id = np.ones(npoints) * 0.7
        ub_max = 5 * vv_max
        coeff = np.array(coeff, dtype=float)
        lb, ub = self._resolve_bounds(coeff, ub_max)

        use_ga = self.method == "ga"

        if self.method not in {'trf', 'dogbox'} and not use_ga:
            print('--' * 50)
            print('No valid optimization method selected.\n')
            print('--' * 50)
            return None, None, ""

        if not use_ga:
            if self.method == 'trf':
                print()
                print('--' * 50)
                print('TRUST REGION REFLECTIVE (TRF) MODE')
                print('--' * 50)
                print()
            else:
                print()
                print('--' * 50)
                print('DOGBOX MODE')
                print('--' * 50)
                print()

        model_fn = Model.calc_model
        weights = self._combine_residual_weights(id_matrix, Vv_flat, count_transfer)
        sigma = error_id / np.sqrt(np.clip(weights, 1e-12, np.inf))

        if self.loss_mode == "adaptive_curve" and not use_ga:
            return self._optimize_adaptive(
                model_fn, Vv_flat, Id_flat, coeff, lb, ub, sigma, id_matrix, count_transfer
            )

        if use_ga:
            print()
            print('--' * 50)
            print('GENETIC ALGORITHM (GA) MODE')
            print('--' * 50)
            print()
            wrapped_model, template_coeff, fixed_indices, free_indices, free_coeff, free_lb, free_ub = (
                self._prepare_optimization_space(model_fn, coeff, lb, ub)
            )
            ga_coeff, ga_score, ga_logs = self._run_genetic_optimization(
                wrapped_model, Vv_flat, Id_flat, free_coeff, free_lb, free_ub, weights
            )
            ga_logs.append(f"GA best weighted_rmse={ga_score:.6e}; starting TRF polish.")

            try:
                polished_coeff, mat_covar, trf_verbose = self._fit_once(
                    wrapped_model, Vv_flat, Id_flat, ga_coeff, free_lb, free_ub, "trf", sigma
                )
                polished_pred = wrapped_model(Vv_flat, *polished_coeff)
                polished_score = self._weighted_rmse(polished_pred - Id_flat, weights)
                if np.isfinite(polished_score) and polished_score <= ga_score:
                    ga_coeff = np.array(polished_coeff, dtype=float)
                    ga_score = polished_score
                    ga_logs.append(f"TRF polish accepted: weighted_rmse={polished_score:.6e}")
                    if trf_verbose.strip():
                        ga_logs.append(trf_verbose.strip())
                else:
                    ga_logs.append(
                        "TRF polish rejected (worse than GA); keeping GA solution."
                    )
            except (ValueError, RuntimeError) as exc:
                ga_logs.append(f"TRF polish failed ({exc}); keeping GA solution.")
            except Exception as exc:
                ga_logs.append(f"TRF polish unexpected error ({exc}); keeping GA solution.")

            free_errors = np.full(len(free_indices), np.nan)
            ga_coeff, ga_error, bounds_report = self._finalize_optimization_result(
                ga_coeff, free_errors, template_coeff, fixed_indices, free_indices, lb, ub
            )
            ga_verbose = "\n".join(
                ga_logs + [f"Final weighted_rmse={ga_score:.6e}", bounds_report]
            )
            return ga_coeff, ga_error, ga_verbose

        coeff_opt, error_coeff, text_verbose, _ = self._run_multistart_fit(
            model_fn,
            Vv_flat,
            Id_flat,
            coeff,
            lb,
            ub,
            sigma,
            weights,
            id_matrix,
            count_transfer,
        )
        return coeff_opt, error_coeff, text_verbose