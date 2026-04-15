import os
import re
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from copy import deepcopy

from modules_otft._model import TFTModel
from modules_otft._read_data import ReadData


class SyntheticFromSettings:
    # Mapeamento dos nomes das chaves para seus índices na lista self.base_params/self.bounds
    PARAM_KEYS = ["VTHO", "DELTA", "N", "L", "LAMBDA", "VGCRIT", "JTH", "RS"]

    def __init__(self, settings: dict, model_cls=TFTModel, out_root="synthetic_from_settings"):
        self.settings = settings
        self.path = settings["path"]
        self.model_cls = model_cls
        self.out_root = out_root
        self.reader = ReadData()

        # -----------------------------
        # Função para garantir floats
        # -----------------------------
        def _ensure_float_params(params):
            return [float(x) for x in params]

        self._ensure_float_params = _ensure_float_params

        # ----- carregar parâmetros base -----
        lp = settings.get("loaded_parameters", {})

        # self.base_params agora usa PARAM_KEYS para garantir ordem consistente
        self.base_params = self._ensure_float_params([
            lp.get(k, 1.0) for k in self.PARAM_KEYS
        ])

        # ----- bounds -----
        ub = settings.get("upper_bounds", {})
        lb = settings.get("lower_bounds", {})

        # O mapping é interno, mas usamos as chaves do JSON
        keys_map = [
            ("ub_VTHO","lb_VTHO"),
            ("ub_DELTA","lb_DELTA"),
            ("ub_N","lb_N"),
            ("ub_L","lb_L"),
            ("ub_LAMBDA","lb_LAMBDA"),
            ("ub_VGCRIT","lb_VGCRIT"),
            ("ub_JTH","lb_JTH"),
            ("ub_RS","lb_RS")
        ]

        self.bounds = []
        for i, (ub_k, lb_k) in enumerate(keys_map):
            low = lb.get(lb_k, None)
            high = ub.get(ub_k, None)
            base = self.base_params[i]
            
            # Lógica de bound: usa os limites do JSON, senão usa +/- 30%
            if low is not None and high is not None:
                low, high = float(low), float(high)
            else:
                low, high = base*0.7, base*1.3
            self.bounds.append((low, high))

        os.makedirs(self.out_root, exist_ok=True)
        
        # Leitura dos parâmetros que o usuário DESEJA VARIAR
        self.vary_keys = self.settings.get("vary_parameters", self.PARAM_KEYS)
        # Garante que sejam strings válidas
        self.vary_keys = [k.upper() for k in self.vary_keys if k.upper() in self.PARAM_KEYS]


    # -----------------------
    # Helper: lista arquivos
    # -----------------------
    def _list_csvs(self):
        return sorted([
            os.path.join(self.path, f)
            for f in os.listdir(self.path)
            if f.lower().endswith(".csv")
        ])

    def _inspect_curve(self, csv_path):
        return self.reader._inspect_curve_file(csv_path)

    def _sample_params_within_bounds(self):
        """
        Gera um conjunto de 8 parâmetros. 
        Amostra aleatoriamente APENAS os parâmetros definidos em self.vary_keys.
        Os demais parâmetros usam o valor base fixo.
        """
        sampled_params = list(self.base_params) # Começa com os valores base

        for i, key in enumerate(self.PARAM_KEYS):
            if key in self.vary_keys:
                # Amostragem uniforme entre low e high APENAS se a chave estiver em vary_keys
                low, high = self.bounds[i]
                sampled_params[i] = np.random.uniform(low, high)
        
        return self._ensure_float_params(sampled_params)


    # ----------------------------------------------------
    # Helper: Gera lista de tensões variadas 
    # (Não alterado, pois a lógica está correta)
    # ----------------------------------------------------
    def _generate_voltages_list(self, base_voltage: float, increment: float, max_variation: float):
        # [Implementação da _generate_voltages_list omitida para brevidade, mas está correta acima]
        voltages = [base_voltage]
        current_voltage = base_voltage
        
        if base_voltage >= 0:
            limit = base_voltage + max_variation
            sign = 1
        else:
            limit = base_voltage - max_variation
            sign = -1
        
        while True:
            next_voltage = current_voltage + (increment * sign)
            
            if sign == 1 and next_voltage > limit: break
            if sign == -1 and next_voltage < limit: break
            
            if abs(next_voltage - current_voltage) < 1e-6: break 

            voltages.append(next_voltage)
            current_voltage = next_voltage
            
            if len(voltages) > 1000: break 

        return voltages[1:]
    
    # ---------------------------
    # Função principal: gerar (CORRIGIDA)
    # ---------------------------
    def generate(self, n_variations_per_file=5, resample_n_points=None, save_csv=True, save_npz=True, verbose=True, 
                 variation_mode="params", voltage_increment=2.0, voltage_max_variation=10.0):

        csvs = self._list_csvs()
        if len(csvs) == 0:
            raise RuntimeError(f"Nenhum CSV encontrado em {self.path}")

        out_index = []
        
        # 1. Determinação dos modos de variação
        mode = variation_mode.lower()
        vary_params = mode in ("params", "both")
        vary_voltages = mode in ("voltages", "both")

        if not (vary_params or vary_voltages):
             raise ValueError("variation_mode inválido. Escolha 'params', 'voltages' ou 'both'.")
        
        # --- Valores Configuráveis Dinâmicos (Omitidos para brevidade) ---
        current_typic = self.settings.get("current_typic", "uA")
        _raw_idleak = self.settings.get("loaded_idleak", 0.0)
        if isinstance(_raw_idleak, dict):
            _vals = list(_raw_idleak.values())
            loaded_idleak = float(_vals[0]) if _vals else 0.0
        elif isinstance(_raw_idleak, (list, tuple)):
            loaded_idleak = float(_raw_idleak[0]) if _raw_idleak else 0.0
        else:
            loaded_idleak = float(_raw_idleak)
        with_transistor = float(self.settings.get("with_transistor", 0.1))
        sr_resistance = float(self.settings.get("resistance_scale", 1e4))
        curr_carry = float(self.settings.get("current_carry", 1e-6))
        type_curve = self.settings.get("type_curve", 'linear')
        mult_idleak = float(self.settings.get("mult_idleak", 0))
        scale_transfer = self.settings.get("experimental_data_scale_transfer", "A")
        scale_output = self.settings.get("experimental_data_scale_output", "uA")
        
        # 2. Loop principal: Iterar sobre os arquivos CSV
        for csv_path in csvs:
            
            curve_info = self._inspect_curve(csv_path)
            curve_type = curve_info.get("curve_type")
            if curve_type not in (0, 1):
                continue

            is_transfer = curve_type == 0
            V_exp = np.asarray(curve_info["sweep_values"], dtype=float)
            V_model = np.linspace(V_exp.min(), V_exp.max(), resample_n_points) if resample_n_points is not None else V_exp.copy()
            fixed_voltage_from_name = curve_info.get("fixed_voltage")
            if fixed_voltage_from_name is None:
                continue


            # --- Determinar listas de variação ---
            if vary_voltages:
                sim_voltages = self._generate_voltages_list(fixed_voltage_from_name, voltage_increment, voltage_max_variation)
                n_voltage_variations = len(sim_voltages)
                if n_voltage_variations == 0 and vary_params is False: continue
            else:
                sim_voltages = [fixed_voltage_from_name]
                n_voltage_variations = 1

            if vary_params:
                # No modo 'params' ou 'both', geramos N conjuntos aleatórios
                n_param_variations = n_variations_per_file
                param_sets = [self._sample_params_within_bounds() for _ in range(n_param_variations)]
            else:
                # CORREÇÃO 1: No modo 'voltages' (vary_params=False), usamos os parâmetros base fixos
                n_param_variations = 1
                param_sets = [self.base_params] # <--- USA OS PARÂMETROS BASE FIXOS
            
            n_total_iterations = max(n_param_variations, n_voltage_variations)


            # [Bloco de definição de metadados omitido para brevidade]
            path_clean = self.settings["path"].replace("\\", "/").split("/"); tech = path_clean[-2]
            tipo_folder = "tipo_p" if "p" in os.path.basename(self.settings["path"]).lower() else "tipo_n"
            mode_folder = "transfer" if is_transfer else "output"
            out_dir = os.path.join(self.out_root, tech, tipo_folder, mode_folder); os.makedirs(out_dir, exist_ok=True)
            type_data = 0 if is_transfer else 1; curv_transfer = 1 if is_transfer else 0
            scale_factor = scale_transfer if is_transfer else scale_output
            type_transitor = -1 if "p" in os.path.basename(self.settings["path"]).lower() else 1
            
            
            # 3. Execução da simulação
            for i in range(n_total_iterations):
                
                # 3a. Determinar Parâmetros
                param_index = i % n_param_variations
                params = param_sets[param_index]

                # 3b. Determinar Tensão de Simulação
                voltage_index = i % n_voltage_variations
                current_sim_v = sim_voltages[voltage_index]

                # --- INSTANCIAÇÃO DO MODELO e CHAMADA DO MODELO (Omitido para brevidade) ---
                if is_transfer: tension_list = [current_sim_v]
                else: tension_list = [float(current_sim_v)]
                
                m = self.model_cls(
                    tension_list=tension_list, n_points=len(V_model), type_curve=type_curve, current_typic=current_typic, 
                    scale_factor=scale_factor, idleak=loaded_idleak, mult_idleak=mult_idleak, type_data=type_data,
                    type_transitor=type_transitor, curv_transfer=curv_transfer, with_transistor=with_transistor, 
                    sr_resistance=sr_resistance, curr_carry=curr_carry
                )

                Id_gen = m.calc_model(V_model, Vtho=params[0], Delta=params[1], N=params[2], L=params[3], Lambda=params[4], Vcrit=params[5], Jth=params[6], Rs=params[7])
                Id_gen = np.array(Id_gen).astype(float).ravel()

                # [Bloco de salvamento de CSV/NPZ e INDEX (out_index.append) omitido para brevidade]
                
                base_name = os.path.splitext(os.path.basename(csv_path))[0]
                v_label = f"{int(round(current_sim_v)) if current_sim_v == round(current_sim_v) else current_sim_v:g}V".replace('-', 'neg').replace('.', 'p')
                base_name_with_v = f"{mode_folder}-{v_label}"; out_base = f"{base_name_with_v}_synth_{i:03d}"
                out_csv = os.path.join(out_dir, out_base + ".csv"); out_npz = os.path.join(out_dir, out_base + ".npz")

                if save_csv:
                    if is_transfer:
                        output_df = pd.DataFrame({
                            "VGS": V_model,
                            "VDS": np.full(len(V_model), current_sim_v, dtype=float),
                            "ID": Id_gen,
                        })
                    else:
                        output_df = pd.DataFrame({
                            "VGS": np.full(len(V_model), current_sim_v, dtype=float),
                            "VDS": V_model,
                            "ID": Id_gen,
                        })
                    output_df.to_csv(out_csv, index=False, float_format="%.10E")

                params_dict = dict(zip(self.PARAM_KEYS, params))
                meta = {"origin_file": os.path.abspath(csv_path), "is_transfer": is_transfer, "fixed_voltage_simulated": current_sim_v, "params": params_dict, "settings": self.settings}
                
                if save_npz: np.savez(out_npz, V=V_model, I=Id_gen, meta=meta)

                out_index.append({
                    "npz_path": out_npz, "csv_path": out_csv, "fixed_voltage_simulated": current_sim_v, "params": params_dict
                })

                if verbose:
                    print(f"Gerado: {out_csv} | Tensão: {current_sim_v} V | params(Vtho={params[0]:.4g}, Jth={params[6]:.4g})")

        # [Bloco de incremento e salvamento do index_generated.json omitido para brevidade]
        index_file = os.path.join(self.out_root, "index_generated.json")
        if os.path.exists(index_file):
            try:
                with open(index_file, "r", encoding="utf8") as f: existing_data = json.load(f)
                if isinstance(existing_data, list): existing_data.extend(out_index); final_index = existing_data
                else: print(f"Aviso: {index_file} encontrado, mas com formato inesperado. Sobrescrevendo com novos dados."); final_index = out_index
            except json.JSONDecodeError: print(f"Aviso: {index_file} corrompido. Sobrescrevendo com novos dados."); final_index = out_index
        else: final_index = out_index

        with open(index_file, "w", encoding="utf8") as f: json.dump(final_index, f, indent=2)
        print("\nIndex salvo em:", index_file)
        return [item["npz_path"] for item in final_index]

    # -----------------------------------
    # Função utilitária para inspeção (Omitida para brevidade)
    # -----------------------------------
    @staticmethod
    def load_and_plot(csv_path, log_plot=False, show=True):
        reader = ReadData()
        curve_info = reader._inspect_curve_file(csv_path)
        V = np.asarray(curve_info["sweep_values"], dtype=float)
        I = np.asarray(curve_info["current_values"], dtype=float)
        df = pd.DataFrame({"V": V, "I": I})

        npz_path = os.path.splitext(csv_path)[0] + ".npz"
        meta = None
        if os.path.exists(npz_path):
            d = np.load(npz_path, allow_pickle=True)
            if "meta" in d.files:
                meta = d["meta"].tolist()

        if show:
            plt.figure(figsize=(6,4))
            if log_plot:
                plt.semilogy(V, np.abs(I) + 1e-30)
            else:
                plt.plot(V, I, marker='.')
            plt.xlabel("V (V)")
            plt.ylabel("I (A)")
            title = os.path.basename(csv_path)
            if meta is not None:
                pp = meta["params"]
                title += " — " + ", ".join([f"{k}={v:.3g}" for k, v in pp.items()])
            plt.title(title)
            plt.grid(True)
            plt.tight_layout()
            plt.show()

        return df, meta
    


