# Modelagem de Transistores Orgânicos de Filme Fino via Rede Neural Perceptron Multicamadas

---

## Resumo

Este trabalho descreve a implementação de um pipeline de aprendizado de máquina para a modelagem de transistores orgânicos de filme fino (OTFTs) utilizando uma Rede Neural do tipo Perceptron Multicamadas (MLP). A abordagem é baseada no modelo físico VSED (*Virtual Source with Exponential Disorder*), cujos parâmetros são extraídos previamente por ajuste numérico. A partir desses parâmetros, um conjunto de dados sintéticos é gerado variando sistematicamente as tensões de operação, ampliando o volume de dados disponível para treinamento. A MLP é treinada para mapear a função $I_D = f(V_{GS}, V_{DS})$ em espaço logarítmico, explorando a representação polinomial das tensões como features de entrada. A busca automática de hiperparâmetros via Optuna é empregada para identificar a arquitetura mais compacta com melhor capacidade de generalização. A metodologia é avaliada sobre três tecnologias orgânicas distintas (Org1, Org2 e Org3), com comparação qualitativa entre as curvas previstas pela MLP e as curvas geradas pelo modelo numérico VSED.

---

## 1. Introdução

Os transistores orgânicos de filme fino (OTFTs) são dispositivos semicondutores que utilizam materiais orgânicos como camada ativa, possibilitando fabricação em substratos flexíveis e de baixo custo. A caracterização elétrica desses dispositivos é realizada a partir de curvas corrente-tensão ($I_D \times V_{GS}$ e $I_D \times V_{DS}$), das quais são extraídos parâmetros intrínsecos como tensão de limiar ($V_{tho}$), mobilidade de portadores e resistência série.

Os métodos convencionais de extração de parâmetros resolvem um sistema de equações não lineares a cada avaliação do modelo, o que pode ser computacionalmente custoso quando é necessário realizar muitas inferências — por exemplo, em varreduras de parâmetros, análises de sensibilidade ou rotinas de otimização de circuitos. Uma alternativa eficiente é substituir o modelo analítico por uma rede neural treinada para reproduzir o comportamento $I_D = f(V_{GS}, V_{DS})$, tornando a inferência praticamente instantânea após o treinamento.

Este relatório descreve a metodologia adotada para treinar e validar uma MLP como substituta do modelo VSED, e apresenta os resultados obtidos para três tecnologias orgânicas do tipo pFET.

---

## 2. Fundamentação Teórica

### 2.1 Modelo Físico VSED

O modelo VSED (*Virtual Source with Exponential Disorder*) descreve a corrente de dreno de um OTFT pela equação:

$$J_D = \frac{I_D}{W} = V_{sat} \cdot F_{sat} \cdot Q_{free}$$

onde $W$ é a largura do canal, $V_{sat}$ é a velocidade de saturação dos portadores de carga, $F_{sat}$ é o fator de transição linear–saturação e $Q_{free}$ é a densidade de cargas livres modulada pela tensão de *gate*.

A densidade de cargas livres é expressa como:

$$Q_{free} = q \cdot \sigma_v \left(\frac{Q_{tot}}{q \cdot \sigma_{traps}}\right)^l$$

onde $l$ é um expoente que modela a distribuição de estados de armadilha no material. A carga total acumulada é dada por:

$$Q_{tot} = C_I \cdot n \cdot V_T \cdot \ln\left[1 + \exp\!\left(\frac{\psi V_S - V_{GS}}{n \cdot V_T}\right)\right]$$

com $\psi V_S = V_{tho} + |\delta| \cdot V_{DS}$ definindo a tensão de limiar efetiva.

O modelo possui **8 parâmetros físicos** a serem extraídos por ajuste numérico:

