import os
import json
import copy
import pickle
import numpy as np
import pandas as pd
from genericpath import exists
from datetime import datetime

# Bibliotecas para gráficos estáticos (Artigos)
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Configuração global de estilo para artigos científicos
sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
plt.rcParams.update({
    'font.family': 'serif',
    'axes.titlesize': 15,
    'axes.labelsize': 13,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11,
    'legend.fontsize': 11,
    'figure.figsize': (10, 6)
})

class MLPModelTrain():
    """
    Classe para treinar uma MLP que mapeia tensões (Vg, Vd) -> Corrente (Id) usando Scikit-Learn.
    Salva Scalers separadamente, gera logs em JSON e plota gráficos estáticos de alta qualidade.
    """
    
    def __init__(self, index_path, scale_factor_min=1e-30, 
                 hidden_layers=(256, 128), 
                 activation='relu', learning_rate=0.001, max_iter=2000, batch_size=32, n_iter=80, tol=1e-5,
                 model_path=None, load_model=False, 
                 test_size=0.2, random_state=42):
        
        self.index_path = index_path
        self.scale_factor_min = scale_factor_min 
        self.hidden_layers = hidden_layers
        self.activation = activation
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.batch_size = batch_size
        self.n_iter_no_change = n_iter
        self.tol = tol
        self.test_size = test_size
        self.random_state = random_state
        
        self.model = None
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler() 
        self.history = {}
        self.num_parameters = 0 # Inicializador da variável de contagem de parâmetros
        
        # 1. Configuração do Timestamp para versionamento
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.artifact_dir = f'artefatos/run_{timestamp}'
        
        # 2. Criação dos diretórios
        for directory in ['models', 'artefatos', self.artifact_dir]:
            if not exists(directory):
                os.makedirs(directory)
            
        self.model_path = model_path if model_path else 'models/mlp_regressor.pkl' 
        self.log_path = os.path.join(self.artifact_dir, 'training_log.json')
        
        if load_model:
            self.load_model()
            
    def calculate_trainable_parameters(self, input_dim, output_dim=1):
        """
        Calcula matematicamente o número de parâmetros treináveis (Pesos + Bias) da arquitetura.
        Baseado em: (N_in * N_out) pesos + N_out biases para cada conexão entre camadas.
        """
        total_params = 0
        current_in = input_dim
        
        # Iterando sobre as camadas ocultas
        for current_out in self.hidden_layers:
            weights = current_in * current_out
            biases = current_out
            total_params += (weights + biases)
            current_in = current_out # A saída desta camada vira a entrada da próxima
            
        # Conexão final: Última camada oculta -> Camada de Saída (Output)
        weights = current_in * output_dim
        biases = output_dim
        total_params += (weights + biases)
        
        return total_params
        
    def _create_model(self):
        return MLPRegressor(
            hidden_layer_sizes=self.hidden_layers,
            activation=self.activation,
            solver='adam',
            alpha=0.0005, 
            learning_rate_init=self.learning_rate,
            random_state=self.random_state
        )
    
    def _load_csv_file(self, csv_path, item):
        """Carrega um arquivo CSV e retorna arrays compatíveis com o pipeline de treinamento.

        Suporta dois formatos:
        - Formato A (vírgula, 3 colunas VGS/VDS/ID): retorna (V_g, V_d, I, None)
        - Formato B (ponto-e-vírgula, 2 colunas, decimal europeu): retorna (V, None, I, is_transfer)
        """
        with open(csv_path, 'r') as f:
            first_line = f.readline()

        if ';' in first_line:
            # Formato B: duas colunas, separador ponto-e-vírgula, decimal europeu
            rows = []
            with open(csv_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(';')
                    v = float(parts[0].replace(',', '.'))
                    i = float(parts[1].replace(',', '.'))
                    rows.append((v, i))
            arr = np.array(rows, dtype=np.float32)
            V, I = arr[:, 0], arr[:, 1]
            is_transfer = item.get("is_transfer")
            if is_transfer is None:
                is_transfer = 'transfer' in os.path.basename(csv_path).lower()
            return V, None, I, is_transfer
        else:
            # Formato A: três colunas VGS, VDS, ID com duas linhas de cabeçalho
            df = pd.read_csv(csv_path, skiprows=2, header=None, names=['VGS', 'VDS', 'ID'])
            V_g = df['VGS'].values.astype(np.float32)
            V_d = df['VDS'].values.astype(np.float32)
            I = df['ID'].values.astype(np.float32)
            return V_g, V_d, I, None

    def load_and_prepare_data(self):
        print(f"Carregando índice de dados em: {self.index_path}")
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {self.index_path}")

        with open(self.index_path, 'r') as f:
            index_data = json.load(f)

        X_features_ponto = []
        Y_labels_ponto = []
        arquivos_com_erro = 0

        for item in index_data:
            npz_path = item.get("npz_path")
            csv_path = item.get("csv_path")

            loaded = False
            V_model = I_model = V_fixed = is_transfer = None

            # Tenta NPZ primeiro
            if npz_path and os.path.exists(npz_path):
                try:
                    data = np.load(npz_path, allow_pickle=True)
                    V_model = data["V"].ravel()
                    I_model = data["I"].ravel()
                    V_fixed = item["fixed_voltage_simulated"]
                    is_transfer = data['meta'].tolist()['is_transfer']
                    loaded = True
                except Exception:
                    pass

            # Fallback para CSV
            if not loaded and csv_path and os.path.exists(csv_path):
                try:
                    result = self._load_csv_file(csv_path, item)
                    if result[1] is None and result[3] is not None:
                        # Formato B: (V, None, I, is_transfer)
                        V_model, _, I_model, is_transfer = result
                        V_fixed = item.get("fixed_voltage_simulated", 0.0)
                        loaded = True
                    elif result[1] is not None:
                        # Formato A: (V_g, V_d, I, None) — V_G e V_D já separados
                        V_g_arr, V_d_arr, I_arr, _ = result
                        for V_G, V_D, I_exp in zip(V_g_arr, V_d_arr, I_arr):
                            X_vec = [V_G, V_D, V_G**2, V_D**2, V_G * V_D]
                            Y_label = np.log(max(np.abs(I_exp), self.scale_factor_min))
                            X_features_ponto.append(X_vec)
                            Y_labels_ponto.append(Y_label)
                        loaded = True
                        continue
                    else:
                        # Formato A sem V_d (só 2 valores retornados como None) — não deveria ocorrer
                        pass
                except Exception:
                    pass

            if not loaded:
                arquivos_com_erro += 1
                continue

            for V_exp, I_exp in zip(V_model, I_model):
                if is_transfer:
                    V_G = V_exp; V_D = V_fixed
                else:
                    V_G = V_fixed; V_D = V_exp

                X_vec = [V_G, V_D, V_G**2, V_D**2, V_G * V_D]
                Y_label = np.log(max(np.abs(I_exp), self.scale_factor_min))

                X_features_ponto.append(X_vec)
                Y_labels_ponto.append(Y_label)

        if len(X_features_ponto) == 0:
            raise ValueError(f"NENHUM DADO CARREGADO! {arquivos_com_erro} arquivos falharam.")

        return np.array(X_features_ponto, dtype=np.float32), np.array(Y_labels_ponto, dtype=np.float32).reshape(-1, 1)

    def train_model(self, filename=None):
        X_all, y_all = self.load_and_prepare_data()

        print("Padronizando Features (X) e Target (Y)...")
        X_scaled = self.scaler_X.fit_transform(X_all)
        y_scaled = self.scaler_y.fit_transform(y_all) 

        # ---> ALTERAÇÃO AQUI: Divisão em 3 conjuntos <---
        # 1. Separa o bloco de treinamento e um bloco temporário
        X_train, X_temp, y_train, y_temp = train_test_split(
            X_scaled, y_scaled, test_size=self.test_size, random_state=self.random_state
        )
        
        # 2. Divide o bloco temporário entre validação (para Early Stopping) e teste (para métrica final)
        X_val, X_test, y_val, y_test = train_test_split(
            X_temp, y_temp, test_size=0.5, random_state=self.random_state
        )
        
        # ---> Cálculo e Log dos Parâmetros Baseados na Configuração <---
        input_dim = X_train.shape[1]
        self.num_parameters = self.calculate_trainable_parameters(input_dim, output_dim=1)
        
        print(f"Iniciando treinamento customizado da MLP (Scikit-Learn)...")
        print(f"Arquitetura: Input({input_dim}) -> {self.hidden_layers} -> Output(1)")
        print(f"Total de Parâmetros Treináveis: {self.num_parameters}")
        print(f"Amostras: Treino={len(X_train)} | Validação={len(X_val)} | Teste={len(X_test)}")
        
        self.model = self._create_model()
        n_samples = X_train.shape[0]
        self.history = {'train_loss': [], 'val_loss': [], 'train_acc': [], 'val_acc': []}
        
        best_val_loss = float('inf')
        best_weights = None
        epochs_no_improve = 0
        
        # Loop de épocas com partial_fit
        for epoch in range(1, self.max_iter + 1):
            indices = np.random.permutation(n_samples)
            X_train_shuf = X_train[indices]
            y_train_shuf = y_train[indices]
            
            for i in range(0, n_samples, self.batch_size):
                X_batch = X_train_shuf[i:i + self.batch_size]
                y_batch = y_train_shuf[i:i + self.batch_size]
                self.model.partial_fit(X_batch, y_batch.ravel())

            # ---> ALTERAÇÃO AQUI: Usando apenas X_val e y_val para acompanhar o progresso <---
            y_pred_train = self.model.predict(X_train).reshape(-1, 1)
            y_pred_val = self.model.predict(X_val).reshape(-1, 1)
            
            t_loss = mean_squared_error(y_train, y_pred_train)
            v_loss = mean_squared_error(y_val, y_pred_val)
            t_acc = r2_score(y_train, y_pred_train)
            v_acc = r2_score(y_val, y_pred_val)
            
            self.history['train_loss'].append(t_loss)
            self.history['val_loss'].append(v_loss)
            self.history['train_acc'].append(t_acc)
            self.history['val_acc'].append(v_acc)
            
            print(f"Epoch {epoch}/{self.max_iter} - loss: {t_loss:.4f} - val_loss: {v_loss:.4f} - acc: {t_acc:.4f} - val_acc: {v_acc:.4f}")
            
            if v_loss < best_val_loss - self.tol:
                best_val_loss = v_loss
                epochs_no_improve = 0
                best_weights = copy.deepcopy(self.model)
            else:
                epochs_no_improve += 1
                
            if epochs_no_improve >= self.n_iter_no_change:
                print(f"\nTreinamento interrompido cedo (Early Stopping) na época {epoch}.")
                break

        if best_weights is not None:
            self.model = best_weights

        # ---> Avaliação Final: Usando os dados de teste intocados (X_test, y_test) <---
        y_pred_final = self.model.predict(X_test).reshape(-1, 1)
        mse_test_scaled = mean_squared_error(y_test, y_pred_final)
        mae_test_scaled = mean_absolute_error(y_test, y_pred_final)
        r2_test_scaled = r2_score(y_test, y_pred_final)
        
        y_test_inv = self.scaler_y.inverse_transform(y_test)
        y_pred_inv = self.scaler_y.inverse_transform(y_pred_final)
        mse_real = mean_squared_error(y_test_inv, y_pred_inv)
        mae_real = mean_absolute_error(y_test_inv, y_pred_inv)
        
        print(f"\nTreinamento Concluído. Resultados do Melhor Modelo no Conjunto de Teste:")
        print(f"MSE (Normalizado): {mse_test_scaled:.6e} | R2: {r2_test_scaled:.4f}")
        print(f"MSE (Escala Real): {mse_real:.6e} | MAE Real: {mae_real:.6e}\n")
        
        self.save_model(filename) 
        self.save_training_logs({
            "mse_scaled": float(mse_test_scaled), "mae_scaled": float(mae_test_scaled), "r2_scaled": float(r2_test_scaled),
            "mse_real": float(mse_real), "mae_real": float(mae_real)
        })
        self.plot_training_metrics()
        return float(mse_test_scaled)

    def predict_current(self, V_g, V_d):
        if self.model is None:
            raise ValueError("O modelo não está treinado.")

        V_g = np.atleast_1d(V_g)
        V_d = np.atleast_1d(V_d)
        
        X_infer = np.column_stack([V_g, V_d, V_g**2, V_d**2, V_g * V_D])
        X_scaled = self.scaler_X.transform(X_infer)
        y_pred_scaled = self.model.predict(X_scaled).reshape(-1, 1)
        y_pred_log = self.scaler_y.inverse_transform(y_pred_scaled)
        I_d_pred = np.exp(y_pred_log).flatten()

        return float(I_d_pred[0]) if len(I_d_pred) == 1 else I_d_pred

    # ----------------------------------------------------------------------
    # MÉTODOS DE ARTEFATOS E LOGS (MATPLOTLIB)
    # ----------------------------------------------------------------------

    def save_training_logs(self, metrics):
        """Salva parâmetros (incluindo a contagem calculada) e métricas em JSON."""
        log_data = {
            "parameters": {
                "total_trainable_parameters": self.num_parameters, # <--- Parâmetro adicionado aqui
                "hidden_layers": self.hidden_layers,
                "activation": self.activation,
                "learning_rate_init": self.learning_rate,
                "batch_size": self.batch_size,
                "max_iter": self.max_iter,
                "patience": self.n_iter_no_change,
                "epochs_trained": len(self.history['train_loss'])
            },
            "final_metrics": metrics
        }
        with open(self.log_path, 'w') as f:
            json.dump(log_data, f, indent=4)

    def plot_training_metrics(self):
        if not self.history.get('train_loss'):
            print("Sem histórico para plotar.")
            return

        epochs = np.arange(1, len(self.history['train_loss']) + 1)
        t_loss = self.history['train_loss']
        v_loss = self.history['val_loss']
        t_acc = self.history['train_acc']
        v_acc = self.history['val_acc']

        c_train_loss = '#1f77b4'; c_val_loss = '#aec7e8'
        c_train_acc = '#ff7f0e'; c_val_acc = '#ffbb78'

        plt.figure()
        plt.plot(epochs, t_loss, label='Train Loss (MSE)', color=c_train_loss, linewidth=2)
        plt.plot(epochs, v_loss, label='Validation Loss (MSE)', color=c_val_loss, linewidth=2, linestyle='--')
        plt.title('Curva de Loss (Erro Quadrático Médio)')
        plt.xlabel('Épocas')
        plt.ylabel('Loss (Escala Logarítmica)')
        plt.yscale('log')
        plt.legend(frameon=True, shadow=True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifact_dir, '1_loss_curve.png'), dpi=300)
        plt.close()

        plt.figure()
        plt.plot(epochs, t_acc, label='Train Accuracy ($R^2$)', color=c_train_acc, linewidth=2)
        plt.plot(epochs, v_acc, label='Validation Accuracy ($R^2$)', color=c_val_acc, linewidth=2, linestyle='--')
        plt.title('Curva de Acurácia (Score $R^2$)')
        plt.xlabel('Épocas')
        plt.ylabel('Acurácia ($R^2$)')
        plt.ylim(bottom=min(min(v_acc), 0), top=1.05)
        plt.legend(loc='lower right', frameon=True, shadow=True)
        plt.tight_layout()
        plt.savefig(os.path.join(self.artifact_dir, '2_accuracy_curve.png'), dpi=300)
        plt.close()

        fig, ax1 = plt.subplots(figsize=(11, 7))
        fig.suptitle('Análise Completa de Treinamento e Overfitting', fontsize=16, y=0.96)

        ax1.set_xlabel('Épocas')
        ax1.set_ylabel('Loss (MSE)', color=c_train_loss, fontweight='bold')
        l1 = ax1.plot(epochs, t_loss, label='Train Loss', color=c_train_loss, linewidth=2)
        l2 = ax1.plot(epochs, v_loss, label='Val Loss', color=c_val_loss, linewidth=2, linestyle='--')
        ax1.tick_params(axis='y', labelcolor=c_train_loss)
        ax1.set_yscale('log')

        ax2 = ax1.twinx() 
        ax2.set_ylabel('Accuracy ($R^2$)', color=c_train_acc, fontweight='bold', rotation=270, labelpad=20)
        l3 = ax2.plot(epochs, t_acc, label='Train Acc', color=c_train_acc, linewidth=2)
        l4 = ax2.plot(epochs, v_acc, label='Val Acc', color=c_val_acc, linewidth=2, linestyle='--')
        ax2.tick_params(axis='y', labelcolor=c_train_acc)
        ax2.set_ylim(bottom=0, top=1.05)

        lines = l1 + l2 + l3 + l4
        labels = [l.get_label() for l in lines]
        ax1.legend(lines, labels, loc='center right', frameon=True, fancybox=True, shadow=True)

        plt.tight_layout()
        plt.savefig(os.path.join(self.artifact_dir, '3_combined_analysis.png'), dpi=300)
        plt.close()

    # ----------------------------------------------------------------------
    # MÉTODOS DE PERSISTÊNCIA (SALVAR/CARREGAR)
    # ----------------------------------------------------------------------

    def save_model(self, filename=None):
        if self.model is None: return False
        if filename is None: filename = self.model_path
            
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        base_name, _ = os.path.splitext(filename)
        
        try:
            with open(filename, 'wb') as f: pickle.dump(self.model, f)
            with open(f"{base_name}_scaler_X.pkl", 'wb') as f: pickle.dump(self.scaler_X, f)
            with open(f"{base_name}_scaler_Y.pkl", 'wb') as f: pickle.dump(self.scaler_y, f)
            return True
        except Exception as e:
            print(f"Erro ao salvar: {str(e)}")
            return False
            
    def load_model(self, filename=None):
        if filename is None: filename = self.model_path
            
        if not os.path.exists(filename): return None, None, None 
            
        try:
            with open(filename, 'rb') as f: obj = pickle.load(f)

            if isinstance(obj, dict) and 'model' in obj:
                self.model = obj['model']
                self.scaler_X = obj.get('scaler_X')
                self.scaler_y = obj.get('scaler_y')
            else:
                self.model = obj
                base_name, _ = os.path.splitext(filename)
                
                path_x = f"{base_name}_scaler_X.pkl"
                if os.path.exists(path_x):
                    with open(path_x, 'rb') as f: self.scaler_X = pickle.load(f)
                else: self.scaler_X = None

                path_y = f"{base_name}_scaler_Y.pkl"
                if os.path.exists(path_y):
                    with open(path_y, 'rb') as f: self.scaler_y = pickle.load(f)
                else: self.scaler_y = None
                
            return self.model, self.scaler_X, self.scaler_y

        except Exception as e:
            print(f"Erro ao carregar: {str(e)}")
            return None, None, None