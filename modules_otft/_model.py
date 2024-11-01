
from ._imports import *
class TFTModel:

    #CONSTANTS VALUES DEFALTS (private):
    __ID_LEAK               = 0
    __WIDTH_TRANSISTOR      = 0.1000        # Transistor width [cm]
    __TYPE_OF_TRANSISTOR    = 0             # type of transistor. nFET type=1; pFET type=-1
    __BOLTZMANN_CONST_KB    = 8.617e-5      # Boltzmann constant [eV/K]
    __JUNCTION_TEMPERATURE  = 298           # Junction temperature [K].
    __PHIT = (__BOLTZMANN_CONST_KB * __JUNCTION_TEMPERATURE)
    # __HYSTERESIS_EFFECT = 0



    def __init__(self, tension_list, n_points, type_curve='linear', current_typic='A', scale_factor='A', idleak=1,
                 mult_idleak=0, type_data=0 , type_transitor=-1,
                 curv_transfer=0, with_transistor=0.1, sr_resistance=None, curr_carry=None):
      '''

      '''

      self.tension_list = tension_list
      self.curv_transfer = curv_transfer
      self.type_data = type_data
      self.mult_idleak = mult_idleak
      self.__TYPE_OF_TRANSISTOR = type_transitor
      self.__ID_LEAK = idleak
      self.__WIDTH_TRANSISTOR = with_transistor

      # número de pontos na amostra do conjunto de dados a ser lido
      self.n_points = n_points
      # Resistencia serial
      self.sr_resistance = sr_resistance
      # corrente jth que sera aplicada no modelo
      self.curr_carry = curr_carry
      # fator de escala associado aos dados
      self.scale_factor = scale_factor
      # corrente tipica associada aos dados
      self.current_typic = current_typic
      # tipo de curva que o modelo irá operar
      self.type_curve = type_curve


    def _convert(self, num):
      """
        Converte um número para uma lista, se ele ainda não é uma lista.
        Args:
            num (int ou list): o número ou lista a ser convertido.
        Returns:
            list: uma lista curv_transferendo o número, se ele não for uma lista.
      """
      return num if isinstance(num, list) else [num]

    #METHODS AND AUXILIAR FUNCTIONS
    def _sign(self, x:float)->int:
      # Retorna o sinal de um número
      return np.where(x < 0, -1, np.where(x > 0, 1, 0))

    # compute the total charge based in parameters
    def _total_charge(self, Vgsi, Vtp, N):
      """
        Calcula a carga total.

        Args:
            Vgsi: O valor de Vgsi.
            Vtp: O valor de Vtp.

        Returns:
          tuple: Retorna uma tupla curv_transfer com os valores calculados:
              nphit (float): O produto de N (uma constante) e PHIT
              (uma variável de instância da classe).
              theta (float): O resultado da equação (Vgsi-Vtp) / nphit.
              qtot (float): O resultado da equação np.log(1 + np.exp(theta)).
      """
      Vgsi = np.float64(Vgsi)
      Vtp  = np.float64(Vtp)

      nphit = (N * self.__PHIT)
      theta = (Vgsi-Vtp) / nphit
      qtot  = np.log(1 + np.exp(theta))
      return nphit, theta, qtot


    # Compute the Jfree
    def _current_calculation(self, qtot, Jth, L):
      """
        Calcula a corrente Jfree.

        Args:
            qtot: O valor de qtot.

        Returns:
            float: O valor da corrente Jfree, calculado como Jth * qtot**L,
            onde Jth e L são constantes predefinidas.
      """
      Jfree = Jth * qtot**L
      return Jfree


    # Identificar a escala dos dados (mA ou uA)
    def __convert_to_ampere_unit(self, scale):
      correction_factor = 0
      unite = {  'A': 1,
                'mA': 1e-3,
                'uA': 1e-6,
                'nA': 1e-9,
                'pA': 1e-12
                            }

      # Verificar se a escala existe no dicionário
      if scale in unite:
          correction_factor = unite[scale]
          # print(correction_factor )
      else:
          raise ValueError("Escala de dados inválida!")
      return correction_factor


    # Compute the Vpt parameter
    def _drain_impact(self, Vds, Vtho, Delta):
      """
        Calcula o parâmetro Vpt.

        Args:
            Vds: O valor de Vds.

        Returns:
            float: O valor de Vtp, calculado como Vtho + Vds * Delta, onde
            Vtho e Delta são constantes predefinidas.
      """
      Vds = np.float64(Vds)
      Vtp = Vtho + Vds * Delta
      return Vtp


    # Compute the Idx that the final current
    def _final_current(self, Idleak, Jfree, Fsat):
      """
        Calcula a corrente final.

        Args:
            Fsat: Calcula o valor de Fsat, que é o fator de saturação que representa a fração da
            corrente de dreno total que flui pela região de saturação do transistor MOS.
            Idleak: Calcula o valor de Idleak, que é a corrente de fuga inversa que flui pelo
            canal do transistor MOS  quando o dispositivo está desligado.
            Jfree:  Calcula o valor de Jfree, que é a densidade de corrente livre que flui pelo
            canal do transistor MOS quando o dispositivo está ligado.

        Returns:
            float: O valor da corrente final, calculado como Idleak +
            (a largura do transistor * Jfree * Fsat), onde a largura do transistor
            é uma variável de instância da classe.
      """
      Idleak = np.float64(Idleak)
      Jfree  = np.float64(Jfree)
      Fsat   = np.float64(Fsat)

      Idx = Idleak + (self.__WIDTH_TRANSISTOR * Jfree * Fsat)
      return Idx


    def _calc_dir(self, Vd, Vs):
      """
        Calcula a direção do transistor.

        Args:
            Vd: O valor de Vd, diferença de potencial entre o dreno e a fonte
            Vs: O valor de Vs, diferença de potencial entre a fonte e o substrato
            do transistor MOS

        Returns:
            int: O valor da direção do transistor, que é calculado como
            TYPE_OF_TRANSISTOR * sign(Vd-Vs), onde TYPE_OF_TRANSISTOR é uma
            variável de instância da classe e sign é uma função que retorna
            -1 se Vd-Vs é negativo, 0 se Vd-Vs é zero e 1 se Vd-Vs é positivo.
      """
      Vd = np.float64(Vd)
      Vs = np.float64(Vs)

      dir = (self.__TYPE_OF_TRANSISTOR*(self._sign(Vd-Vs)))
      return dir


    def _calc_vgs_or_vbs(self, Vd, Vg, Vs):
      """
        Calcula o valor da tensão gate-source (Vgs) ou gate-bulk (Vbs),
        dependendo do tipo do transistor.

        Args:
            Vd: O valor da tensão do dreno.
            Vg: O valor da tensão da porta.
            Vs: O valor da tensão da fonte.

        Returns:
            float: O valor da tensão gate-source (Vgs) ou gate-bulk (Vbs),
            calculado como o máximo entre duas expressões diferentes,
            dependendo do tipo do transistor, que envolvem a diferença de
            potencial entre a porta e a fonte e a diferença de potencial
            entre a porta e o dreno ou substrato.
      """
      Vgs = np.maximum(self.__TYPE_OF_TRANSISTOR * (Vg - Vs), self.__TYPE_OF_TRANSISTOR * (Vg - Vd))
      return Vgs


    # Determine the values of Fsat
    def _fsat_calculation(self, Vds, nphit, qtot, Vcrit):
      """
        Calcula o valor de Fsat e recebe três parâmetros:
        Args:
            Vds:   a tensão entre o dreno e a fonte do transistor.
            nphit: o produto do número de portadores majoritários (N) e o potencial térmico (PHIT)
            do dispositivo.
            qtot:  a carga total do transistor.
        Returns:
            A função utiliza esses parâmetros para calcular a fração da corrente de saturação (Fsat)
            e o valor de eta, que é um parâmetro utilizado no cálculo de Fsat. Fsat é um parâmetro
            importante na modelagem do transistor MOS, que representa a fração da corrente que flui
            pelo canal do transistor em relação à corrente total que flui pelo dispositivo.
      """


      Vds   = np.float64(Vds)
      nphit = np.float64(nphit)
      qtot  = np.float64(qtot)

      Vgt = nphit * qtot
      Vgn = (2 * Vgt) / (1 + np.sqrt(2 * Vgt / Vcrit))
      x = Vds / Vgn
      eta = 1 - np.tanh(x)

      # eta = 1 - x / (1+(x^beta))^(1/beta)
      y = np.float64(Vgn) / np.float64(self.__PHIT)

      # Version 1
      # ll = (2 / (np.square(y) * (1 - np.square(eta))) * (np.exp(y * (eta-1)) * (1 - (y * eta)) - (1 - y)))
      # ll = np.nan_to_num(ll)
      # if (np.array(Vds == 0)).any():
      #   ll[0] = 1e10
      # at = 1 / (2*ll)  # 1/(1+2*ll)

      # Version 2
      llinv = (np.square(y) * (1 - np.square(eta))) / (2*(np.exp(y * (eta-1)) * (1 - (y * eta)) - (1 - y)))
      at = llinv / 2

      Fsat = at * (1 - np.exp(-Vds / self.__PHIT)) / (1 + at * np.exp(-Vds / self.__PHIT))
      Fsat = np.nan_to_num(Fsat)
      #print(Fsat)

      # #return Fsat = 0 if Vds = 0:
      # for i in range(len(Fsat)):
      #   if np.isnan(Fsat[i]) == True:
      #     Fsat[i] = 0

      return Fsat, eta


    def _creat_matrix(self, V, n_rows_max=99, n_rows=50):
      # Create current empty matrix

      """
        Função que recebe um vetor ou matriz e verifica se o array passado como parâmetro
        possui mais elementos que o tamanho máximo, se sim, ele cria uma matriz com 50 linhas e
        o numero de colunas parametrizado por tension_list que representa uma lista de tensões de
        entrada que o modelo vai receber. A quantidade de colunas então, será definida dessa forma
        o que garante que para qualquer quantidade de elementos na lista, será possivel realizar
        esse "reshape".

        Para o caso de V > 50 e V < 99, então, o reshape não acurv_transferece pois é entendido que o número
        de amostras aqui pode estar curv_transferido nesse intervalo, e portanto, só retona um
        vetor/ lista unidimensional

        Args:
          V: vetor ou matriz
          n_rows: numero de linhas que representa a quantidade de amostras esperimentais colhidas

        Returns:
          Vetor se   n_rows < V < n_rows_max.
          Matriz com n_rows linhas e len(tension_list) colunas se V > n_rows_max
      """
      if (V.size > n_rows_max):
        n_colunms = len(self._convert(self.tension_list))
        chain_matrix_id = np.zeros((n_rows, n_colunms))
      if ((V.size >= n_rows and V.size < n_rows_max) or V.size < n_rows):
        chain_matrix_id = []
      return chain_matrix_id


    #Traform vector in matrix
    n_rows_max = 99

    # check the dimension of vector if him is matrix or not
    def _checks_v(self, V_tensions, n_rows_max, tension_list):
      n_rows = self.n_points
      Vv = 0
      if (V_tensions.size > n_rows_max):
        Vv = np.reshape(V_tensions, (n_rows, len(tension_list)))
      elif (V_tensions.size > n_rows and V_tensions.size < n_rows_max):
        Vv = V_tensions
      else:
        Vv = V_tensions
        Vv = np.concatenate([Vv, np.zeros(self.n_points - len(V_tensions))])
      return Vv


    def _calc_vd_vg(self, V, tension_list, i, type_data):

      """
        calc_vd_vg recebe como entrada uma matriz ou vetor V, uma lista de tensões tension_list,
        um índice i e um tipo de dados type_data. O objetivo da função é retornar dois valores Vd e Vg,
        que podem ser escalares ou vetores, dependendo dos parâmetros de entrada.
        Primeiro, a matriz V é transformada em uma matriz Vv com um número máximo de linhas de 70. Se V
        tiver menos de 50 linhas, ele é preenchido com zeros.
        Em seguida, é verificado se i é menor que um curv_transferador curv_transfer e se a dimensão de Vv é maior do que 1.
        Se essa condição for verdadeira, Vg recebe o i-ésimo coluna de Vv e Vd recebe o i-ésimo elemento de
        tension_list.
        Se i for maior ou igual a curv_transfer e a dimensão de Vv for maior do que 1, Vg recebe o i-ésimo elemento
        de tension_list e `Vd recebe a i-ésima coluna de Vv.

        Se a dimensão de Vv for 1, é verificado o valor da variável type_data. Se type_data for 0,
        significa que V é uma tensão aplicada em Vg e Vd é uma tensão constante definida pelo i-ésimo
        elemento de tension_list. Nesse caso, Vg recebe uma cópia de Vv e Vd recebe o i-ésimo elemento
        de tension_list.

        Se type_data for 1, significa que V é uma tensão aplicada em Vd e Vg é uma tensão constante
        definida pelo i-ésimo elemento de tension_list. Nesse caso, Vd recebe uma cópia de Vv e Vg recebe
        o i-ésimo elemento de tension_list.

        Por fim, a função retorna Vd e Vg

        Args:
            V: matriz mxn ou vetor
            tension_list: lista de tensões de entrada
            i: indice que irá interar no valores de Vg ou Vd
            type_data: tipo de dados de entrada, type_data = 0 --> dados de trasferencia
            type_data = 1 --> dados de saída ( output_transfer )

        Returns:
          Retorna os vetores Vd e Vg que são tensões aplicadas aos terminais do transistor MOSFET.
          Vd é a tensão entre o dreno e a fonte do dispositivo, enquanto
          Vg é a tensão entre o gate (porta) e a fonte

      """

      Vv = self._checks_v(V, self.n_rows_max, tension_list)

      Vg = 0
      Vd = 0

      if i < self.curv_transfer and Vv.ndim > 1:
        # Vg é um vetor e Vd é um escalar
        Vg = Vv[:, i]
        Vd = tension_list[i]

      elif i >= self.curv_transfer and Vv.ndim > 1 :
        # Vd é um vetor e Vg é um escalar
        Vg = tension_list[i]  # soma-se 5v por motivos do efeito de hysteresis
        Vd = Vv[:, i]


      elif V.ndim == 1:

        if type_data == 0:

          Vg = np.copy(Vv)
          Vd = tension_list[i]

        if type_data == 1:

          Vd = np.copy(Vv)
          Vg = tension_list[i]

      return Vd, Vg


    def calc_model(self, V, Vtho=1, Delta=1, N=1, L=1, Vcrit=1, Jth=1, Rs=1):
      """
        Essa função é uma parte do modelo de simulação de um transistor MOSFET. Ela é responsável por realizar cálculos
        envolvendo diversos parâmetros físicos do transistor e das condições de operação para determinar a corrente que
        passa pelo dispositivo.

        Args:
            V: vetor de tensões de porta (ou base) do transistor.
            Vtho: tensão de limiar de porta do transistor.
            Delta: coeficiente de modulação de canal.
            N: número de canais do transistor.
            L: comprimento de canal do transistor.
            Vcrit: tensão de ruptura do transistor.
            Jth: corrente de saturação do transistor.
            Rs: resistência de fonte (ou emissor) do transistor.

        Returns:
            Dapendendo do tamanho da entrada que for passada essa função irá retornar um vetor > 50 elementos de
            correntes que serão as correntes Id calculas para cada par de tensões Id = F (Vgs, Vds) = escalar.
            Essencialmente o que ela retona é uma matriz na forma de um vetor unidimensional. Fazendo uso da
            função ´np.ravel() que retorna uma cópia do array original, com todos os elementos do array
            original "achatados" em um único array unidimensional. Isso significa que a função retorna um array
            com todas as linhas do array original concatenadas em uma única linha.
            Caso V < 50 então, ela irá computar as correntes apenas para esse V.

      """
      res=self.sr_resistance
      curr=self.curr_carry

      # Parameter Scaling
      if res is not None:
        Rs = Rs * res     #Scaling of serial sr_resistance to 10kOhm
      if curr is not None:
        Jth = Jth * curr  #Scaling of current carrying capacity to 1uA/cm

      # SERIAL RESISTANCE
      Rd = Rs

      # Create current matrix
      chain_matrix_id = self._creat_matrix(V, n_rows=self.n_points)

      vdv = np.array(self._convert(self.tension_list))

      # quantity of columns
      for i in range(len(vdv)):
        # Dertermine Vectores Vd and Vg
        Vd, Vg = self._calc_vd_vg(V, vdv, i, self.type_data)

        Vb = 0
        Vs = 0

        dir = self._calc_dir(Vd, Vs)

        Vds = np.abs(Vd-Vs)
        Vgs = self._calc_vgs_or_vbs(Vd, Vg, Vs)
        Vbs = self._calc_vgs_or_vbs(Vd, Vg, Vs)



        # Drain Impact
        Vtp = self._drain_impact(Vds, Vtho, Delta)

        # Total change (normalized)
        nphit, theta, qtot  = self._total_charge(Vgs, Vtp, N)


        # Fsat calculation - Long channel device
        Fsat, eta = self._fsat_calculation(Vds, nphit, qtot, Vcrit)


        #  Current calculation
        Jfree = self._current_calculation(qtot, Jth, L)

        Idleak = 0

        # Valor de Idleak constante
        if self.mult_idleak == 0:
          Idleak = self.__ID_LEAK

        # Modifica o valor de Idleak (lista)
        elif self.mult_idleak == 1:
          if i < self.curv_transfer:
            Idleak = self.__ID_LEAK[i]
            # print(f'Valor de Ideleak={Idleak}, com {i} < {self.curv_transfer} ')

          elif i >= self.curv_transfer:
            # print(f'valor de {i=} > que {self.curv_transfer}')
            Idleak = 0
        else:
          raise ValueError("Idleak value invalid\n")


        # Final
        Idx = self._final_current(Idleak, Jfree, Fsat)


        # Vds -> Vdsi
        tolerance = 1e-10
        Idxx = Idleak
        dvg = Idxx * Rs
        dvd = Idxx * Rd
        count = 1

        while np.greater(np.max(np.abs((Idx - Idxx) / Idx)), tolerance).any():
            count += 1
            if count > 500: break

            Idxx = Idx
            dvg  = 0.1*Idx*Rs + 0.9*dvg
            dvd  = 0.1*Idx*Rd + 0.9*dvd
            dvds = dvg  + dvd

            Vdsi = np.maximum(Vds -  dvds,0)
            Vgsi = np.maximum(Vgs -  dvg,0)
            Vbsi = np.maximum(Vbs -  dvg,0)

            # Drain   impact
            Vtp = self._drain_impact(Vdsi, Vtho, Delta)

            # Total charg (normalized)
            nphit, theta, qtot  = self._total_charge(Vgsi, Vtp, N)

            # Fsat calculation - Long channel device
            Fsat, eta = self._fsat_calculation(Vdsi,nphit, qtot, Vcrit)

            # Current calculation
            Jfree = self._current_calculation(qtot, Jth, L)

            #  Final
            Idx = self._final_current(Idleak, Jfree, Fsat)



        # Substituir valores NaN e infinitos por zero e valores negativos por 1e-20
        # Idx = np.nan_to_num(Idx)
        # Idx[Idx <= 0] = 1e-20 #Valor muito pequeno e positivo
        #  Wrapping up
        Id = self.__TYPE_OF_TRANSISTOR * dir * Idx
        Id = np.array(Id).transpose()
        # Id = np.nan_to_num(Id)

        # n_rows = self.n_points
        n_rows_max = 99

        # verifica se V é um vetor unidimensinal ou um que pode ser tranformado em uma matriz
        Vv = self._checks_v(V, n_rows_max, self.tension_list)

        # se i < a curva é transfer e uma matriz:
        trsf_curve = ((i < self.curv_transfer) and (Vv.ndim > 1))
        # se i >= a curva é de saída  e uma matriz:
        out_curve = (i >= self.curv_transfer) and (Vv.ndim > 1)

        # se i < a curva é transfer e um vetor:
        trsf_curve_vet = (self.type_data == 0 and Vv.ndim == 1)
        # se i >= a curva é de saída e um vetor:
        out_curve_vet = (self.type_data == 1 and Vv.ndim == 1)



        sc_factor = self.__convert_to_ampere_unit(self.scale_factor)
        curr_typic = self.__convert_to_ampere_unit(self.current_typic)
        # print(curr_typic)


        if self.type_curve == 'log':
          if trsf_curve:
              # print("ENTREI no LOG")
              chain_matrix_id[:, i] = np.log10(Idx)
          elif out_curve:
              chain_matrix_id[:, i] = -Idx / curr_typic
          elif trsf_curve_vet:
              chain_matrix_id = np.log10(Idx)
          elif out_curve_vet:
              chain_matrix_id = -Idx / curr_typic

        else:
          if self.type_curve == 'linear':
            # Curva de transferencia
            if trsf_curve:
                chain_matrix_id[:, i] = -Idx / curr_typic
                # print("ENTREI no LINEAR")
            # Curvas de saída
            elif out_curve:
                chain_matrix_id[:, i] = -Idx / curr_typic
            # Curva de transferencia
            elif trsf_curve_vet:
                chain_matrix_id = -Idx / curr_typic
            # Curvas de saída
            elif out_curve_vet:
                chain_matrix_id = -Idx / curr_typic

      return np.ravel(chain_matrix_id)