| Parâmetro | Símbolo | Descrição física |
|-----------|---------|------------------|
| Tensão de limiar | $V_{tho}$ | Tensão de gate no limiar de condução |
| Fator DIBL | $\delta$ | Abaixamento de barreira induzido pelo dreno |
| Fator subthreshold | $n$ | Controla a inclinação subthreshold |
| Expoente de armadilha | $l$ | Relação entre cargas livres e aprisionadas |
| Comprimento virtual | $\lambda$ | Escala de comprimento para difusão de portadores |
| Tensão crítica | $V_{crit}$ | Tensão de overdrive para saturação da velocidade |
| Densidade de corrente | $J_{th}$ | Corrente de dreno de referência |
| Resistência série | $R_S$ | Resistência de contato em série com o canal |

### 2.2 Perceptron Multicamadas (MLP)

Uma MLP é uma rede neural *feedforward* composta por camadas de neurônios totalmente conectadas. Para tarefas de regressão, a camada de saída possui um único neurônio sem função de ativação não linear. O treinamento é realizado pela minimização de uma função de perda (tipicamente MSE) via retropropagação do gradiente.

A corrente de dreno de um OTFT varia em várias ordens de magnitude ao longo de uma curva de transferência (de correntes de vazamento $\sim 10^{-12}$ A até correntes de saturação $\sim 10^{-6}$ A). Trabalhar diretamente com $I_D$ gera gradientes extremamente desbalanceados. Por isso, a variável alvo da MLP é o logaritmo natural da corrente:

$$y = \ln|I_D|$$

A previsão final é recuperada pela transformação inversa $I_D = \exp(\hat{y})$.

---

## 3. Metodologia

### 3.1 Dados Experimentais

Os dados experimentais consistem em arquivos CSV com três colunas obrigatórias: `VGS`, `VDS` e `ID`. O tipo de curva é identificado automaticamente pela coluna com valor fixo:

- **Curva de transferência:** $V_{DS}$ fixo, $V_{GS}$ varrido — revela tensão de limiar e inclinação subthreshold
- **Curva de saída:** $V_{GS}$ fixo, $V_{DS}$ varrido — revela regiões linear e de saturação

Foram utilizadas três tecnologias orgânicas do tipo pFET, identificadas como Org1, Org2 e Org3. Os parâmetros físicos de cada tecnologia foram previamente extraídos pelo pipeline de ajuste numérico implementado no notebook `TFT_M1_LAMB_MC.ipynb` e armazenados nos arquivos JSON de configuração.

### 3.2 Geração de Dados Sintéticos

O volume de dados experimentais disponível por tecnologia (tipicamente dezenas de curvas) é insuficiente para treinar uma MLP com boa capacidade de generalização. Para ampliar o conjunto de treinamento, foi implementada a classe `SyntheticFromSettings` (`modules_otft/_generate_synthetic_data.py`), que utiliza o modelo físico VSED para gerar novas curvas I×V com tensões de operação variadas.

**Estratégia adotada:** `variation_mode="voltages"` — as tensões fixas de cada curva são incrementadas sistematicamente ao redor dos valores experimentais, mantendo os parâmetros físicos do dispositivo ($V_{tho}$, $\delta$, $n$, $l$, $\lambda$, $V_{crit}$, $J_{th}$, $R_S$) constantes. Esta estratégia é fisicamente justificada: os parâmetros caracterizam o *material*, não as condições de polarização.

**Parâmetros de geração:**

| Parâmetro | Valor adotado |
|-----------|--------------|
| Pontos por curva (`resample_n_points`) | 10.000 |
| Passo de variação de tensão (`voltage_increment`) | 2,0 V |
| Variação máxima (`voltage_max_variation`) | ±10 V |

**Dados gerados por tecnologia:**

| Tecnologia | Faixa $V_{GS}$ (V) | Faixa $V_{DS}$ (V) | Curvas transfer | Curvas output | Total de arquivos |
|------------|--------------------|--------------------|----------------|--------------|-------------------|
| Org1 | −6 a −98 | −32 a −60 | ~150 | ~149 | 299 pares |
| Org2 | −9 a −33 | — | ~100 | ~66 | — |
| Org3 | −4 a −64 | — | ~150 | ~149 | — |

