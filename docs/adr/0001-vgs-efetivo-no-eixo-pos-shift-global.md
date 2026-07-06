# VGS efetivo das curvas de saída vive no eixo pós-shift-global das transfers

O shift global de pré-processamento é gravado em disco apenas no eixo de tensão das curvas de
transferência; o modelo é ajustado contra esse eixo. A tensão efetiva de cada curva de saída é,
por definição, o VGS que reproduz na transfer de referência a corrente observada em `VDS_ref` —
portanto ela só faz sentido nesse mesmo eixo. Decidimos que o modelo recebe a tensão efetiva
exatamente como encontrada na transfer (ex.: CNT `cnt-4VGS`: -3.902 V), sem descontar o shift
global.

O comportamento anterior descontava o shift global do valor passado ao modelo
(`_adjust_shift_with_preprocess`) e o re-somava apenas na exibição
(`apply_global_shift_to_output_display`), fazendo o modelo calcular com um VGS deslocado em
relação ao próprio eixo de ajuste. Verificação numérica (CNT, transfer `cnt-3VDS.csv` no disco):
ID(-3.902 V) = 347.2 µA = corrente alvo da saída; ID(-2.902 V) = 263.5 µA (erro de ~24%). No CNT
o shift global (-1 V) é da ordem da tensão de operação, tornando o erro dominante; em
tecnologias sem shift global (Org1–4) o defeito era invisível.

Consequência: a re-soma de exibição torna-se desnecessária e deve ser removida junto com o
desconto, senão as legendas passam a mostrar tensões que não correspondem ao cálculo.
