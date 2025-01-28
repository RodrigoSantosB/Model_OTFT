from IPython.display import clear_output
from ._imports import *

class ReadData:

  def __init__(self, factor_correction=1):
    self.factor_correction = factor_correction


  # GROUP DATA IN TUPLE OF TRANSFER AND OUTPUT
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

    # count is the number of transfer data in the sample
    paths = []
    for i in range(len(path_voltages)):
      if i < count:
        paths.append((path_voltages[i], 0 , voltage[i]))
      else:
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

    # Identify the scale of the data (mA or uA)
    correction_factor = 0
    unite = {  'A': 1,
              'mA': 1e-3,
              'uA': 1e-6,
              'nA': 1e-9,
              'pA': 1e-12
                          }

    # Check if the scale exists in the dictionary
    if scale in unite:
        correction_factor = unite[scale]
    else:
        raise ValueError("Invalid data scale!")
    return correction_factor


  def read_files_experimental(  self, directory, list_tension, selected_files=None,
                                transfer_pattern=r'transfer', output_pattern=r'output'):
    """
      Reads experimental files in a directory and returns a list of paths and 
      associated information.

      Args:
          directory (str): The      directory     containing the experimental files.
          list_tension (list): A  list of voltages corresponding to the experiments.
          selected_files (list): An optional list of selected file names to consider.
          transfer_pattern (str): The name pattern for transfer files.
          output_pattern (str): The name pattern for output files.

      Returns:
          list: A list of tuples containing information about the files, where each tuple 
          is in the format:
              (file path, curve type (0 for transfer, 1 for output), associated voltage).

      Example:
          >>> directory = 'data_folder'
          >>> tension_list = [1.0, 2.0, 3.0]
          >>> selected_files = ['transfer-1V.csv', 'output-2V.csv']
          >>> paths = read_files_experimental(directory, tension_list, selected_files)
          >>> print(paths)
          [('data_folder/transfer-1V.csv', 0, 1.0), ('data_folder/output-2V.csv', 1, 2.0)]
    """

    # Get list of all files in directory
    files = os.listdir(directory)

    # Create name patterns for "transfer" and "output" based on parameters
    transfer_pattern_file = re.compile(fr'{transfer_pattern}-\d+V.csv')
    output_pattern_file = re.compile(fr'{output_pattern}-\d+V.csv')

    # Filter files with transfer and output name patterns
    transfer_files = [f for f in files if transfer_pattern_file.match(f)]
    output_files = [f for f in files if output_pattern_file.match(f)]

    if selected_files is not None:
        transfer_files = [f for f in transfer_files if f in selected_files]
        output_files = [f for f in output_files if f in selected_files]
    # Create lists to store transfer and output curves ordered by voltage,
    # type of curve (0: transfer, 1: output) and associated voltages
    curves = []
    curve_types = []
    voltages = []
    count_transfer = 0
    count_output = 0

    # Add transfer curves to the list, ordering them by voltage
    transfer_files.sort(key=lambda f: int(re.findall(r'\d+', f)[0]))
    for transfer_file in transfer_files:
        curves.append(os.path.join(directory, transfer_file))
        curve_types.append(0)  # Type 0 for transfer curve
        voltage = int(re.findall(r'\d+', transfer_file)[0])
        voltages.append(voltage)
        count_transfer += 1

    # Add the output curves to the list, ordering them by voltage
    output_files.sort(key=lambda f: int(re.findall(r'\d+', f)[0]))
    for output_file in output_files:
        curves.append(os.path.join(directory, output_file))
        curve_types.append(1)  # Type 1 for output curve
        voltage = int(re.findall(r'\d+', output_file)[0])
        voltages.append(voltage)
        count_output += 1

    paths = self._load_paths_in_tuple_data(curves, list_tension, count_transfer)

    return paths


  ### READING FUNCTION WITHOUT INTERPOLATION
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


    # Get the quantity of each curve
    count_transfer = 0
    count_output   = 0

    # get the number of points in the sample
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
            checks whether the second element (arg[1]) of the tuple arg is equal to 1.
            If so, this indicates that the data type is of the output type. Right away,
            reads data from a CSV file using pd.read_csv, where arg[0]
            contains the file path
            '''
            data = pd.read_csv(arg[0], header=None)
            Vv_temp = data[0].values[:min_value]
            Id_temp = data[1].values[:min_value] * (sc_output / curr_typic)
            type_out.append((Vv_temp, Id_temp))
            list_type_out.append(arg[2])
            count_output+=1


          elif arg[1] == curv_transfer:
              data = pd.read_csv(arg[0], header=None)

              #allocates in Vv_temp only the points up tomin_value
              Vv_temp = data[0].values[:min_value]

              #allocate the log10 of currents in Id_temp
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
              raise ValueError(f"Unknown data type: {arg[1]}")

      except ValueError as err:
          if "divide by zero encountered in log10" or "invalid value encountered in log10" in str(err):
              print("Possibly the input is 'Out' and not 'Transfer'.")
          else:
              raise err

    # checks if the set of points passed from the sample has - or + data than what was passed by nv    # se for - ou + ele completa com
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

  # READ THE DATA AND INTERPOLATE WITH THE VALUE OF THE BIGGEST QTY OF POINTS IT FINDS
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

    # Get the quantity of each curve
    count_transfer = 0
    count_output   = 0


    # Get the number of points in the sample
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

            #plot data on log or linear scale just for the case where we are going to optimize linear as well
            if curve == 'log':
              Id_temp = np.log10(abs(Id_temp))

            elif curve == 'linear':
              # look at this multiplication by -1 (adjust)
              #use a factor value 2 to differentiate the two curves (in A)
              Id_temp = (-1)*abs((Id_temp * sc_transfer / curr_typic))
              # Id_temp = abs(Id_temp / max_value)
            else:
              raise ValueError("Option not valide\n")

            type_transfer.append((Vv_temp, Id_temp))
            list_type_transfer.append(arg[2])
            count_transfer+=1
        else:
            raise ValueError(f"Unknown data type: {arg[1]}")

      except ValueError as err:
        if "divide by zero encountered in log10" or "invalid value encountered in log10" in str(err):
            print("Possibly the input is 'Out' and not 'Transfer'.")
        else:
            raise err
    # checks if the set of points passed from the sample has - or + data than what was passed by nv
    # if it is - or + it completes with
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

###############_AUXILIARY FUNCTIONS TO GROUP DATA FOR GRAPH PLOT######################### ##########
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
    
    # Create in_model_data iteratively
    for i in range(count_transfer):
      in_model_data.append((Vv[:, i], model_id[i]))


    # Add optimized data to in_model_data
    if compare:
      for i in range(count_transfer):
        in_model_data.append((Vv[:, i], model_id_opt[i]))

    # Create in_exp_data iteratively
    if count_transfer >= 2:
      for i in range(0, count_transfer, 2):
          in_exp_data.extend([Vv[:, i], Id[:, i], Vv[:, i+1], Id[:, i+1]])

    elif count_transfer == 1:
      in_exp_data.extend([Vv[:, 0], Id[:, 0]])

    elif count_transfer == 0:
      in_model_data = []
      in_exp_data   = []
    else:
        raise ValueError("Error in read data")

    return in_model_data, in_exp_data


  # GROUPING THE OUTPUT DATA
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

    # Create out_model_data iteratively
    max_data = ( int(count_output) + int(count_transfer) )
    for i in range(count_transfer, max_data):
      out_model_data.append((Vv[:, i], model_id[i]))


    if compare:
      for i in range(count_transfer, max_data):
        out_model_data.append((Vv[:, i], model_id_opt[i]))


    # Create out_exp_data iteratively
    for i in range(count_transfer, max_data):
      out_exp_data.extend([ Vv[:, i], Id[:, i] ])
    return out_model_data, out_exp_data


  # CREATE MODEL INSTANCES
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

    # Calculate model based on static idleak
    def idleak_int(value, i, select=True):
      if select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak, mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Call model
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))

      elif not select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak=0, mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Call model
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))


      else:
        ValueError(" 'select possible 'True' or 'False' ")


    # Calculate model based on dynamic idleak
    def idleak_list(value, i, select=True):
      if select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak[i], mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Call model
        Model_data.append(Modelo.calc_model(Vv[:,i], *parameters))

      elif not select:
        Modelo = model( tensions[i], n_points, type_curve, current_typic,
                        scale_factor, idleak=0, mult_idleak=0, type_data = value,
                        with_transistor=w, sr_resistance=res, curr_carry=curr,
                        type_transitor=tp_tst)

        # Call model
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


  # Makes the voltage shift in the voltage list for the output curves
  def apply_shifts(self, count_transfer, shift_tesion, list_tension):
    """
      Applies a voltage shift to the list of voltages for the output curves.

      Args:
          count_transfer (int): The number of transfer curves in the voltage list.
          shift_tension (list): A list of voltage shift values.
          list_tension (list): A list of voltages associated with the curves.

      Returns:
          list: A list of voltages updated with the applied shifts.

      Example:
          >>> count_transfer = 3
          >>> shift_tension = [0.1, -0.2]
          >>> list_tension = [1.0, 2.0, 3.0, 4.0, 5.0]
          >>> updated_tensions = apply_shifts(count_transfer, shift_tension, list_tension)
          >>> print(updated_tensions)
          [1.0, 2.0, 3.1, 3.8, 5.0]
    """

    result_list = []
    shifted_values = []

    if count_transfer > 0:
      # Separate the elements that will not be altered and the remaining elements
      list_temp_trf = list_tension[:count_transfer]
      # print(list_temp_trf)
      after_values = list_tension[count_transfer:]
      # print(after_values)
    else:
      # size of the shift_list
      qtde_tension_output  = len(shift_list)
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
    if shift_tesion is not None:
      for tension, shift in zip(after_values, shift_tesion):
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

    # sort the list of choices
    select_files = sorted(select_files)

    for i in select_files:
      new_files_filter.append(list_curves[i])
      new_values_tension.append(list_tension_shift[i])
      new_list_tension.append(list_tension[i])

    return new_files_filter, new_values_tension, new_list_tension



  # def compute_relative_distance(self, experiment_curve_id, model_curve_id):
  #     """
  #     Computes the relative distance between the experiment and model curves.

  #     Args:
  #         experiment_curve (np.ndarray): Array representing the experiment curve.
  #         model_curve (np.ndarray): Array representing the model curve.

  #     Returns:
  #         float: Relative distance between the curves.
  #     """

  #     # Empilha as correntes em um única estrutura de dados (vetor)
  #     experiment_curve_id = np.ravel(experiment_curve_id)
  #     model_curve_id      = np.ravel(model_curve_id)

  #     # Ensure the curves have the same length
  #     assert len(experiment_curve_id) == len(model_curve_id), "Curves must have the same length"

  #     # Compute the absolute difference between the curves
  #     absolute_difference = np.abs(experiment_curve_id - model_curve_id)

  #     # Compute the relative distance
  #     relative_distance = np.sum(absolute_difference / (abs(experiment_curve_id) + 1e-10) )
  #     print('**'*73)
  #     print()
  #     print('|' + f"RELATIVE ERROR BETWEEN CURVES: {relative_distance:.4f}")
  #     print()
  #     print('**'*73)


  def compute_relative_distance(self, experiment_curve_id, model_curve_id, plot=False, plot_width=1100, plot_height=600):
      """
      Computes the relative distance between the experiment and model curves and plots the relative error.

      Args:
          experiment_curve_id (list of arrays): List of arrays representing the experiment curve.
          model_curve_id (list of arrays): List of arrays representing the model curve.
          plot_width (int): Width of the plot.
          plot_height (int): Height of the plot.

      Returns:
          float: Relative distance between the curves.
      """
      # Flattening using manual iteration
      experiment_flattened = []
      model_flattened = []

      for curve in experiment_curve_id:
          experiment_flattened.extend(curve)

      for curve in model_curve_id:
          model_flattened.extend(curve)

      # Ensure the curves have the same length
      assert len(experiment_flattened) == len(model_flattened), "Curves must have the same length"

      # Normalize the curves to a common scale
      experiment_flattened = [(val - min(experiment_flattened)) / (max(experiment_flattened) - min(experiment_flattened) + 1e-5) for val in experiment_flattened]
      model_flattened = [(val - min(model_flattened)) / (max(model_flattened) - min(model_flattened) + 1e-5) for val in model_flattened]

      # Compute the absolute difference and relative error using a loop
      absolute_difference = []
      relative_error = []
      weights = []
      denominator = []

      for i in range(len(experiment_flattened)):
          abs_diff = abs(experiment_flattened[i] - model_flattened[i])
          denom = abs(experiment_flattened[i]) + 1e-5
          rel_err = abs_diff / denom

          absolute_difference.append(abs_diff)
          relative_error.append(rel_err)
          denominator.append(denom)

          # Adding weights (optional, example of decreasing weights)
          weights.append(1 - i / len(experiment_flattened) * 0.9)  # Example: Linear decay from 1 to 0.1

      # Compute the relative distance with weights
      relative_distance = sum(weights[i] * (absolute_difference[i] / denominator[i]) for i in range(len(experiment_flattened)))

      if plot:
          # Plot using Plotly
          import plotly.graph_objects as go

          fig = go.Figure()

          fig.add_trace(go.Scatter(
              y=relative_error,
              mode='lines+markers',
              name="Relative Error (Point-wise)",
              line=dict(width=2),
              marker=dict(size=5)
          ))

          fig.update_layout(
              width=plot_width,
              height=plot_height,
              title=dict(
                  text="<b>Point-wise Relative Error Between Curves</b>",
                  x=0.5,  # Center alignment
                  xanchor='center',
                  font=dict(size=18, family='Arial', color='black')
              ),
              xaxis=dict(
                  title="<b>Data Points</b>",
                  titlefont=dict(size=14, family='Arial', color='black'),
                  showgrid=True,
                  gridcolor='lightgrey'
              ),
              yaxis=dict(
                  title="<b>Relative Error</b>",
                  titlefont=dict(size=14, family='Arial', color='black'),
                  showgrid=True,
                  gridcolor='lightgrey'
              ),
              plot_bgcolor="white",
              margin=dict(l=50, r=50, t=50, b=50),
              legend=dict(
                  x=0.02, y=0.98,
                  font=dict(size=12)
              )
          )
          fig.show()

      print('**' * 73)
      print(f"RELATIVE ERROR BETWEEN CURVES: {relative_distance:.4f}")
      print('**' * 73)