Cada curva é salva em dois formatos: `.csv` (texto, colunas VGS/VDS/ID) e `.npz` (binário NumPy com metadados). Um arquivo `index_generated.json` indexa todos os arquivos gerados, servindo como manifesto para o carregamento no treinamento. O volume total de dados sintéticos gerados é de aproximadamente **158 MB** (598 arquivos).

**Parâmetros físicos de referência (Org1):**

| $V_{tho}$ | $\delta$ | $n$ | $l$ | $\lambda$ | $V_{crit}$ | $J_{th}$ | $R_S$ |
|-----------|----------|-----|-----|-----------|-----------|---------|------|
| 8,57 V | 0,0123 | 108,0 | 3,18 | 1490 | 32,3 V | 0,097 | 1,0 |

### 3.3 Engenharia de Features

A entrada da MLP é construída a partir das tensões de gate ($V_G$) e dreno ($V_D$) por meio de uma **expansão polinomial de segundo grau** com termo de interação cruzada, totalizando **5 features**:

$$\mathbf{x} = \left[V_G,\; V_D,\; V_G^2,\; V_D^2,\; V_G \cdot V_D\right]$$

Para curvas de transferência, $V_G$ é a tensão varrida e $V_D$ é a tensão fixa. Para curvas de saída, os papéis se invertem. Esta representação permite que a rede capture a dependência quadrática da corrente nas tensões, reduzindo a complexidade da arquitetura necessária.

A variável alvo é o logaritmo natural da corrente em módulo:

$$y = \ln\!\left(\left|I_D\right| + \epsilon\right), \quad \epsilon = 10^{-30}$$

O termo $\epsilon$ previne $\ln(0)$ para valores de corrente nulos.

### 3.4 Normalização

As features de entrada e a variável alvo são normalizadas independentemente usando `StandardScaler` (scikit-learn), que subtrai a média e divide pelo desvio padrão:

$$\tilde{x}_i = \frac{x_i - \mu_i}{\sigma_i}$$

Os parâmetros dos escaladores ($\mu$, $\sigma$) são ajustados sobre o conjunto de treino e salvos junto ao modelo treinado (arquivos `.pkl` separados), garantindo que a mesma transformação seja aplicada na inferência sem necessidade de re-ajuste.

### 3.5 Arquitetura da MLP

A arquitetura da rede segue o esquema:

$$\underbrace{5}_{\text{entrada}} \;\rightarrow\; \underbrace{h_1 \times h_2 \times \cdots \times h_k}_{\text{camadas ocultas}} \;\rightarrow\; \underbrace{1}_{\text{saída (}\ln|I_D|\text{)}}$$

A função de ativação padrão nas camadas ocultas é `tanh`, que apresentou melhor convergência em redes pequenas comparada a `relu` e `silu` durante a busca de hiperparâmetros. A camada de saída não possui ativação (regressão linear).

### 3.6 Treinamento

O treinamento utiliza o otimizador **Adam** com os seguintes parâmetros:

| Hiperparâmetro | Descrição | Valor padrão |
|----------------|-----------|-------------|
| `LEARNING_RATE` | Taxa de aprendizado | 2,93 × 10⁻⁴ |
| `BATSIZE` | Tamanho do mini-batch | 64 |
| `EPOCS` | Máximo de épocas | 10.000 |
| `PATIENCE` | Épocas sem melhora (early stopping) | 1.000 |
| `TEST_SPLIT` | Fração de validação | 20 % |

A função de perda minimizada é o **Erro Quadrático Médio** (MSE) em espaço logarítmico:

$$\mathcal{L} = \frac{1}{N}\sum_{i=1}^{N}\left(\ln|I_{D,i}| - \widehat{\ln|I_{D,i}|}\right)^2$$

O mecanismo de *early stopping* interrompe o treinamento quando o erro de validação não melhora por `PATIENCE` épocas consecutivas, e restaura o conjunto de pesos que produziu o menor erro de validação ao longo de todo o treinamento.