def main():
    # Exemplo de uso
    settings = {
        "path": "experimental_data/M1_LAMB_MC",  # Pasta com arquivos CSV experimentais
        "loaded_parameters": {
            "VTHO": 5.0,
            "DELTA": 0.5,
            "N": 2.0,
            "L": 1.0,
            "LAMBDA": 0.02,
            "VGCRIT": 0.0,
            "JTH": 1e-6,
            "RS": 100.0
        },
        "upper_bounds": {
            "ub_VTHO": 10.0,
            "ub_DELTA": 1.0,
            "ub_N": 3.0,
            "ub_L": 2.0,
            "ub_LAMBDA": 0.05,
            "ub_VGCRIT": 5.0,
            "ub_JTH": 5e-6,
            "ub_RS": 200.0
        },
        "lower_bounds": {
            "lb_VTHO": 0.0,
            "lb_DELTA": 0.1,
            "lb_N": 1.0,
            "lb_L": 0.5,
            "lb_LAMBDA": 0.01,
            "lb_VGCRIT": -5.0,
            "lb_JTH": 1e-7,
            "lb_RS": 50.0
        },
        "vary_parameters": ["VTHO", "JTH", "LAMBDA"],  # Parâmetros a variar
        # Outros parâmetros configuráveis...
    }

    gen = SyntheticFromSettings(settings, out_root="synthetic_M1_LAMB_MC")
    generated_index = gen.generate(
        n_variations_per_file=2, 
        resample_n_points=10000, 
        variation_mode="voltages", 
        voltage_increment=4.0, 
        voltage_max_variation=20, 
        save_csv=True, 
        save_npz=True
    )

if __name__ == "__main__":
    main()      