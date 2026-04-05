from IPython.display import clear_output
from ._imports import *
class ReadData:

  def __init__(self, factor_correction=1):
    self.factor_correction = factor_correction


  # AGRUPA PATHS, TIPO DE DADOS E TENSÂO EM TUPLAS
  def _load_paths_in_tuple_data(self, path_voltages, voltage, count):
    """
      Groups paths, data type, and voltage into tuples.

      Args:
          path_voltages (list): A list of paths associated with transfer data.
          voltage (list): A list of voltages corresponding to the experiments.
          count (int): The number of transfer data in the sample.

      Returns:
          list: A list of tuples where each tuple contains (path, data type, voltage).

      Note:
          This function groups the paths according to the data type (0 for transfer, 1 for output),
          along with the corresponding voltage.

      Example:
          >>> paths = _load_paths_in_tuple_data(['path1', 'path2'], [3.0, 4.0], 1)
          >>> print(paths)
          [('path1', 0, 3.0), ('path2', 1, 4.0)]
    """

    # count é a quantidade de dados de transferencia da amostra
    paths = []
    for i in range(len(path_voltages)):
      if i < count:
        # voltage = input("Voltage do experimento transfer \n")
        paths.append((path_voltages[i], 0 , voltage[i]))
      else:
        # voltage = input("Voltage do experimento out \n")
        paths.append((path_voltages[i], 1 , voltage[i]))
    return paths


  def __convert_to_ampere_unit(self, scale):
    """
      Converts a current unit scale to amperes.

      Args:
          scale (str): The current unit scale to be converted. It should be one of the following options:
              - 'A' for amperes.
              - 'mA' for milliamperes (1 mA = 0.001 A).
              - 'uA' for microamperes (1 uA = 0.000001 A).
              - 'nA' for nanoamperes (1 nA = 0.000000001 A).
              - 'pA' for picoamperes (1 pA = 0.000000000001 A).

      Returns:
          float: The correction factor to convert the current unit scale to amperes.

      Raises:
          ValueError: If the data scale is not among the valid options.

      Example:
          >>> factor = __convert_to_ampere_unit('mA')
          >>> print(factor)
          0.001
    """

    # Identificar a escala dos dados (mA ou uA)
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


  def _classify_experimental_file(self, filename, transfer_pattern='transfer', output_pattern='output'):
    """Classifies an experimental CSV as transfer/output from its filename."""
    lowered = filename.lower()
    transfer_prefix = f'{transfer_pattern.lower()}-'
    output_prefix = f'{output_pattern.lower()}-'

    if lowered.endswith('.csv') and lowered.startswith(transfer_prefix):
      return 0
    if lowered.endswith('.csv') and lowered.startswith(output_prefix):
      return 1
    return None


  def _experimental_sort_key(self, filename):
    voltage = self._extract_voltage_from_filename(filename)
    return (voltage is None, voltage if voltage is not None else filename.lower())


  def _get_experimental_file_lists(self, directory, selected_files=None,
                                   transfer_pattern='transfer', output_pattern='output'):
    """
      Returns sorted transfer and output filenames discovered from the directory.
    """
    files = os.listdir(directory)
    selected_set = None if selected_files is None else {str(file_name).lower() for file_name in selected_files}

    transfer_files = []
    output_files = []

    for filename in files:
      curve_type = self._classify_experimental_file(filename, transfer_pattern, output_pattern)
      if curve_type is None:
        continue
      if selected_set is not None and filename.lower() not in selected_set:
        continue

      if curve_type == 0:
        transfer_files.append(filename)
      else:
        output_files.append(filename)

    transfer_files.sort(key=self._experimental_sort_key)
    output_files.sort(key=self._experimental_sort_key)
    return transfer_files, output_files


  def get_curve_counts(self, path_voltages):
    """Returns transfer/output counts from the typed curve tuples."""
    count_transfer = sum(1 for _, curve_type, _ in path_voltages if curve_type == 0)
    count_output = sum(1 for _, curve_type, _ in path_voltages if curve_type == 1)
    return count_transfer, count_output


  def read_files_experimental(  self, directory, list_tension, selected_files=None,
                                transfer_pattern=r'transfer', output_pattern=r'output'):
    """
      Reads experimental files in a directory and returns a list of paths and associated information.

      Args:
          directory (str): The directory containing the experimental files.
          list_tension (list): A list of voltages corresponding to the experiments.
          selected_files (list): An optional list of selected file names to consider.
          transfer_pattern (str): The name pattern for transfer files.
          output_pattern (str): The name pattern for output files.

      Returns:
          list: A list of tuples containing information about the files, where each tuple is in the format:
              (file path, curve type (0 for transfer, 1 for output), associated voltage).

      Example:
          >>> directory = 'data_folder'
          >>> tension_list = [1.0, 2.0, 3.0]
          >>> selected_files = ['transfer-1V.csv', 'output-2V.csv']
          >>> paths = read_files_experimental(directory, tension_list, selected_files)
          >>> print(paths)
          [('data_folder/transfer-1V.csv', 0, 1.0), ('data_folder/output-2V.csv', 1, 2.0)]
    """

    transfer_files, output_files = self._get_experimental_file_lists(
        directory,
        selected_files=selected_files,
        transfer_pattern=transfer_pattern,
        output_pattern=output_pattern
    )

    typed_paths = []
    normalized_tensions = list(list_tension) if list_tension is not None else []
    transfer_count = len(transfer_files)

    for index, transfer_file in enumerate(transfer_files):
      filename_voltage = self._extract_voltage_from_filename(transfer_file)
      associated_voltage = normalized_tensions[index] if index < len(normalized_tensions) else filename_voltage
      typed_paths.append((os.path.join(directory, transfer_file), 0, associated_voltage))

    output_offset = transfer_count
    for index, output_file in enumerate(output_files):
      filename_voltage = self._extract_voltage_from_filename(output_file)
      tension_index = output_offset + index
      associated_voltage = normalized_tensions[tension_index] if tension_index < len(normalized_tensions) else filename_voltage
      typed_paths.append((os.path.join(directory, output_file), 1, associated_voltage))

    return typed_paths


  ###__FUNÇÃO DE LEITURA SEM INTERPORLAÇÂO
  def read_pure_data(self, *args, current_typic='A', scale_transfer='A', scale_output='A', curve='linear'):
    """
      Reads experimental data, without noise (as provided), from multiple files and returns voltage and current arrays.

      Args:
          *args: A sequence of arguments, where each argument is a tuple containing:
              - The path to the CSV file containing the data.
              - The curve type (0 for transfer, 1 for output).
              - The voltage associated with the curve.
          current_typic (str): The typical unit of current in the data (e.g., 'A' for amperes).
          scale_transfer (str): The unit scale for transfer curves.
          scale_output (str): The unit scale for output curves.
          curve (str): The curve type (can be 'log' or 'linear').

      Returns:
          tuple: A tuple containing:
              - Vv (array): An array of voltages.
              - Id (array): An array of corresponding currents.
              - voltage (list): A list of voltages associated with the curves.
              - n_points (int): The minimum number of points in the curves.
              - count_transfer (int): The count of transfer curves.
              - count_output (int): The count of output curves.

      Raises:
          ValueError: If the data type is unknown or if errors occur during reading.

      Example:
          >>> args = [('data_transfer.csv', 0, 1.0), ('data_output.csv', 1, 2.0)]
          >>> Vv, Id, voltage, n_points, count_transfer, count_output = read_pure_data(*args)
          >>> print(Vv)
          [[1.0 2.0]
          [1.5 2.5]
          [2.0 3.0]]
    """


    Vv = []
    Id = []

    type_transfer = []
    type_out = []

    list_type_transfer = []
    list_type_out = []
    n_points   =  []


    # Obtem a quantidade de cada curva
    count_transfer = 0
    count_output   = 0

    # obtem o número de pontos da amostra
    def get_points(args, transfer, out):
      for arg in args:
        data = np.loadtxt(arg[0], delimiter=',')
        if arg[1] == out:
          max_points = len(data[:,1])
          n_points.append(max_points)

        elif arg[1] == transfer:
          max_points = len(data[:,0])
          n_points.append(max_points)


    get_points(args, 0, 1)
    min_value = np.min(n_points)

    # print(min_value)
    curr_typic = self.__convert_to_ampere_unit(current_typic)
    sc_transfer = self.__convert_to_ampere_unit(scale_transfer)
    sc_output = self.__convert_to_ampere_unit(scale_output)

    for arg in args:
      # print(curr_typic, sc_transfer)
      try:
          # type of curvs
          curv_transfer = 0
          curv_out = 1

          if arg[1] == curv_out:
            '''
            verifica se o segundo elemento (arg[1]) da tupla arg é igual a 1.
            Se for, isso indica que o tipo de dado é do tipo saída. Em seguida,
            lê os dados de um arquivo CSV usando pd.read_csv, onde arg[0]
            contém o caminho do arquivo
            '''
            data = pd.read_csv(arg[0], header=None)
            Vv_temp = data[0].values[:min_value]
            Id_temp = data[1].values[:min_value] * (sc_output / curr_typic)
            type_out.append((Vv_temp, Id_temp))
            list_type_out.append(arg[2])
            count_output+=1


          elif arg[1] == curv_transfer:
              data = pd.read_csv(arg[0], header=None)

              #aloca em Vv_temp apenas os pontos até min_value
              Vv_temp = data[0].values[:min_value]

              #aloca em Id_temp o log10 das correntes
              if curve == 'log':
                Id_temp = np.log10(abs((data[1].values[:min_value])))

              elif curve == 'linear':
                # Id_temp = data[1].values[:min_value]
                Id_temp = (-1)*abs((data[1].values[:min_value] * sc_transfer / curr_typic))
              else:
                raise ValueError("Option not valide\n")

              type_transfer.append((Vv_temp, Id_temp))
              list_type_transfer.append(arg[2])
              count_transfer += 1
          else:
              raise ValueError(f"Tipo de dado desconhecido: {arg[1]}")

      except ValueError as err:
          if "divide by zero encountered in log10" or "invalid value encountered in log10" in str(err):
              print("Possivelmente a entrada é 'Out' e não 'Transfer'.")
          else:
              raise err

    # verifica se o conjunto de pontos passado da amostra possui - ou + dados do que foi passado por nv
    # se for - ou + ele completa com
    def process_type(type_, Vv, Id, nv):
      for v, i in type_:
          if len(v) > nv:
              idx = np.round(np.linspace(0, len(v) - 1, nv)).astype(int)
              v = v[idx]
              i = i[idx]
          else:
              v = np.pad(v, (0, nv - len(v)), mode='edge')
              i = np.pad(i, (0, nv - len(i)), mode='edge')
          Vv.append(v)
          Id.append(i)
      return Vv, Id

    Vv, Id = process_type(type_transfer, Vv, Id, min_value)
    Vv, Id = process_type(type_out, Vv, Id, min_value)

    Vv = np.vstack(Vv).T
    Id = np.vstack(Id).T
    voltage = list_type_transfer + list_type_out

    n_points = np.min(n_points)

    return Vv, Id, voltage, n_points, count_transfer, count_output


  # FAZ A LEITURA DOS DADOS E INTERPOLA COM O VALOR DA MAIOR QTDE DE PONTOS QUE ENCONTRA
  def read_interpoll_datas(self, *args, current_typic='A', scale_transfer='A', scale_output='A', curve='linear'):
    """
      Reads experimental data from multiple files, interpolates to the maximum number of points, and returns voltage and current arrays.

      Args:
          *args: A sequence of arguments, where each argument is a tuple containing:
              - The path to the CSV file containing the data.
              - The curve type (0 for transfer, 1 for output).
              - The voltage associated with the curve.
          current_typic (str): The typical unit of current in the data (e.g., 'A' for amperes).
          scale_transfer (str): The unit scale for transfer curves.
          scale_output (str): The unit scale for output curves.
          curve (str): The curve type (can be 'log' or 'linear').

      Returns:
          tuple: A tuple containing:
              - Vv (array): An array of interpolated voltages.
              - Id (array): An array of corresponding interpolated currents.
              - voltage (list): A list of voltages associated with the curves.
              - nv (int): The maximum number of interpolated points.
              - count_transfer (int): The count of transfer curves.
              - count_output (int): The count of output curves.

      Raises:
          ValueError: If the data type is unknown or if errors occur during reading.

      Example:
          >>> args = [('data_transfer.csv', 0, 1.0), ('data_output.csv', 1, 2.0)]
          >>> Vv, Id, voltage, nv, count_transfer, count_output = read_interpolated_data(*args)
          >>> print(Vv)
          [[1.0 2.0]
          [1.5 2.5]
          [2.0 3.0]]
    """

    Vv = []
    Id = []

    type_transfer = []
    type_out = []

    list_type_transfer = []
    list_type_out = []
    n_points   =  []

    # Obtem a quantidade de cada curva
    count_transfer = 0
    count_output   = 0


    # Obtem o número de pontos da amostra
    def get_points(args, transfer, out):
      for arg in args:
        data = np.loadtxt(arg[0], delimiter=',')
        if arg[1] == out:
          Id_temp = data[:,1]
          max_points = len(Id_temp)
          n_points.append(max_points)

        elif arg[1] == transfer:
          max_points = len(data[:,0])
          n_points.append(max_points)


    get_points(args, 0, 1)
    nv = np.max(n_points)

    for arg in args:
      # type of curvs
      curv_transfer = 0
      curv_out = 1

      curr_typic  = self.__convert_to_ampere_unit(current_typic)
      sc_transfer = self.__convert_to_ampere_unit(scale_transfer)
      sc_output   = self.__convert_to_ampere_unit(scale_output)

      # print(curr_typic, sc_transfer)

      try:
        if arg[1] == curv_out:
            data = np.loadtxt(arg[0], delimiter=',')
            Vv_temp = data[:, 0]
            Id_temp = (data[:, 1])

            type_out.append((Vv_temp, Id_temp * (sc_output / curr_typic)))
            list_type_out.append(arg[2])
            count_output+=1

        elif arg[1] == curv_transfer:
            data = np.loadtxt(arg[0], delimiter=',')
            Vmax, Vmin = np.max(data[:,0]), np.min(data[:,0])
            Vv_temp = np.linspace(Vmin, Vmax, nv)
            Id_temp = np.interp(Vv_temp, data[:,0], data[:,1])

            #plotar dados em escala log ou linear só para o caso em que vamos otimizar linear também
            if curve == 'log':
              Id_temp = np.log10(abs(Id_temp))

            elif curve == 'linear':
              # olhar esse multiplicação por -1 (ajustar)
              #usar um factor value 2 para diferenciar as duas curvas (em A)
              Id_temp = (-1)*abs((Id_temp * sc_transfer / curr_typic))
              # Id_temp = abs(Id_temp / max_value)
            else:
              raise ValueError("Option not valide\n")

            type_transfer.append((Vv_temp, Id_temp))
            list_type_transfer.append(arg[2])
            count_transfer+=1
        else:
            raise ValueError(f"Tipo de dado desconhecido: {arg[1]}")

      except ValueError as err:
        if "divide by zero encountered in log10" or "invalid value encountered in log10" in str(err):
            print("Possivelmente a entrada é 'Out' e não 'Transfer'.")
        else:
            raise err

    # verifica se o conjunto de pontos passado da amostra possui - ou + dados do que foi passado por nv
    # se for - ou + ele completa com
    def process_type(type_, Vv, Id, nv):
      for v, i in type_:
          if len(v) > nv:
              idx = np.round(np.linspace(0, len(v) - 1, nv)).astype(int)
              v = v[idx]
              i = i[idx]
          else:
              v = np.pad(v, (0, nv - len(v)), mode='edge')
              i = np.pad(i, (0, nv - len(i)), mode='edge')
          Vv.append(v)
          Id.append(i)
      return Vv, Id

    Vv, Id = process_type(type_transfer, Vv, Id, nv)
    Vv, Id = process_type(type_out, Vv, Id, nv)

    Vv = np.vstack(Vv).T
    Id = np.vstack(Id).T
    voltage = list_type_transfer + list_type_out

    # n_points = np.max(n_points)
    return Vv, Id, voltage, nv, count_transfer, count_output

