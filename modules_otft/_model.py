
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



    def __init__(self, tension_list, n_points, type_curve='linear', current_typic='A',
                 scale_factor='A', idleak=1, mult_idleak=0, type_data=0 , type_transitor=-1,
                 curv_transfer=0, with_transistor=0.1, sr_resistance=None, curr_carry=None
                 ):


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
        Converts a number to a list if it is not already a list.

        Args:
            num (int or list): The number or list to be converted.

        Returns:
            list: A list containing the number if it is not already a list.
      """

      return num if isinstance(num, list) else [num]

    #METHODS AND AUXILIAR FUNCTIONS
    def _sign(self, x:float)->int:
      # Retorna o sinal de um número
      return np.where(x < 0, -1, np.where(x > 0, 1, 0))

    # compute the total charge based in parameters
    def _total_charge(self, Vgsi, Vtp, N):
      """
        Calculates the total charge.

        Args:
            Vgsi: The value of Vgsi.
            Vtp: The value of Vtp.

        Returns:
            tuple: Returns a tuple with the calculated values:
                nphit (float): The product of N (a constant) and PHIT (an instance variable of the class).
                theta (float): The result of the equation (Vgsi - Vtp) / nphit.
                qtot (float): The result of the equation np.log(1 + np.exp(theta)).
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
        Calculates the Jfree current.

        Args:
            qtot: The value of qtot.

        Returns:
            float: The value of Jfree current, calculated as Jth * qtot**L, where Jth and L are predefined constants.
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
        Calculates the Vpt parameter.

        Args:
            Vds: The value of Vds.

        Returns:
            float: The value of Vtp, calculated as Vtho + Vds * Delta, where Vtho and Delta are predefined constants.
      """

      Vds = np.float64(Vds)
      Vtp = Vtho + Vds * Delta
      return Vtp


    # Compute the Idx that the final current
    def _final_current(self, Idleak, Jfree, Fsat):
      """
        Calculates the final current.

        Args:
            Fsat: Calculates the value of Fsat, which is the saturation factor representing the fraction of
            the total drain current that flows through the saturation region of the MOS transistor.
            Idleak: Calculates the value of Idleak, which is the reverse leakage current that flows through
            the channel of the MOS transistor when the device is off.
            Jfree: Calculates the value of Jfree, which is the free current density that flows through
            the channel of the MOS transistor when the device is on.

        Returns:
            float: The value of the final current, calculated as Idleak + (transistor width * Jfree * Fsat),
            where the transistor width is an instance variable of the class.
      """

      Idleak = np.float64(Idleak)
      Jfree  = np.float64(Jfree)
      Fsat   = np.float64(Fsat)

      Idx = Idleak + (self.__WIDTH_TRANSISTOR * Jfree * Fsat)
      return Idx


    def _calc_dir(self, Vd, Vs):
      """
        Calculates the direction of the transistor.

        Args:
            Vd: The value of Vd, the potential difference between the drain and the source.
            Vs: The value of Vs, the potential difference between the source and the substrate of the MOS transistor.

        Returns:
            int: The value of the transistor direction, calculated as TYPE_OF_TRANSISTOR * sign(Vd - Vs),
            where TYPE_OF_TRANSISTOR is an instance variable of the class, and sign is a function that returns
            -1 if Vd - Vs is negative, 0 if Vd - Vs is zero, and 1 if Vd - Vs is positive.
      """

      Vd = np.float64(Vd)
      Vs = np.float64(Vs)

      dir = (self.__TYPE_OF_TRANSISTOR*(self._sign(Vd-Vs)))
      return dir


    def _calc_vgs_or_vbs(self, Vd, Vg, Vs):
      """
        Calculates the gate-source voltage (Vgs) or gate-bulk voltage (Vbs) value, depending on the transistor type.

        Args:
            Vd: The value of the drain voltage.
            Vg: The value of the gate voltage.
            Vs: The value of the source voltage.

        Returns:
            float: The value of the gate-source voltage (Vgs) or gate-bulk voltage (Vbs),
            calculated as the maximum between two different expressions, depending on the transistor type,
            involving the potential difference between the gate and the source and the potential difference
            between the gate and the drain or substrate.
      """

      Vgs = np.maximum(self.__TYPE_OF_TRANSISTOR * (Vg - Vs), self.__TYPE_OF_TRANSISTOR * (Vg - Vd))
      return Vgs


    # Determine the values of Fsat
    def _fsat_calculation(self, Vds, nphit, qtot, Vcrit, Lambda):
      """
        Calculates the value of Fsat and receives three parameters:
        Args:
            Vds:   The voltage between the drain and source of the transistor.
            nphit: The product of the number of majority carriers (N) and the thermal potential (PHIT) of the device.
            qtot:  The total charge of the transistor.

        Returns:
            The function uses these parameters to calculate the fraction of saturation current (Fsat)
            and the value of eta, which is a parameter used in the calculation of Fsat. Fsat is an important
            parameter in the modeling of MOS transistors, representing the fraction of current flowing
            through the transistor's channel relative to the total current flowing through the device.
      """

      Vds   = np.float64(Vds)
      nphit = np.float64(nphit)
      qtot  = np.float64(qtot)

      Vgt = nphit * qtot
      Vgn = (2 * Vgt) / (1 + np.sqrt(2 * Vgt / Vcrit))
      x = Vds / Vgn
      eta = 1 - np.tanh(x)

      y = np.float64(Vgn) / np.float64(self.__PHIT)
      try:
        # Version 1 ( with lambda):
        ll = (2 * Lambda / (np.square(y) * (1 - np.square(eta))) * (np.exp(y * (eta-1)) * (1 - (y * eta)) - (1 - y)))
        # ll = (2*Lambda) / (y*(1-np.square(eta)))
        ll = np.nan_to_num(ll,nan = Lambda)
        # tau = 1 / (1+ll)
        # at = tau / (2 - tau) # 1/(1+2*ll)
        at = 1 / (1+2*ll)
        Fsat = at * (1 - np.exp(-Vds / self.__PHIT)) / (1 + at * np.exp(-Vds / self.__PHIT))
        # print(Fsat)
        # Fsat = np.nan_to_num(Fsat)
        # print("Hello1")
        return Fsat , eta

      except ValueError as e:
        print(f"Erro  em ll, at ou Fsat erro: {e}")


    def _creat_matrix(self, V, n_rows_max=99, n_rows=50):
      # Create current empty matrix
      """
        Function that takes a vector or matrix and checks if the array passed as a parameter
        has more elements than the maximum size. If so, it creates a matrix with 50 rows and
        the number of columns parameterized by tension_list, which represents a list of input voltages
        that the model will receive. The number of columns will be defined in this way,
        which ensures that for any number of elements in the list, this "reshape" can be done.

        For the case where V > 50 and V < 99, the reshape does not occur because it is understood
        that the number of samples in this range can be accommodated, and therefore, only a
        one-dimensional vector/list is returned.

        Args:
          V: vector or matrix
          n_rows: number of rows representing the number of experimental samples collected

        Returns:
          Vector if n_rows < V < n_rows_max.
          Matrix with n_rows rows and len(tension_list) columns if V > n_rows_max
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
        The calc_vd_vg function takes as input a matrix or vector V, a list of voltages tension_list,
        an index i, and a data type type_data. The function's goal is to return two values Vd and Vg,
        which can be scalars or vectors, depending on the input parameters.
        First, the matrix V is transformed into a matrix Vv with a maximum number of rows of 70. If V
        has fewer than 50 rows, it is filled with zeros.
        Then, it checks if i is less than a certain threshold curv_transfer and if the dimension of Vv is greater than 1.
        If this condition is true, Vg receives the i-th column of Vv, and Vd receives the i-th element of
        tension_list.
        If i is greater than or equal to curv_transfer and the dimension of Vv is greater than 1, Vg receives the i-th element
        of tension_list, and Vd receives the i-th column of Vv.

        If the dimension of Vv is 1, it checks the value of the type_data variable. If type_data is 0,
        it means that V is a voltage applied to Vg, and Vd is a constant voltage defined by the i-th
        element of tension_list. In this case, Vg receives a copy of Vv, and Vd receives the i-th element
        of tension_list.

        If type_data is 1, it means that V is a voltage applied to Vd, and Vg is a constant voltage
        defined by the i-th element of tension_list. In this case, Vd receives a copy of Vv, and Vg receives
        the i-th element of tension_list.

        Finally, the function returns Vd and Vg.

        Args:
            V: mxn matrix or vector
            tension_list: list of input voltages
            i: index to iterate over the values of Vg or Vd
            type_data: input data type, type_data = 0 --> transfer data
                        type_data = 1 --> output data (output_transfer)

        Returns:
          Returns the vectors Vd and Vg, which are voltages applied to the terminals of the MOSFET transistor.
          Vd is the voltage between the drain and source of the device, while
          Vg is the voltage between the gate (gate) and the source.
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

    # Versão com Lambda
    def calc_model(self, V, Vtho=1, Delta=1, N=1, L=1, Lambda=1, Vcrit=1, Jth=1, Rs=1):
      """
        This function is part of the MOSFET transistor simulation model. It is responsible for performing calculations
        involving various physical parameters of the transistor and operating conditions to determine the current
        passing through the device.

        Args:
            V: vector of gate (or base) voltages of the transistor.
            Vtho: transistor gate threshold voltage.
            Delta: channel modulation coefficient.
            N: number of transistor channels.
            L: transistor channel length.
            Lambda: channel modulation length.
            Vcrit: transistor breakdown voltage.
            Jth: transistor saturation current.
            Rs: source (or emitter) resistance of the transistor.

        Returns:
            numpy.ndarray: A NumPy array representing the calculated model.
            Depending on the size of the input passed to this function, it will return a vector of > 50 current values
            representing the currents calculated for each voltage pair Id = F(Vgs, Vds) = scalar.
            Essentially, it returns a matrix in the form of a one-dimensional vector. Using the `np.ravel()` function
            which returns a flattened copy of the original array, with all elements of the original array
            concatenated into a single one-dimensional array. This means that the function returns an array
            with all rows of the original array concatenated into a single row.
            If V < 50, it will compute the currents only for that V.

        Example:
            >>> V = np.array([1.0, 2.0, 3.0])  # Voltage values
            >>> Vtho = 1.0  # Value of parameter Vtho
            >>> Delta = 2.0  # Value of parameter Delta
            >>> N = 3.0  # Value of parameter N
            >>> L = 4.0  # Value of parameter L
            >>> Lambda = 5.0  # Value of parameter Lambda
            >>> Vcrit = 6.0  # Value of parameter Vcrit
            >>> Jth = 7.0  # Value of parameter Jth
            >>> Rs = 8.0  # Value of parameter Rs
            >>> model = calc_model(V, Vtho, Delta, N, L, Lambda, Vcrit, Jth, Rs)
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
        Fsat, eta = self._fsat_calculation(Vds, nphit, qtot, Vcrit, Lambda)


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
            Fsat, eta = self._fsat_calculation(Vdsi,nphit, qtot, Vcrit, Lambda)

            # Current calculation
            Jfree = self._current_calculation(qtot, Jth, L)

            #  Final
            Idx = self._final_current(Idleak, Jfree, Fsat)



        # Substituir valores NaN e infinitos por zero e valores negativos por 1e-20
        Idx = np.nan_to_num(Idx)
        # Idx[Idx <= 0] = 1e-20 #Valor muito pequeno e positivo
        #  Wrapping up
        Id = self.__TYPE_OF_TRANSISTOR * dir * Idx
        Id = np.array(Id).transpose()
        Id = np.nan_to_num(Id)

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