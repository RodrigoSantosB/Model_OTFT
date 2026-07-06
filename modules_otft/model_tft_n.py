import numpy as np

from ._model import TFTModel


class TFTModelN(TFTModel):
    """nFET backend aligned with the 11-parameter MATLAB reference in `Au2_new`."""

    PARAM_KEYS = [
        "VTHO",
        "DELTA",
        "N",
        "L",
        "LAMBDA",
        "VGCRIT",
        "JTH",
        "RS",
        "VTUN",
        "V0",
        "RMAX",
    ]

    def _normalize_params(
        self,
        Vtho,
        Delta,
        N,
        L,
        Lambda,
        Vcrit,
        Jth,
        Rs,
        Vtun,
        V0,
        Rmax,
        extra_kwargs,
    ):
        aliases = {
            "delta": "Delta",
            "n": "N",
            "l": "L",
            "lam": "Lambda",
            "vgcrit": "Vcrit",
            "rso": "Rs",
            "vtun": "Vtun",
            "v0": "V0",
            "rmax": "Rmax",
        }
        resolved = {
            "Vtho": Vtho,
            "Delta": Delta,
            "N": N,
            "L": L,
            "Lambda": Lambda,
            "Vcrit": Vcrit,
            "Jth": Jth,
            "Rs": Rs,
            "Vtun": Vtun,
            "V0": V0,
            "Rmax": Rmax,
        }
        for raw_key, value in list(extra_kwargs.items()):
            key = aliases.get(str(raw_key).strip().lower())
            if key is None:
                raise TypeError(f"Unexpected keyword argument '{raw_key}' for TFTModelN.calc_model().")
            resolved[key] = value
        return resolved

    def _fsat_calculation_matlab_n(self, Vds, nphit, qtot, Vcrit, Lambda, near_zero_threshold=0.0):
        """Mirror the MATLAB n-type `Fsat` block, including the first-point `ll` override."""
        Vds = np.asarray(Vds, dtype=float)
        nphit = np.asarray(nphit, dtype=float)
        qtot = np.asarray(qtot, dtype=float)

        Vgt = nphit * qtot
        safe_vcrit = max(float(Vcrit), 1e-30)
        sqrt_term = np.sqrt(np.maximum(2.0 * Vgt / safe_vcrit, 0.0))
        Vgn = (2.0 * Vgt) / np.maximum(1.0 + sqrt_term, 1e-30)
        x = Vds / np.maximum(Vgn, 1e-30)
        eta = 1.0 - np.tanh(x)
        y = Vgn / self._TFTModel__PHIT

        with np.errstate(divide="ignore", invalid="ignore", over="ignore", under="ignore"):
            ll = (
                2.0
                * Lambda
                / (np.square(y) * (1.0 - np.square(eta)))
                * (np.exp(y * (eta - 1.0)) * (1.0 - (y * eta)) - (1.0 - y))
            )

        ll = np.asarray(ll, dtype=float)
        if ll.size:
            threshold = float(near_zero_threshold)
            first_vds = float(np.ravel(Vds)[0])
            if threshold == 0.0:
                should_replace = first_vds == 0.0
            else:
                should_replace = first_vds < threshold
            if should_replace:
                ll = np.array(ll, copy=True)
                ll.flat[0] = float(Lambda)
        ll = np.nan_to_num(ll, nan=float(Lambda), posinf=float(Lambda), neginf=float(Lambda))

        tau = 1.0 / (1.0 + ll)
        at = tau / np.maximum(2.0 - tau, 1e-30)
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            Fsat = at * (1.0 - np.exp(-Vds / self._TFTModel__PHIT)) / (
                1.0 + at * np.exp(-Vds / self._TFTModel__PHIT)
            )
        Fsat = np.clip(np.nan_to_num(Fsat, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
        return Fsat, eta

    def _matlab_rel_change(self, current, previous):
        """Approximate the MATLAB convergence metric with only minimal zero protection."""
        current = np.asarray(current, dtype=float)
        previous = np.asarray(previous, dtype=float)
        if np.all(np.abs(current) < 1e-30) and np.all(np.abs(previous) < 1e-30):
            return 0.0
        with np.errstate(divide="ignore", invalid="ignore"):
            rel = np.abs((current - previous) / current)
        rel = np.nan_to_num(rel, nan=np.inf, posinf=np.inf, neginf=np.inf)
        return float(np.max(rel)) if rel.size else 0.0

    def calc_model(
        self,
        V,
        Vtho=1,
        Delta=1,
        N=1,
        L=1,
        Lambda=1,
        Vcrit=1,
        Jth=1,
        Rs=1,
        Vtun=1,
        V0=5,
        Rmax=1e4,
        debug_terms=False,
        **kwargs,
    ):
        params = self._normalize_params(
            Vtho, Delta, N, L, Lambda, Vcrit, Jth, Rs, Vtun, V0, Rmax, kwargs
        )

        Vtho = float(params["Vtho"])
        Delta = float(params["Delta"])
        N = float(params["N"])
        L = float(params["L"])
        Lambda = float(params["Lambda"])
        Vcrit = float(params["Vcrit"])
        Jth = float(params["Jth"])
        Rso = float(params["Rs"])
        Vtun = max(abs(float(params["Vtun"])), 1e-30)
        V0 = float(params["V0"])
        Rmax = float(params["Rmax"])

        res = self.sr_resistance
        curr = self.curr_carry
        if res is not None:
            Rso = Rso * res
            Rmax = Rmax * res
        if curr is not None:
            Jth = Jth * curr

        current_sign = 1 if self._TFTModel__TYPE_OF_TRANSISTOR == 1 else -1
        chain_matrix_id = self._creat_matrix(V, n_rows=self.n_points)

        debug_idleak = None
        debug_conduction = None
        debug_total = None
        debug_vd = None
        debug_vg = None
        debug_vds = None
        debug_vgs_ref = None
        debug_vgd_ref = None
        debug_vgs_eff = None
        debug_vdsi = None
        debug_vgsi = None
        debug_vtp_initial = None
        debug_vtp_final = None
        debug_theta_initial = None
        debug_theta_final = None
        debug_qtot_initial = None
        debug_qtot_final = None
        debug_fsat_initial = None
        debug_fsat_final = None
        if debug_terms:
            debug_idleak = np.zeros_like(chain_matrix_id, dtype=float)
            debug_conduction = np.zeros_like(chain_matrix_id, dtype=float)
            debug_total = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vd = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vg = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vds = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vgs_ref = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vgd_ref = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vgs_eff = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vdsi = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vgsi = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vtp_initial = np.zeros_like(chain_matrix_id, dtype=float)
            debug_vtp_final = np.zeros_like(chain_matrix_id, dtype=float)
            debug_theta_initial = np.zeros_like(chain_matrix_id, dtype=float)
            debug_theta_final = np.zeros_like(chain_matrix_id, dtype=float)
            debug_qtot_initial = np.zeros_like(chain_matrix_id, dtype=float)
            debug_qtot_final = np.zeros_like(chain_matrix_id, dtype=float)
            debug_fsat_initial = np.zeros_like(chain_matrix_id, dtype=float)
            debug_fsat_final = np.zeros_like(chain_matrix_id, dtype=float)

        vdv = np.array(self._convert(self.tension_list))

        for i in range(len(vdv)):
            Vd, Vg = self._calc_vd_vg(V, vdv, i, self.type_data)
            Vb = 0
            Vs = 0

            direction = self._calc_dir(Vd, Vs)
            Vds = np.abs(Vd - Vs)
            Vgs_ref = self._TFTModel__TYPE_OF_TRANSISTOR * (Vg - Vs)
            Vgd_ref = self._TFTModel__TYPE_OF_TRANSISTOR * (Vg - Vd)
            Vgs = self._calc_vgs_or_vbs(Vd, Vg, Vs)
            Vbs = self._calc_vgs_or_vbs(Vd, Vg, Vs)

            Vtp = self._drain_impact(Vds, Vtho, Delta)
            nphit, theta, qtot = self._total_charge(Vgs, Vtp, N)
            Fsat, eta = self._fsat_calculation_matlab_n(Vds, nphit, qtot, Vcrit, Lambda)
            Vtp_initial = np.array(Vtp, copy=True)
            theta_initial = np.array(theta, copy=True)
            qtot_initial = np.array(qtot, copy=True)
            Fsat_initial = np.array(Fsat, copy=True)
            Jfree = self._current_calculation(qtot, Jth, L)

            Idleak = 0
            if self.mult_idleak == 0:
                Idleak = self._TFTModel__ID_LEAK
            elif self.mult_idleak == 1:
                if i < self.curv_transfer:
                    Idleak = self._TFTModel__ID_LEAK[i]
                elif i >= self.curv_transfer:
                    Idleak = 0
            else:
                raise ValueError("Idleak value invalid\n")

            Idx = self._final_current(Idleak, Jfree, Fsat)

            tolerance = 1e-10
            Idxx = np.array(Idleak, copy=True, dtype=float)
            Rs_eff = Rso + 0.5 * (Rmax - Rso) * (1 - np.tanh((Vds - V0) / Vtun))
            Rd = Rso
            dvg = Idx * Rs_eff
            dvd = Idx * Rd
            Vdsi = np.array(Vds, copy=True)
            Vgsi = np.array(Vgs, copy=True)
            count = 1

            while self._matlab_rel_change(Idx, Idxx) > tolerance:
                count += 1
                if count > 500:
                    break

                Idxx = Idx
                dvg = 0.2 * Idx * Rs_eff + 0.8 * dvg
                dvd = 0.2 * Idx * Rd + 0.8 * dvd
                dvds = dvg + dvd

                Vdsi = np.maximum(Vds - dvds, 0)
                Vgsi = np.maximum(Vgs - dvg, 0)
                Vbsi = np.maximum(Vbs - dvg, 0)

                Vtp = self._drain_impact(Vdsi, Vtho, Delta)
                nphit, theta, qtot = self._total_charge(Vgsi, Vtp, N)
                Fsat, eta = self._fsat_calculation_matlab_n(
                    Vdsi, nphit, qtot, Vcrit, Lambda, near_zero_threshold=1e-8
                )
                Jfree = self._current_calculation(qtot, Jth, L)
                Idx = self._final_current(Idleak, Jfree, Fsat)

            Idx = np.nan_to_num(Idx, nan=0.0, posinf=1e30, neginf=-1e30)
            if debug_terms:
                idleak_term = np.nan_to_num(
                    np.asarray(Idleak, dtype=float), nan=0.0, posinf=1e30, neginf=-1e30
                )
                if np.ndim(idleak_term) == 0:
                    idleak_term = np.full_like(Idx, float(idleak_term), dtype=float)
                conduction_term = np.nan_to_num(
                    self._TFTModel__WIDTH_TRANSISTOR
                    * np.asarray(Jfree, dtype=float)
                    * np.asarray(Fsat, dtype=float),
                    nan=0.0,
                    posinf=1e30,
                    neginf=-1e30,
                )
                total_term = np.nan_to_num(
                    idleak_term + conduction_term, nan=0.0, posinf=1e30, neginf=-1e30
                )

            Id = self._TFTModel__TYPE_OF_TRANSISTOR * direction * Idx
            Id = np.array(Id).transpose()
            Id = np.nan_to_num(Id, nan=0.0, posinf=1e30, neginf=-1e30)

            n_rows_max = 99
            Vv = self._checks_v(V, n_rows_max, self.tension_list)
            trsf_curve = ((i < self.curv_transfer) and (Vv.ndim > 1))
            out_curve = (i >= self.curv_transfer) and (Vv.ndim > 1)
            trsf_curve_vet = (self.type_data == 0 and Vv.ndim == 1)
            out_curve_vet = (self.type_data == 1 and Vv.ndim == 1)

            curr_typic = self._TFTModel__convert_to_ampere_unit(self.current_typic)
            curr_typic = max(curr_typic, 1e-30)

            if debug_terms:
                def _assign_debug(target, values, use_abs=False):
                    arr = np.nan_to_num(
                        np.asarray(values, dtype=float), nan=0.0, posinf=1e30, neginf=-1e30
                    )
                    if np.ndim(arr) == 0:
                        arr = np.full_like(Idx, float(arr), dtype=float)
                    if use_abs and self.type_curve == "log" and (trsf_curve or trsf_curve_vet):
                        arr = np.abs(arr)
                    if trsf_curve or out_curve:
                        target[:, i] = arr
                        return target
                    return arr

            if self.type_curve == "log":
                if trsf_curve:
                    safe_vals = np.maximum(np.abs(Idx), 1e-30)
                    chain_matrix_id[:, i] = np.log10(safe_vals)
                elif out_curve:
                    chain_matrix_id[:, i] = current_sign * Idx / curr_typic
                elif trsf_curve_vet:
                    safe_vals = np.maximum(np.abs(Idx), 1e-30)
                    chain_matrix_id = np.log10(safe_vals)
                elif out_curve_vet:
                    chain_matrix_id = current_sign * Idx / curr_typic
            else:
                if self.type_curve == "linear":
                    if trsf_curve:
                        chain_matrix_id[:, i] = current_sign * Idx / curr_typic
                    elif out_curve:
                        chain_matrix_id[:, i] = current_sign * Idx / curr_typic
                    elif trsf_curve_vet:
                        chain_matrix_id = current_sign * Idx / curr_typic
                    elif out_curve_vet:
                        chain_matrix_id = current_sign * Idx / curr_typic

            if debug_terms:
                debug_idleak = _assign_debug(
                    debug_idleak,
                    idleak_term,
                    use_abs=self.type_curve == "log" and (trsf_curve or trsf_curve_vet),
                )
                debug_conduction = _assign_debug(
                    debug_conduction,
                    conduction_term,
                    use_abs=self.type_curve == "log" and (trsf_curve or trsf_curve_vet),
                )
                debug_total = _assign_debug(
                    debug_total,
                    total_term,
                    use_abs=self.type_curve == "log" and (trsf_curve or trsf_curve_vet),
                )
                debug_vd = _assign_debug(debug_vd, Vd)
                debug_vg = _assign_debug(debug_vg, Vg)
                debug_vds = _assign_debug(debug_vds, Vds)
                debug_vgs_ref = _assign_debug(debug_vgs_ref, Vgs_ref)
                debug_vgd_ref = _assign_debug(debug_vgd_ref, Vgd_ref)
                debug_vgs_eff = _assign_debug(debug_vgs_eff, Vgs)
                debug_vdsi = _assign_debug(debug_vdsi, Vdsi)
                debug_vgsi = _assign_debug(debug_vgsi, Vgsi)
                debug_vtp_initial = _assign_debug(debug_vtp_initial, Vtp_initial)
                debug_vtp_final = _assign_debug(debug_vtp_final, Vtp)
                debug_theta_initial = _assign_debug(debug_theta_initial, theta_initial)
                debug_theta_final = _assign_debug(debug_theta_final, theta)
                debug_qtot_initial = _assign_debug(debug_qtot_initial, qtot_initial)
                debug_qtot_final = _assign_debug(debug_qtot_final, qtot)
                debug_fsat_initial = _assign_debug(debug_fsat_initial, Fsat_initial)
                debug_fsat_final = _assign_debug(debug_fsat_final, Fsat)

        if debug_terms:
            self.last_terms = {
                "idleak_A": debug_idleak,
                "conduction_A": debug_conduction,
                "total_A": debug_total,
                "vd_V": debug_vd,
                "vg_V": debug_vg,
                "vds_V": debug_vds,
                "vgs_ref_V": debug_vgs_ref,
                "vgd_ref_V": debug_vgd_ref,
                "vgs_effective_V": debug_vgs_eff,
                "vdsi_V": debug_vdsi,
                "vgsi_V": debug_vgsi,
                "vtp_initial_V": debug_vtp_initial,
                "vtp_final_V": debug_vtp_final,
                "theta_initial": debug_theta_initial,
                "theta_final": debug_theta_final,
                "qtot_initial": debug_qtot_initial,
                "qtot_final": debug_qtot_final,
                "fsat_initial": debug_fsat_initial,
                "fsat_final": debug_fsat_final,
                "type_curve": self.type_curve,
                "type_data": self.type_data,
            }

        return np.ravel(chain_matrix_id)
