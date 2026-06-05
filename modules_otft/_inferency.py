import numpy as np 
import pandas as pd
import plotly.graph_objects as go
from typing import Optional, Tuple, Callable
import json
import os
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")




# Pré-processamento de treino.
def prepare_mlp_features(V_data: np.ndarray, V_fixed: float, is_transfer: bool) -> np.ndarray:
    """
    Gera o array de features X para a MLP a partir dos vetores de tensão de uma curva.

    Input: [Vg, Vd, Vg^2, Vd^2, Vg*Vd]
    """
    # V_data é o vetor do eixo X. V_fixed é a tensão constante.
    if is_transfer:
        # Transfer: V_data = Vg, V_fixed = Vd
        V_G = V_data
        V_D = np.full_like(V_data, V_fixed)
    else:
        # Output: V_data = Vd, V_fixed = Vg
        V_G = np.full_like(V_data, V_fixed)
        V_D = V_data

    # Construindo as 5 features
    X_features = np.column_stack([
        V_G,
        V_D,
        V_G**2,
        V_D**2,
        V_G * V_D
    ])
    
    return X_features



def predict_current(self, V_g, V_d, is_transfer: bool) -> np.ndarray:
        """
        Realiza a inferência da corrente (Id) dados os valores de tensão Vg e Vd.
        Pode receber valores únicos (float) ou listas/arrays (para múltiplas previsões).
        """
        if self.model is None:
            raise ValueError("O modelo não está carregado ou treinado. Execute train_model() ou load_model() primeiro.")

        # Converte para array numpy caso o usuário passe números simples ou listas
        V_g = np.atleast_1d(V_g)
        V_d = np.atleast_1d(V_d)
        
        if V_g.shape != V_d.shape:
            raise ValueError("As entradas V_g e V_d devem ter o mesmo tamanho.")

        # 1. Constrói as features polinomiais exatamente como no treinamento
        X_infer = prepare_mlp_features(V_g, V_d, is_transfer)

        # 2. Aplica a padronização salva no scaler_X
        X_scaled = self.scaler_X.transform(X_infer)

        # 3. O modelo faz a previsão (resultado ainda estará escalado e em log)
        y_pred_scaled = self.model.predict(X_scaled).reshape(-1, 1)

        # 4. Desfaz a padronização do scaler_Y
        y_pred_log = self.scaler_y.inverse_transform(y_pred_scaled)

        # 5. Desfaz o logaritmo usando a função exponencial (np.exp)
        # Atenção: Como no treino foi usado np.log(abs(I)), isso retorna a magnitude da corrente (abs).
        I_d_pred = np.exp(y_pred_log).flatten()

        # Retorna um float nativo se a entrada foi apenas um ponto, ou o array se foram vários
        if len(I_d_pred) == 1:
            return float(I_d_pred[0])
        return I_d_pred
    
    
    
def load_data_for_inference(csv_path: str) -> Tuple[np.ndarray, np.ndarray]:
    with open(csv_path, 'r') as f:
        infer_data = json.load(f)
    
    for item in infer_data:
        npz_path = item["npz_path"]
        csv_path = item["csv_path"]
        v_fixed = item["fixed_voltage_simulated"]
        params = item["params"]
        
        # Verificar se o arquivo é .csv ou .npz e extrair o nome para determinar o tipo de curva
        if npz_path.endswith(".npz"):
            # Determinar se é curva de Transferência ou Saída
            is_transfer = 'transfer' in os.path.basename(npz_path).lower()
        elif csv_path.endswith(".csv"):
            is_transfer = 'transfer' in os.path.basename(csv_path).lower()
        else:
            raise ValueError(f"Tipo de arquivo desconhecido para {npz_path}")
        
        # Carregar dados do CSV
        df_exp = pd.read_csv(csv_path)
        V_data = df_exp.iloc[:, 0].to_numpy()   # VGS ou V (sempre coluna 0)
        I_data = df_exp.iloc[:, -1].to_numpy()  # ID ou I (sempre última coluna)
        break  # Usar apenas o primeiro item do JSON
    return V_data, I_data, v_fixed, is_transfer


