# Robust Benchmarking Strategy for Organic Thin-Film Transistors
[![NPM](https://img.shields.io/npm/l/react)](https://github.com/RodrigoSantosB/speech-recognition-signal-project/blob/main/LICENSE) 

# About The Project 
Transistores orgânicos de película fina (OTFTs) utilizam semicondutores orgânicos para gerar respostas eletrônicas. Operando com três terminais, esses dispositivos controlam o fluxo de corrente entre os eletrodos de fonte e dreno, aplicando tensão a um eletrodo de porta. A tecnologia OTFT é avaliada por meio de relatórios de parâmetros importantes, como tensão limite, mobilidade do portador de carga e resistência em série. No entanto, os métodos convencionais de extração de parâmetros adaptados para transistores de silício podem produzir resultados imprecisos para OTFTs.

A aplicação visa a determinação dos parâmetros intrínsecos do transistor, utilizando dados experimentais de corrente e tensão. Por meio dessa abordagem, torna-se viável avaliar a qualidade do ajuste de curva, empregando métricas como o erro quadrático médio e o erro relativo. Essa análise reveste-se de significância particular na definição de um padrão de referência intra e intertecnologias, empregadas como substrato. Além disso, nossa alpicação tem o objetivo de ser de fácil uso por ter sido desenvolvida em python, adicionalmente pode ser executada no ambiente em nuvem (Google Colaboratory)


## **OBJETIVOS**
A otimização de parâmetros dos dispositivos TFTs é um processo crucial na fabricação de eletrônicos de filme fino. A principal razão para realizar essa otimização é melhorar o desempenho dos dispositivos, tornando-os mais eficientes, confiáveis e econômicos. O objetivo é otimizar parâmetros específicos dentro de um modelo que fornecerá os melhores resultados para a produção desses dispositivos. Uma forma simplificada de como o modelo opera pode ser descrita pela relação $I_D = F(V_{GS}, V_{DS})$, onde:

- **$I_D$**: Corrente elétrica que flui entre os terminais da fonte e do dreno de um transistor de filme fino (TFT).
- **$V_{GS}$**: Tensão aplicada ao terminal da porta do transistor, que controla a corrente que flui entre o terminal da fonte e o terminal do dreno.
- **$V_{DS}$**: Tensão aplicada ao terminal do dreno do transistor, que determina a corrente que flui entre os terminais da fonte e do dreno quando a tensão da porta é mantida constante.

As tensões $V_{GS}$ e $V_{DS}$ são fundamentais para a operação do transistor TFT e para a otimização de seus parâmetros, que podem ser obtidos a partir das curvas de transferência e saída do dispositivo. A partir dessas operações, é possível obter informações sobre seus parâmetros, como $V_{tho}$, $l$, $n$, $J_D$, $\delta$, $R_S$, $\lambda$ e $V_{crit}$. O modelo, ao limitar esses parâmetros, permite ajustar todos os valores simultaneamente.

A otimização dos parâmetros é realizada empregando um solucionador de mínimos quadrados não linear, que permite ajustar os parâmetros de forma eficiente e sem ambiguidade. Dessa maneira, é possível obter uma melhor compreensão do comportamento do dispositivo TFT e otimizar sua operação para aplicações específicas. Além disso, a otimização dos parâmetros é fundamental para garantir a qualidade e confiabilidade do dispositivo, bem como sua integração em circuitos eletrônicos complexos.

## **DESCRIÇÃO DO MODELO**
TFTs são chaves eletrônicas onde a corrente flui da fonte para o terminal de dreno, controlada pela tensão aplicada ao terminal da porta, veja a Fig. 1. Os modelos de referência devem reproduzir consistentemente as características de corrente-tensão dos TFTs com um número mínimo de parâmetros. Isto significa que os parâmetros do modelo podem ser extraídos de forma confiável e inequívoca das curvas experimentais.

A representação física mais simples da corrente de dreno em um TFT envolve cargas móveis moduladas pela tensão porta-fonte, VGS, movendo-se a uma velocidade influenciada pela tensão dreno-fonte, VDS. Para campos elétricos fonte-dreno muito altos, a velocidade do portador de carga satura. À medida que os transportadores se movem da fonte para o dreno, eles encontram uma barreira potencial, que atua como um gargalo para o transporte de carga. A taxa limitada de injeção de carga no topo desta barreira potencial pode ser descrita como uma fonte virtual (VS).

<p align="center">
<img src="https://github.com/RodrigoSantosB/Model_OTFT/blob/master/figures/semicondutor.png" alt="Fig 1 Seções transversais esquemáticas de (a) um coplanar e (b) um OTFT escalonado. As linhas tracejadas mostram os caminhos atuais esperados." height="300" width="800">
</p>

O modelo matemático ao qual os dados experimentais serão submetidos consiste em um conjunto de equações, onde cada variável possui seu grau de importância e contribuição. A seguir, apresenta-se a prototipagem deste modelo, juntamente com a descrição de cada parâmetro:

A corrente de dreno de um TFT consiste em cargas móveis $Q_{free}$ moduladas pela tensão de porta, que se movem com uma velocidade modulada pela tensão de dreno. Em altos campos elétricos de fonte para dreno, a velocidade dos portadores de carga satura em um valor $V_{sat}$. No entanto, os portadores de carga precisam superar uma barreira potencial no caminho da fonte para o dreno, representando um gargalo para o transporte dos portadores de carga. A taxa limitada de injeção de carga no topo da barreira de potencial de estrangulamento pode ser denominada como uma fonte virtual (VS). O modelo $V_{sed}$ modificado sugere uma forma específica da corrente de dreno por largura de porta $W$ na VS:

$$J_D = \frac{I_D}{W} = V_{sat}.F_{sat}.Q_{free} $$

onde:

- $J_D$ é a densidade de corrente de dreno por unidade de largura,
- $I_D$ é a corrente de dreno,
- $W$ é a largura da porta,
- $V_{sat}$ é a velocidade de saturação dos portadores de carga,
- $F_{sat}$ é o fator de saturação,
- $Q_{free}$ são as cargas livres móveis moduladas pela tensão de porta.

Este modelo destaca a importância da velocidade de saturação dos portadores de carga e da barreira potencial como fatores críticos no desempenho dos TFTs.

Algumas partículas carregadas não são móveis. Em certos casos, uma cauda exponencial de estados de aprisionamento, que se estende da borda da banda de valência até o band gap, pode relacionar a densidade livre e total de portadores de carga por uma lei de potência. Isso ocorre porque todos os estados são ocupados de acordo com o mesmo quase-nível de Fermi, como mostrado na Equação (B4) em [8] e sua derivação anterior. Assim, a equação é expressa como:

$$Q_{free} = q.σ_v.\biggl(\frac{Q_{tot}}{q.σ_{traps}}\biggr)^l$$

onde:

- $Q_{free}$ é a densidade de portadores de carga livres,
- $Q_{tot}$ é a densidade total de portadores de carga,
- $q$ é a carga elementar,
- $\sigma_v$ é um fator de proporcionalidade relacionado aos estados livres,
- $\sigma_{traps}$ é um fator de proporcionalidade relacionado aos estados de aprisionamento,
- $l$ é um expoente característico que descreve a relação entre os estados livres e aprisionados.

Esta equação ilustra a dependência da densidade de portadores de carga livres em relação à densidade total de portadores, modulada pelos fatores de proporcionalidade $\sigma_v$ e $\sigma_{traps}$, e o expoente $l$, refletindo a distribuição dos estados de aprisionamento no material.

Neste contexto,  $σ_V$ e $σ_{traps}$  representam a densidade dos estados de valência e armadilhas em uma única camada do semicondutor no $V_S$, respectivamente. O valor do expoente $l$ é determinado pela razão da "temperatura" efetiva que define a distribuição exponencial de energia dos estados de armadilhas e a temperatura do dispositivo, originada da distribuição de energia de Boltzmann dos portadores de carga livre. No entanto, como a distribuição exata de armadilhas é geralmente desconhecida, $l$ é tratado como um parâmetro do modelo. A distinção entre portadores de carga livres e aprisionados, conforme apresentado na Equação (2), é a principal adaptação do framework VSED para materiais de filmes finos proposto neste trabalho.

Para um semicondutor esgotado, espera­se um acúmulo exponencial de lacunas (cargas positivas) com o aumento do campo de porta, que cessa quando a blindagem substancial pela folha de carga acumulada se estabelece. A seguinte expressão fenomenológica proposta pela primeira vez em [9] é empregada:
$$Q_{tot} = C_I.n.V_T.ln \biggr[ 1 + e^{ψ.V_S − V_{GS}} . n . V_T \biggr],$$
$$ψ.V_S = V_{tho} + |δ|.V_{DS}$$

A capacitância do isolador da porta depende da constante dielétrica ε e da espessura tI do isolador: $C_I = \frac{ε}{t_I}$. A tensão térmica é representada por $V_T = \frac{kT}{q}$. A transição da acumulação fraca para forte é modelada pelos parâmetros $n, V_{th0}$ e $δ$ , sendo que o parâmetro $n$ é influenciado pelo carregamento da região semicondutora adjacente à interface do isolador da porta, preenchendo estados de superfície e afetando a taxa de flexão de banda com a polarização da porta.

O potencial da interface se torna independente de VGS quando atinge um valor de polarização $ψ.V_S$, também conhecido como tensão limiar. Isso permite parametrizar o controle da barreira de potencial pela polarização da porta em TFTs. O parâmetro $ψ.V_S$ representa a polarização crítica para a qual o potencial em $V_S$ se torna independente da tensão da porta. Durante o acúmulo de lacunas na interface do isolador da porta, os parâmetros n e $l$ descrevem o carregamento dos estados de armadilhas, e a escala de tensão para o aumento exponencial da corrente de dreno com a polarização da porta é dada por $(\frac{n}{l}).V_T$ no modelo VSED. O parâmetro $δ$ não representa necessariamente um DIBL (drain-induced barrier lowering).

A velocidade de injeção de cargas $Q_{free}$ no canal do transistor é representada por $V_{inj} = V_{sat}.F_{sat}$. É comum estimar a corrente de dreno em TFTs como um movimento de deriva dos portadores de carga injetados, mas isso pode levar a uma conclusão equivocada sobre a velocidade de saturação $V_{sat}$. Enquanto em regiões de alto campo elétrico a velocidade de saturação é igual à velocidade de saturação no corpo do semicondutor, em regiões de baixo campo elétrico a velocidade de saturação é definida pela velocidade térmica unidirecional do quase potencial de Fermi e não do potencial eletrostático. Este conceito é discutido em [10]:
$$V_{sat} = \frac{2D}{\bar{λ}_{free}}$$ = $$\frac{2.μ.V_T}{\bar{λ}_{free}}$$

que é aqui parametrizado pelo coeficiente de difusão $D$ e pode estar relacionado com a mobilidade de deriva $μ$ através da relação de Einstein. Em baixa polarização de dreno, a difusão do portador de carga é o mecanismo de transporte dominante em grande parte do TFT e não apenas no $V_S$. O comprimento característico na Eq. (5) não será mais dado pelo caminho livre
médio $\bar{λ}_{free}$ mas pelo comprimento de difusão. Uma vez que apenas portadores de carga de um único tipo são injetados em um semicondutor basicamente intrínseco, o comprimento de difusão pode ser muito grande e comparável à dimensão do dispositivo dada pelo comprimento da porta $L_G$. $F_{sat}$ introduz uma escala de comprimento $λ = \frac{L_G}{\bar{λ}_{free}}$ , que efetivamente substitui ${\bar{λ}_{free}}$ → $L_G$ em baixa polarização de drenagem.

A função restante $F_{sat}$ descreve a drenagem das lacunas acumulados. Para TFTs de canal longo, a teoria de difusão e emissão [11, 5] representa uma abordagem interessante para determinar $F_{sat}$:

$$F_{sat} = \frac{1}{1 + 2t}.\frac{1-e^{\Bigl(\frac{-V_{SD}}{V_T}\Bigl)}}{1+e^{\Bigl(\frac{-V_{SD}}{V_T}\Bigl)}.\frac{1}{1+2t}}$$

Para uma polarização de dreno que exceda significativamente a tensão térmica, a função de transição é descrita por $F_{sat} = \frac{1}{1 + 2t}$. O fator de probabilidade crítico $t$ é determinado por um fator de Boltzmann médio na região do canal controlada pela porta e pode ser obtido a partir do perfil de potencial específico. Para dispositivos de canal longo, uma forma analítica foi proposta, que pode ser encontrada nas equações (4) a (12) do artigo [11].

$$ t = \frac{2.λ}{m^{2}(1-η^{2})}.\Bigl[(1-m.η).e^{-m(1-η)} -(1-m) \Bigl]$$

$$ η = 1 − tanh\Bigl(\frac{V_{SD}}{mV_T}\Bigl)$$

$$m = \frac{2.\frac{V_{Gt}}{V_T}}{1+ \sqrt{\frac{2.V_{Gt}}{{V_{crit}}}}}$$

$$ V_{Gt} = \frac{Q_{tot}}{CI}$$


Note que, um aumento no overdrive do transistor leva a uma região de difusão espaçosa e muda o início da saturação para uma polarização de dreno maior. Na polarização de porta grande, o aumento necessário na tensão de saturação diminui e se transforma em crescimentos de raiz quadrada para $V_{Gt} > V_{crit}$. Observe que a velocidade de saturação dada pela Eq. (5) só é alcançada para
ambos, grande $V_{SG}$ (baixa barreira) e grande $V_{SD}$ (carga afundar). Em geral, o comprimento crítico para difusão que substitui $λ_{free}$ na Eq. (5) é uma fração de $L_G$ dependente na tensão da porta. O $V_{Gt}$ necessário para atingir a velocidade máxima de injeção dada pela velocidade térmica unidirecional diminui com $L_G$.


* A primeira equação é usada para calcular o tempo de vida médio de uma partícula instável. Ela relaciona o tempo de vida médio ($t$) de uma partícula instável com sua massa (m), sua energia de ligação ($λ$) e seu fator de amortecimento ($η$). A equação é uma expressão matemática da lei de decaimento exponencial da partícula.

* A segunda equação é usada para calcular o coeficiente de reflexão de uma onda em um transistor MOSFET (transistor de efeito de campo de porta isolada metal-óxido-semicondutor). A equação relaciona o coeficiente de reflexão ($η$) com a diferença de potencial entre o dreno e a fonte ($V_{SD}$), a temperatura ambiente ($V_T$) e um parâmetro do dispositivo (m).

* A terceira equação é usada em dispositivos semicondutores para calcular o fator de inclinação de um transistor MOSFET. O fator de inclinação é uma medida da eficiência do transistor em ligar e desligar rapidamente. A equação relaciona o fator de inclinação (m) com a tensão de limiar do transistor ($V_{GT}$), uma constante crítica de tensão ($V_{crit}$) e a temperatura ambiente ($V_T$).

* A quarta equação é usada para calcular a tensão de limiar de um transistor MOSFET. A tensão de limiar é a tensão mínima necessária para ligar o transistor. A equação relaciona a tensão de limiar ($V_{GT}$) com a carga total ($Q_{tot}$) armazenada na porta do transistor, a capacitância ($C$) da porta e a corrente ($I$) aplicada à porta.

Compreendendo a relação e a composição de cada equação, podemos implementar essas expressões matemáticas em código para analisar os resultados obtidos. O objetivo é otimizar os coeficientes $J_T$, $V_{tho}$, $\delta$, $l$, $n$, $\lambda$, e $V_{crit}$, que são fundamentais na modelagem das equações.

Definições dos coeficientes:

- **$J_T$** (Coeficiente de temperatura de Junção): Representa a variação da temperatura na junção de um dispositivo eletrônico, importante para o projeto e operação adequados desses dispositivos.
- **$V_{tho}$** (Tensão de Threshold): A tensão mínima necessária para iniciar a condução de corrente em dispositivos como transistores MOSFET, determinada pelas propriedades do material semicondutor.
- **$\delta$** (Espessura da camada de difusão): A espessura da camada de material semicondutor dopado depositada na superfície de um substrato semicondutor.
- **$l$** (Comprimento de difusão): A distância que a dopagem do material semicondutor se difunde na superfície do substrato durante a fabricação.
- **$n$** (Coeficiente de idealidade do diodo): Descreve a relação entre corrente elétrica e tensão em um diodo, usado para calcular a queda de tensão em diferentes níveis de corrente.
- **$\lambda$** (Coeficiente de queda de tensão): Descreve a queda de tensão em um dispositivo eletrônico em relação à corrente elétrica que passa por ele.
- **$V_{crit}$** (Tensão crítica): A tensão máxima que um dispositivo pode suportar sem danificar sua estrutura, determinada pelas propriedades dos materiais semicondutores.






