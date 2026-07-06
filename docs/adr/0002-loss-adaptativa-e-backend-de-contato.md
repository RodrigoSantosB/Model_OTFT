# Loss adaptativa e backend de contato para CNT

## Contexto

No CNT (pFET / org1), o ajuste conjunto transfers×saídas converge para um compromisso que
sacrifica curvas específicas (ex.: transfer em VDS = −0.10 V). A análise de sensibilidade
mostrou conflito estrutural entre L e λ entre regimes, e VGCRIT não identificável (delta RMSE ≈ 0,
satura bounds).

## Decisões

### 1. `fixed_parameters` no otimizador

Parâmetros listados em `fixed_parameters` (JSON) permanecem no valor inicial durante o TRF;
são removidos do espaço livre e reportados com erro `NaN`. Para CNT: `["VGCRIT"]`.

### 2. Loss adaptativa (`loss_mode: adaptive_curve`)

Em vez de minimizar apenas \(\sum_k w_k \|r_k\|^2\), aproximamos a escalarização de Chebyshev
\(\min_\theta \max_k \tilde r_k(\theta)\) por reponderação iterativa:

\[
w_k^{(t+1)} = w_k^{(t)} \left(\frac{\tilde r_k}{\bar r}\right)^\beta
\]

A solução guardada é a de menor \(\max_k \tilde r_k\) entre as iterações. Configs:
`adaptive_iterations`, `adaptive_beta`. Loss robusta por ponto opcional: `point_loss: soft_l1`,
`f_scale`.

### 3. Backend de contato (`model_backend: contact`) — opcional, desligado no CNT

Habilita `TFTModelN` também para pFET/CNT (antes só nFET). O termo
\(R_{s,\mathrm{eff}}(V_{DS}) = R_{so} + \tfrac{1}{2}(R_{max}-R_{so})(1-\tanh((V_{DS}-V_0)/V_{tun}))\)
absorve resistência de contato Schottky em baixo VDS. Três parâmetros extras: VTUN, V0, RMAX.

**Status (2026-07-05):** desligado na config canônica do CNT. Com os chutes iniciais testados
(`RMAX=50` × escala `1e4`, `V0=1.5`), `Rs_eff` satura em baixo VDS e o laço auto-consistente
de `TFTModelN` (amortecimento 0.2/0.8) oscila — picos na transfer de −0.10 V e ruído nas saídas.
Reativar só após estabilizar o laço ou recalibrar VTUN/V0/RMAX.

### 4. Ferramenta de Pareto

`tools/pareto_tradeoff.py` varre `transfer_curve_weight` e gera CSV + PNG da fronteira
transfers×saídas, com ponto de joelho sugerido.

## Consequências

- Config canônica CNT: [`inputs/tipo p/inputs_cnts_v2.json`](../inputs/tipo%20p/inputs_cnts_v2.json)
  com **`TFTModel` base (8 params)**, `loss_mode: adaptive_curve`, `fixed_parameters: ["VGCRIT"]`.
  Sem `model_backend: contact` (backend de contato permanece no código, opt-in via JSON).
- Outras tecnologias mantêm defaults (`model_backend` ausente, `loss_mode: fixed`).
- `verify_display_contract.py` e `create_model_opt` passam `settings` para `resolve_model_class`.

## Alternativas descartadas (por ora)

- GradNorm / NSGA-II bi-objetivo: complexidade desproporcional; Pareto por varredura de peso
  cobre o diagnóstico.
- \(L_{\mathrm{eff}}(V_{DS}) = L + \Delta L(1-e^{-|V_{DS}|/V_L})\): fallback documentado se
  contato não bastar.
