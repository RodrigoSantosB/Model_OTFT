from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


class PreProcessingData:
    """
    Pre-processa curvas experimentais em CSV.

    Recursos principais:
    - leitura recursiva de arquivos CSV;
    - aplicacao de shift horizontal (shift right) na tensao apenas em
      curvas de transferencia;
    - selecao opcional de curvas especificas para receber o shift;
    - limpeza generica de curvas nFET para remover pontos invalidos e
      normalizar o eixo das saidas;
    - limpeza de histerese por consolidacao de tensoes redundantes;
    - analise de assinatura de histerese (tensoes repetidas com correntes distintas);
    - salvamento dos dados tratados em uma nova pasta.
    """

    def __init__(self, voltage_round_decimals: int = 9):
        self.voltage_round_decimals = voltage_round_decimals

    def analyze_hysteresis(
        self,
        df: pd.DataFrame,
        min_duplicate_groups: int = 1,
        min_relative_spread: float = 1e-6,
        min_absolute_spread: float = 1e-12,
    ) -> dict[str, Any]:
        """
        Mede redundancia por tensao (apos o mesmo arredondamento de _clean_hysteresis).

        hysteresis_detected e True se existir numero suficiente de grupos com tensao
        repetida e diferenca de corrente acima dos limiares (absoluto ou relativo).
        """
        empty = {
            "hysteresis_duplicate_groups": 0,
            "hysteresis_redundant_points": 0,
            "hysteresis_max_spread_abs": 0.0,
            "hysteresis_max_spread_rel": 0.0,
            "hysteresis_detected": False,
        }
        if df is None or df.empty:
            return empty

        work = df[["voltage", "current"]].copy()
        work["voltage_key"] = work["voltage"].round(self.voltage_round_decimals)
        sizes = work.groupby("voltage_key", sort=False).size()
        duplicate_mask = sizes > 1
        duplicate_groups = int(duplicate_mask.sum())
        redundant_points = int((sizes - 1).clip(lower=0).sum())

        max_spread_abs = 0.0
        max_spread_rel = 0.0
        for _, sub in work.groupby("voltage_key", sort=False):
            if len(sub) < 2:
                continue
            curr = sub["current"].to_numpy(dtype=float)
            spread = float(np.max(curr) - np.min(curr))
            max_spread_abs = max(max_spread_abs, spread)
            scale = max(float(np.mean(np.abs(curr))), 1e-30)
            max_spread_rel = max(max_spread_rel, spread / scale)

        significant_spread = (
            max_spread_rel >= float(min_relative_spread)
            or max_spread_abs >= float(min_absolute_spread)
        )
        detected = (
            duplicate_groups >= int(min_duplicate_groups) and significant_spread
        )

        return {
            "hysteresis_duplicate_groups": duplicate_groups,
            "hysteresis_redundant_points": redundant_points,
            "hysteresis_max_spread_abs": max_spread_abs,
            "hysteresis_max_spread_rel": max_spread_rel,
            "hysteresis_detected": bool(detected),
        }

    def _pipeline_before_hysteresis_clean(
        self,
        csv_path: str | Path,
        shift_voltage: float,
        threshold_voltage: float | None,
        transistor_type: str = "nFET",
    ) -> pd.DataFrame:
        csv_path = Path(csv_path)
        df = self._read_curve(csv_path)
        curve_attrs = dict(df.attrs)
        curve_type = df.attrs.get("curve_type", self._detect_curve_type(csv_path.name))
        if self._should_apply_physical_shift(curve_type):
            df = df.copy()
            df["voltage"] = df["voltage"] + shift_voltage
            df.attrs.update(curve_attrs)
        df = self._apply_generic_nfet_cleanup(df, transistor_type=transistor_type)
        return self._apply_voltage_threshold(
            df,
            threshold_voltage=threshold_voltage,
            transistor_type=transistor_type,
        )

    def _apply_generic_nfet_cleanup(
        self,
        df: pd.DataFrame,
        transistor_type: str = "nFET",
    ) -> pd.DataFrame:
        normalized_type = self._normalize_transistor_type(transistor_type)
        curve_type = str(df.attrs.get("curve_type", "")).strip().lower()
        strategy = "none"

        cleaned = df.copy()
        if normalized_type == "nFET" and curve_type == "transfer":
            cleaned["current"] = np.abs(cleaned["current"].to_numpy(dtype=float))
            cleaned = cleaned[np.abs(cleaned["current"]) > 0].copy()
            strategy = "nfet_transfer_abs_and_zero_filter"
        elif normalized_type == "nFET" and curve_type == "output":
            cleaned = cleaned[cleaned["current"] > 0].copy()
            if not cleaned.empty:
                first_valid_voltage = float(cleaned["voltage"].iloc[0])
                cleaned["voltage"] = cleaned["voltage"] - first_valid_voltage
            strategy = "nfet_output_positive_filter_and_rebase"

        if cleaned.empty:
            raise ValueError(
                "Nenhum ponto restante apos a limpeza generica "
                f"para {normalized_type} ({curve_type})."
            )

        result = cleaned.reset_index(drop=True)
        result.attrs.update(df.attrs)
        result.attrs["generic_cleanup_strategy"] = strategy
        return result

    def process_directory(
        self,
        input_path: str | Path,
        shift_voltage: float,
        threshold_voltage: float | None = 0.0,
        transistor_type: str = "nFET",
        hysteresis_mode: Any = "media",
        apply_hysteresis: bool = True,
        selected_curves: Iterable[str] | None = None,
        output_folder_name: str = "dados_tratados",
        recursive: bool = True,
        hysteresis_detect_min_groups: int = 1,
        hysteresis_detect_min_rel_spread: float = 1e-6,
        hysteresis_detect_min_abs_spread: float = 1e-12,
    ) -> list[dict]:
        """
        Processa todos os CSVs de um diretorio.

        Args:
            input_path: Pasta raiz com os arquivos CSV.
            shift_voltage: Valor em volts a ser somado no eixo de tensao.
            threshold_voltage: Aplica o corte no eixo de tensao apos o shift.
                Para nFET, mantem pontos com tensao maior ou igual ao limiar.
                Para pFET, mantem pontos com tensao menor ou igual ao limiar.
                Use None para nao aplicar corte.
            transistor_type: Tipo do transistor usado para decidir o lado do
                eixo preservado pelo corte ("nFET" ou "pFET").
            hysteresis_mode: Estrategia de consolidacao da histerese para
                tensoes repetidas. Aceita "media", "menor" ou "maior".
                Tambem aceita um dict com chaves por tipo de curva.
            apply_hysteresis: Se True, aplica a consolidacao da histerese.
            selected_curves: Lista opcional de curvas que receberao shift.
                Aceita nome do arquivo, stem ou caminho relativo.
                Se None, o shift e aplicado em todas as curvas.
            output_folder_name: Nome da pasta onde os dados tratados serao salvos.
            recursive: Se True, busca CSVs em subpastas.

        Returns:
            Lista com um resumo do processamento de cada arquivo.
        """
        input_dir = Path(input_path).expanduser().resolve()
        if not input_dir.exists():
            raise FileNotFoundError(f"Diretorio nao encontrado: {input_dir}")
        if not input_dir.is_dir():
            raise NotADirectoryError(f"O path informado nao e um diretorio: {input_dir}")

        output_dir = input_dir / output_folder_name
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_files = self._collect_csv_files(input_dir, recursive=recursive)
        if not csv_files:
            raise ValueError(f"Nenhum arquivo CSV encontrado em: {input_dir}")

        selected_set = self._normalize_selected_curves(selected_curves)
        summary = []

        for csv_path in csv_files:
            if output_folder_name in csv_path.parts:
                continue

            curve_type = self._detect_curve_type(csv_path)
            apply_shift = self._should_apply_shift(
                csv_path=csv_path,
                base_dir=input_dir,
                selected_curves=selected_set,
            )
            physical_shift_applied = apply_shift and self._should_apply_physical_shift(curve_type)

            resolved_hysteresis_mode = self._resolve_hysteresis_mode(curve_type, hysteresis_mode)

            processed_df, hyst_metrics = self._process_prepared_curve(
                csv_path=csv_path,
                shift_voltage=shift_voltage if apply_shift else 0.0,
                threshold_voltage=threshold_voltage,
                transistor_type=transistor_type,
                hysteresis_mode=resolved_hysteresis_mode,
                apply_hysteresis=apply_hysteresis,
                min_duplicate_groups=hysteresis_detect_min_groups,
                min_relative_spread=hysteresis_detect_min_rel_spread,
                min_absolute_spread=hysteresis_detect_min_abs_spread,
            )

            relative_parent = csv_path.relative_to(input_dir).parent
            target_dir = output_dir / relative_parent
            target_dir.mkdir(parents=True, exist_ok=True)

            target_name = f"{csv_path.stem}.csv"
            target_path = target_dir / target_name
            self._write_curve(processed_df, target_path)

            summary.append(
                {
                    "input_file": str(csv_path),
                    "output_file": str(target_path),
                    "curve_type": curve_type,
                    "shift_applied": physical_shift_applied,
                    "shift_voltage": shift_voltage if physical_shift_applied else 0.0,
                    "threshold_voltage": threshold_voltage,
                    "hysteresis_mode": (
                        resolved_hysteresis_mode
                        if apply_hysteresis
                        else self._describe_hysteresis_mode(hysteresis_mode)
                    ),
                    "hysteresis_applied": apply_hysteresis,
                    "generic_cleanup_strategy": processed_df.attrs.get("generic_cleanup_strategy", "none"),
                    "original_points": self._count_rows(csv_path),
                    "processed_points": len(processed_df),
                    **hyst_metrics,
                }
            )

        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(output_dir / "resumo_processamento.csv", index=False)
        return summary

    def _process_prepared_curve(
        self,
        csv_path: str | Path,
        shift_voltage: float,
        threshold_voltage: float | None,
        transistor_type: str,
        hysteresis_mode: Any,
        apply_hysteresis: bool,
        min_duplicate_groups: int = 1,
        min_relative_spread: float = 1e-6,
        min_absolute_spread: float = 1e-12,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        df_pre = self._pipeline_before_hysteresis_clean(
            csv_path,
            shift_voltage=shift_voltage,
            threshold_voltage=threshold_voltage,
            transistor_type=transistor_type,
        )
        metrics = self.analyze_hysteresis(
            df_pre,
            min_duplicate_groups=min_duplicate_groups,
            min_relative_spread=min_relative_spread,
            min_absolute_spread=min_absolute_spread,
        )
        if apply_hysteresis:
            df_out = self._clean_hysteresis(df_pre, mode=hysteresis_mode)
        else:
            df_out = df_pre
        return df_out, metrics

    def process_file(
        self,
        csv_path: str | Path,
        shift_voltage: float = 0.0,
        threshold_voltage: float | None = 0.0,
        transistor_type: str = "nFET",
        hysteresis_mode: Any = "media",
        apply_hysteresis: bool = True,
        hysteresis_detect_min_groups: int = 1,
        hysteresis_detect_min_rel_spread: float = 1e-6,
        hysteresis_detect_min_abs_spread: float = 1e-12,
    ) -> pd.DataFrame:
        """
        Le um CSV, aplica shift horizontal apenas em curvas de transferencia,
        corta por limiar de tensao e remove redundancias por histerese.
        """
        resolved_hysteresis_mode = self._resolve_hysteresis_mode(
            self._detect_curve_type(csv_path),
            hysteresis_mode,
        )

        df_out, _ = self._process_prepared_curve(
            csv_path=csv_path,
            shift_voltage=shift_voltage,
            threshold_voltage=threshold_voltage,
            transistor_type=transistor_type,
            hysteresis_mode=resolved_hysteresis_mode,
            apply_hysteresis=apply_hysteresis,
            min_duplicate_groups=hysteresis_detect_min_groups,
            min_relative_spread=hysteresis_detect_min_rel_spread,
            min_absolute_spread=hysteresis_detect_min_abs_spread,
        )
        return df_out

    def process_directory_in_place(
        self,
        input_path: str | Path,
        shift_voltage: float = 0.0,
        threshold_voltage: float | None = None,
        transistor_type: str = "nFET",
        hysteresis_mode: Any = "media",
        apply_hysteresis: bool = False,
        selected_curves: Iterable[str] | None = None,
        recursive: bool = True,
        backup_suffix: str = "_old",
        hysteresis_detect_min_groups: int = 1,
        hysteresis_detect_min_rel_spread: float = 1e-6,
        hysteresis_detect_min_abs_spread: float = 1e-12,
    ) -> list[dict]:
        """
        Processa os CSVs no proprio diretorio de origem.

        Os arquivos originais sao movidos para uma subpasta de backup nomeada
        como <nome_da_pasta_original>_old somente na primeira execucao.
        Se a pasta de backup ja existir, ela e preservada e nao e sobrescrita.
        Os dados processados sao gravados novamente no diretorio original com
        os mesmos nomes.
        """
        input_dir = Path(input_path).expanduser().resolve()
        if not input_dir.exists():
            raise FileNotFoundError(f"Diretorio nao encontrado: {input_dir}")
        if not input_dir.is_dir():
            raise NotADirectoryError(f"O path informado nao e um diretorio: {input_dir}")

        backup_dir = input_dir / f"{input_dir.name}{backup_suffix}"
        backup_exists = backup_dir.exists()

        csv_files = self._collect_csv_files(
            input_dir,
            recursive=recursive,
            excluded_directories={backup_dir.name},
        )
        if not csv_files:
            raise ValueError(f"Nenhum arquivo CSV encontrado em: {input_dir}")

        selected_set = self._normalize_selected_curves(selected_curves)
        summary = []

        for csv_path in csv_files:
            relative_path = csv_path.relative_to(input_dir)
            backup_path = backup_dir / relative_path

            if not backup_exists:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(csv_path), str(backup_path))
                source_path = backup_path
                backup_file = str(backup_path)
                original_points = self._count_rows(backup_path)
            else:
                source_path = csv_path
                backup_file = str(backup_path) if backup_path.exists() else None
                original_points = self._count_rows(csv_path)

            curve_type = self._detect_curve_type(source_path)
            apply_shift = self._should_apply_shift(
                csv_path=source_path,
                base_dir=backup_dir if not backup_exists else input_dir,
                selected_curves=selected_set,
            )
            physical_shift_applied = apply_shift and self._should_apply_physical_shift(curve_type)

            resolved_hysteresis_mode = self._resolve_hysteresis_mode(curve_type, hysteresis_mode)

            processed_df, hyst_metrics = self._process_prepared_curve(
                csv_path=source_path,
                shift_voltage=shift_voltage if apply_shift else 0.0,
                threshold_voltage=threshold_voltage,
                transistor_type=transistor_type,
                hysteresis_mode=resolved_hysteresis_mode,
                apply_hysteresis=apply_hysteresis,
                min_duplicate_groups=hysteresis_detect_min_groups,
                min_relative_spread=hysteresis_detect_min_rel_spread,
                min_absolute_spread=hysteresis_detect_min_abs_spread,
            )

            csv_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_curve(processed_df, csv_path)

            summary.append(
                {
                    "input_file": str(source_path),
                    "output_file": str(csv_path),
                    "backup_file": backup_file,
                    "backup_created": not backup_exists,
                    "backup_reused": backup_exists,
                    "curve_type": curve_type,
                    "shift_applied": physical_shift_applied,
                    "shift_voltage": shift_voltage if physical_shift_applied else 0.0,
                    "threshold_voltage": threshold_voltage,
                    "hysteresis_mode": (
                        resolved_hysteresis_mode
                        if apply_hysteresis
                        else self._describe_hysteresis_mode(hysteresis_mode)
                    ),
                    "hysteresis_applied": apply_hysteresis,
                    "generic_cleanup_strategy": processed_df.attrs.get("generic_cleanup_strategy", "none"),
                    "original_points": original_points,
                    "processed_points": len(processed_df),
                    **hyst_metrics,
                }
            )

        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(input_dir / "resumo_processamento.csv", index=False)
        return summary

    def _collect_csv_files(
        self,
        input_dir: Path,
        recursive: bool = True,
        excluded_directories: set[str] | None = None,
    ) -> list[Path]:
        pattern = "**/*.csv" if recursive else "*.csv"
        excluded_directories = excluded_directories or set()
        return sorted(
            path for path in input_dir.glob(pattern)
            if path.is_file()
            and path.name != "resumo_processamento.csv"
            and not any(part in excluded_directories for part in path.parts)
        )

    def _normalize_curve_header(self, value: str) -> str:
        return str(value).strip().upper().replace(" ", "")

    def _is_effectively_constant(
        self,
        values: np.ndarray,
        atol: float = 1e-9,
        rtol: float = 1e-6,
    ) -> bool:
        numeric_values = np.asarray(values, dtype=float)
        if numeric_values.size == 0:
            return False
        span = float(np.nanmax(numeric_values) - np.nanmin(numeric_values))
        reference = max(float(np.nanmax(np.abs(numeric_values))), 1.0)
        return span <= max(float(atol), float(rtol) * reference)

    def _read_with_supported_delimiters(
        self,
        csv_path: str | Path,
        header: int | None | str = "infer",
        min_columns: int = 2,
    ) -> pd.DataFrame:
        for delimiter in ("\t", ",", ";"):
            try:
                frame = pd.read_csv(csv_path, sep=delimiter, engine="python", header=header)
                if frame.shape[1] >= min_columns:
                    return frame
            except pd.errors.ParserError:
                continue

        frame = pd.read_csv(csv_path, sep=None, engine="python", header=header)
        if frame.shape[1] < min_columns:
            raise ValueError(f"O arquivo precisa ter ao menos {min_columns} colunas: {csv_path}")
        return frame

    def _read_curve(self, csv_path: str | Path) -> pd.DataFrame:
        csv_path = Path(csv_path)
        raw_data = self._read_with_supported_delimiters(csv_path)
        normalized_columns = {
            self._normalize_curve_header(column): column
            for column in raw_data.columns
        }

        if all(column in normalized_columns for column in ["VGS", "VDS", "ID"]):
            df = raw_data[[normalized_columns["VGS"], normalized_columns["VDS"], normalized_columns["ID"]]].copy()
            df.columns = ["VGS", "VDS", "ID"]
            for column in ["VGS", "VDS", "ID"]:
                df[column] = pd.to_numeric(df[column], errors="coerce")
            df = df.dropna(subset=["VGS", "VDS", "ID"]).reset_index(drop=True)

            if df.empty:
                raise ValueError(f"O arquivo nao contem dados numericos validos: {csv_path}")

            vgs_constant = self._is_effectively_constant(df["VGS"].to_numpy(dtype=float))
            vds_constant = self._is_effectively_constant(df["VDS"].to_numpy(dtype=float))
            if vgs_constant and not vds_constant:
                curve_type = "output"
                sweep_column = "VDS"
                fixed_column = "VGS"
            elif vds_constant and not vgs_constant:
                curve_type = "transfer"
                sweep_column = "VGS"
                fixed_column = "VDS"
            else:
                raise ValueError(
                    "Nao foi possivel identificar a coluna fixa entre VGS e VDS "
                    f"em {csv_path}."
                )

            curve_df = pd.DataFrame(
                {
                    "voltage": df[sweep_column].to_numpy(dtype=float),
                    "current": df["ID"].to_numpy(dtype=float),
                }
            )
            curve_df.attrs.update(
                {
                    "curve_type": curve_type,
                    "format": "structured",
                    "sweep_column": sweep_column,
                    "fixed_column": fixed_column,
                    "fixed_voltage": float(df[fixed_column].mean()),
                }
            )
            return curve_df

        data = self._read_with_supported_delimiters(csv_path, header=None)

        if data.shape[1] < 2:
            raise ValueError(f"O arquivo precisa ter ao menos 2 colunas: {csv_path}")

        df = data.iloc[:, :2].copy()
        df.columns = ["voltage", "current"]
        df["voltage"] = pd.to_numeric(df["voltage"], errors="coerce")
        df["current"] = pd.to_numeric(df["current"], errors="coerce")
        df = df.dropna(subset=["voltage", "current"]).reset_index(drop=True)

        if df.empty:
            raise ValueError(f"O arquivo nao contem dados numericos validos: {csv_path}")

        df.attrs.update(
            {
                "curve_type": self._detect_curve_type_from_name(csv_path.name),
                "format": "legacy",
                "sweep_column": "voltage",
                "fixed_column": None,
                "fixed_voltage": None,
            }
        )
        return df

    def _write_curve(self, df: pd.DataFrame, target_path: str | Path) -> None:
        target_path = Path(target_path)
        if df.attrs.get("format") == "structured":
            sweep_column = df.attrs["sweep_column"]
            fixed_column = df.attrs["fixed_column"]
            fixed_voltage = float(df.attrs["fixed_voltage"])
            output_df = pd.DataFrame(
                {
                    "VGS": np.full(len(df), fixed_voltage, dtype=float),
                    "VDS": np.full(len(df), fixed_voltage, dtype=float),
                    "ID": df["current"].to_numpy(dtype=float),
                }
            )
            output_df[sweep_column] = df["voltage"].to_numpy(dtype=float)
            output_df[fixed_column] = fixed_voltage
            output_df.to_csv(target_path, index=False, float_format="%.10E")
            return

        df.to_csv(target_path, header=False, index=False, float_format="%.10E")

    def _clean_hysteresis(self, df: pd.DataFrame, mode: str = "media") -> pd.DataFrame:
        """
        Remove pontos redundantes gerados por varreduras de ida e volta.

        Estrategia:
        - arredonda a tensao para consolidar valores equivalentes;
        - agrupa tensoes repetidas;
        - seleciona uma corrente representativa por tensao repetida;
        - retorna a curva ordenada pelo eixo de tensao.
        """
        aggregation_mode = self._normalize_hysteresis_mode(mode)
        work_df = df.copy()
        work_df["voltage_key"] = work_df["voltage"].round(self.voltage_round_decimals)

        current_agg = {
            "media": "mean",
            "menor": "min",
            "maior": "max",
        }[aggregation_mode]

        cleaned = (
            work_df.groupby("voltage_key", as_index=False)
            .agg(
                voltage=("voltage", "mean"),
                current=("current", current_agg),
            )
            .sort_values("voltage", kind="mergesort")
            .reset_index(drop=True)
        )

        cleaned_df = cleaned[["voltage", "current"]]
        cleaned_df.attrs.update(df.attrs)
        return cleaned_df

    def _describe_hysteresis_mode(self, mode: Any) -> str:
        """Converts the hysteresis configuration to a readable summary."""
        if isinstance(mode, dict):
            normalized = {}
            for key, value in mode.items():
                try:
                    normalized[str(key)] = self._normalize_hysteresis_mode(str(value))
                except ValueError:
                    normalized[str(key)] = str(value).strip().lower()
            return str(normalized)
        return str(mode).strip().lower()

    def _resolve_hysteresis_mode(self, curve_type: str, mode: Any) -> str:
        """Resolves a per-curve hysteresis mode with global fallback."""
        if isinstance(mode, dict):
            normalized_curve_type = str(curve_type).strip().lower()
            fallback_mode = (
                mode.get(normalized_curve_type)
                or mode.get(curve_type)
                or mode.get("default")
                or mode.get("all")
                or mode.get("global")
                or mode.get("both")
                or "media"
            )
            return self._normalize_hysteresis_mode(str(fallback_mode))
        return self._normalize_hysteresis_mode(str(mode))

    def _normalize_hysteresis_mode(self, mode: str) -> str:
        normalized = mode.strip().lower()
        aliases = {
            "media": "media",
            "mean": "media",
            "avg": "media",
            "average": "media",
            "menor": "menor",
            "min": "menor",
            "minimum": "menor",
            "baixo": "menor",
            "bottom": "menor",
            "lower": "menor",
            "maior": "maior",
            "max": "maior",
            "maximum": "maior",
            "cima": "maior",
            "top": "maior",
            "upper": "maior",
        }

        if normalized not in aliases:
            raise ValueError(
                "Modo de eliminacao de histerese invalido. "
                "Use 'media', 'menor' (ou 'baixo'), 'maior' (ou 'cima'), ou equivalentes em ingles."
            )

        return aliases[normalized]

    def _apply_voltage_threshold(
        self,
        df: pd.DataFrame,
        threshold_voltage: float | None = 0.0,
        transistor_type: str = "nFET",
    ) -> pd.DataFrame:
        """
        Mantem apenas os pontos a partir do limiar informado.
        """
        if threshold_voltage is None:
            result = df.reset_index(drop=True)
            result.attrs.update(df.attrs)
            return result

        normalized_type = self._normalize_transistor_type(transistor_type)
        if normalized_type == "pFET":
            filtered = df[df["voltage"] <= threshold_voltage].copy()
        else:
            filtered = df[df["voltage"] >= threshold_voltage].copy()
        if filtered.empty:
            raise ValueError(
                "Nenhum ponto restante apos aplicar o limiar de tensao "
                f"{threshold_voltage} V para {normalized_type}."
            )
        result = filtered.reset_index(drop=True)
        result.attrs.update(df.attrs)
        return result

    def _normalize_transistor_type(self, transistor_type: Any) -> str:
        normalized = str(transistor_type).strip().lower()
        if normalized == "pfet":
            return "pFET"
        return "nFET"

    def _count_rows(self, csv_path: Path) -> int:
        return len(self._read_curve(csv_path))

    def _detect_curve_type_from_name(self, filename: str) -> str:
        lowered = str(filename).lower()
        if "transfer" in lowered or "transf" in lowered:
            return "transfer"
        return "output" if "output" in lowered or "saida" in lowered else "unknown"

    def _detect_curve_type(self, filename: str | Path) -> str:
        candidate_path = Path(filename)
        if candidate_path.exists() and candidate_path.is_file():
            try:
                return self._read_curve(candidate_path).attrs.get("curve_type", "unknown")
            except ValueError:
                pass
        return self._detect_curve_type_from_name(candidate_path.name)

    def _should_apply_physical_shift(self, curve_type: str) -> bool:
        # Curvas de saida nao devem ser deslocadas fisicamente no eixo x.
        # Tipos desconhecidos preservam o comportamento legado.
        return curve_type != "output"

    def _normalize_selected_curves(self, selected_curves: Iterable[str] | None) -> set[str] | None:
        if selected_curves is None:
            return None

        normalized = set()
        for item in selected_curves:
            value = item.strip().replace("\\", "/")
            if value:
                normalized.add(value.lower())
        return normalized or None

    def _should_apply_shift(
        self,
        csv_path: Path,
        base_dir: Path,
        selected_curves: set[str] | None,
    ) -> bool:
        if selected_curves is None:
            return True

        relative_path = csv_path.relative_to(base_dir).as_posix().lower()
        filename = csv_path.name.lower()
        stem = csv_path.stem.lower()

        return any(
            selected in {relative_path, filename, stem}
            for selected in selected_curves
        )