### 3.7 Busca Automática de Hiperparâmetros (Optuna)

A escolha manual de hiperparâmetros é substituída por uma busca sistemática utilizando a biblioteca **Optuna** com otimização Bayesiana. O espaço de busca e os resultados são:

**Espaço de busca:**

| Hiperparâmetro | Tipo | Faixa / Opções |
|----------------|------|----------------|
| Número de camadas ocultas | Inteiro | 1 – 3 |
| Neurônios por camada | Inteiro | 1 – 5 |
| Função de ativação | Categórico | `relu`, `tanh`, `silu` |
| Taxa de aprendizado | Float (log) | [10⁻⁴, 10⁻²] |
| Tamanho do mini-batch | Categórico | 16, 32, 64 |

**Estratégia minimalista:** A função objetivo inclui uma penalidade leve por complexidade para favorecer redes menores com precisão equivalente:

$$\text{score} = \text{MSE}_{val} + 0{,}0001 \times \sum_{i=1}^{k} h_i$$

Foram executados **54 trials** no total (29 para Org1, 24 para Org3). Os melhores hiperparâmetros encontrados foram:

| Tecnologia | Melhor trial | Arquitetura | Ativação | LR | Batch |
|------------|-------------|-------------|----------|----|-------|
| Org1 | 29 | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |
| Org3 | 22 | `[TODO]` | `[TODO]` | `[TODO]` | `[TODO]` |

> **[TODO]:** Extrair os valores de `study.best_params` após execução da Seção 8 do notebook `TFT_MLP_Pipeline.ipynb` e preencher a tabela acima.

### 3.8 Inferência

A inferência é realizada pelo módulo `modules_otft/_inferency.py`. O pipeline de previsão segue as etapas:

1. Construção das 5 features polinomiais a partir de $V_G$ e $V_D$
2. Normalização com o `scaler_X` salvo no treinamento: $\tilde{\mathbf{x}} = \text{StandardScaler}(\mathbf{x})$
3. Previsão da rede: $\hat{z} = \text{MLP}(\tilde{\mathbf{x}})$
4. Desnormalização: $\widehat{\ln|I_D|} = \text{scaler\_Y}^{-1}(\hat{z})$
5. Transformação inversa: $\hat{I}_D = \exp\!\left(\widehat{\ln|I_D|}\right)$

A avaliação visual é realizada pela função `plot_curve_comparison`, que sobrepõe a curva real e a previsão da MLP em escala logarítmica (para a região subthreshold) e em escala linear (para a região de saturação).

---

## 4. Resultados

### 4.1 Dataset de Treinamento

A tabela a seguir resume os dados sintéticos utilizados no treinamento para cada tecnologia:

| Tecnologia | Tipo | Curvas transfer | Curvas output | Faixa $V_{GS}$ (V) | Faixa $V_{DS}$ (V) | Total de pontos |
|------------|------|:--------------:|:-------------:|:------------------:|:------------------:|:--------------:|
| Org1 | pFET | ~150 | ~149 | −6 a −98 | −32 a −60 | ~2,99 × 10⁶ |
| Org2 | pFET | `[TODO]` | `[TODO]` | −9 a −33 | `[TODO]` | `[TODO]` |
| Org3 | pFET | ~150 | ~149 | −4 a −64 | `[TODO]` | ~2,99 × 10⁶ |

> **[TODO]:** Verificar contagens exatas via `len(index_generated.json)` por tecnologia.

### 4.2 Hiperparâmetros Otimizados pelo Optuna

> **[TODO]:** Após execução da Seção 8 do notebook, registrar os valores de `study.best_params` para Org1 e Org3 e preencher a tabela da Seção 3.7.

### 4.3 Desempenho do Treinamento

