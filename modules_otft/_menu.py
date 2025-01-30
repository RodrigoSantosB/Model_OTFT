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

  def show_table_info(self, coeff, coeff_opt, coeff_error, curr_typic, curr_carry, resistance):

      name_par = ['VTHO [V]', 'DELTA', 'N', 'L', 'VGCRIT [V]',
            'JTH [μA cm^−1]', 'RS [kΩ]', 'JTH / N [μA cm^−1]']

      print()
      print('---------------------------')
      print(" COEFICIENTES OTIMIZADOS:\n")
      data = []
      for name, initial, opt, error in zip(name_par, coeff, coeff_opt, coeff_error):
          data.append([name, initial, opt, error])

      curr_typic_ = self.__convert_to_ampere_unit(curr_typic)

      # # Faz a leitura dos dados experimentais e do modelo (de transferencia) a serem exibidos no gráfico

      #  JTH [μA cm^−1]
      data[5][1] = data[5][1] * (curr_carry / 1e-6) # JTH = 2mA * curr_typic / 1e-6 (fixo uA)
      data[5][2] = data[5][2] * (curr_carry / 1e-6) # scale/1e-6

      # RS [kΩ]
      data[6][1] = data[6][1] * (resistance / 1e3) # res/1e3
      data[6][2] = data[6][2] * (resistance / 1e3) # res/1e3


      # Calculando e adicionando o valor de JTH / N para o Valor Inicial
      jth_lambda_n_initial = data[5][1] / (data[2][1])

      # Calculando e adicionando o valor de JTH / N
      jth_lambda_n = data[5][2] / (data[2][2])

      # Calculando e adicionando o valor de JTH / N para o Erro Associado
      jth_lambda_n_error = data[5][3] / (data[2][3])

      data.append(['JTH / N [μA cm^−1]',
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
    print('   VTHO     |    DELTA   |      N     |     L      |   VGCRIT   |    JTH     |     RS    |')
    print('-'*90)
    print("[" + formatted_output + "]")
    print('-'*90)



  def extract_filename(self, path):
    return os.path.basename(path)


  def view_path_reads(self, path_voltages, voltages):
    
    print('-'*44)
    print('-'*44)
    print("|" + " "*16 + "READ FILES" + " "*16 + "|")
    print('-'*44)
    print('-'*44)

    new_curves = []

    for i, (j,  k) in enumerate(zip(path_voltages, voltages)):
      tes = path_voltages[i][0]
      filename = self.extract_filename(tes)
      new_curves.append(filename)

      if len(filename) > 14:
        print('|' + ' '*(len(filename)-3) + f'{filename}' + ' '*( len(filename)-3) + '|')
        print('-'*44)

      else:
        print('|' + ' '*(len(filename)) + f'{filename}' + ' '*( len(filename)) + '|')
        print('-'*44)
    print('-'*44)
