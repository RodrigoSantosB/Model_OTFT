from ._imports import *
class TFTGraphicsPlot():

  def __init__(self, height=600, width=1100):
    self.height = height
    self.width = width


  def __convert_to_ampere_unit(self, scale):
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

  # Function to handle voltage data for comparison graphs
  def __calc_volt_data(self, compare, volt_data):
    """
      Calculates voltage data for comparison graphs.

      Args:
          compare (bool): Indicates whether the comparison is between optimized models (True) or experimental data and a model (False).
          volt_data (list): A list of voltage data.

      Returns:
          tuple: A tuple containing the following elements:
              - title_update (str): The updated title for the graph.
              - volt_data (list): Updated list of voltage data.

      Example:
          >>> compare = True
          >>> volt_data = [1.0, 2.0, 3.0]
          >>> title_update, volt_data = __calc_volt_data(compare, volt_data)
    """

    title_update = ''
    name = ''

    # Create a cyclic iterator using itertools.cycle
    iterador = itertools.cycle(volt_data)
    repeticoes = 2
    if compare:
        title_update = '<b>Model Vs Model Optimazed<b>'
        volt_data = [next(iterador) for _ in range(repeticoes * len(volt_data))]
    else:
        title_update = '<b>Experimental Datas Vs Model<b>'
    return title_update, volt_data

  # change the shift signal
  def __change_signal_shift(self, shift_list):
    """
      Inverts the signs of elements in the voltage shift list.

      Args:
          shift_list (list): A list of voltage shift values.

      Returns:
          list: A new list with the signs of elements inverted.

      Example:
          >>> shift_list = [0.1, -0.2, 0.0, -0.3]
          >>> inverted_list = __change_signal_shift(shift_list)
    """

    normalized_list = []
    for shift in shift_list:
      if isinstance(shift, dict):
        normalized_shift = dict(shift)
        normalized_shift['manual'] = float(shift.get('manual', 0.0))
        normalized_shift['automatic'] = float(shift.get('automatic', 0.0))
        normalized_shift['total'] = float(shift.get('total', 0.0))
        normalized_list.append(normalized_shift)
      else:
        normalized_list.append(float(shift))
    return normalized_list


  def __format_shift_display(self, shift_value):
    """Formats the operational shift (effective minus nominal) with explicit sign."""
    if isinstance(shift_value, dict):
      applied_shift = float(shift_value.get(
          'operational_shift',
          shift_value.get('total', shift_value.get('automatic', 0.0)),
      ))
      return f'{applied_shift:+.2f}V'

    return f'{float(shift_value):+.2f}V'


  def __format_voltage_display(self, voltage_value):
    """Formats legend voltages with two decimal places when numeric."""
    try:
      return f'{float(voltage_value):.2f}V'
    except (TypeError, ValueError):
      return f'{voltage_value}V'


  def __format_consistency_display(self, shift_value):
    """Formats duplicate-curve diagnostics for plot legends."""
    if not isinstance(shift_value, dict):
      return ''

    if shift_value.get('curve_consistency_status') != 'duplicate_output_curve':
      return ''

    duplicate_voltage = shift_value.get('duplicate_of_nominal_voltage')
    if duplicate_voltage in (None, ''):
      duplicate_file = shift_value.get('duplicate_of_file')
      return f' [dup. de {duplicate_file}]' if duplicate_file else ' [curva duplicada]'

    return f' [dup. de {self.__format_voltage_display(duplicate_voltage)}]'


  def __normalize_selected_curves(self, selected_curves):
    """
      Normalizes selected curve names preserving user order.
    """
    if selected_curves in (None, "", []):
      return []

    if isinstance(selected_curves, str):
      tokens = [token.strip() for token in selected_curves.split(",")]
      return [token.lower() for token in tokens if token]

    return [
      str(value).strip().replace("\\", "/").lower()
      for value in selected_curves
      if str(value).strip() != ""
    ]


  def __prepare_shift_list(self, shift_list, selected_curves, count, type_data):
    """Prepares the shift list used by both model and experimental legends."""
    if shift_list is None:
      return []

    if shift_list and isinstance(shift_list[0], dict):
      expected_curve_type = 'transfer' if type_data == 0 else 'output'
      shift_list = [
        shift_entry for shift_entry in shift_list
        if str(shift_entry.get('curve_type', expected_curve_type)).strip().lower() == expected_curve_type
      ]

    normalized_selected_curves = self.__normalize_selected_curves(selected_curves)
    if len(normalized_selected_curves) == 0:
      return shift_list

    alias_map = {}
    for shift_entry in shift_list:
      curve_name = shift_entry.get('curve_name') if isinstance(shift_entry, dict) else None
      if not curve_name:
        return shift_list

      normalized_curve_name = str(curve_name).strip().replace("\\", "/").lower()
      filename = os.path.basename(normalized_curve_name)
      stem = os.path.splitext(filename)[0]
      alias_map.setdefault(normalized_curve_name, shift_entry)
      alias_map.setdefault(filename, shift_entry)
      alias_map.setdefault(stem, shift_entry)

    shift_list_update = []
    for selected_curve in normalized_selected_curves:
      shift_entry = alias_map.get(selected_curve)
      if shift_entry is not None and shift_entry not in shift_list_update:
        shift_list_update.append(shift_entry)

    if shift_list_update:
      return shift_list_update
    return shift_list_update

  # Function to generate legend names
  def __legend_name(self, volt_data, exp_data, shift_list, j, no_shift=False):
    """
      Generates names for the graph legend based on voltage data, experimental data, voltage shift, and index j.

      Args:
          volt_data (list): A list of voltage data.
          exp_data (list): A list of experimental data.
          shift_list (list): A list of voltage shift values.
          j (int): The current index for which the legend name is being generated.
          no_shift (bool, optional): Indicates whether the voltage shift should not be included in the name (default is False).

      Returns:
          str: The generated legend name.

      Example:
          >>> volt_data = [1.0, 2.0, 3.0]
          >>> exp_data = [0.1, 0.2, 0.3]
          >>> shift_list = [0.1, -0.2, 0.0, -0.3]
          >>> j = 1
          >>> no_shift = False
          >>> legend_name = __legend_name(volt_data, exp_data, shift_list, j, no_shift)
    """

    shift_list = self.__change_signal_shift(shift_list) if shift_list is not None else []

    def safe_index(values, idx, default='?'):
      if not values:
        return default
      if idx < 0 or idx >= len(values):
        return default
      return values[idx]

    volt = safe_index(volt_data, j)
    base_name = '<b>Exp <b>' + ' ' + f'<b>{self.__format_voltage_display(volt)}<b>'
    if no_shift or not shift_list:
      return str(base_name)

    shift = safe_index(shift_list, j, None)
    if shift is None:
      return str(base_name)
    shift_text = self.__format_shift_display(shift)
    consistency_text = self.__format_consistency_display(shift)
    return str(base_name + ' ' + f'<b> ({shift_text})<b>' + consistency_text)

  # Function to generate legend text
  def __legend_text(self, xlegend, volt_data, exp_data, shift_list, j, no_shift=False):

    """
      Generates text for the graph legend based on voltage data, voltage shift, index j, and an x-axis label.

      Args:
          xlegend (str): An x-axis label.
          volt_data (list): A list of voltage data.
          exp_data (list): A list of experimental data.
          shift_list (list): A list of voltage shift values.
          j (int): The current index for which the legend text is being generated.
          no_shift (bool, optional): Indicates whether the voltage shift should not be included in the legend text (default is False).

      Returns:
          list: A list containing the generated legend text.

      Example:
          >>> xlegend = 'Voltage'
          >>> volt_data = [1.0, 2.0, 3.0]
          >>> exp_data = [0.1, 0.2, 0.3]
          >>> shift_list = [0.1, -0.2, 0.0, -0.3]
          >>> j = 1
          >>> no_shift = False
          >>> legend_text = __legend_text(xlegend, volt_data, exp_data, shift_list, j, no_shift)
    """

    shift_list = self.__change_signal_shift(shift_list) if shift_list is not None else []

    def safe_index(values, idx, default='?'):
      if not values:
        return default
      if idx < 0 or idx >= len(values):
        return default
      return values[idx]

    volt = safe_index(volt_data, j)
    base_text = [f'{xlegend}={self.__format_voltage_display(volt)}']
    if no_shift or not shift_list:
      return base_text

    shift = safe_index(shift_list, j, None)
    if shift is None:
      return base_text
    shift_text = self.__format_shift_display(shift)
    consistency_text = self.__format_consistency_display(shift)
    return [base_text[0] + ' ' + f'({shift_text})' + consistency_text]


  def plot_vgs_vds( self, list_tension, input_tension_shift, type_data, count, model_data,
                    shift_list, selected_curves, *exp_data, sample_unit='A', plot_type='linear', compare=False):
    """
      Generates a graph comparing experimental data and models for transfer or output curves.

      Args:
          list_tension (list): A list of voltage values.
          input_tension_shift (list/int): A list of voltage shifts or a single shift value.
          type_data (int): The type of data to be plotted (0 for transfer curves, 1 for output curves).
          count (int): The number of curves in the dataset.
          model_data (list): A list of model data.
          shift_list (list): A list of voltage shifts corresponding to output curves.
          *exp_data (list): Experimental data for plotting. Each pair of elements [x, y] represents a curve.
          sample_unit (str): The sample unit used (e.g., 'A' for amperes).
          plot_type (str): The type of plotting ('linear' or 'log').
          compare (bool): If True, optimized model data is plotted along with model data.

      Returns:
          None

      Example:
          >>> list_tension = [1.0, 2.0, 3.0]
          >>> input_tension_shift = [0.1, -0.2, 0.0]
          >>> type_data = 0
          >>> count = 3
          >>> model_data = [(x, [x**2 for x in range(5)]) for x in list_tension]
          >>> shift_list = [0.1, -0.2, 0.0]
          >>> exp_data = [[list(range(5)), [x**2 for x in range(5)]] for _ in range(count)]
          >>> sample_unit = 'A'
          >>> plot_type = 'linear'
          >>> compare = True
          >>> plot_vgs_vds(list_tension, input_tension_shift, type_data, count, model_data,
          ...               shift_list, *exp_data, sample_unit, plot_type, compare)
    """

    shift_list_update = self.__prepare_shift_list(shift_list, selected_curves, count, type_data)

    # Predefined color options for plotting
    list_colors = ['rgb(255, 0, 0)', 'rgb(0, 0, 255)', 'rgb(30, 144, 255)',
                  'rgb(0, 255, 0)', 'rgb(255, 0, 255)', 'rgb(0, 255, 255)']

    # Constants for data types
    curv_transfer = 0
    curv_out = 1

    # Create a figure object
    fig = go.Figure()

    if plot_type == 'log':
      scale = "log"

    elif plot_type == 'linear':
      scale = "linear"
    else:
      print('Not valide')

    # Handle different data types and set plot labels (curves transfer)
    if type_data == curv_transfer:
      if scale == 'log':
        text = "<b>VGS / V<b>"
        xlegend = '<b>VDS<b>'
        ylegend = f"<b>|ID| / A<b>"
        title_update = '<b>Experimental Datas Vs Model<b>'
        volt_data = []
      else:
        text = "<b>VGS / V<b>"
        xlegend = '<b>VDS<b>'
        ylegend = f"<b>ID / {sample_unit}<b>"
        title_update = '<b>Experimental Datas Vs Model<b>'
        volt_data = []
        new_volt =  []


      if isinstance(input_tension_shift, int):
          volt_data = [input_tension_shift]
          new_volt  = [list_tension]
          title_update, volt_data = self.__calc_volt_data(compare, volt_data)
          _ , new_volt = self.__calc_volt_data(compare, new_volt)

      else:
          volt_data = input_tension_shift[:count]
          new_volt  = list_tension[:count]
          title_update, volt_data = self.__calc_volt_data(compare, volt_data)
          _ , new_volt  = self.__calc_volt_data(compare, new_volt)

    # Curves out
    elif type_data == curv_out:
        text = "<b>VDS / V<b>"
        xlegend = '<b>VGS<b>'
        ylegend = f"<b>ID / {sample_unit}<b>"
        title_update = '<b>Experimental Datas Vs Model<b>'
        volt_data = []
        new_volt =  []

        if isinstance(input_tension_shift, int):
            volt_data = [input_tension_shift]
            new_volt  = [list_tension]
            title_update, volt_data = self.__calc_volt_data(compare, volt_data)
        else:
            volt_data = input_tension_shift[count:]
            new_volt  = list_tension[count:]
            title_update, volt_data = self.__calc_volt_data(compare, volt_data)
            _ , new_volt  = self.__calc_volt_data(compare, new_volt)

    else:
        print("ERROR in type_data")

    # ------------------------------------------------------------------------
    # MODEL PLOT
    # Iterate through model data ---------------------------------------------
    cor_index = 0  # color index
    for i, data in enumerate(model_data):
        name = ''

        if scale == 'log' and type_data == curv_transfer:
          y_data = 10**(data[1])
        else:
          y_data = data[1]

        if type_data == curv_transfer or type_data == curv_out:
            if i < (len(volt_data) // 2) or not compare:
                cor = list_colors[cor_index]
                cor_index = (cor_index + 1) % len(list_colors)
                dash_style = 'dash'  # Linha pontilhada para modelos aproximados
                name = '<b>Model OVSED<b>'
            elif i >= (len(volt_data) // 2) and compare:
                cor = 'black'  # The first color aways black
                dash_style = 'solid'  # Linha sólida para modelos otimizados
                name = '<b>Model OPT<b>'

            if volt_data:
                legend_voltage = volt_data[i] if i < len(volt_data) else volt_data[-1]
            else:
                legend_voltage = 0.0
            if shift_list_update:
                base_output_count = len(new_volt) // 2 if compare else len(new_volt)
                output_count = max(1, base_output_count)
                shift_index = i % output_count
                if shift_index < len(shift_list_update):
                    shift_text = self.__format_shift_display(shift_list_update[shift_index])
                else:
                    shift_text = self.__format_shift_display(0.0)
                model_name = name + ' ' + f'<b>{self.__format_voltage_display(legend_voltage)}<b>' + ' ' + f'<b>({shift_text})<b>'
            else:
                model_name = name + ' ' + f'<b>{self.__format_voltage_display(legend_voltage)}<b>'

            fig.add_trace(go.Scatter(x=data[0], y=y_data,
                                    mode='lines+text',
                                    name=model_name,
                                    line=dict(color=cor,  dash=dash_style),  # Use the choice color
                                    text=[self.__format_voltage_display(legend_voltage)],
                                    textposition='bottom center',
                                    textfont=dict(
                                        family="Times New Roman",
                                        size=13,
                                        color=cor)))  # use the same color in text

        else:
            print("ERROR TYPE OF DATA")
    # ------------------------------------------------------------------------

    j = 0

    # ------------------------------------------------------------------------
    #DATA PLOT
    # Plot experimental data -------------------------------------------------
    for i in range(0, len(exp_data), 2):
        colors = list_colors[j % len(list_colors)]
        if type_data == curv_transfer and scale == 'log':
            data = 10**(exp_data[i + 1])

        elif type_data == curv_transfer and scale == 'linear':
            data = exp_data[i + 1]

        else:
            data = exp_data[i + 1]

        fig.add_trace(go.Scatter(x=exp_data[i], y=data,
                                mode='markers+text',
                                name=self.__legend_name(new_volt, exp_data, shift_list_update, j, no_shift=True),
                                text=self.__legend_text(xlegend, volt_data, exp_data, shift_list_update, j, no_shift=True),
                                textposition='top right',
                                textfont=dict(
                                    family="Times New Roman",
                                    size=18,
                                    color=colors),
                                marker=dict(color=colors,
                                            size=11,
                                            opacity=0.5,
                                            line=dict(color='MediumPurple',
                                                      width=0.8)
                                            )))
        j += 1

    # Update layout of the plot
    fig.update_layout(
        title=str(title_update),
        title_x=0.45,
        title_y=0.9,
        title_font=dict(
            family="Overpass",
            size=25,
            color='black'
        ),
        height=self.height, width=self.width,
        legend=dict(font=dict(size=16))
    )

    size_text = 25
    fig.update_xaxes(
        title_text=text,
        title_font=dict(
            family="Overpass",
            size=size_text,
            color='black'),
        title_standoff=25)

    if type_data == curv_transfer:
      fig.update_yaxes(
          type=scale,
          title_text = ylegend,
          title_font=dict(
            family="Overpass",
            size=size_text,
            color= 'black'),
          title_standoff = 10)
      # print('SCALE', scale)
    else:
      fig.update_yaxes(
        type='linear',
        title_text = ylegend,
        title_font=dict(
          family="Overpass",
          size=size_text,
          color= 'black'),
        title_standoff = 10)

    # Show the plot
    fig.show()
