# Documentacao da Remocao de Histerese

Este documento descreve a tecnica implementada em `modules_otft/_pre_processing_data.py` para reduzir o efeito de histerese presente nas curvas experimentais lidas a partir de arquivos CSV.

## Objetivo

Em varias curvas experimentais, principalmente nas curvas de saida, o arquivo CSV contem uma varredura de ida e volta no eixo de tensao. Isso faz com que o mesmo valor de tensao apareca mais de uma vez, mas com correntes diferentes. No grafico, esse comportamento aparece como um laco de histerese.

Para o fluxo de modelagem e treinamento, esse tipo de repeticao pode introduzir:

- redundancia de amostras;
- inconsistencias para interpolacao;
- ambiguidade na relacao entre tensao e corrente;
- ruido adicional no ajuste do modelo.

O objetivo do pre-processamento e transformar cada curva em uma representacao unica, monotonicamente ordenada no eixo de tensao, reduzindo o impacto da histerese sem destruir a tendencia fisica global dos dados.

## Onde a tecnica foi implementada

O tratamento foi implementado na classe `PreProcessingData`, principalmente no metodo `._clean_hysteresis()`.

O fluxo principal da rotina e:

1. ler o CSV;
2. aplicar o shift horizontal na tensao;
3. aplicar o corte por tensao limiar;
4. eliminar redundancias associadas a histerese;
5. salvar a curva tratada em uma nova pasta.

## Descricao da tecnica

### 1. Leitura dos pares tensao-corrente

Cada arquivo CSV e interpretado como uma curva bidimensional com duas colunas:

- coluna 1: tensao;
- coluna 2: corrente.

Valores nao numericos sao descartados antes do processamento.

### 2. Aplicacao do shift right

Antes da limpeza de histerese, o algoritmo permite deslocar a curva horizontalmente:

`V_novo = V_original + shift_voltage`

Isso permite alinhar curvas experimentais deslocadas em tensao, como no caso de curvas de transferencia que precisam ser movidas para a direita.

O `shift` pode ser aplicado:

- a todas as curvas;
- somente a curvas selecionadas pelo nome do arquivo, pelo `stem` ou pelo caminho relativo.

### 3. Corte por tensao limiar

Depois do shift, os dados podem ser recortados a partir de uma tensao limite:

- por padrao, o limiar e `0.0 V`;
- somente os pontos com `V >= threshold_voltage` sao mantidos.

Isso atende ao caso em que, apos o deslocamento, todos os valores "do zero para tras" devem ser excluidos.

### 4. Consolidacao de pontos redundantes

O nucleo da remocao de histerese esta na consolidacao de tensoes repetidas.

Quando existe histerese, o mesmo valor de tensao aparece mais de uma vez no CSV porque a medicao foi feita em ida e volta. Nesses casos, para uma mesma tensao podem existir duas ou mais correntes medidas.

Para eliminar essa redundancia, a rotina:

1. arredonda a tensao com uma precisao configuravel;
2. cria uma chave de agrupamento para valores de tensao equivalentes;
3. agrupa todos os pontos com a mesma tensao;
4. calcula uma unica corrente representativa para cada tensao.

Na implementacao atual, a corrente representativa pode ser escolhida por meio do parametro `hysteresis_mode`.

Os modos disponiveis sao:

- `media`: usa a media aritmetica das correntes repetidas;
- `menor`: usa a menor corrente associada aquela tensao;
- `maior`: usa a maior corrente associada aquela tensao.

De forma geral:

- `I_representativa(V) = media(I_1, I_2, ..., I_n)` no modo `media`;
- `I_representativa(V) = min(I_1, I_2, ..., I_n)` no modo `menor`;
- `I_representativa(V) = max(I_1, I_2, ..., I_n)` no modo `maior`.

Esse procedimento substitui o laco de ida e volta por uma unica curva consolidada.

## Escolha da estrategia de consolidacao

### Modo `media`

O modo `media` foi escolhido como padrao por ser uma estrategia simples, estavel e robusta para este tipo de consolidacao, especialmente quando:

- a histerese aparece como duplicacao da mesma tensao;
- o objetivo e obter uma curva unica para treinamento;
- pequenas diferencas entre ida e volta devem ser absorvidas como variacao experimental.

Na pratica, essa abordagem:

- reduz a duplicidade de amostras;
- evita manter dois valores de corrente para a mesma tensao;
- preserva a tendencia global da curva;
- facilita comparacoes com modelos e rotinas de interpolacao.

### Modo `menor`

O modo `menor` seleciona, para cada tensao repetida, o menor valor de corrente observado. Essa opcao e util quando se deseja uma representacao mais conservadora da curva, privilegiando o ramo inferior do laco de histerese.

Na pratica, esse modo pode ser util quando:

- se deseja minimizar a influencia de picos locais;
- o ramo inferior e o mais relevante para a analise;
- se quer evitar superestimativa da corrente em tensoes repetidas.

### Modo `maior`

O modo `maior` seleciona, para cada tensao repetida, o maior valor de corrente observado. Essa opcao e util quando se deseja preservar o ramo superior da histerese.

Na pratica, esse modo pode ser util quando:

- se deseja uma curva mais envolvente superior;
- o ramo de maior conducao e o mais relevante;
- se quer evitar subestimativa da corrente em tensoes repetidas.

## Reordenacao final da curva

Apos a consolidacao, a curva e ordenada crescentemente pelo eixo de tensao.

Isso garante que o arquivo final:

- tenha apenas um ponto representativo por tensao;
- fique pronto para leitura por outras rotinas do projeto;
- nao mantenha a "volta" da histerese como uma segunda passada no mesmo CSV.

## Comportamento esperado nas curvas

### Curvas de transferencia

Se uma curva de transferencia for deslocada com `shift right`, todos os pontos terao sua tensao aumentada. Em seguida, o corte por limiar remove a regiao indesejada, por exemplo a parte com tensao negativa apos o ajuste.

### Curvas de saida

Nas curvas de saida, onde frequentemente existe ida e volta da varredura, o algoritmo remove a duplicidade de tensoes e gera uma curva unica. Isso reduz visualmente o efeito de histerese observado no grafico original.

## Limitacoes da abordagem

Esta tecnica nao tenta modelar fisicamente a histerese. Ela foi desenhada para limpeza e consolidacao de dados.

Algumas implicacoes:

- a diferenca entre ramo de ida e ramo de volta nao e preservada separadamente;
- a curva final representa uma versao consolidada da medicao, segundo o modo escolhido;
- se a histerese for muito forte e fisicamente relevante, talvez seja melhor tratar cada ramo separadamente em outra rotina.

## Parametro de configuracao

A escolha da estrategia de eliminacao da histerese e feita pelo parametro `hysteresis_mode`, aceito nas rotinas de processamento.

Valores aceitos:

- `media`
- `menor`
- `maior`

Exemplo:

```python
from modules_otft._pre_processing_data import process_experimental_data

process_experimental_data(
    input_path="datas/cnts",
    shift_voltage=0.3,
    threshold_voltage=0.0,
    hysteresis_mode="menor",
)
```

## Quando essa tecnica e adequada

Esta abordagem e recomendada quando o objetivo principal e:

- preparar dados para treinamento de modelos;
- gerar uma unica curva por arquivo;
- remover ambiguidades para interpolacao, ajuste e comparacao;
- reduzir redundancias experimentais sem criar um modelo fisico adicional.

## Resumo

A tecnica de remocao de histerese implementada neste projeto consiste em:

1. ler a curva experimental;
2. aplicar `shift` horizontal na tensao;
3. recortar a curva por um limiar de tensao;
4. agrupar tensoes repetidas;
5. substituir correntes repetidas por uma corrente representativa definida por `hysteresis_mode`;
6. ordenar a curva e salvar um novo CSV tratado.

Essa estrategia transforma curvas com ida e volta em uma unica curva limpa, mais apropriada para as etapas seguintes do pipeline.