import numpy as np
import plotly.graph_objects as go
from typing import Optional, Tuple, Callable

def plot_curve_comparison(
    V_data: np.ndarray, 
    I_real: np.ndarray,
    V_fixed: float,
    is_transfer: bool,
    # !!! ALTERAÇÃO 1: A tupla agora espera 4 itens, incluindo o scaler_y
    mlp_model: Optional[Tuple[Callable, object, object, object]] = None, 
    yscale: str = "log", 
    title: Optional[str] = None
):
    """
    Plota a curva real e a previsão da MLP (com suporte a Y escalado).
    mlp_model deve ser: (prepare_X_func, model, scaler_X, scaler_y)
    """

    fig = go.Figure()
    
    # Normaliza a escala Y
    y_scale = yscale.lower()
    is_log_scale = y_scale in ("log", "logarithmic")
    y_axis_title = "Corrente Absoluta (A)" if is_log_scale else "Corrente (A)"
    
    # -------------------------------
    # PREPARAÇÃO DA CURVA REAL
    # -------------------------------
    I_plot_real = np.abs(I_real)
    # Evita log(0) ou valores negativos no plot log
    if is_log_scale:
        mask = I_plot_real > 0
        # Substitui zeros/negativos por um valor muito pequeno apenas visualmente
        safe_min = np.min(I_plot_real[mask]) if np.any(mask) else 1e-12
        I_plot_real[I_plot_real <= 0] = safe_min 

    fig.add_trace(go.Scatter(
        x=V_data, 
        y=I_plot_real, 
        mode='lines+markers', 
        name="Real (Dados CSV)",
        line=dict(color='blue')
    ))

    # -------------------------------
    # PREVISÃO DA MLP
    # -------------------------------
    if mlp_model is not None:
        # !!! ALTERAÇÃO 2: Desempacotar o scaler_y
        prepare_X_func, model, scaler_X, scaler_y = mlp_model
        
        # 1. Preparar features X
        X_test = prepare_X_func(V_data, V_fixed, is_transfer)
        
        # 2. Padronizar X
        X_test_scaled = scaler_X.transform(X_test)
        
        # 3. Prever (Resultado está na escala NORMALIZADA)
        Y_pred_scaled = model.predict(X_test_scaled)
        
        # Desnormalizar o Y (Voltar para a escala original, ex: ln(|Id|))
        Y_pred_ln_original = scaler_y.inverse_transform(Y_pred_scaled.reshape(-1, 1))  
              
        # Achatar para vetor 1D
        Y_pred_ln = Y_pred_ln_original.ravel()
        
        # 4. Converter ln(|Id|) para Corrente (|Id|)
        I_pred_abs = np.exp(Y_pred_ln)
        
        # 5. Tratamento para plot (mesma lógica do real)
        I_plot_pred = I_pred_abs.copy()
        if is_log_scale:
             I_plot_pred[I_plot_pred <= 0] = 1e-30 
        
        fig.add_trace(go.Scatter(
            x=V_data, 
            y=I_plot_pred, 
            mode='lines', 
            name="Previsão MLP",
            line=dict(color='red', dash='dash')
        ))
        
        # Calcula MAE na escala logarítmica (Unidade Real: ln(A))
        # Nota: I_real deve ser convertido para log para comparar com Y_pred_ln
        I_real_ln_safe = np.log(I_plot_real) # Usando a versão tratada > 0
        
        mae = np.mean(np.abs(I_real_ln_safe - Y_pred_ln))
        
        if title is None:
             title = f"V_fixed={V_fixed}V | MAE(ln)={mae:.3f}"
        else:
             title += f" (MAE={mae:.3f})"

    fig.update_layout(
        title=title if title is not None else "Curva Real",
        xaxis_title="V_GS (V)" if is_transfer else "V_DS (V)",
        yaxis_title=y_axis_title,
        yaxis_type="log" if is_log_scale else "linear",
        template="plotly_dark",
        legend_title="Curves"
    )

    fig.show()