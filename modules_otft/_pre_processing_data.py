from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Iterable

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
    - limpeza de histerese por consolidacao de tensoes redundantes;
    - salvamento dos dados tratados em uma nova pasta.
    """

    def __init__(self, voltage_round_decimals: int = 9):
        self.voltage_round_decimals = voltage_round_decimals

    def process_directory(
        self,
        input_path: str | Path,
        shift_voltage: float,
        threshold_voltage: float | None = 0.0,
        hysteresis_mode: str = "media",
        apply_hysteresis: bool = True,
        selected_curves: Iterable[str] | None = None,
        output_folder_name: str = "dados_tratados",
        recursive: bool = True,
    ) -> list[dict]:
        """
        Processa todos os CSVs de um diretorio.

        Args:
            input_path: Pasta raiz com os arquivos CSV.
            shift_voltage: Valor em volts a ser somado no eixo de tensao.
            threshold_voltage: Mantem apenas os pontos com tensao maior ou igual
                a este valor apos o shift. Use None para nao aplicar corte.
            hysteresis_mode: Estrategia de consolidacao da histerese para
                tensoes repetidas. Aceita "media", "menor" ou "maior".
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

            curve_type = self._detect_curve_type(csv_path.name)
            apply_shift = self._should_apply_shift(
                csv_path=csv_path,
                base_dir=input_dir,
                selected_curves=selected_set,
            )
            physical_shift_applied = apply_shift and self._should_apply_physical_shift(curve_type)

            processed_df = self.process_file(
                csv_path=csv_path,
                shift_voltage=shift_voltage if apply_shift else 0.0,
                threshold_voltage=threshold_voltage,
                hysteresis_mode=hysteresis_mode,
                apply_hysteresis=apply_hysteresis,
            )

            relative_parent = csv_path.relative_to(input_dir).parent
            target_dir = output_dir / relative_parent
            target_dir.mkdir(parents=True, exist_ok=True)

            target_name = f"{csv_path.stem}.csv"
            target_path = target_dir / target_name
            processed_df.to_csv(target_path, header=False, index=False, float_format="%.10E")

            summary.append(
                {
                    "input_file": str(csv_path),
                    "output_file": str(target_path),
                    "curve_type": curve_type,
                    "shift_applied": physical_shift_applied,
                    "shift_voltage": shift_voltage if physical_shift_applied else 0.0,
                    "threshold_voltage": threshold_voltage,
                    "hysteresis_mode": hysteresis_mode,
                    "hysteresis_applied": apply_hysteresis,
                    "original_points": self._count_rows(csv_path),
                    "processed_points": len(processed_df),
                }
            )

        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(output_dir / "resumo_processamento.csv", index=False)
        return summary

    def process_file(
        self,
        csv_path: str | Path,
        shift_voltage: float = 0.0,
        threshold_voltage: float | None = 0.0,
        hysteresis_mode: str = "media",
        apply_hysteresis: bool = True,
    ) -> pd.DataFrame:
        """
        Le um CSV, aplica shift horizontal apenas em curvas de transferencia,
        corta por limiar de tensao e remove redundancias por histerese.
        """
        csv_path = Path(csv_path)
        df = self._read_curve(csv_path)
        curve_type = self._detect_curve_type(csv_path.name)
        if self._should_apply_physical_shift(curve_type):
            df["voltage"] = df["voltage"] + shift_voltage
        df = self._apply_voltage_threshold(df, threshold_voltage=threshold_voltage)
        if apply_hysteresis:
            df = self._clean_hysteresis(df, mode=hysteresis_mode)
        return df

    def process_directory_in_place(
        self,
        input_path: str | Path,
        shift_voltage: float = 0.0,
        threshold_voltage: float | None = None,
        hysteresis_mode: str = "media",
        apply_hysteresis: bool = False,
        selected_curves: Iterable[str] | None = None,
        recursive: bool = True,
        backup_suffix: str = "_old",
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

            curve_type = self._detect_curve_type(source_path.name)
            apply_shift = self._should_apply_shift(
                csv_path=source_path,
                base_dir=backup_dir if not backup_exists else input_dir,
                selected_curves=selected_set,
            )
            physical_shift_applied = apply_shift and self._should_apply_physical_shift(curve_type)

            processed_df = self.process_file(
                csv_path=source_path,
                shift_voltage=shift_voltage if apply_shift else 0.0,
                threshold_voltage=threshold_voltage,
                hysteresis_mode=hysteresis_mode,
                apply_hysteresis=apply_hysteresis,
            )

            csv_path.parent.mkdir(parents=True, exist_ok=True)
            processed_df.to_csv(csv_path, header=False, index=False, float_format="%.10E")

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
                    "hysteresis_mode": hysteresis_mode,
                    "hysteresis_applied": apply_hysteresis,
                    "original_points": original_points,
                    "processed_points": len(processed_df),
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

    def _read_curve(self, csv_path: str | Path) -> pd.DataFrame:
        csv_path = Path(csv_path)
        data = pd.read_csv(csv_path, header=None)

        if data.shape[1] < 2:
            raise ValueError(f"O arquivo precisa ter ao menos 2 colunas: {csv_path}")

        df = data.iloc[:, :2].copy()
        df.columns = ["voltage", "current"]
        df["voltage"] = pd.to_numeric(df["voltage"], errors="coerce")
        df["current"] = pd.to_numeric(df["current"], errors="coerce")
        df = df.dropna(subset=["voltage", "current"]).reset_index(drop=True)

        if df.empty:
            raise ValueError(f"O arquivo nao contem dados numericos validos: {csv_path}")

        return df

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

        return cleaned[["voltage", "current"]]

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
            "maior": "maior",
            "max": "maior",
            "maximum": "maior",
        }

        if normalized not in aliases:
            raise ValueError(
                "Modo de eliminacao de histerese invalido. "
                "Use 'media', 'menor' ou 'maior'."
            )

        return aliases[normalized]

    def _apply_voltage_threshold(
        self,
        df: pd.DataFrame,
        threshold_voltage: float | None = 0.0,
    ) -> pd.DataFrame:
        """
        Mantem apenas os pontos a partir do limiar informado.
        """
        if threshold_voltage is None:
            return df.reset_index(drop=True)

        filtered = df[df["voltage"] >= threshold_voltage].copy()
        if filtered.empty:
            raise ValueError(
                "Nenhum ponto restante apos aplicar o limiar de tensao "
                f"{threshold_voltage} V."
            )
        return filtered.reset_index(drop=True)

    def _count_rows(self, csv_path: Path) -> int:
        return len(pd.read_csv(csv_path, header=None))

    def _detect_curve_type(self, filename: str) -> str:
        lowered = filename.lower()
        if "transfer" in lowered or "transf" in lowered:
            return "transfer"
        return "output" if "output" in lowered or "saida" in lowered else "unknown"

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
    hysteresis_mode: str = "media",
    apply_hysteresis: bool = True,
    selected_curves: Iterable[str] | None = None,
    output_folder_name: str = "dados_tratados",
    recursive: bool = True,
    voltage_round_decimals: int = 9,
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
    )


def extract_voltage_from_filename(filename: str) -> float | None:
    """
    Extrai tensao de nomes como:
    - transfer-1V.csv
    - output-0.1.csv
    - output-4V.csv
    """
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*V?(?=\.csv$)", filename, flags=re.IGNORECASE)
    return float(match.group(1)) if match else None
