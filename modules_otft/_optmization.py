from ._imports import *
from ._read_data import ReadData

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
        self.ga_population = 60
        self.ga_generations = 150
        self.ga_mutation_rate = 0.1
        self.ga_crossover_rate = 0.8
        self.ga_elitism = 2
        self.ga_stall_generations = 30
        self.ga_seed = None
        self.sigma_mode = "relative"

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
        self.ga_population = max(4, self._safe_int(config.get("ga_population", self.ga_population), self.ga_population))
        self.ga_generations = max(1, self._safe_int(config.get("ga_generations", self.ga_generations), self.ga_generations))
        self.ga_mutation_rate = min(1.0, max(0.0, self._safe_float(config.get("ga_mutation_rate", self.ga_mutation_rate), self.ga_mutation_rate)))
        self.ga_crossover_rate = min(1.0, max(0.0, self._safe_float(config.get("ga_crossover_rate", self.ga_crossover_rate), self.ga_crossover_rate)))
        self.ga_elitism = max(1, self._safe_int(config.get("ga_elitism", self.ga_elitism), self.ga_elitism))
        self.ga_stall_generations = max(1, self._safe_int(config.get("ga_stall_generations", self.ga_stall_generations), self.ga_stall_generations))
        self.ga_seed = self._safe_int(config.get("ga_seed", self.ga_seed), self.ga_seed, allow_none=True)

        sigma_cfg = str(config.get("sigma", self.sigma_mode)).strip().lower()
        if sigma_cfg in {"absolute", "relative"}:
            self.sigma_mode = sigma_cfg
        elif config.get("sigma") is not None:
            print(f"Invalid sigma value '{config.get('sigma')}'. Using default '{self.sigma_mode}'.")

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

    def _build_hysteresis_weights(self, vv_flat):
        weights = np.ones_like(vv_flat, dtype=float)
        mode = self.hysteresis_weight_mode

        if mode == "global":
            weights *= self.hysteresis_weight_factor
            return weights

        if mode == "windows":
            for window in self.hysteresis_weight_windows:
                mask = (vv_flat >= window["min"]) & (vv_flat <= window["max"])
                weights[mask] *= window["weight"]
            return weights

        return weights

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
        Vv, Id, voltages, _, _, _ = super().load_data(self.type_read, self.path_voltages,
                                                      self.current_typic, self.scale_transfer,
                                                      self.scale_output, self.type_curve)

        # Flatten data arrays
        Vv_flat = np.ravel(Vv)
        Id_flat = np.ravel(Id)

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
        weights = self._build_hysteresis_weights(Vv_flat)
        if self.sigma_mode == "absolute":
            sigma = np.ones_like(Id_flat, dtype=float)
        else:
            sigma = np.maximum(np.abs(Id_flat), 1e-30)

        if use_ga:
            print()
            print('--' * 50)
            print('GENETIC ALGORITHM (GA) MODE')
            print('--' * 50)
            print()
            ga_coeff, ga_score, ga_logs = self._run_genetic_optimization(
                model_fn, Vv_flat, Id_flat, coeff, lb, ub, weights
            )
            ga_error = np.full(len(ga_coeff), np.nan)
            ga_verbose = "\n".join(ga_logs + [f"Final GA weighted_rmse={ga_score:.6e}"])
            return ga_coeff, ga_error, ga_verbose

        candidate_logs = []
        candidates = self._build_multistart_candidates(coeff, lb, ub)
        optuna_candidates, optuna_logs = self._build_optuna_candidates(
            model_fn, Vv_flat, Id_flat, lb, ub, weights
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
            if not self._is_feasible(p0, lb, ub):
                candidate_logs.append(f"Candidate {idx + 1}: infeasible p0 discarded.")
                continue

            try:
                preview = model_fn(Vv_flat, *p0)
                preview_score = self._weighted_rmse(preview - Id_flat, weights)
                if preview_score < best_fallback_score:
                    best_fallback_score = preview_score
                    best_fallback = p0.copy()
            except Exception as exc:
                candidate_logs.append(f"Candidate {idx + 1}: preview failed ({exc}).")
                continue

            try:
                coeff_opt, mat_covar, text_verbose = self._fit_once(
                    model_fn, Vv_flat, Id_flat, p0, lb, ub, self.method, sigma
                )
                fit_pred = model_fn(Vv_flat, *coeff_opt)
                score = self._weighted_rmse(fit_pred - Id_flat, weights)
                candidate_logs.append(
                    f"Candidate {idx + 1}: success, weighted_rmse={score:.6e}."
                )

                if score < best_score:
                    best_score = score
                    best_fit = {
                        "coeff_opt": np.array(coeff_opt, dtype=float),
                        "mat_covar": np.array(mat_covar, dtype=float),
                        "text_verbose": text_verbose,
                    }
            except (ValueError, RuntimeError) as exc:
                candidate_logs.append(f"Candidate {idx + 1}: fit failed ({exc}).")
            except Exception as exc:
                candidate_logs.append(f"Candidate {idx + 1}: unexpected fit error ({exc}).")

        if best_fit is not None:
            mat_covar = best_fit["mat_covar"]
            diag = np.diag(mat_covar) if mat_covar.ndim == 2 else np.array([])
            diag = np.where(diag >= 0, diag, np.nan)
            error_coeff = np.sqrt(diag) if diag.size else np.full(len(coeff), np.nan)
            text_verbose = best_fit["text_verbose"] + "\n" + "\n".join(candidate_logs)
            return best_fit["coeff_opt"], error_coeff, text_verbose

        if best_fallback is not None:
            fallback_error = np.full(len(best_fallback), np.nan)
            fallback_log = "\n".join(candidate_logs + ["All curve_fit attempts failed. Returning best feasible preview candidate."])
            return best_fallback, fallback_error, fallback_log

        fail_coeff = np.clip(coeff, lb, ub)
        fail_error = np.full(len(fail_coeff), np.nan)
        fail_log = "\n".join(candidate_logs + ["No valid candidate generated. Returning clipped initial coefficients."])
        return fail_coeff, fail_error, fail_log