def process_experimental_data(
    input_path: str | Path,
    shift_voltage: float,
    threshold_voltage: float | None = 0.0,
    hysteresis_mode: Any = "media",
    apply_hysteresis: bool = True,
    selected_curves: Iterable[str] | None = None,
    output_folder_name: str = "dados_tratados",
    recursive: bool = True,
    voltage_round_decimals: int = 9,
    hysteresis_detect_min_groups: int = 1,
    hysteresis_detect_min_rel_spread: float = 1e-6,
    hysteresis_detect_min_abs_spread: float = 1e-12,
) -> list[dict]:
    """
    Funcao de conveniencia para processar um diretorio sem instanciar a classe.
    """
    processor = PreProcessingData(voltage_round_decimals=voltage_round_decimals)
    return processor.process_directory(
        input_path=input_path,
        shift_voltage=shift_voltage,
        threshold_voltage=threshold_voltage,
        hysteresis_mode=hysteresis_mode,
        apply_hysteresis=apply_hysteresis,
        selected_curves=selected_curves,
        output_folder_name=output_folder_name,
        recursive=recursive,
        hysteresis_detect_min_groups=hysteresis_detect_min_groups,
        hysteresis_detect_min_rel_spread=hysteresis_detect_min_rel_spread,
        hysteresis_detect_min_abs_spread=hysteresis_detect_min_abs_spread,
    )


def extract_voltage_from_filename(filename: str) -> float | None:
    """
    Extrai tensao de nomes como:
    - transfer-1V.csv
    - output-0.1.csv
    - org1_2VGS.csv
    - org1_-40_VDS.csv
    """
    match = re.search(
        r"(-?\d+(?:\.\d+)?)\s*(?=(?:_?V(?:GS|DS)|V)?(?:\.csv|\.txt)$)",
        filename,
        flags=re.IGNORECASE,
    )
    return float(match.group(1)) if match else None
