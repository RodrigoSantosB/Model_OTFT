# Robust Benchmarking Strategy for Organic Thin-Film Transistors
[![NPM](https://img.shields.io/npm/l/react)](https://github.com/RodrigoSantosB/speech-recognition-signal-project/blob/main/LICENSE) 

# About The Project 
Transistores orgânicos de película fina (OTFTs) utilizam semicondutores orgânicos para gerar respostas eletrônicas. Operando com três terminais, esses dispositivos controlam o fluxo de corrente entre os eletrodos de fonte e dreno, aplicando tensão a um eletrodo de porta. A tecnologia OTFT é avaliada por meio de relatórios de parâmetros importantes, como tensão limite, mobilidade do portador de carga e resistência em série. No entanto, os métodos convencionais de extração de parâmetros adaptados para transistores de silício podem produzir resultados imprecisos para OTFTs.

A aplicação visa a determinação dos parâmetros intrínsecos do transistor, utilizando dados experimentais de corrente e tensão. Por meio dessa abordagem, torna-se viável avaliar a qualidade do ajuste de curva, empregando métricas como o erro quadrático médio e o erro relativo. Essa análise reveste-se de significância particular na definição de um padrão de referência intra e intertecnologias, empregadas como substrato.

## **DESCRIÇÃO DO MODELO**
TFTs são chaves eletrônicas onde a corrente flui da fonte para o terminal de dreno, controlada pela tensão aplicada ao terminal da porta, veja a Fig. 1. Os modelos de referência devem reproduzir consistentemente as características de corrente-tensão dos TFTs com um número mínimo de parâmetros. Isto significa que os parâmetros do modelo podem ser extraídos de forma confiável e inequívoca das curvas experimentais.

A representação física mais simples da corrente de dreno em um TFT envolve cargas móveis moduladas pela tensão porta-fonte, VGS, movendo-se a uma velocidade influenciada pela tensão dreno-fonte, VDS. Para campos elétricos fonte-dreno muito altos, a velocidade do portador de carga satura. À medida que os transportadores se movem da fonte para o dreno, eles encontram uma barreira potencial, que atua como um gargalo para o transporte de carga. A taxa limitada de injeção de carga no topo desta barreira potencial pode ser descrita como uma fonte virtual (VS).

<p align="center">
<img src="https://github.com/RodrigoSantosB/Model_OTFT/blob/master/figures/semicondutor.png" alt="Fig 1 Seções transversais esquemáticas de (a) um coplanar e (b) um OTFT escalonado. As linhas tracejadas mostram os caminhos atuais esperados." height="300" width="800">
</p>

Eq. (1) representa o modelo corrente-tensão para a corrente de dreno $J_D$ de TFTs adaptado de trabalhos anteriores [7]:
