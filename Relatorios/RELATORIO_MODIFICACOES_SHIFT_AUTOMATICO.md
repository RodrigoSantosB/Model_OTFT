# Relatorio de Modificacoes do Shift Automatico

Este arquivo resume as modificacoes implementadas para adicionar o calculo automatico de `shift` individual nas curvas de saida, mantendo compatibilidade com o `shift` manual/global ja existente no projeto.

## Objetivo implementado

Foi adicionada uma rotina que calcula automaticamente um `shift` individual para cada curva de saida a partir da curva de transferencia correspondente com a mesma tensao nominal.

O valor automatico calculado:

- e somado ao `shift` manual definido em `shift_volt_data`;
- e repassado para o modelo por meio da lista de tensoes deslocadas;
- e passa a aparecer nas informacoes exibidas para o usuario;
- e pode ser consultado em um relatorio interno de execucao.

## Protocolo implementado

Para cada curva de saida:

1. usa-se como referencia principal a tensao nominal lida diretamente da coluna fixa do CSV;
2. curvas com `VDS` fixo sao tratadas como transferencia e curvas com `VGS` fixo como saida;
3. o valor nominal e validado contra a faixa de tensao disponivel no proprio CSV;
4. busca-se a curva de transferencia correspondente com a mesma tensao nominal identificada na curva;
5. na curva de saida, calcula-se a corrente no ponto `VDS = V_nominal_csv`;
6. na curva de transferencia correspondente, procura-se o valor de tensao cujo valor de corrente melhor coincide com a corrente obtida no passo anterior;
7. o `shift` automatico e calculado como:

`shift_automatico = V_nominal - V_transfer_equivalente`

8. o `shift` total usado pelo modelo passa a ser:

`shift_total = shift_manual + shift_automatico`

## Arquivos modificados

### `modules_otft/_read_data.py`

Foram adicionadas rotinas auxiliares para:

- extrair a tensao nominal da coluna fixa do arquivo CSV;
- ler curvas experimentais diretamente dos arquivos;
- consolidar tensoes repetidas em curvas com histerese;
- interpolar corrente em funcao da tensao;
- interpolar tensao em funcao da corrente;
- calcular automaticamente um `shift` por curva de saida.

Tambem foi ajustada a funcao `apply_shifts()` para aceitar tanto valores numericos quanto estruturas com:

- `manual`
- `automatic`
- `total`

### `modules_otft/_utils.py`

Foi alterado o fluxo de `shift` para:

- montar uma estrutura de metadados por curva de saida;
- preservar o `shift` manual/global;
- calcular e injetar o `shift` automatico no mesmo objeto;
- recalcular o `shift` total usado para o modelo;
- armazenar detalhes do calculo automatico em `settings['_automatic_shift_report']`.

Com isso, a variavel `shift_list` criada no notebook permanece utilizavel, mas passa a carregar os componentes:

- `manual`
- `automatic`
- `total`

### `modules_otft/_grafics.py`

Foi atualizada a formatacao das legendas para suportar os novos metadados de `shift`.

Agora:

- a legenda das curvas experimentais de saida exibe apenas o `shift` automatico calculado;
- a legenda das curvas de modelo de saida tambem exibe esse valor;
- os valores aparecem com duas casas decimais;
- os detalhes internos `global/manual` e `automatico` nao sao mais exibidos no grafico.

### `modules_otft/_display.py`

Foi ajustada a exibicao de configuracoes para mostrar o detalhamento por curva no formato:

- `total`
- `global`
- `auto`

## Dados agora disponiveis em execucao

Depois da chamada de `get_shift_list(read, settings)`, o dicionario `settings` passa a conter:

- `settings['_shift_metadata']`: lista com os componentes `manual`, `automatic` e `total` por curva;
- `settings['_automatic_shift_report']`: relatorio detalhado do casamento entre curvas de transferencia e saida.

## Resultado pratico

Com as alteracoes implementadas:

- o `shift` manual/global continua funcionando;
- cada curva de saida passa a receber um `shift` automatico proprio;
- o modelo passa a usar o `shift` total;
- o valor aplicado pode ser mostrado ao usuario no grafico e nas configuracoes;
- o calculo automatico fica rastreavel por meio do relatorio interno.

## Observacao

Os avisos atuais do linter encontrados nos arquivos alterados sao avisos de estilo e refatoracao (`Sourcery`), sem erro funcional identificado na validacao do fluxo do `shift` automatico.
