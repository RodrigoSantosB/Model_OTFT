from ._imports import *

class TFTGraphicsPlot():
  
  COUNT_TRANSFER = 0

  def __init__(self, height=600, width=1100):
    self.height = height
    self.width = width
    
  def set_count_transfer(self, count_transfer):
    self.COUNT_TRANSFER = count_transfer

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
        title_update = '<b>Model Vs Model Optimized<b>'
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

    inverted_list = [-x if x > 0 else abs(x) for x in shift_list]
    return inverted_list

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


    shift_list = self.__change_signal_shift(shift_list)

    def format_name(volt_data, shift_list, j):
        return '<b>Exp <b>' + ' ' + f'<b>{volt_data[j]}' + 'V<b>' + ' ' + f'<b> ({shift_list[j]}V)<b>'

    def _name(volt_data, shift_list, j):
        return '<b>Exp <b>' + ' ' + f'<b>{volt_data[j]}' + 'V<b>'

    if len(exp_data) < 3:
      if shift_list is not None:
        if no_shift:
          name = _name(volt_data, shift_list, j)
        else:
          name = format_name(volt_data, shift_list, 0)
      else:
          name = _name(volt_data, shift_list, 0)

    elif len(exp_data) > 2:
      if shift_list is not None:
        if len(shift_list) == 1:
          if j >= len(shift_list):
              name = _name(volt_data, shift_list, j)
          else:
              if no_shift:
                name = _name(volt_data, shift_list, j)
              else:
                name = format_name(volt_data, shift_list, 0)

        elif len(shift_list) >= 2:
          try:
              if no_shift:
                name = _name(volt_data, shift_list, j)
              else:
                name = format_name(volt_data, shift_list, j)
          except IndexError:
              name = _name(volt_data, shift_list, j)
      else:
          name = _name(volt_data, shift_list, j)
    return str(name)

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

    def format_text(volt_data, shift_list, j):
      # Formata o texto da legenda com base nos dados de tensão, deslocamento de tensão e um índice j.
      #Args:
        #volt_data (list): Uma lista de dados de tensão.
        #shift_list (list): Uma lista de deslocamento de tensão.
        #j (int): O índice atual para o qual o texto da legenda está sendo gerado.

      #Returns:
        # list: Uma lista contendo o texto formatado da legenda.
      return [f'{xlegend}={volt_data[j]}V' + ' ' + f' ({shift_list[j]})']

    # Formata o texto da legenda sem incluir o deslocamento de tensão com base nos dados de tensão e um índice j.
    def _text(volt_data, shift_list, j):
        return [f'{xlegend}={volt_data[j]}V']

    shift_list = self.__change_signal_shift(shift_list)

    if len(exp_data) < 3:
      if shift_list is not None:
        if no_shift:
          text = _text(volt_data, shift_list, 0)
        else:
          text = format_text(volt_data, shift_list, 0)
      else:
          text = _text(volt_data, shift_list, j)

    elif len(exp_data) > 2:
      if shift_list is not None:
        if len(shift_list) == 1:
          if j >= len(shift_list):
              text = _text(volt_data, shift_list, j)
          else:
            if no_shift:
              text = _text(volt_data, shift_list, 0)
            else:
              text = format_text(volt_data, shift_list, 0)

        elif len(shift_list) >= 2:
          try:
            if no_shift:
              text = _text(volt_data, shift_list, j)
            else:
              text = format_text(volt_data, shift_list, j)
          except IndexError:
              text = _text(volt_data, shift_list, j)
      else:
          text = _text(volt_data, shift_list, 0)
    return text


  def plot_vgs_vds( self, list_tension, input_tension_shift, type_data, count, model_data,
                    shift_list, select_files, *exp_data, sample_unit='A', plot_type='linear', compare=False):
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


    if isinstance(select_files, str):
      if not select_files:
        select_files = ""
      else:
        select_files = list(eval(select_files))

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
        ylegend = f"<b>|ID| / {sample_unit}<b>"
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
    for i, data in enumerate(model_data):
        name = ''

        if scale == 'log' and type_data == curv_transfer:
          y_data = 10**(data[1])
        else:
          y_data = data[1]

        if type_data == curv_transfer:
            if i < (len(volt_data) // 2) or not compare:
                name = '<b>Model OVSED<b>'
            elif i >= (len(volt_data) // 2) and compare:
                name = '<b>Model OPT<b>'

            fig.add_trace(go.Scatter(x=data[0], y=y_data,
                                    mode='lines+text',
                                    name=name + ' ' + f'<b>{volt_data[i]}' + 'V<b>',
                                    line=dict(color='black'),
                                    text=[f'{volt_data[i]}V'],
                                    textposition='bottom center',
                                    textfont=dict(
                                        family="Times New Roman",
                                        size=13,
                                        color="black")))


        elif type_data == curv_out:
            if i < (len(volt_data) / 2) or not compare:
                name = '<b>Model OVSED<b>'
            elif i >= (len(volt_data) / 2) and compare:
                name = '<b>Model OPT<b>'

            fig.add_trace(go.Scatter(x=data[0], y=data[1],
                                    mode='lines+text',
                                    name=name + ' ' + f'<b>{volt_data[i]}' + 'V<b>',
                                    line=dict(color='black'),
                                    textposition='bottom center',
                                    textfont=dict(
                                        family="Times New Roman",
                                        size=13,
                                        color="black")))
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
            no_shift = True

        elif type_data == curv_transfer and scale == 'linear':
            data = exp_data[i + 1]
            no_shift = True

        else:
            data = exp_data[i + 1]
            no_shift = False

        shift_list_update = []
        if (len(select_files) != 0) and (len(select_files) < len(shift_list)):
          for index in select_files:
            try:
              if self.COUNT_TRANSFER == 0:
                shift_list_update.append(shift_list[index-1])
              else:
                shift_list_update.append(shift_list[index-self.COUNT_TRANSFER])

            except IndexError:
              if self.COUNT_TRANSFER == 0:
                shift_list_update.append(shift_list[index-1])
              else:
                shift_list_update.append(shift_list[index-self.COUNT_TRANSFER])

        else:

          shift_list_update = shift_list

        fig.add_trace(go.Scatter(x=exp_data[i], y=data,
                                mode='markers+text',
                                name=self.__legend_name(new_volt, exp_data, shift_list_update, j, no_shift),
                                text=self.__legend_text(xlegend, volt_data, exp_data, shift_list_update, j, no_shift),
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