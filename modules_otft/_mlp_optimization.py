from ._imports import *
from ._read_data import ReadData
import numpy as np
import os
import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor

class MLPOptimizer(ReadData):
    """
    Class for optimizing models using a Multi-Layer Perceptron (MLP) neural network.
    
    Esta classe implementa uma alternativa ao otimizador TRF usando redes neurais
    para prever os parâmetros ótimos do modelo diretamente a partir dos dados experimentais.
    """
    
    def __init__(self, current_typic, scale_transfer, scale_output, type_read, 
                 path_voltages, type_curve='log', hidden_layers=(100, 50, 25), 
                 activation='relu', learning_rate=0.001, max_iter=1000, tol=1e-4,
                 model_path=None, load_model=False):
        """
        Inicializa o otimizador MLP.
        
        Args:
            current_typic (str): Tipo de corrente.
            scale_transfer (float): Escala de transferência.
            scale_output (float): Escala de saída.
            type_read (str): Tipo de leitura.
            path_voltages (str): Caminho para os dados de tensão.
            type_curve (str, opcional): Tipo de curva (padrão é 'log').
            hidden_layers (tuple, opcional): Tupla com o número de neurônios em cada camada oculta.
            activation (str, opcional): Função de ativação para as camadas ocultas.
            learning_rate (float, opcional): Taxa de aprendizado para o otimizador.
            max_iter (int, opcional): Número máximo de iterações para treinamento.
            tol (float, opcional): Tolerância para critério de parada.
            model_path (str, opcional): Caminho para salvar/carregar o modelo treinado.
            load_model (bool, opcional): Se True, tenta carregar um modelo existente.
        """
        super().__init__()
        self.current_typic = current_typic
        self.scale_transfer = scale_transfer
        self.scale_output = scale_output
        self.type_read = type_read
        self.path_voltages = path_voltages
        self.type_curve = type_curve
        self.hidden_layers = hidden_layers
        self.activation = activation
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.tol = tol
        self.model = None
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        
        # Definir caminho padrão para o modelo se não for fornecido
        if model_path is None:
            self.model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'mlp_model.pkl')
        else:
            self.model_path = model_path
            
        # Tentar carregar um modelo existente se solicitado
        if load_model:
            self.load_model()
        
    def _create_model(self):
        """
        Cria o modelo MLP com os parâmetros especificados.
        
        Returns:
            MLPRegressor: Modelo de regressão MLP.
        """
        return MLPRegressor(
            hidden_layer_sizes=self.hidden_layers,
            activation=self.activation,
            solver='adam',
            alpha=0.0001,
            batch_size='auto',
            learning_rate='adaptive',
            learning_rate_init=self.learning_rate,
            max_iter=self.max_iter,
            tol=self.tol,
            verbose=True,
            random_state=42
        )
    
    def _generate_training_data(self, Model, coeff, n_samples=1000):
        """
        Gera dados de treinamento para a MLP.
        
        Args:
            Model (object): Instância do modelo a ser otimizado.
            coeff (array-like): Coeficientes iniciais para o modelo.
            n_samples (int, opcional): Número de amostras a gerar.
            
        Returns:
            tuple: X_train, y_train para treinamento da MLP.
        """
        # Carregar dados experimentais para obter o intervalo de tensões
        Vv, Id, voltages, _, _, _ = super().load_data(
            self.type_read, self.path_voltages,
            self.current_typic, self.scale_transfer,
            self.scale_output, self.type_curve
        )
        
        # Achatar os arrays de dados
        Vv_flat = np.ravel(Vv)
        Id_flat = np.ravel(Id)
        
        # Criar variações dos parâmetros
        param_variations = []
        for param in coeff:
            # Variações de ±30% em torno do valor inicial
            variations = np.random.uniform(0.7 * param, 1.3 * param, n_samples)
            param_variations.append(variations)
        
        param_variations = np.array(param_variations).T  # [n_samples, n_params]
        
        # Criar matriz de features (tensões)
        X = np.tile(Vv_flat, (n_samples, 1))  # [n_samples, n_voltages]
        
        # Calcular saídas do modelo para cada conjunto de parâmetros
        y = np.zeros((n_samples, len(Vv_flat)))
        for i in range(n_samples):
            y[i] = Model.calc_model(Vv_flat, *param_variations[i])
        
        # Normalizar os dados
        X_scaled = self.scaler_X.fit_transform(X)
        y_scaled = self.scaler_y.fit_transform(y)
        
        # Dividir em conjuntos de treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_scaled, test_size=0.2, random_state=42
        )
        
        return X_train, y_train, param_variations
    
    def _evaluate_parameters(self, Model, params, Vv_flat, Id_flat):
        """
        Avalia a qualidade dos parâmetros calculando o erro quadrático médio.
        
        Args:
            Model (object): Instância do modelo a ser otimizado.
            params (array-like): Parâmetros a serem avaliados.
            Vv_flat (array-like): Tensões experimentais.
            Id_flat (array-like): Correntes experimentais.
            
        Returns:
            float: Erro quadrático médio.
        """
        # Calcular a saída do modelo com os parâmetros
        model_output = Model.calc_model(Vv_flat, *params)
        
        # Calcular o erro quadrático médio
        mse = np.mean((model_output - Id_flat) ** 2)
        
        return mse
        
    def save_model(self, filename=None):
        """
        Salva o modelo MLP treinado e os scalers em um arquivo.
        
        Args:
            filename (str, opcional): Caminho para salvar o modelo. Se None, usa o caminho padrão.
            
        Returns:
            bool: True se o modelo foi salvo com sucesso, False caso contrário.
        """
        if self.model is None:
            print("Erro: Não há modelo treinado para salvar.")
            return False
            
        if filename is None:
            filename = self.model_path
            
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        try:
            # Salvar modelo e scalers
            with open(filename, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler_X': self.scaler_X,
                    'scaler_y': self.scaler_y
                }, f)
            print(f"Modelo salvo com sucesso em: {filename}")
            return True
        except Exception as e:
            print(f"Erro ao salvar o modelo: {str(e)}")
            return False
            
    def load_model(self, filename=None):
        """
        Carrega um modelo MLP treinado e os scalers de um arquivo.
        
        Args:
            filename (str, opcional): Caminho para carregar o modelo. Se None, usa o caminho padrão.
            
        Returns:
            bool: True se o modelo foi carregado com sucesso, False caso contrário.
        """
        if filename is None:
            filename = self.model_path
            
        if not os.path.exists(filename):
            print(f"Arquivo de modelo não encontrado: {filename}")
            return False
            
        try:
            # Carregar modelo e scalers
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler_X = data['scaler_X']
                self.scaler_y = data['scaler_y']
            print(f"Modelo carregado com sucesso de: {filename}")
            return True
        except Exception as e:
            print(f"Erro ao carregar o modelo: {str(e)}")
            return False
    
    def optimize_all(self, Model, coeff, *args, save_model_after=True, use_saved_model=True):
        """
        Otimiza o modelo usando uma rede neural MLP.
        
        Args:
            Model (object): Instância do modelo a ser otimizado.
            coeff (array-like): Coeficientes iniciais para otimização.
            *args: Lista de parâmetros a serem otimizados.
            save_model_after (bool): Se True, salva o modelo após o treinamento.
            use_saved_model (bool): Se True, tenta usar um modelo salvo anteriormente.
            
        Returns:
            tuple: Coeficientes otimizados, erros associados e texto de saída.
        """
        print()
        print('--' * 50)
        print('MULTI-LAYER PERCEPTRON (MLP) MODE')
        print('--' * 50)
        print()
        
        try:
            # Carregar dados experimentais
            Vv, Id, voltages, _, _, _ = super().load_data(
                self.type_read, self.path_voltages,
                self.current_typic, self.scale_transfer,
                self.scale_output, self.type_curve
            )
            
            # Achatar os arrays de dados
            Vv_flat = np.ravel(Vv)
            Id_flat = np.ravel(Id)
            
            # Verificar se devemos usar um modelo salvo
            model_loaded = False
            if use_saved_model:
                model_loaded = self.load_model()
                if model_loaded:
                    print("Modelo MLP carregado com sucesso. Usando modelo pré-treinado.")
            
            # Se não conseguiu carregar o modelo ou não deve usar modelo salvo, treinar um novo
            if not model_loaded:
                # Gerar dados de treinamento
                print("Gerando dados de treinamento...")
                X_train, y_train, param_variations = self._generate_training_data(Model, coeff)
                
                # Criar e treinar o modelo MLP
                print("Treinando o modelo MLP...")
                self.model = self._create_model()
                self.model.fit(X_train, y_train)
                
                # Salvar o modelo treinado se solicitado
                if save_model_after:
                    self.save_model()
            
            # Avaliar diferentes conjuntos de parâmetros
            print("Avaliando parâmetros...")
            best_mse = float('inf')
            best_params = coeff.copy()
            
            # Se treinamos um novo modelo, avaliar os parâmetros gerados durante o treinamento
            if not model_loaded:
                for params in param_variations:
                    mse = self._evaluate_parameters(Model, params, Vv_flat, Id_flat)
                    if mse < best_mse:
                        best_mse = mse
                        best_params = params.copy()
            
            # Refinar os melhores parâmetros com otimização local
            print("Refinando os melhores parâmetros...")
            from scipy.optimize import minimize
            
            def objective(params):
                return self._evaluate_parameters(Model, params, Vv_flat, Id_flat)
            
            result = minimize(
                objective,
                best_params,
                method='Nelder-Mead',
                options={'maxiter': 100, 'disp': True}
            )
            
            coeff_opt = result.x
            
            # Calcular erro associado a cada parâmetro (usando bootstrap)
            n_bootstrap = 50
            bootstrap_predictions = []
            
            print("Calculando incertezas com bootstrap...")
            for _ in range(n_bootstrap):
                # Amostragem com reposição
                indices = np.random.choice(len(Vv_flat), len(Vv_flat), replace=True)
                Vv_bootstrap = Vv_flat[indices]
                Id_bootstrap = Id_flat[indices]
                
                # Otimização local para esta amostra
                def bootstrap_objective(params):
                    model_output = Model.calc_model(Vv_bootstrap, *params)
                    return np.mean((model_output - Id_bootstrap) ** 2)
                
                bootstrap_result = minimize(
                    bootstrap_objective,
                    coeff_opt,
                    method='Nelder-Mead',
                    options={'maxiter': 50}
                )
                
                bootstrap_predictions.append(bootstrap_result.x)
            
            # Calcular desvio padrão das previsões bootstrap
            bootstrap_predictions = np.array(bootstrap_predictions)
            error_coeff = np.std(bootstrap_predictions, axis=0)
            
            # Gerar texto de saída
            text_verbose = f"MLP optimization completed.\n"
            if model_loaded:
                text_verbose += f"Used pre-trained model.\n"
            text_verbose += f"Final MSE: {best_mse:.6e}\n"
            text_verbose += f"Parameters: {coeff_opt}\n"
            text_verbose += f"Errors: {error_coeff}\n"
            
            return coeff_opt, error_coeff, text_verbose
            
        except Exception as e:
            print()
            print('--' * 50)
            print(f"Erro na otimização MLP: {str(e)}")
            print('--' * 50)
            print()
            return coeff, np.zeros_like(coeff), str(e)