###############_FUNÇÔES AUXILIARES PARA AGRUPAR DADOS PARA PLOTAGEM DO GRAFICO_####################################

  def group_by_trasfer(self, count_transfer, Vv, Id, model_id, model_id_opt=[], compare=False):
    """
      Groups transfer data for analysis and comparison purposes.

      Args:
          count_transfer (int): The number of transfer curves.
          Vv (array): An array of voltages.
          Id (array): An array of corresponding currents.
          model_id (list): A list of model IDs associated with the transfer curves.
          model_id_opt (list, optional): An optional list of optimized model IDs. It can be empty.
          compare (bool, optional): If True, optimized data is added to the input data.

      Returns:
          tuple: A tuple containing two lists:
              - in_model_data (list): A list of tuples containing voltages and model IDs of the transfer curves.
              - in_exp_data (list): A list of voltages and corresponding currents of the transfer curves.

      Raises:
          ValueError: If there is an error in reading the data.

      Example:
          >>> count_transfer = 3
          >>> Vv = [[1.0, 2.0], [1.5, 2.5], [2.0, 3.0]]
          >>> Id = [[0.1, 0.2], [0.15, 0.25], [0.2, 0.3]]
          >>> model_id = [1, 2, 3]
          >>> in_model_data, in_exp_data = group_by_transfer(count_transfer, Vv, Id, model_id)
          >>> print(in_model_data)
          [([1.0, 1.5, 2.0], 1), ([1.0, 1.5, 2.0], 2), ([1.0, 1.5, 2.0], 3)]
    """

    in_model_data = []
    in_exp_data = []

    # Cria in_model_data de forma iterativa
    for i in range(count_transfer):
      in_model_data.append((Vv[:, i], model_id[i]))


    # Adiciona a in_model_data os dados otimizados
    if compare:
      for i in range(count_transfer):
        in_model_data.append((Vv[:, i], model_id_opt[i]))

    # Cria in_exp_data de forma iterativa sem assumir pares de curvas.
    # Isso evita que, quando count_transfer for ímpar, a primeira curva
    # de saída seja indevidamente incluída nas curvas de transferência.
    if count_transfer >= 1:
      for i in range(count_transfer):
        in_exp_data.extend([Vv[:, i], Id[:, i]])

    elif count_transfer == 0:
      in_model_data = []
      in_exp_data   = []
    else:
        raise ValueError("Error in read data")

    return in_model_data, in_exp_data


  # AGRUPA DOS DADOS DE SAÍDA
  def group_by_output(self, count_output, count_transfer, Vv, Id, model_id, model_id_opt=[], compare=False):
    """
      Groups output data for analysis and comparison purposes.

      Args:
          count_output (int): The number of output curves.
          count_transfer (int): The number of transfer curves.
          Vv (array): An array of voltages.
          Id (array): An array of corresponding currents.
          model_id (list): A list of model IDs associated with both transfer and output curves.
          model_id_opt (list, optional): An optional list of optimized model IDs. It can be empty.
          compare (bool, optional): If True, optimized data is added to the input data.

      Returns:
          tuple: A tuple containing two lists:
              - out_model_data (list): A list of tuples containing voltages and model IDs of the output curves.
              - out_exp_data (list): A list of voltages and corresponding currents of the output curves.

      Example:
          >>> count_output = 2
          >>> count_transfer = 3
          >>> Vv = [[1.0, 2.0], [1.5, 2.5], [2.0, 3.0], [3.0, 4.0], [4.0, 5.0]]
          >>> Id = [[0.1, 0.2], [0.15, 0.25], [0.2, 0.3], [0.3, 0.4], [0.4, 0.5]]
          >>> model_id = [1, 2, 3, 4, 5]
          >>> in_model_data, in_exp_data = group_by_output(count_output, count_transfer, Vv, Id, model_id)
          >>> print(in_model_data)
          [([3.0, 4.0], 4), ([4.0, 5.0], 5)]
    """


    out_model_data = []
    out_exp_data = []

    # Cria out_model_data de forma iterativa
    max_data = ( int(count_output) + int(count_transfer) )
    for i in range(count_transfer, max_data):
      out_model_data.append((Vv[:, i], model_id[i]))


    if compare:
      for i in range(count_transfer, max_data):
        out_model_data.append((Vv[:, i], model_id_opt[i]))


    # Cria out_exp_data de forma iterativa
    for i in range(count_transfer, max_data):
      out_exp_data.extend([ Vv[:, i], Id[:, i] ])
    return out_model_data, out_exp_data


  # CRIA INSTÂNCIAS DO MODELO
  def create_models_datas(self, model, n_points, type_curve, parameters, tensions, Vv, idleak,
                          w, count, tp_tst, current_typic='A', scale_factor='A',
                          res=None, curr=None):
    """
      Creates model instances based on input data and provided parameters.

      Args:
          model (object): The model to be used for creating the instances.
          n_points (int): The number of data points.
          type_curve (str): The curve type ('log' or 'linear').
          parameters (tuple): A tuple of model parameters.
          tensions (list): A list of voltages associated with the input data.
          Vv (array): An array of input data voltages.
          idleak (float, list): The static idleak value or a list of dynamic idleak values.
          w (float): Indicates the width of a transistor for a given technology.
          count (int): The index limit for classifying input data.
          lambda_factor (bool): Defines if the lambda factor is present in estimating other parameters.
          tp_tst (int): The type of transistor to be used in the model.
          current_typic (str, optional): The typical unit of current in the data (e.g., 'A' for amperes).
          scale_factor (str, optional): The unit scale for the data.
          res (float, optional): The serial resistance of the transistor.
          curr (float, optional): The transistor transport current.

      Returns:
          list: A list of model instances created based on the provided data.

      Example:
          >>> class MyModel:
          ...     def __init__(self, voltage, n_points, curve_type, current_typic,
          ...                  scale_factor, idleak, mult_idleak, type_data,
          ...                  with_transistor, sr_resistance, curr_carry, type_transistor):
          ...         pass
          ...
          ...     def set_lambda_factor(self, lambda_factor):
          ...         pass
          ...
          ...     def calc_model(self, Vv, *parameters):
          ...         pass
          ...
          >>> n_points = 100
          >>> type_curve = 'linear'
          >>> parameters = (1.0, 2.0, 3.0)
          >>> tensions = [1.0, 2.0, 3.0]
          >>> Vv = [[1.0, 2.0], [1.5, 2.5], [2.0, 3.0]]
          >>> idleak = 0.01
          >>> w = 0.01
          >>> count = 2
          >>> lambda_factor = False
          >>> tp_tst = 1
          >>> model_instances = create_models_datas(MyModel, n_points, type_curve, parameters,
          ...                                       tensions, Vv, idleak, w, count, lambda_factor, tp_tst)
          >>> print(model_instances)
          [<MyModel object at 0x7f84ac50b610>, <MyModel object at 0x7f84ac50b5e0>]
    """

    # input datas Transfer
    Model_data = []

    # Calcula modelo baseado no idleak estático
    def idleak_int(value, i, select=True):
      if select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak, mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Chama modelo
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))

      elif not select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak=0, mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Chama modelo
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))


      else:
        ValueError(" 'select possible 'True' or 'False' ")


    # Calcula modelo baseado no idleak dinâmico
    def idleak_list(value, i, select=True):
      if select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak[i], mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Chama modelo
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))

      elif not select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak=0, mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Chama modelo
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))

      else:
        ValueError(" 'select possible 'True' or 'False' ")

    # Itera sobre os valores de Idleak
    for i in range(len(tensions)):
      if isinstance(idleak, float) or isinstance(idleak, int):
        if i < count:
          idleak_int(0, i)

        else:
          idleak_int(1, i)


      elif isinstance(idleak, list):
        if i < count:
          idleak_list(0, i)

        else:
          idleak_list(1, i, False)

      else:
        print("Idleak must be an integer or a list!")
        return None

    return Model_data


  def _extract_voltage_from_filename(self, file_path):
    """Extracts the reference voltage encoded in the CSV filename."""
    filename = os.path.basename(str(file_path))
    match = re.search(r'(\d+(?:\.\d+)?)\s*V?(?=\.csv$)', filename, flags=re.IGNORECASE)
    return float(match.group(1)) if match else None


  def _get_curve_current_factor(self, curve_type=None, current_typic='A',
                                scale_transfer='A', scale_output='A'):
    """Returns the factor that converts a curve current to the working unit."""
    current_typic_factor = self.__convert_to_ampere_unit(current_typic)
    curve_scale = scale_transfer if curve_type in (0, 'transfer') else scale_output
    curve_scale_factor = self.__convert_to_ampere_unit(curve_scale)
    return float(curve_scale_factor / current_typic_factor)


  def _read_curve_points(self, csv_path, curve_type=None, current_typic='A',
                         scale_transfer='A', scale_output='A'):
    """Reads a two-column CSV curve and returns voltage/current arrays."""
    data = np.loadtxt(csv_path, delimiter=',')
    if data.ndim == 1:
      data = np.atleast_2d(data)

    voltages = np.asarray(data[:, 0], dtype=float)
    currents = np.asarray(data[:, 1], dtype=float)
    current_factor = self._get_curve_current_factor(
        curve_type,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )
    return voltages, np.abs(currents * current_factor)


  def _collapse_duplicate_axis(self, axis_values, target_values):
    """Collapses repeated axis coordinates using the mean target value."""
    work_df = pd.DataFrame({
        'x_value': np.asarray(axis_values, dtype=float),
        'target': np.asarray(target_values, dtype=float)
    })
    work_df['axis_key'] = work_df['x_value'].round(9)

    grouped = (
        work_df.groupby('axis_key', as_index=False)
        .agg(x_value=('x_value', 'mean'), target=('target', 'mean'))
        .sort_values('x_value', kind='mergesort')
        .reset_index(drop=True)
    )
    return grouped['x_value'].to_numpy(dtype=float), grouped['target'].to_numpy(dtype=float)


  def _prepare_curve_for_interpolation(self, csv_path, curve_type=None, current_typic='A',
                                       scale_transfer='A', scale_output='A'):
    """Loads, sorts and collapses a curve before interpolation."""
    voltages, currents = self._read_curve_points(
        csv_path,
        curve_type=curve_type,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )
    return self._collapse_duplicate_axis(voltages, currents)


  def _get_curve_voltage_range(self, csv_path):
    """Returns the effective interpolation range of a curve."""
    voltages, _ = self._prepare_curve_for_interpolation(csv_path)
    return {
        'min_voltage': float(np.min(voltages)),
        'max_voltage': float(np.max(voltages)),
    }


  def _infer_curve_voltage_sign(self, csv_path, fallback_voltage=None):
    """Infers the sign convention of a curve voltage axis."""
    if fallback_voltage not in (None, 0, 0.0):
      return -1.0 if float(fallback_voltage) < 0 else 1.0

    voltage_range = self._get_curve_voltage_range(csv_path)
    min_voltage = voltage_range['min_voltage']
    max_voltage = voltage_range['max_voltage']
    if max_voltage <= 0:
      return -1.0
    if min_voltage >= 0:
      return 1.0
    return -1.0 if abs(min_voltage) >= abs(max_voltage) else 1.0


  def _get_signed_filename_voltage(self, csv_path, fallback_voltage=None):
    """Reads the voltage encoded in the filename and restores its sign."""
    filename_voltage = self._extract_voltage_from_filename(csv_path)
    if filename_voltage is None:
      if fallback_voltage is None:
        return None
      return float(fallback_voltage)

    sign = self._infer_curve_voltage_sign(csv_path, fallback_voltage=fallback_voltage)
    return float(sign * abs(filename_voltage))


  def _value_in_voltage_window(self, voltage_value, voltage_window, tolerance=1e-6):
    """Checks whether a voltage lies inside an interpolation window."""
    if voltage_value is None or voltage_window is None:
      return False

    return (
        float(voltage_window['min_voltage']) - tolerance
        <= float(voltage_value)
        <= float(voltage_window['max_voltage']) + tolerance
    )


  def _resolve_largest_common_voltage(self, voltage_window, requested_voltage):
    """Finds the largest common voltage compatible with the requested polarity."""
    if voltage_window is None:
      return None

    min_voltage = float(voltage_window['min_voltage'])
    max_voltage = float(voltage_window['max_voltage'])
    if min_voltage > max_voltage:
      return None

    if requested_voltage is None:
      return min_voltage if abs(min_voltage) >= abs(max_voltage) else max_voltage

    requested_voltage = float(requested_voltage)
    if requested_voltage < 0:
      return min_voltage if min_voltage <= 0 else None
    if requested_voltage > 0:
      return max_voltage if max_voltage >= 0 else None
    return 0.0 if min_voltage <= 0 <= max_voltage else None


  def _resolve_common_vds_reference(self, reference_transfer_curve, output_curves):
    """Resolves a valid VDS reference common to the reference transfer and outputs."""
    reference_transfer_path, _, reference_transfer_loaded_voltage = reference_transfer_curve
    reference_transfer_filename_voltage = self._get_signed_filename_voltage(
        reference_transfer_path,
        fallback_voltage=reference_transfer_loaded_voltage,
    )
    reference_transfer_range = self._get_curve_voltage_range(reference_transfer_path)
    output_ranges = [self._get_curve_voltage_range(output_path) for output_path, _, _ in output_curves]

    common_min_voltage = max(
        [reference_transfer_range['min_voltage']]
        + [voltage_range['min_voltage'] for voltage_range in output_ranges]
    )
    common_max_voltage = min(
        [reference_transfer_range['max_voltage']]
        + [voltage_range['max_voltage'] for voltage_range in output_ranges]
    )

    common_voltage_window = None
    if common_min_voltage <= common_max_voltage:
      common_voltage_window = {
          'min_voltage': float(common_min_voltage),
          'max_voltage': float(common_max_voltage),
      }

    vds_ref_requested = reference_transfer_filename_voltage
    if self._value_in_voltage_window(vds_ref_requested, common_voltage_window):
      vds_ref_effective = float(vds_ref_requested)
      reference_mode = 'filename_voltage'
    else:
      vds_ref_effective = self._resolve_largest_common_voltage(
          common_voltage_window,
          vds_ref_requested,
      )
      reference_mode = 'largest_common_voltage' if vds_ref_effective is not None else 'no_common_voltage'

    return {
        'reference_transfer_file': os.path.basename(reference_transfer_path),
        'reference_transfer_loaded_voltage': (
            None if reference_transfer_loaded_voltage is None else float(reference_transfer_loaded_voltage)
        ),
        'reference_transfer_filename_voltage': reference_transfer_filename_voltage,
        'reference_transfer_voltage_range': reference_transfer_range,
        'common_output_voltage_range': common_voltage_window,
        'vds_ref_requested': vds_ref_requested,
        'vds_ref_effective': vds_ref_effective,
        'reference_mode': reference_mode,
    }


  def _interpolate_current_at_voltage(self, csv_path, target_voltage, curve_type=None,
                                      current_typic='A', scale_transfer='A', scale_output='A'):
    """Interpolates the current value in a curve for a given voltage."""
    voltages, currents = self._prepare_curve_for_interpolation(
        csv_path,
        curve_type=curve_type,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )
    return float(np.interp(target_voltage, voltages, currents))


  def _curve_contains_voltage(self, csv_path, target_voltage, tolerance=1e-6):
    """Checks whether a curve supports a reference voltage from the JSON input."""
    voltages, _ = self._prepare_curve_for_interpolation(csv_path)
    min_voltage = float(np.min(voltages))
    max_voltage = float(np.max(voltages))
    nearest_voltage = float(voltages[np.argmin(np.abs(voltages - target_voltage))])
    in_range = min_voltage - tolerance <= target_voltage <= max_voltage + tolerance
    exact_match = bool(np.isclose(nearest_voltage, target_voltage, atol=tolerance))
    return {
        'in_range': in_range,
        'exact_match': exact_match,
        'nearest_voltage': nearest_voltage,
        'min_voltage': min_voltage,
        'max_voltage': max_voltage,
    }


  def _interpolate_voltage_for_current(self, csv_path, target_current, reference_voltage=None,
                                       curve_type=None, current_typic='A',
                                       scale_transfer='A', scale_output='A',
                                       tolerance=1e-12):
    """
      Finds the voltage in a transfer curve that best matches a target current.

      If multiple crossings exist, chooses the one closest to the reference voltage.
    """
    voltages, currents = self._prepare_curve_for_interpolation(
        csv_path,
        curve_type=curve_type,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )
    current_range = {
        'min_current': float(np.min(currents)),
        'max_current': float(np.max(currents)),
    }
    if (
        float(target_current) < current_range['min_current'] - tolerance
        or float(target_current) > current_range['max_current'] + tolerance
    ):
      return {
          'voltage': None,
          'status': 'target_current_out_of_transfer_range',
          'current_range': current_range,
      }

    delta = currents - float(target_current)
    crossing_indices = np.where(delta[:-1] * delta[1:] <= 0)[0]
    candidates = []

    for idx in crossing_indices:
      x1, x2 = voltages[idx], voltages[idx + 1]
      y1, y2 = currents[idx], currents[idx + 1]

      if np.isclose(y1, y2):
        candidates.append(float((x1 + x2) / 2.0))
        continue

      interpolated_voltage = x1 + (target_current - y1) * (x2 - x1) / (y2 - y1)
      candidates.append(float(interpolated_voltage))

    if candidates:
      best_voltage = candidates[0]
      if reference_voltage is not None:
        best_voltage = min(candidates, key=lambda voltage: abs(voltage - reference_voltage))
      return {
          'voltage': float(best_voltage),
          'status': 'matched',
          'current_range': current_range,
      }

    return {
        'voltage': None,
        'status': 'no_transfer_current_crossing',
        'current_range': current_range,
    }


  def _find_reference_transfer_curve(self, transfer_curves):
    """Selects the transfer curve with the highest absolute polarization."""
    if not transfer_curves:
      return None

    def _curve_magnitude(curve):
      curve_path, _, loaded_voltage = curve
      filename_voltage = self._get_signed_filename_voltage(curve_path, fallback_voltage=loaded_voltage)
      if filename_voltage is not None:
        return abs(float(filename_voltage))
      if loaded_voltage is None:
        return 0.0
      return abs(float(loaded_voltage))

    return max(transfer_curves, key=_curve_magnitude)


  def _limit_effective_gate_voltage(self, curve_name, nominal_voltage, raw_effective_voltage,
                                    previous_nominal_voltage=None, previous_effective_voltage=None,
                                    min_gate_separation=0.5):
    """Constrains |Vgs_eff| to remain strictly increasing across output curves."""
    if previous_effective_voltage is None or previous_nominal_voltage is None:
      return float(raw_effective_voltage), None, False

    raw_magnitude = abs(float(raw_effective_voltage))
    previous_magnitude = abs(float(previous_effective_voltage))
    if raw_magnitude > previous_magnitude:
      return float(raw_effective_voltage), None, False

    nominal_gap = abs(abs(float(nominal_voltage)) - abs(float(previous_nominal_voltage)))
    required_gap = max(float(min_gate_separation), float(nominal_gap))
    limited_magnitude = previous_magnitude + required_gap
    signal = -1.0 if float(nominal_voltage) < 0 else 1.0
    limited_voltage = signal * limited_magnitude
    warning = (
        f"Aviso: Compressão de gate detectada na curva {curve_name}. "
        "Shift limitado para manter consistência física."
    )
    return float(limited_voltage), warning, True


  def _adjust_shift_with_preprocess(self, automatic_shift, pre_process_shift_volt_data=None):
    """Adjusts the local shift using the preprocessing shift while preserving local sign."""
    automatic_shift = float(automatic_shift)
    if pre_process_shift_volt_data in ("", None):
      return automatic_shift, False

    preprocess_shift = float(pre_process_shift_volt_data)
    shift_signal = -1.0 if automatic_shift < 0 else 1.0
    adjusted_magnitude = abs(preprocess_shift - abs(automatic_shift))
    adjusted_shift = shift_signal * adjusted_magnitude
    return float(adjusted_shift), True


  def estimate_output_shifts(self, path_voltages, min_gate_separation=0.5,
                             pre_process_shift_volt_data=None, current_typic='A',
                             scale_transfer='A', scale_output='A'):
    """
      Estimates automatic output shifts using a fixed VDS reference taken from
      the transfer curve with the highest polarization magnitude.
    """
    transfer_curves = [curve for curve in path_voltages if curve[1] == 0]
    output_curves = [curve for curve in path_voltages if curve[1] == 1]

    auto_shifts = [0.0] * len(output_curves)
    shift_details = []
    if not output_curves:
      return auto_shifts, shift_details

    reference_transfer_curve = self._find_reference_transfer_curve(transfer_curves)
    if reference_transfer_curve is None:
      for output_path, _, output_loaded_voltage in output_curves:
        shift_details.append({
            'output_file': os.path.basename(output_path),
            'output_nominal_voltage': float(output_loaded_voltage),
            'output_filename_voltage': self._extract_voltage_from_filename(output_path),
            'reference_transfer_file': None,
            'reference_transfer_loaded_voltage': None,
            'reference_transfer_filename_voltage': None,
            'reference_transfer_voltage_range': None,
            'common_output_voltage_range': None,
            'vds_ref_requested': None,
            'vds_ref_effective': None,
            'id_at_vds_ref': None,
            'transfer_current_range': None,
            'vgs_nominal': float(output_loaded_voltage),
            'vgs_effective_raw': None,
            'vgs_effective_limited': None,
            'delta_vgs': 0.0,
            'automatic_shift_base': 0.0,
            'automatic_shift': 0.0,
            'pre_process_shift_volt_data': pre_process_shift_volt_data,
            'automatic_shift_adjusted_by_preprocess': False,
            'status': 'no_reference_transfer',
            'reference_mode': 'no_reference_transfer',
            'warning': None,
        })
      return auto_shifts, shift_details

    reference_transfer_path, _, _ = reference_transfer_curve
    reference_info = self._resolve_common_vds_reference(reference_transfer_curve, output_curves)
    vds_ref_requested = reference_info['vds_ref_requested']
    vds_ref_effective = reference_info['vds_ref_effective']
    ordered_details = [{} for _ in output_curves]
    if vds_ref_effective is None:
      for original_index, (output_path, _, output_loaded_voltage) in enumerate(output_curves):
        ordered_details[original_index] = {
            'output_file': os.path.basename(output_path),
            'output_nominal_voltage': float(output_loaded_voltage),
            'output_filename_voltage': self._extract_voltage_from_filename(output_path),
            'reference_transfer_file': reference_info['reference_transfer_file'],
            'reference_transfer_loaded_voltage': reference_info['reference_transfer_loaded_voltage'],
            'reference_transfer_filename_voltage': reference_info['reference_transfer_filename_voltage'],
            'reference_transfer_voltage_range': reference_info['reference_transfer_voltage_range'],
            'common_output_voltage_range': reference_info['common_output_voltage_range'],
            'vds_ref_requested': vds_ref_requested,
            'vds_ref_effective': None,
            'id_at_vds_ref': None,
            'transfer_current_range': None,
            'vgs_nominal': float(output_loaded_voltage),
            'vgs_effective_raw': None,
            'vgs_effective_limited': None,
            'delta_vgs': 0.0,
            'automatic_shift_base': 0.0,
            'automatic_shift': 0.0,
            'pre_process_shift_volt_data': pre_process_shift_volt_data,
            'automatic_shift_adjusted_by_preprocess': False,
            'status': 'no_common_vds_reference',
            'reference_mode': reference_info['reference_mode'],
            'warning': (
                'Aviso: Nenhum VDS comum foi encontrado entre a transfer de referência '
                'e as curvas de saída desta tecnologia.'
            ),
        }
      return auto_shifts, ordered_details

    ordered_outputs = sorted(
        enumerate(output_curves),
        key=lambda item: abs(float(item[1][2]))
    )
    previous_nominal_voltage = None
    previous_effective_voltage = None

    for original_index, (output_path, _, output_loaded_voltage) in ordered_outputs:
      output_nominal_voltage = float(output_loaded_voltage)
      output_filename_voltage = self._extract_voltage_from_filename(output_path)
      output_voltage_match = self._curve_contains_voltage(output_path, vds_ref_effective)
      detail = {
          'output_file': os.path.basename(output_path),
          'output_nominal_voltage': output_nominal_voltage,
          'output_filename_voltage': output_filename_voltage,
          'reference_transfer_file': reference_info['reference_transfer_file'],
          'reference_transfer_loaded_voltage': reference_info['reference_transfer_loaded_voltage'],
          'reference_transfer_filename_voltage': reference_info['reference_transfer_filename_voltage'],
          'reference_transfer_voltage_range': reference_info['reference_transfer_voltage_range'],
          'common_output_voltage_range': reference_info['common_output_voltage_range'],
          'vds_ref_requested': vds_ref_requested,
          'vds_ref_effective': vds_ref_effective,
          'id_at_vds_ref': None,
          'transfer_current_range': None,
          'vgs_nominal': output_nominal_voltage,
          'vgs_effective_raw': None,
          'vgs_effective_limited': None,
          'delta_vgs': 0.0,
          'automatic_shift_base': 0.0,
          'automatic_shift': 0.0,
          'pre_process_shift_volt_data': pre_process_shift_volt_data,
          'automatic_shift_adjusted_by_preprocess': False,
          'output_voltage_match': output_voltage_match,
          'status': 'no_common_vds_reference',
          'reference_mode': reference_info['reference_mode'],
          'warning': None,
      }

      if not output_voltage_match['in_range']:
        ordered_details[original_index] = detail
        continue

      id_at_vds_ref = self._interpolate_current_at_voltage(
          output_path,
          vds_ref_effective,
          curve_type=1,
          current_typic=current_typic,
          scale_transfer=scale_transfer,
          scale_output=scale_output,
      )
      voltage_match = self._interpolate_voltage_for_current(
          reference_transfer_path,
          id_at_vds_ref,
          reference_voltage=output_nominal_voltage,
          curve_type=0,
          current_typic=current_typic,
          scale_transfer=scale_transfer,
          scale_output=scale_output,
      )
      detail['id_at_vds_ref'] = float(id_at_vds_ref)
      detail['transfer_current_range'] = voltage_match.get('current_range')

      if voltage_match.get('voltage') is None:
        detail.update({
            'status': voltage_match.get('status', 'target_current_out_of_transfer_range'),
            'warning': (
                'Aviso: A corrente de referência da curva de saída ficou fora da faixa '
                'válida da curva de transferência.'
                if voltage_match.get('status') == 'target_current_out_of_transfer_range'
                else 'Aviso: Nenhum cruzamento físico válido foi encontrado na curva de transferência.'
            ),
        })
        ordered_details[original_index] = detail
        continue

      vgs_effective_raw = float(voltage_match['voltage'])
      vgs_effective_limited, warning, was_limited = self._limit_effective_gate_voltage(
          os.path.basename(output_path),
          output_nominal_voltage,
          vgs_effective_raw,
          previous_nominal_voltage=previous_nominal_voltage,
          previous_effective_voltage=previous_effective_voltage,
          min_gate_separation=min_gate_separation,
      )

      delta_vgs = float(vgs_effective_limited - output_nominal_voltage)
      automatic_shift_base = float(output_nominal_voltage - vgs_effective_limited)
      automatic_shift, adjusted_by_preprocess = self._adjust_shift_with_preprocess(
          automatic_shift_base,
          pre_process_shift_volt_data=pre_process_shift_volt_data,
      )

      detail.update({
          'vgs_effective_raw': vgs_effective_raw,
          'vgs_effective_limited': float(vgs_effective_limited),
          'delta_vgs': delta_vgs,
          'automatic_shift_base': automatic_shift_base,
          'automatic_shift': automatic_shift,
          'pre_process_shift_volt_data': pre_process_shift_volt_data,
          'automatic_shift_adjusted_by_preprocess': adjusted_by_preprocess,
          'status': 'matched_with_monotonicity_limit' if was_limited else 'matched',
          'warning': warning,
      })

      auto_shifts[original_index] = automatic_shift
      ordered_details[original_index] = detail
      previous_nominal_voltage = output_nominal_voltage
      previous_effective_voltage = vgs_effective_limited

    return auto_shifts, ordered_details


  def calculate_automatic_output_shifts(self, path_voltages, pre_process_shift_volt_data=None,
                                        current_typic='A', scale_transfer='A', scale_output='A'):
    """
      Backward-compatible wrapper around the VDS-match shift estimator.
    """
    return self.estimate_output_shifts(
        path_voltages,
        pre_process_shift_volt_data=pre_process_shift_volt_data,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )


  def estimate_output_curve_shifts(self, path_voltages, pre_process_shift_volt_data=None,
                                   current_typic='A', scale_transfer='A', scale_output='A'):
    """Compatibility alias for callers using the older method name."""
    return self.estimate_output_shifts(
        path_voltages,
        pre_process_shift_volt_data=pre_process_shift_volt_data,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )


  # Faz o deslocamento de tensão na lista de tensões para as curvas de saída
  def apply_shifts(self, path_voltages, shift_tesion):
    """
      Applies a voltage shift to the list of voltages for the output curves.

      Args:
          path_voltages (list): Curve tuples with type information.
          shift_tension (list): A list of voltage shift values.

      Returns:
          list: A list of voltages updated with the applied shifts.

      Example:
          >>> path_voltages = [('transfer-1V.csv', 0, 1.0), ('output-2V.csv', 1, 2.0)]
          >>> shift_tension = [0.1, -0.2]
          >>> updated_tensions = apply_shifts(path_voltages, shift_tension)
          >>> print(updated_tensions)
          [1.0, 2.1]
    """

    result_list = []
    shifted_values = []
    count_transfer, _ = self.get_curve_counts(path_voltages)
    list_tension = [curve[2] for curve in path_voltages]

    if count_transfer > 0:
      # Separate the elements that will not be altered and the remaining elements
      list_temp_trf = list_tension[:count_transfer]
      # print(list_temp_trf)
      after_values = list_tension[count_transfer:]
      # print(after_values)
    else:
      # size of the shift_list
      qtde_tension_output  = len(shift_tesion)
      qtde_tension_in_list = len(list_tension)
      window_cut = 0

      if  qtde_tension_in_list >= qtde_tension_output:
        window_cut =  (qtde_tension_in_list - qtde_tension_output)
      else:
        print('the list of shifts you entered is larger than the original list, adjust this\n')
          # Separate the elements that will not be altered and the remaining elements
      list_temp_trf = list_tension[:window_cut]
      # print(list_temp_trf)
      after_values = list_tension[window_cut:]
      # print(after_values)

    # # Calculate the altered values based on the shifts
    def _extract_shift_value(shift_item):
      if isinstance(shift_item, dict):
        return float(shift_item.get('total', shift_item.get('manual', 0.0) + shift_item.get('automatic', 0.0)))
      return float(shift_item)

    if shift_tesion is not None:
      for tension, shift_item in zip(after_values, shift_tesion):
        shift = _extract_shift_value(shift_item)
        if shift >= 0 and tension >= 0:
          shifted_values.append(shift + tension)
        elif shift < 0 and tension >= 0:
          shifted_values.append(shift + tension)
        elif shift < 0 and tension < 0:
          shifted_values.append(abs(shift) + tension)
        elif shift >= 0 and tension < 0:
          shifted_values.append(-shift + tension)

      # Identify the remaining non-altered values
      remaining_values = after_values[len(shifted_values):]

      # Combine the original, altered, and non-altered elements into the new result list
      result_list = list_temp_trf + shifted_values + remaining_values

    else:
      result_list = list_tension

    return result_list


  def load_data(self, type_read_data_exp, path_voltages, curr_typic, scale_trfr, scale_out, type_curve_plot):
    """
      Loads experimental data with different options for reading and interpolation.

      Args:
          type_read_data_exp (str): The type of experimental data reading ('read interpolated data' or 'read original data').
          path_voltages (list): A list of paths to data files.
          curr_typic (str): The typical current type ('A', 'mA', 'uA', 'nA', 'pA').
          scale_trfr (str): The scale for transfer curves ('A', 'mA', 'uA', 'nA', 'pA').
          scale_out (str): The scale for output curves ('A', 'mA', 'uA', 'nA', 'pA').
          type_curve_plot (str): The type of curve to be plotted ('linear' or 'log').

      Returns:
          tuple: A tuple containing the following elements:
              - Vv (numpy.ndarray): Voltage values.
              - Id (numpy.ndarray): Current values.
              - input_voltage (list): List of input voltages.
              - n_points (int): Number of points in the sample.
              - count_transfer (int): Number of transfer curves.
              - count_output (int): Number of output curves.

      Example:
          >>> type_read_data_exp = 'read interpolated data'
          >>> path_voltages = ['data1.csv', 'data2.csv']
          >>> curr_typic = 'mA'
          >>> scale_trfr = 'uA'
          >>> scale_out = 'uA'
          >>> type_curve_plot = 'linear'
          >>> Vv, Id, input_voltage, n_points, count_transfer, count_output = load_data(type_read_data_exp, path_voltages, curr_typic, scale_trfr, scale_out, type_curve_plot)
    """

    if type_read_data_exp == 'read interpolated data':
        Vv, Id, input_voltage, n_points, count_transfer, count_output = self.read_interpoll_datas(*path_voltages, current_typic=curr_typic, scale_transfer=scale_trfr,
                                                                                                                        scale_output=scale_out, curve=type_curve_plot)
    elif type_read_data_exp == 'read original data':
        Vv, Id, input_voltage, n_points, count_transfer, count_output = self.read_pure_data(*path_voltages, current_typic=curr_typic, scale_transfer=scale_trfr,
                                                                                                                  scale_output=scale_out, curve=type_curve_plot)
    else:
        print("No type available\n")

    return Vv, Id, input_voltage, n_points, count_transfer, count_output


  def filter_files(self, select_files, list_curves, list_tension_shift, list_tension):
    """
      Filters and selects files, voltage shift values, and associated voltages based on the provided choices.

      Args:
          select_files (list): A list of indices of files to be selected.
          list_curves (list): A list of paths to curve files.
          list_tension_shift (list): A list of voltage shift values corresponding to the files.
          list_tension (list): A list of voltages associated with the curves.

      Returns:
          tuple: A tuple containing the following elements:
              - new_files_filter (list): List of paths to the selected curve files.
              - new_values_tension (list): List of voltage shift values corresponding to the selected files.
              - new_list_tension (list): List of voltages associated with the selected curves.

      Example:
          >>> select_files = [0, 2, 4]
          >>> list_curves = ['curve1.csv', 'curve2.csv', 'curve3.csv', 'curve4.csv']
          >>> list_tension_shift = [0.1, -0.2, 0.0, 0.3]
          >>> list_tension = [1.0, 2.0, 3.0, 4.0]
          >>> new_files_filter, new_values_tension, new_list_tension = filter_files(select_files, list_curves, list_tension_shift, list_tension)
    """

    new_files_filter = []
    new_values_tension = []
    new_list_tension= []

    if select_files is None:
      return list_curves, list_tension_shift, list_tension

    if not isinstance(select_files, (list, tuple)):
      raise TypeError("select_files must be a list or tuple of indices.")

    seen_indices = set()
    normalized_indices = []
    total_curves = len(list_curves)

    for raw_index in select_files:
      try:
        index = int(raw_index)
      except (TypeError, ValueError) as err:
        raise ValueError(f"Invalid index in select_files: {raw_index}") from err

      if index < 0 or index >= total_curves:
        raise IndexError(
            f"select_files index out of range: {index}. "
            f"Valid range is 0 to {max(total_curves - 1, 0)}."
        )
      if index in seen_indices:
        raise ValueError(f"Duplicate index in select_files: {index}")

      seen_indices.add(index)
      normalized_indices.append(index)

    for i in sorted(normalized_indices):
      new_files_filter.append(list_curves[i])
      new_values_tension.append(list_tension_shift[i])
      new_list_tension.append(list_tension[i])

    return new_files_filter, new_values_tension, new_list_tension



  def compute_relative_distance(self, experiment_curve_id, model_curve_id):
      """
      Computes the relative distance between the experiment and model curves.

      Args:
          experiment_curve (np.ndarray): Array representing the experiment curve.
          model_curve (np.ndarray): Array representing the model curve.

      Returns:
          float: Relative distance between the curves.
      """

      # Empilha as correntes em um única estrutura de dados (vetor)
      experiment_curve_id = np.ravel(experiment_curve_id)
      model_curve_id      = np.ravel(model_curve_id)

      # Ensure the curves have the same length
      assert len(experiment_curve_id) == len(model_curve_id), "Curves must have the same length"

      # Compute the absolute difference between the curves
      absolute_difference = np.abs(experiment_curve_id - model_curve_id)

      # Compute the relative distance
      relative_distance = np.sum(absolute_difference / (abs(experiment_curve_id) + 1e-10) )
      print('**'*73)
      print()
      print('|' + f"RELATIVE ERROR BETWEEN CURVES: {relative_distance:.4f}")
      print()
      print('**'*73)
