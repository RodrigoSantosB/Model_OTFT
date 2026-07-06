# Model_OTFT — Modelagem e ajuste de curvas de TFT/OTFT

Pipeline para extração de parâmetros de transistores de filme fino (Org1–4, CNT, Au2) a partir
de curvas experimentais CSV, com pré-processamento de histerese, compensação de tensão (shift)
e otimização do modelo OVSED.

## Language

**Curva de transferência**:
Curva ID×VGS com VDS fixo; nos CSVs o nome termina em `...VDS.csv` (o sufixo indica a grandeza fixa).
_Avoid_: chamar de "curva VGS"

**Curva de saída**:
Curva ID×VDS com VGS fixo; nos CSVs o nome termina em `...VGS.csv`.
_Avoid_: chamar de "curva VDS"

**Tensão nominal**:
Tensão de polarização fixa lida da coluna do CSV experimental, como foi medida (ex.: -4.0 V).
_Avoid_: tensão do arquivo, tensão medida

**Tensão efetiva**:
Tensão de porta que, na transfer de referência, reproduz a corrente observada na curva de saída
em `VDS_ref`; é a tensão com que o modelo deve calcular a curva de saída.
_Avoid_: tensão ajustada, tensão corrigida

**Shift automático**:
Componente estimado por curva de saída via casamento de corrente em `VDS_ref` na transfer de
referência (`estimate_output_shifts`); converte nominal em efetiva.

**Shift manual**:
Componente por curva definido no JSON (`manual_shift_data` / chaves legadas); quando habilitado,
substitui o automático.

**Shift total**:
`manual + automático`; único valor aplicado à tensão nominal (`_apply_shift_to_nominal_voltage`).

**Shift global (de pré-processamento)**:
Deslocamento horizontal aplicado UMA vez, em disco, ao eixo de tensão dos CSVs de transferência
(`V_novo = V_original + shift`); persistido em `pre_process_global_shift_persisted_value`.
Não altera os CSVs de saída — é re-somado às tensões de saída apenas para exibição
(`apply_global_shift_to_output_display`).
_Avoid_: confundir com shift automático/manual (que são por curva e não tocam os arquivos)

**Consolidação de histerese**:
Substituição da varredura ida-e-volta por uma curva única por tensão (`media`/`menor`/`maior`),
feita em disco pelo pré-processamento (`_clean_hysteresis`).

## Relationships

- Cada **curva de saída** tem uma **transfer de referência** (a de maior |polarização|), onde a
  **tensão efetiva** é procurada por casamento de corrente.
- **Shift total** transforma **tensão nominal** em **tensão efetiva**.
- O **shift global** vive no eixo dos CSVs de transferência em disco; as curvas de saída
  permanecem no espaço medido.

## Contrato de exibição (resolvido em 2026-07-02)

Nos gráficos de saída: a legenda do **experimento** mostra a **tensão nominal** medida
(ex.: `Exp -4.00V`); a legenda do **modelo** mostra a **tensão efetiva** usada no cálculo, com a
compensação por curva entre parênteses como delta assinado real `efetiva − nominal`
(ex.: `Model -3.90V (+0.10V)`). A aritmética deve fechar na própria figura:
`nominal + parêntese = efetiva`. O shift global NÃO entra no parêntese (já está embutido no
eixo das transfers; citá-lo uma vez no texto, não por curva).

## Escopo da correção (resolvido em 2026-07-02)

A correção das convenções acima é feita nos módulos compartilhados (`modules_otft`) e na
passagem de dados dos notebooks; TODAS as figuras do apêndice são regeneradas com a mesma
versão do código (as legendas mudam em todas as tecnologias, não só no CNT). O padrão de
célula defeituoso (`read_files_experimental(path, list_tension_shift)` sobrescrevendo a
nominal) existe em `TFT_M1_LAMB_MC.ipynb` (célula 8), `TFT_MLP_Pipeline.ipynb` (célula 8) e
`MLPV1.ipynb` (célula 3) — os três precisam do mesmo ajuste.

