from IPython.display import clear_output
from ._imports import *
from ._idleak_resolve import resolve_idleak_for_transfers


class ReadData:

  def __init__(self, factor_correction=1):
    self.factor_correction = factor_correction
    self._last_path_voltages = None
    self._curve_cache = {}
    self._last_load_data_diagnostics = {}

  def set_curve_processing_config(self, settings=None):
    """Backward-compatible no-op after removing loader-specific `nfet_*` rules."""
    return


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


  def _normalize_curve_header(self, value):
    """Normalizes CSV headers so VGS/VDS/ID can be recognized reliably."""
    return str(value).strip().upper().replace(" ", "")


  def _is_effectively_constant(self, values, atol=1e-9, rtol=1e-6):
    """Checks whether a voltage column can be treated as fixed."""
    numeric_values = np.asarray(values, dtype=float)
    if numeric_values.size == 0:
      return False

    span = float(np.nanmax(numeric_values) - np.nanmin(numeric_values))
    reference = max(float(np.nanmax(np.abs(numeric_values))), 1.0)
    return span <= max(float(atol), float(rtol) * reference)


  def _detect_legacy_curve_type(self, filename):
    """Best-effort curve typing for the historical two-column format."""
    lowered = os.path.basename(str(filename)).lower()
    stem_name, _ = os.path.splitext(lowered)

    # New naming convention: <technology>-<fixed_voltage><axis>.csv
    # Examples: cnt-2vgs.csv (output), cnt-1vds.csv (transfer).
    if re.search(r'vgs$', stem_name, flags=re.IGNORECASE):
      return 1
    if re.search(r'vds$', stem_name, flags=re.IGNORECASE):
      return 0

    # Backward compatibility with older naming.
    if "transfer" in lowered or "transf" in lowered:
      return 0
    if "output" in lowered or "saida" in lowered:
      return 1
    return None


  def _read_with_supported_delimiters(self, csv_path, header='infer', min_columns=2):
    """Reads a table trying explicit delimiters before autodetection."""
    candidate_delimiters = ['\t', ',', ';']
    for delimiter in candidate_delimiters:
      try:
        frame = pd.read_csv(csv_path, sep=delimiter, engine='python', header=header)
        if frame.shape[1] >= min_columns:
          return frame
      except pd.errors.ParserError:
        continue

    frame = pd.read_csv(csv_path, sep=None, engine='python', header=header)
    if frame.shape[1] < min_columns:
      raise ValueError(f"Esperado ao menos {min_columns} colunas em {csv_path}.")
    return frame


  def _read_structured_curve_file(self, csv_path):
    """Reads the new 3-column format and infers curve type from the fixed column."""
    raw_frame = self._read_with_supported_delimiters(csv_path)
    normalized_columns = {
        self._normalize_curve_header(column): column
        for column in raw_frame.columns
    }
    required_columns = ["VGS", "VDS", "ID"]
    if not all(column in normalized_columns for column in required_columns):
      return None

    frame = raw_frame[[normalized_columns[column] for column in required_columns]].copy()
    frame.columns = required_columns
    for column in required_columns:
      frame[column] = pd.to_numeric(frame[column], errors='coerce')
    frame = frame.dropna(subset=required_columns).reset_index(drop=True)
    if frame.empty:
      raise ValueError(f"Nenhum ponto numerico valido encontrado em {csv_path}.")

    vgs_values = frame["VGS"].to_numpy(dtype=float)
    vds_values = frame["VDS"].to_numpy(dtype=float)
    id_values = frame["ID"].to_numpy(dtype=float)
    vgs_constant = self._is_effectively_constant(vgs_values)
    vds_constant = self._is_effectively_constant(vds_values)

    if vgs_constant and not vds_constant:
      curve_type = 1
      fixed_column = "VGS"
      sweep_column = "VDS"
    elif vds_constant and not vgs_constant:
      curve_type = 0
      fixed_column = "VDS"
      sweep_column = "VGS"
    else:
      raise ValueError(
          "Nao foi possivel classificar a curva. O novo padrao exige uma coluna "
          f"fixa entre VGS e VDS em {csv_path}."
      )

    fixed_voltage = float(frame[fixed_column].mean())
    return {
        "curve_type": curve_type,
        "fixed_voltage": fixed_voltage,
        "fixed_column": fixed_column,
        "sweep_column": sweep_column,
        "sweep_values": frame[sweep_column].to_numpy(dtype=float),
        "current_values": id_values,
        "format": "structured",
    }


  def _read_legacy_curve_file(self, csv_path):
    """Reads the historical two-column format kept as compatibility fallback."""
    raw_frame = self._read_with_supported_delimiters(csv_path, header=None)
    if raw_frame.shape[1] < 2:
      raise ValueError(f"Esperado ao menos 2 colunas em {csv_path}.")

    frame = raw_frame.iloc[:, :2].copy()
    frame.columns = ["V", "I"]
    for column in ["V", "I"]:
      frame[column] = pd.to_numeric(frame[column], errors='coerce')
    frame = frame.dropna(subset=["V", "I"]).reset_index(drop=True)
    if frame.empty:
      raise ValueError(f"Nenhum ponto numerico valido encontrado em {csv_path}.")

    fixed_voltage = self._get_signed_filename_voltage(
        csv_path,
        fallback_voltage=self._extract_voltage_from_filename(csv_path),
        curve_info={
            "sweep_values": frame["V"].to_numpy(dtype=float),
            "fixed_voltage": None,
        },
    )
    return {
        "curve_type": self._detect_legacy_curve_type(csv_path),
        "fixed_voltage": fixed_voltage,
        "fixed_column": None,
        "sweep_column": "V",
        "sweep_values": frame["V"].to_numpy(dtype=float),
        "current_values": frame["I"].to_numpy(dtype=float),
        "format": "legacy",
    }


  def _inspect_curve_file(self, csv_path):
    """Returns cached curve metadata and numeric arrays for a data file."""
    cache_key = os.path.abspath(str(csv_path))
    if cache_key in self._curve_cache:
      return self._curve_cache[cache_key]

    try:
      curve_info = self._read_structured_curve_file(csv_path)
    except pd.errors.ParserError:
      curve_info = None

    if curve_info is None:
      curve_info = self._read_legacy_curve_file(csv_path)

    self._curve_cache[cache_key] = curve_info
    return curve_info

  def _experimental_sort_key(self, curve_entry):
    fixed_voltage = curve_entry.get("fixed_voltage")
    filename = curve_entry.get("filename", "")
    sort_rank = curve_entry.get("sort_rank")
    return (
        sort_rank is None,
        int(sort_rank) if sort_rank is not None else 0,
        fixed_voltage is None,
        float(fixed_voltage) if fixed_voltage is not None else 0.0,
        filename.lower(),
    )


  def _get_experimental_file_lists(self, directory, selected_files=None,
                                   transfer_pattern='transfer', output_pattern='output'):
    """
      Returns sorted experimental files discovered from the directory by file content.
    """
    files = os.listdir(directory)
    selected_set = None
    if selected_files is not None:
      selected_set = set()
      for file_name in selected_files:
        normalized = str(file_name).strip().replace("\\", "/").lower()
        if not normalized:
          continue
        selected_set.add(normalized)
        selected_set.add(os.path.basename(normalized))
        selected_set.add(os.path.splitext(os.path.basename(normalized))[0])

    transfer_files = []
    output_files = []
    known_non_curve_files = {"resumo_processamento.csv"}
    skipped_files = []

    for filename in files:
      lowered = filename.lower()
      if not lowered.endswith(('.csv', '.txt')):
        continue
      if lowered in known_non_curve_files:
        continue
      if selected_set is not None:
        stem = os.path.splitext(lowered)[0]
        if lowered not in selected_set and stem not in selected_set:
          continue

      file_path = os.path.join(directory, filename)
      try:
        curve_info = self._inspect_curve_file(file_path)
      except (ValueError, pd.errors.ParserError) as err:
        skipped_files.append((filename, str(err)))
        continue
      curve_type = curve_info.get("curve_type")
      if curve_type is None:
        continue

      entry = {
          "filename": filename,
          "curve_type": curve_type,
          "fixed_voltage": curve_info.get("fixed_voltage"),
      }
      if curve_type == 0:
        transfer_files.append(entry)
      else:
        output_files.append(entry)

    if skipped_files:
      print(
          f"[ReadData] Ignorando {len(skipped_files)} arquivo(s) sem formato de curva em '{directory}'."
      )
      for file_name, reason in skipped_files:
        print(f"  - {file_name}: {reason}")

    transfer_files.sort(key=self._experimental_sort_key)
    output_files.sort(key=self._experimental_sort_key)
    return transfer_files, output_files


  def get_curve_counts(self, path_voltages):
    """Returns transfer/output counts from the typed curve tuples."""
    count_transfer = sum(1 for _, curve_type, _ in path_voltages if curve_type == 0)
    count_output = sum(1 for _, curve_type, _ in path_voltages if curve_type == 1)
    return count_transfer, count_output


  def read_files_experimental(  self, directory, list_tension=None, selected_files=None,
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
      detected_voltage = transfer_file.get("fixed_voltage")
      associated_voltage = detected_voltage
      if index < len(normalized_tensions):
        associated_voltage = normalized_tensions[index]
      typed_paths.append((os.path.join(directory, transfer_file["filename"]), 0, associated_voltage))

    output_offset = transfer_count
    for index, output_file in enumerate(output_files):
      tension_index = output_offset + index
      detected_voltage = output_file.get("fixed_voltage")
      associated_voltage = detected_voltage
      if tension_index < len(normalized_tensions):
        associated_voltage = normalized_tensions[tension_index]
      typed_paths.append((os.path.join(directory, output_file["filename"]), 1, associated_voltage))

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
    point_counts = []
    per_curve_diagnostics = []

    # Obtem a quantidade de cada curva
    count_transfer = 0
    count_output = 0
    prepared_args = []

    for arg in args:
      curve_info = self._inspect_curve_file(arg[0])
      point_counts.append(len(curve_info["current_values"]))
      prepared_args.append((arg, curve_info))

    min_value = np.min(point_counts)

    curr_typic = self.__convert_to_ampere_unit(current_typic)
    sc_transfer = self.__convert_to_ampere_unit(scale_transfer)
    sc_output = self.__convert_to_ampere_unit(scale_output)

    for arg, curve_info in prepared_args:
      try:
          curv_transfer = 0
          curv_out = 1
          raw_voltages = np.asarray(curve_info["sweep_values"], dtype=float)
          raw_currents = np.asarray(curve_info["current_values"], dtype=float)
          Vv_temp, sampled_current, sampling_strategy = self._sample_curve_to_length(
              raw_voltages,
              raw_currents,
              min_value,
          )

          if arg[1] == curv_out:
            Id_temp = sampled_current * (sc_output / curr_typic)
            type_out.append((Vv_temp, Id_temp))
            list_type_out.append(arg[2])
            count_output += 1

          elif arg[1] == curv_transfer:
              if curve == 'log':
                Id_temp = np.log10(abs(sampled_current))

              elif curve == 'linear':
                Id_temp = (-1) * abs((sampled_current * sc_transfer / curr_typic))
              else:
                raise ValueError("Option not valide\n")

              type_transfer.append((Vv_temp, Id_temp))
              list_type_transfer.append(arg[2])
              count_transfer += 1
          else:
              raise ValueError(f"Tipo de dado desconhecido: {arg[1]}")

          per_curve_diagnostics.append(
              {
                  "file": str(arg[0]),
                  "curve_type": "transfer" if arg[1] == curv_transfer else "output",
                  "nominal_voltage": arg[2],
                  "original_points": int(len(curve_info["current_values"])),
                  "effective_points": int(len(Vv_temp)),
                  "sampling_strategy": sampling_strategy,
                  "original_voltage_range": self._get_voltage_range(curve_info["sweep_values"]),
                  "effective_voltage_range": self._get_voltage_range(Vv_temp),
              }
          )

      except ValueError as err:
          if "divide by zero encountered in log10" or "invalid value encountered in log10" in str(err):
              print("Possivelmente a entrada é 'Out' e não 'Transfer'.")
          else:
              raise err

    def append_type(type_, Vv, Id):
      for v, i in type_:
          Vv.append(v)
          Id.append(i)
      return Vv, Id

    Vv, Id = append_type(type_transfer, Vv, Id)
    Vv, Id = append_type(type_out, Vv, Id)

    Vv = np.vstack(Vv).T
    Id = np.vstack(Id).T
    voltage = list_type_transfer + list_type_out

    n_points = int(min_value)
    self._store_load_data_diagnostics(
        read_mode='read original data',
        shared_points=n_points,
        original_point_counts=point_counts,
        per_curve=per_curve_diagnostics,
        count_transfer=count_transfer,
        count_output=count_output,
    )

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
    point_counts = []
    per_curve_diagnostics = []

    # Obtem a quantidade de cada curva
    count_transfer = 0
    count_output = 0
    prepared_args = []

    for arg in args:
      curve_info = self._inspect_curve_file(arg[0])
      point_counts.append(len(curve_info["current_values"]))
      prepared_args.append((arg, curve_info))

    nv = np.max(point_counts)

    for arg, curve_info in prepared_args:
      # type of curvs
      curv_transfer = 0
      curv_out = 1

      curr_typic  = self.__convert_to_ampere_unit(current_typic)
      sc_transfer = self.__convert_to_ampere_unit(scale_transfer)
      sc_output   = self.__convert_to_ampere_unit(scale_output)

      # print(curr_typic, sc_transfer)

      try:
        if arg[1] == curv_out:
            prepared_voltages = np.asarray(curve_info["sweep_values"], dtype=float)
            prepared_currents = np.asarray(curve_info["current_values"], dtype=float)
            prepared_voltages, prepared_currents = self._collapse_duplicate_axis(
                prepared_voltages, prepared_currents
            )
            Vmax, Vmin = np.max(prepared_voltages), np.min(prepared_voltages)
            Vv_temp = np.linspace(Vmin, Vmax, nv)
            Id_temp = np.interp(Vv_temp, prepared_voltages, prepared_currents)
            sampling_strategy = "collapse_duplicate_axis_and_interpolate"

            type_out.append((Vv_temp, Id_temp * (sc_output / curr_typic)))
            list_type_out.append(arg[2])
            count_output += 1
            per_curve_diagnostics.append(
                {
                    "file": str(arg[0]),
                    "curve_type": "output",
                    "nominal_voltage": arg[2],
                    "original_points": int(len(curve_info["current_values"])),
                    "effective_points": int(len(Vv_temp)),
                    "sampling_strategy": sampling_strategy,
                    "original_voltage_range": self._get_voltage_range(curve_info["sweep_values"]),
                    "effective_voltage_range": self._get_voltage_range(Vv_temp),
                }
            )

        elif arg[1] == curv_transfer:
            prepared_voltages = np.asarray(curve_info["sweep_values"], dtype=float)
            prepared_currents = np.asarray(curve_info["current_values"], dtype=float)
            prepared_voltages, prepared_currents = self._collapse_duplicate_axis(
                prepared_voltages, prepared_currents
            )
            Vmax, Vmin = np.max(prepared_voltages), np.min(prepared_voltages)
            Vv_temp = np.linspace(Vmin, Vmax, nv)
            Id_temp = np.interp(Vv_temp, prepared_voltages, prepared_currents)

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
            count_transfer += 1
            per_curve_diagnostics.append(
                {
                    "file": str(arg[0]),
                    "curve_type": "transfer",
                    "nominal_voltage": arg[2],
                    "original_points": int(len(curve_info["current_values"])),
                    "effective_points": int(len(Vv_temp)),
                    "sampling_strategy": "collapse_duplicate_axis_and_interpolate",
                    "original_voltage_range": self._get_voltage_range(curve_info["sweep_values"]),
                    "effective_voltage_range": self._get_voltage_range(Vv_temp),
                }
            )
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

    self._store_load_data_diagnostics(
        read_mode='read interpolated data',
        shared_points=nv,
        original_point_counts=point_counts,
        per_curve=per_curve_diagnostics,
        count_transfer=count_transfer,
        count_output=count_output,
    )

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
                          res=None, curr=None, path_voltages=None, settings=None):
    """
      Creates model instances based on input data and provided parameters.

      Args:
          model (object): The model to be used for creating the instances.
          n_points (int): The number of data points.
          type_curve (str): The curve type ('log' or 'linear').
          parameters (tuple): A tuple of model parameters.
          tensions (list): A list of voltages associated with the input data.
          Vv (array): An array of input data voltages.
          idleak (float, list, dict): Static value, per-transfer list, or dict mapping curve ids
              to values (dict requires path_voltages).
          path_voltages (list, optional): (path, curve_type, voltage) tuples; required if idleak is a dict.
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

    if getattr(model, "__name__", "") == "TFTModel" and getattr(model, "__module__", "") == "modules_otft._model":
      from ._utils import uses_matlab_n_model, MATLAB_N_PARAM_KEYS
      param_count = len(parameters) if hasattr(parameters, "__len__") else 0
      if uses_matlab_n_model(settings=settings, tp_tst=tp_tst) or param_count == len(MATLAB_N_PARAM_KEYS):
        from .model_tft_n import TFTModelN
        model = TFTModelN

    if isinstance(idleak, dict):
      if path_voltages is None:
        raise ValueError(
          "path_voltages must be provided when idleak is a dict (per-curve idleak mapping), "
          "or call read.load_data(...) first on the same ReadData instance so path_voltages is cached."
        )
      idleak = resolve_idleak_for_transfers(idleak, path_voltages, count)
    elif isinstance(idleak, list) and count:
      if len(idleak) != count:
        raise ValueError(
          "loaded_idleak list length (%s) must equal count_transfer (%s) in multi-idleak mode."
          % (len(idleak), count)
        )

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
    match = re.search(
        r'(-?\d+(?:\.\d+)?)\s*(?=(?:_?V(?:GS|DS)|V)?(?:\.csv|\.txt)$)',
        filename,
        flags=re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


  def _get_curve_current_factor(self, curve_type=None, current_typic='A',
                                scale_transfer='A', scale_output='A'):
    """Returns the factor that converts a curve current to the working unit."""
    current_typic_factor = self.__convert_to_ampere_unit(current_typic)
    curve_scale = scale_transfer if curve_type in (0, 'transfer') else scale_output
    curve_scale_factor = self.__convert_to_ampere_unit(curve_scale)
    return float(curve_scale_factor / current_typic_factor)


  def _get_voltage_range(self, axis_values):
    """Returns the numeric range of a curve axis."""
    values = np.asarray(axis_values, dtype=float)
    if values.size == 0:
      return {"min": None, "max": None}
    return {"min": float(np.min(values)), "max": float(np.max(values))}


  def _sample_curve_to_length(self, axis_values, target_values, target_len):
    """Resamples a curve by index so the full span is preserved."""
    axis = np.asarray(axis_values, dtype=float)
    target = np.asarray(target_values, dtype=float)
    current_len = len(axis)

    if current_len == 0 or target_len is None or target_len <= 0:
      return axis, target, "kept"

    if current_len > target_len:
      idx = np.round(np.linspace(0, current_len - 1, target_len)).astype(int)
      return axis[idx], target[idx], "full_span_index_downsample"

    if current_len < target_len:
      return (
          np.pad(axis, (0, target_len - current_len), mode='edge'),
          np.pad(target, (0, target_len - current_len), mode='edge'),
          "edge_padding",
      )

    return axis, target, "kept"


  def _store_load_data_diagnostics(self, read_mode, shared_points, original_point_counts,
                                   per_curve, count_transfer, count_output):
    """Persists diagnostics about the most recent data loading step."""
    unique_point_counts = sorted({int(value) for value in original_point_counts})
    had_mismatched_lengths = len(unique_point_counts) > 1
    recommendation = None
    if read_mode == 'read original data' and had_mismatched_lengths:
      recommendation = (
          "Curvas com comprimentos diferentes foram reamostradas em toda a faixa "
          "do eixo. Prefira 'read interpolated data' ao comparar dados tratados "
          "por histerese."
      )

    def summarize_ranges(curve_type_name):
      ranges = [
          item["effective_voltage_range"]
          for item in per_curve
          if item["curve_type"] == curve_type_name
          and item["effective_voltage_range"]["min"] is not None
      ]
      if not ranges:
        return {"min": None, "max": None}
      return {
          "min": float(min(entry["min"] for entry in ranges)),
          "max": float(max(entry["max"] for entry in ranges)),
      }

    self._last_load_data_diagnostics = {
        "read_mode": read_mode,
        "shared_points": int(shared_points) if shared_points is not None else None,
        "original_point_counts": [int(value) for value in original_point_counts],
        "unique_point_counts": unique_point_counts,
        "had_mismatched_lengths": had_mismatched_lengths,
        "count_transfer": int(count_transfer),
        "count_output": int(count_output),
        "transfer_voltage_range": summarize_ranges("transfer"),
        "output_voltage_range": summarize_ranges("output"),
        "recommendation": recommendation,
        "per_curve": per_curve,
    }


  def get_last_load_data_diagnostics(self):
    """Returns diagnostics about the most recent load_data execution."""
    return self._last_load_data_diagnostics


  def _read_curve_points(self, csv_path, curve_type=None, current_typic='A',
                         scale_transfer='A', scale_output='A'):
    """Reads a curve file and returns the sweep axis with scaled current values."""
    curve_info = self._inspect_curve_file(csv_path)
    resolved_curve_type = curve_info["curve_type"] if curve_type is None else curve_type
    voltages = np.asarray(curve_info["sweep_values"], dtype=float)
    currents = np.asarray(curve_info["current_values"], dtype=float)
    current_factor = self._get_curve_current_factor(
        resolved_curve_type,
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


  def _get_signed_filename_voltage(self, csv_path, fallback_voltage=None, curve_info=None):
    """Resolves the nominal curve voltage, preferring the fixed column from the CSV."""
    if curve_info is None:
      curve_info = self._inspect_curve_file(csv_path)

    fixed_voltage = curve_info.get("fixed_voltage")
    if fixed_voltage is not None:
      return float(fixed_voltage)

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


  def _calculate_shift_for_target_voltage(self, nominal_voltage, target_voltage):
    """
      Inverts the `apply_shifts()` convention to reach a target nominal voltage.

      For positive nominal voltages the shift is additive.
      For negative nominal voltages `apply_shifts()` effectively uses
      `target = nominal - shift`.
    """
    nominal_voltage = float(nominal_voltage)
    target_voltage = float(target_voltage)
    if nominal_voltage < 0:
      return float(nominal_voltage - target_voltage)
    return float(target_voltage - nominal_voltage)


  def _adjust_shift_with_preprocess(self, nominal_voltage, effective_voltage, global_display_shift=0.0):
    """
      Calculates the local shift needed so the displayed output gate voltage
      matches the effective VGS after the global visual shift is applied.
    """
    nominal_voltage = float(nominal_voltage)
    effective_voltage = float(effective_voltage)
    global_display_shift = float(global_display_shift or 0.0)

    display_signal = -1.0 if nominal_voltage < 0 else 1.0
    target_display_voltage = display_signal * abs(effective_voltage)
    target_voltage_before_global_display = target_display_voltage - global_display_shift
    local_shift = self._calculate_shift_for_target_voltage(
        nominal_voltage,
        target_voltage_before_global_display,
    )
    adjusted_by_preprocess = not np.isclose(global_display_shift, 0.0)
    return float(local_shift), adjusted_by_preprocess


  def estimate_output_shifts(self, path_voltages, min_gate_separation=0.5,
                             pre_process_shift_volt_data=None, global_display_shift=0.0,
                             current_typic='A',
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
            'output_filename_voltage': self._get_signed_filename_voltage(
                output_path,
                fallback_voltage=output_loaded_voltage,
            ),
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
            'global_display_shift': float(global_display_shift or 0.0),
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
            'output_filename_voltage': self._get_signed_filename_voltage(
                output_path,
                fallback_voltage=output_loaded_voltage,
            ),
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
            'global_display_shift': float(global_display_shift or 0.0),
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
      output_filename_voltage = self._get_signed_filename_voltage(
          output_path,
          fallback_voltage=output_loaded_voltage,
      )
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
          'global_display_shift': float(global_display_shift or 0.0),
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
      automatic_shift = automatic_shift_base

      detail.update({
          'vgs_effective_raw': vgs_effective_raw,
          'vgs_effective_limited': float(vgs_effective_limited),
          'delta_vgs': delta_vgs,
          'automatic_shift_base': automatic_shift_base,
          'automatic_shift': automatic_shift,
          'pre_process_shift_volt_data': pre_process_shift_volt_data,
          'global_display_shift': float(global_display_shift or 0.0),
          'automatic_shift_adjusted_by_preprocess': False,
          'status': 'matched_with_monotonicity_limit' if was_limited else 'matched',
          'warning': warning,
      })

      auto_shifts[original_index] = automatic_shift
      ordered_details[original_index] = detail
      previous_nominal_voltage = output_nominal_voltage
      previous_effective_voltage = vgs_effective_limited

    return auto_shifts, ordered_details


  def calculate_automatic_output_shifts(self, path_voltages, pre_process_shift_volt_data=None,
                                        global_display_shift=0.0,
                                        current_typic='A', scale_transfer='A', scale_output='A'):
    """
      Backward-compatible wrapper around the VDS-match shift estimator.
    """
    return self.estimate_output_shifts(
        path_voltages,
        pre_process_shift_volt_data=pre_process_shift_volt_data,
        global_display_shift=global_display_shift,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )


  def estimate_output_curve_shifts(self, path_voltages, pre_process_shift_volt_data=None,
                                   global_display_shift=0.0,
                                   current_typic='A', scale_transfer='A', scale_output='A'):
    """Compatibility alias for callers using the older method name."""
    return self.estimate_output_shifts(
        path_voltages,
        pre_process_shift_volt_data=pre_process_shift_volt_data,
        global_display_shift=global_display_shift,
        current_typic=current_typic,
        scale_transfer=scale_transfer,
        scale_output=scale_output,
    )


  def detect_duplicate_output_curves(self, path_voltages, current_typic='A',
                                     scale_transfer='A', scale_output='A',
                                     atol=1e-15, rtol=1e-9):
    """
      Detects output curves that are identical or numerically equivalent.

      The comparison is done after the interpolation-preparation path so the
      report reflects the same voltage/current basis used elsewhere.
    """
    output_curves = [curve for curve in path_voltages if curve[1] == 1]
    duplicate_report = []
    prepared_curves = []

    for output_path, _, output_loaded_voltage in output_curves:
      voltages, currents = self._prepare_curve_for_interpolation(
          output_path,
          curve_type=1,
          current_typic=current_typic,
          scale_transfer=scale_transfer,
          scale_output=scale_output,
      )
      prepared_curves.append({
          'path': output_path,
          'nominal_voltage': float(output_loaded_voltage),
          'voltages': voltages,
          'currents': currents,
      })

    for index, curve_data in enumerate(prepared_curves):
      duplicate_of = None
      for reference_curve in prepared_curves[:index]:
        same_length = (
            len(curve_data['voltages']) == len(reference_curve['voltages'])
            and len(curve_data['currents']) == len(reference_curve['currents'])
        )
        if not same_length:
          continue

        same_voltages = np.allclose(
            curve_data['voltages'],
            reference_curve['voltages'],
            atol=atol,
            rtol=rtol,
        )
        same_currents = np.allclose(
            curve_data['currents'],
            reference_curve['currents'],
            atol=atol,
            rtol=rtol,
        )
        if same_voltages and same_currents:
          duplicate_of = reference_curve
          break

      warning = None
      status = 'unique_output_curve'
      if duplicate_of is not None:
        status = 'duplicate_output_curve'
        warning = (
            f"Aviso: A curva {os.path.basename(curve_data['path'])} possui dados "
            f"experimentais idênticos aos de {os.path.basename(duplicate_of['path'])}, "
            "embora represente outra polarização nominal."
        )

      duplicate_report.append({
          'output_file': os.path.basename(curve_data['path']),
          'output_nominal_voltage': curve_data['nominal_voltage'],
          'duplicate_of_file': (
              None if duplicate_of is None else os.path.basename(duplicate_of['path'])
          ),
          'duplicate_of_nominal_voltage': (
              None if duplicate_of is None else float(duplicate_of['nominal_voltage'])
          ),
          'status': status,
          'warning': warning,
      })

    return duplicate_report


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
        self._last_path_voltages = list(path_voltages)
    elif type_read_data_exp == 'read original data':
        Vv, Id, input_voltage, n_points, count_transfer, count_output = self.read_pure_data(*path_voltages, current_typic=curr_typic, scale_transfer=scale_trfr,
                                                                                                                  scale_output=scale_out, curve=type_curve_plot)
        self._last_path_voltages = list(path_voltages)
    else:
        print("No type available\n")
        return None, None, None, None, 0, 0

    diagnostics = self.get_last_load_data_diagnostics()
    if diagnostics.get("recommendation"):
      print(f"[ReadData] {diagnostics['recommendation']}")

    return Vv, Id, input_voltage, n_points, count_transfer, count_output


  def filter_files(self, selected_curves, list_curves, list_tension_shift, list_tension):
    """
      Filters and selects files, voltage shift values, and associated voltages based on curve names.

      Args:
          selected_curves (list): A list of curve names or stems to be selected.
          list_curves (list): A list of paths to curve files.
          list_tension_shift (list): A list of voltage shift values corresponding to the files.
          list_tension (list): A list of voltages associated with the curves.

      Returns:
          tuple: A tuple containing the following elements:
              - new_files_filter (list): List of paths to the selected curve files.
              - new_values_tension (list): List of voltage shift values corresponding to the selected files.
              - new_list_tension (list): List of voltages associated with the selected curves.

      Example:
          >>> selected_curves = ['curve1', 'curve3']
          >>> list_curves = ['curve1.csv', 'curve2.csv', 'curve3.csv', 'curve4.csv']
          >>> list_tension_shift = [0.1, -0.2, 0.0, 0.3]
          >>> list_tension = [1.0, 2.0, 3.0, 4.0]
          >>> new_files_filter, new_values_tension, new_list_tension = filter_files(selected_curves, list_curves, list_tension_shift, list_tension)
    """

    new_files_filter = []
    new_values_tension = []
    new_list_tension= []

    if selected_curves is None:
      return list_curves, list_tension_shift, list_tension

    if not isinstance(selected_curves, (list, tuple, set)):
      raise TypeError("selected_curves must be a list, tuple, or set of curve names.")

    seen_curves = set()
    normalized_indices = []
    total_curves = len(list_curves)
    curve_aliases = []

    for curve_name in list_curves:
      normalized_curve = str(curve_name).strip().replace("\\", "/").lower()
      filename = os.path.basename(normalized_curve)
      stem = os.path.splitext(filename)[0]
      curve_aliases.append({normalized_curve, filename, stem})

    for raw_curve_name in selected_curves:
      normalized_curve_name = str(raw_curve_name).strip().replace("\\", "/").lower()
      if normalized_curve_name == "":
        continue

      matched_index = None
      for index, aliases in enumerate(curve_aliases):
        if normalized_curve_name in aliases:
          matched_index = index
          break

      if matched_index is None:
        raise ValueError(f"selected_curves entry not found: {raw_curve_name}")
      if matched_index in seen_curves:
        raise ValueError(f"Duplicate curve in selected_curves: {raw_curve_name}")

      seen_curves.add(matched_index)
      normalized_indices.append(matched_index)

    for i in normalized_indices:
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
