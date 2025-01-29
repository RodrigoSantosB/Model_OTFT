from IPython.display import clear_output
from ._imports import *

class TFTMenu:
  def __init__(self):
    pass

  def __convert_to_ampere_unit(self, scale):
      # Identificar a escala dos dados (mA ou uA)
      convert_to_ampere_unit = 0
      unite = {  'A': 1,
                'mA': 1e-3,
                'uA': 1e-6,
                'nA': 1e-9,
                'pA': 1e-12
                            }

      # Verificar se a escala existe no dicionário
      if scale in unite:
          convert_to_ampere_unit = unite[scale]
          # print(convert_to_ampere_unit )
      else:
          raise ValueError("Escala de dados inválida!")
      return convert_to_ampere_unit

  def show_table_info(self, scale, coeff, coeff_opt, coeff_error, curr_typic, resistance):

    name_par = ['VTHO [V]', 'DELTA', 'N', 'L', 'LAMBDA', 'VGCRIT [V]',
                'JTH [μA cm^−1]', 'RS [kΩ]', 'JTH / LAMBDA * N [μA cm^−1]']

    print()
    print('---------------------------')
    print(" COEFICIENTES OTIMIZADOS:\n")
    data = []
    for name, initial, opt, error in zip(name_par, coeff, coeff_opt, coeff_error):
        data.append([name, initial, opt, error])

    curr_typic_ = self.__convert_to_ampere_unit(curr_typic)

    # # Faz a leitura dos dados experimentais e do modelo (de transferencia) a serem exibidos no gráfico

    #  JTH [μA cm^−1]
    data[6][1] = data[6][1] * (eval(current_carry) / 1e-6) # JTH = 2mA * curr_typic / 1e-6 (fixo uA)
    data[6][2] = data[6][2] * (eval(current_carry) / 1e-6) # scale/1e-6

    # RS [kΩ]
    data[7][1] = data[7][1] * (resistance / 1e3) # res/1e3
    data[7][2] = data[7][2] * (resistance / 1e3) # res/1e3


    # Calculando e adicionando o valor de JTH / LAMBDA * N para o Valor Inicial
    jth_lambda_n_initial = data[6][1] / (data[4][1] * data[2][1])

    # Calculando e adicionando o valor de JTH / LAMBDA * N
    jth_lambda_n = data[6][2] / (data[4][2] * data[2][2])

    # Calculando e adicionando o valor de JTH / LAMBDA * N para o Erro Associado
    jth_lambda_n_error = data[6][3] / (data[4][3] * data[2][3])

    data.append(['JTH / LAMBDA * N [μA cm^−1]',
                jth_lambda_n_initial, jth_lambda_n, jth_lambda_n_error ])


    # Função para centralizar o texto nas células da tabela
    def wrap_cell_text(text, width=20):
        return "\n".join(textwrap.wrap(text, width=width, subsequent_indent=" "*5))

    # Formatar os valores para até 8 casas decimais
    for row in data:
        for i in range(1, len(row)):
            if isinstance(row[i], float):
                row[i] = "{:.8e}".format(row[i])

    # Centralizar os valores da tabela
    for row in data:
        for i in range(len(row)):
            row[i] = wrap_cell_text(str(row[i]))



    table = tabulate(data, headers=["Parâmetro", "Valor Inicial", "Valor Otimizado",
                                    "Erro associado (desvio padrão)"], tablefmt="fancy_grid")
    print(table)


  def print_values(self, values):
    # Formatar e imprimir os valores estilizados
    formatted_values = ["{:.4e}".format(val) for val in values]
    formatted_output = " │ ".join(formatted_values)
    print('   VTHO     |    DELTA   |      N     |     L      |    LAMBDA  |   VGCRIT   |    JTH     |     RS    |')
    print('-'*103)
    print("[" + formatted_output + "]")
    print('-'*103)


  def view_path_reads(self, path_voltages, voltages):
    def extract_filename(path):
        return os.path.basename(path)

    print('-'*44)
    print('-'*44)
    print("|" + " "*16 + "READ FILES" + " "*16 + "|")
    print('-'*44)
    print('-'*44)

    new_curves = []

    for i, (j,  k) in enumerate(zip(path_voltages, voltages)):
      tes = path_voltages[i][0]
      filename = extract_filename(tes)
      new_curves.append(filename)

      if len(filename) > 14:
        print('|' + ' '*(len(filename)-3) + f'{filename}' + ' '*( len(filename)-3) + '|')
        print('-'*44)

      else:
        print('|' + ' '*(len(filename)) + f'{filename}' + ' '*( len(filename)) + '|')
        print('-'*44)
    print('-'*44)
    return new_curves