O config canônico de CNT é `inputs/tipo p/inputs_cnts_v2.json` (movido de `tipo n`, onde estava
com `type_of_transistor: pFET` apontando para dados tipo p); os demais JSONs de CNT ficam em
`inputs/obsoletos/`. O contrato de exibição é verificado por `tools/verify_display_contract.py`,
que roda o fluxo completo por JSON e falha se: legenda experimental ≠ nominal; legenda do
modelo ≠ efetiva; `nominal + parêntese ≠ efetiva`; ou `input_voltage` do modelo/otimizador ≠
lista de efetivas de `_shift_metadata`.

## Pesos da função de custo (resolvido em 2026-07-05)

O custo do otimizador combina três camadas de peso por ponto (`_combine_residual_weights`):
(1) **balanceamento por curva** — cada curva contribui de forma comparável, normalizando pela
escala RMS da própria curva (transfers em log10 vs. saídas em corrente linear);
(2) **peso de transfers** (`transfer_curve_weight`, JSON) — multiplicador aplicado só às curvas
de transferência, para arbitrar o compromisso transfers×saídas (CNT usa 3.0);
(3) **janelas de tensão** (`hysteresis_weight_windows`) — aplicadas **apenas aos pontos de
transferência**: o eixo das janelas é VGS, e o VDS das saídas ocupa a mesma faixa numérica,
então sem essa restrição a janela vazava e inflava as saídas, anulando a intenção.
No TRF, os parâmetros são normalizados via `x_scale` (magnitudes de ~0.2 a ~4000).
Parâmetros não identificáveis podem ser congelados via `fixed_parameters` (CNT: VGCRIT).
_Avoid_: assumir que a janela de peso atinge as curvas de saída.

## Loss adaptativa e backend de contato (resolvido em 2026-07-05)

Para tecnologias com conflito transfers×saídas (CNT), o JSON canônico usa:
- **`loss_mode: adaptive_curve`** — reponderação iterativa min-max por curva (Chebyshev);
- **`fixed_parameters`** — ex.: `["VGCRIT"]` quando o parâmetro satura bounds sem ganho de fit;
- **`TFTModel` base (8 params)** — chute inicial estável; sem `model_backend: contact`.
Opcional/experimental: **`model_backend: contact`** — `TFTModelN` com \(R_{s,\mathrm{eff}}(V_{DS})\);
hoje **não** é default do CNT (instabilidade numérica em baixo VDS com chutes testados).
Diagnóstico de trade-off: `tools/pareto_tradeoff.py`. Ver ADR-0002.
_Avoid_: ativar `model_backend: contact` no CNT sem recalibrar VTUN/V0/RMAX ou estabilizar o laço.

## Example dialogue

> **Dev:** "A curva `cnt-4VGS.csv` é de transferência, já que varre VGS?"
> **Especialista:** "Não — o sufixo indica a grandeza *fixa*. `4VGS` significa VGS fixo em -4 V,
> então é curva de **saída**. Transferência é `cnt-3VDS.csv` (VDS fixo)."
>
> **Dev:** "E o modelo calcula essa saída em -4 V?"
> **Especialista:** "Não, na **tensão efetiva** (~-3.9 V), que compensa a histerese; a legenda do
> experimento continua mostrando a **nominal** -4 V."

## Flagged ambiguities

- "No CNT o shift é zero" — **resolvido**: o shift automático do CNT é não-nulo (-0.84 a -1.10 V);
  a ilusão vem de (1) a tensão efetiva exibida (-3.90 V) ficar a só 0.10 V da nominal (-4.0 V) e
  (2) a célula 8 do `TFT_M1_LAMB_MC.ipynb` sobrescrever a nominal com a lista shiftada
  (`read_files_experimental(path, list_tension_shift)`), igualando as legendas de modelo e
  experimento em TODAS as tecnologias.
- Espaço de coordenadas do VGS efetivo passado ao modelo — **resolvido** (ver ADR-0001): o
  modelo recebe a tensão efetiva no eixo pós-shift-global das transfers (-3.90 V), sem o
  desconto feito por `_adjust_shift_with_preprocess`.
- Significado do shift entre parênteses na legenda do modelo — **resolvido**: delta assinado
  `efetiva − nominal` por curva (≈ +0.10 V), sem incluir o shift global e sem as inversões de
  sinal de `__change_signal_shift`/`_apply_shift_to_nominal_voltage` na exibição.
