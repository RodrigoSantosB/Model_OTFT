from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


class PreProcessingData:
    """
    Pre-processa curvas experimentais em CSV.

    Recursos principais:
    - leitura recursiva de arquivos CSV;
    - aplicacao de shift horizontal (shift right) na tensao;
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
        threshold_voltage: float = 0.0,
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
                a este valor apos o shift. O padrao e 0.0 V.
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

            apply_shift = self._should_apply_shift(
                csv_path=csv_path,
                base_dir=input_dir,
                selected_curves=selected_set,
            )

            processed_df = self.process_file(
                csv_path=csv_path,
                shift_voltage=shift_voltage if apply_shift else 0.0,
                threshold_voltage=threshold_voltage,
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
                    "curve_type": self._detect_curve_type(csv_path.name),
                    "shift_applied": apply_shift,
                    "shift_voltage": shift_voltage if apply_shift else 0.0,
                    "original_points": self._count_rows(csv_path),
                    "processed_points": int(len(processed_df)),
                }
            )

        summary_df = pd.DataFrame(summary)
        summary_df.to_csv(output_dir / "resumo_processamento.csv", index=False)
        return summary

    def process_file(
        self,
        csv_path: str | Path,
        shift_voltage: float = 0.0,
        threshold_voltage: float = 0.0,
    ) -> pd.DataFrame:
        """
        Le um CSV, aplica shift horizontal, corta por limiar de tensao e
        remove redundancias por histerese.
        """
        df = self._read_curve(csv_path)
        df["voltage"] = df["voltage"] + float(shift_voltage)
        df = self._apply_voltage_threshold(df, threshold_voltage=threshold_voltage)
        df = self._clean_hysteresis(df)
        return df

    def _collect_csv_files(self, input_dir: Path, recursive: bool = True) -> list[Path]:
        pattern = "**/*.csv" if recursive else "*.csv"
        return sorted(path for path in input_dir.glob(pattern) if path.is_file())

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

    def _clean_hysteresis(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove pontos redundantes gerados por varreduras de ida e volta.

        Estrategia:
        - arredonda a tensao para consolidar valores equivalentes;
        - agrupa tensoes repetidas;
        - usa a media da corrente como curva representativa unica;
        - retorna a curva ordenada pelo eixo de tensao.
        """
        work_df = df.copy()
        work_df["voltage_key"] = work_df["voltage"].round(self.voltage_round_decimals)

        cleaned = (
            work_df.groupby("voltage_key", as_index=False)
            .agg(
                voltage=("voltage", "mean"),
                current=("current", "mean"),
            )
            .sort_values("voltage", kind="mergesort")
            .reset_index(drop=True)
        )

        return cleaned[["voltage", "current"]]

    def _apply_voltage_threshold(
        self,
        df: pd.DataFrame,
        threshold_voltage: float = 0.0,
    ) -> pd.DataFrame:
        """
        Mantem apenas os pontos a partir do limiar informado.
        """
        filtered = df[df["voltage"] >= float(threshold_voltage)].copy()
        if filtered.empty:
            raise ValueError(
                "Nenhum ponto restante apos aplicar o limiar de tensao "
                f"{threshold_voltage} V."
            )
        return filtered.reset_index(drop=True)

    def _count_rows(self, csv_path: Path) -> int:
        return int(len(pd.read_csv(csv_path, header=None)))

    def _detect_curve_type(self, filename: str) -> str:
        lowered = filename.lower()
        if "transfer" in lowered or "transf" in lowered:
            return "transfer"
        if "output" in lowered or "saida" in lowered:
            return "output"
        return "unknown"

    def _normalize_selected_curves(self, selected_curves: Iterable[str] | None) -> set[str] | None:
        if selected_curves is None:
            return None

        normalized = set()
        for item in selected_curves:
            value = str(item).strip().replace("\\", "/")
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
    threshold_voltage: float = 0.0,
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
    if not match:
        return None
    return float(match.group(1))