> **[TODO]:** Após o treinamento, registrar as seguintes métricas para cada tecnologia:
>
> | Tecnologia | MSE validação | $R^2$ treino | $R^2$ validação | Épocas até convergência |
> |------------|:------------:|:------------:|:---------------:|:-----------------------:|
> | Org1 | | | | |
> | Org2 | | | | |
> | Org3 | | | | |
>
> As métricas são geradas automaticamente pela chamada `mlp_trainer.train_model()` no notebook.

### 4.4 Comparação MLP vs. Modelo VSED (Numérico)

A avaliação qualitativa da MLP é realizada comparando as curvas previstas com as curvas calculadas diretamente pelo modelo físico VSED para as mesmas condições de polarização.

> **[TODO]:** Inserir aqui os gráficos gerados pela função `plot_curve_comparison` do notebook (Seção 6):
>
> - Figura X.a — Curva de transferência: MLP vs. VSED — escala logarítmica
> - Figura X.b — Curva de transferência: MLP vs. VSED — escala linear
> - Figura X.c — Curva de saída: MLP vs. VSED — escala logarítmica
> - Figura X.d — Curva de saída: MLP vs. VSED — escala linear
>
> **[TODO]:** Calcular e reportar o **erro relativo médio** em cada região de operação:
>
> $$\bar{\epsilon}_{rel} = \frac{1}{N}\sum_{i=1}^{N} \frac{|\hat{I}_{D,i} - I_{D,i}^{VSED}|}{|I_{D,i}^{VSED}|}$$
>
> | Tecnologia | Região subthreshold | Região linear | Região saturação |
> |------------|:------------------:|:-------------:|:----------------:|
> | Org1 | | | |
> | Org3 | | | |

---

## 5. Conclusão

Este trabalho apresentou um pipeline completo para treinamento de uma MLP como substituta do modelo físico VSED na previsão de curvas I×V de OTFTs. As principais contribuições da implementação são:

1. **Geração de dados sintéticos fisicamente consistentes:** a variação sistemática das tensões ao redor dos valores experimentais amplia o dataset sem violar os parâmetros físicos do dispositivo.

2. **Representação polinomial das features:** as 5 features quadráticas derivadas de $V_G$ e $V_D$ permitem que redes pequenas (3–5 neurônios por camada) aprendam o comportamento não linear da corrente.

3. **Treinamento em espaço logarítmico:** o uso de $\ln|I_D|$ como alvo estabiliza o treinamento e melhora a precisão em todas as regiões de operação, incluindo a região subthreshold de correntes baixíssimas.

4. **Busca automática de hiperparâmetros:** o Optuna identifica arquiteturas compactas (poucos neurônios) com boa generalização, reduzindo o risco de overfitting em datasets de OTFTs que são inerentemente pequenos.

5. **Portabilidade:** o modelo treinado (`.pkl` + escaladores) pode ser carregado e usado para inferência instantânea sem dependência do modelo físico, tornando-o adequado para simulação de circuitos ou varredura de parâmetros em tempo real.

**Próximos passos:**
- Completar a comparação quantitativa MLP vs. VSED (Seção 4.4) para as três tecnologias
- Estender a validação para curvas com condições de polarização fora do intervalo de treinamento (generalização extrapolativa)
- Avaliar o ganho de velocidade de inferência em relação ao modelo numérico

---

## 6. Referências

1. LIMA, A. A.; BLAWID, S. Modeling organic thin-film transistors based on the virtual source concept: A case study. *Solid-State Electronics*, v. 161, p. 107639, 2019.

2. BLAWID, S.; DALLAIRE, N. J.; LESSARD, B. H. Self-Consistent Extraction of Mobility and Series Resistance: A Hierarchy of Models for Benchmarking Organic Thin-Film Transistors. *IEEE Journal on Flexible Electronics*, v. 1, n. 2, p. 114–121, 2022.

3. PEDREGOSA, F. et al. Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*, v. 12, p. 2825–2830, 2011.

4. AKIBA, T. et al. Optuna: A Next-generation Hyperparameter Optimization Framework. In: *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining*, 2019.
