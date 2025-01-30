from modules_otft._imports import *
from modules_otft._imports import *
from modules_otft._grafics import  TFTGraphicsPlot
from modules_otft._optmization import ModelOptmization

import json

def enter_with_json_file():
    print(200 * '-')
    json_path = input('Enter the JSON file path, for example: "/content/gdrive/your/path/json": \n\n')
    print(200 * '-')

    with open(json_path, 'r') as file:
        inputs = json.load(file)

    global settings
    settings = {}

    print('\n')
    print(83 * '_' + ' SETTINGS PRESENT IN THE JSON FILE:' + 83 * '_' + '\n')
    for block in inputs:
        # Iterates over each key-value pair in the data block
        for key, value in block.items():
            # Assigns the value to the corresponding variable
            settings[key] = value
            print('|' + ' ' + f'{key}: {value}')
            print('--' * 100)

    return settings


def get_load_voltages(settings):
    """Loads voltage values."""
    
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'loaded_voltages' not in settings:
        print("Error: 'loaded_voltages' key not found in settings.")
        return []

    try:
        value = eval(settings['loaded_voltages'])
        if isinstance(value, int):
            return [value]
        elif isinstance(value, (list, tuple)) and len(value) > 2:
            return list(value)
    except (SyntaxError, NameError):
        print("No parameters entered in --- settings['loaded_voltages'] ---, please load them\n")
    
    return []


def get_type_plot(settings):
    """Returns the type of plot."""
    
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'type_curve_plot' not in settings:
        print("Error: 'type_curve_plot' key not found in settings.")
        return []

    
    if (settings['type_curve_plot'] == 'logarithmic') or (settings['type_curve_plot'] == 'log'):
        return 'log'
    else:
        return 'linear'
    
    
def calculate_shift_list(settings):
  """Calculates the displacement list."""
  
  if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []

  ld_voltages = get_load_voltages(settings)
  max_curves = len(ld_voltages) - int(settings['curves_transfer'])
  try:
      if settings['shift_volt_data'] =="":
          return [0] * max_curves
      elif isinstance(eval(settings['shift_volt_data']), int):
          return [int(settings['shift_volt_data'])]
      
      elif len(settings['shift_volt_data']) > 1:
          return list(eval(settings['shift_volt_data']))
  except ValueError:
      print("No shift value passed, please enter a value\n")
      return []
  

def get_shift_list(read, settings):
  # Returns the shifted list with the passed voltage value [V]
  curves_transfer = int(settings['curves_transfer'])
  shift_list = calculate_shift_list(settings)
  ld_voltages = get_load_voltages(settings)

  list_tension_shift = read.apply_shifts(curves_transfer ,shift_list, ld_voltages)
  return list_tension_shift


# new curves calculation
def new_curves_calculation(path_voltages, voltages):
    new_curves = []
    for i, (j,  k) in enumerate(zip(path_voltages, voltages)):
      tes = path_voltages[i][0]
      filename = os.path.basename(tes)
      new_curves.append(filename)
    return new_curves


# filter files with the selected values
def filter_and_load_files(read, settings, path_voltages, list_tension_shift):
    """Filters and loads files."""

    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    elif not isinstance(read, object):
        print("Error: read must be an object.")
        return []

    f_selection = []
    list_tension_shift = get_shift_list(read, settings)
    ld_voltages = get_load_voltages(settings)
    list_curves = new_curves_calculation(path_voltages, list_tension_shift)
    
    if settings['select_files'] == "":
      return read.read_files_experimental(settings['path'], list_tension_shift), ld_voltages, list_tension_shift
    try:
        if isinstance(eval(settings['select_files']), int):
            f_selection = [int(settings['select_files'])]
        elif len(settings['select_files']) > 1:
            f_selection = list(eval(settings['select_files']))
        else:
            print("No value available\n")
            return None
    except NameError:
        print("No value available, please enter a valid value\n")
        return None

    new_files_filter, new_values_tension, new_list_tension = read.filter_files(
                                                             f_selection, list_curves, list_tension_shift, ld_voltages)
    path_voltages = read.read_files_experimental(settings['path'], new_values_tension, selected_files=new_files_filter)
    return path_voltages, new_values_tension, new_list_tension


def get_transistor_type(settings):
    """Gets the transistor type."""
    
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'type_of_transistor' not in settings:
        print("Error: 'type_of_transistor' key not found in settings.")
        return []

    return 1 if settings['type_of_transistor'] == 'nFET' else -1


def get_resistance(settings):
    """Gets the resistance value."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'resistance_scale' not in settings:
        print("Error: 'resistance_scale' key not found in settings.")
        return []
    
    if not settings['resistance_scale']:
        print("No `RESISTANCE` value loaded\n")
        return None
    return float(settings['resistance_scale'])


def get_current(settings):
    """Gets the current value."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'current_carry' not in settings:
        print("Error: 'current_carry' key not found in settings.")
        return []
    
    if not settings['current_carry']:
        print("No `CURRENT` value loaded\n")
        return None
    return float(settings['current_carry'])


def get_transistor_width(settigs):
    """Gets the width of the transistor."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'with_transistor' not in settings:
        print("Error: 'with_transistor' key not found in settings.")
        return []
    
    return float(settings['with_transistor']) if settings['with_transistor'] else 0.1000


def load_coefficients(settings):
    """Load the parameters."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'loaded_parameters' not in settings:
        print("Error: 'loaded_parameters' key not found in settings.")
        return []
    try:
        return list(settings['loaded_parameters'].values())
    except SyntaxError:
        print("No parameters entered, please load them\n")
        return []


def load_idleak_parameters(settings):
    """Loads idleak parameters."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'idleak_mode' not in settings or 'loaded_idleak' not in settings:
        print("Error: 'idleak_mode' or loaded_idleak key not found in settings.")
        return []
    
    mode_idleak = 0 if settings['idleak_mode'] == 'unique idleak value' else 1
    try:
        if mode_idleak == 0:
            return mode_idleak, float(settings['loaded_idleak'])
        else:
            return mode_idleak, list(eval(settings['loaded_idleak']))
    except SyntaxError:
        print("No parameters entered, please load them\n")
        return mode_idleak, []


def initialize_graphics_plot(settings):
    """Initializes the graphics class with the given dimensions."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'image_size_height' not in settings or 'image_size_width' not in settings:
        print("Error: 'image_size_height' or 'image_size_width' key not found in settings.")
        return []
    
    if not settings['image_size_width'] or not settings['image_size_height']:
        settings['image_size_width'] = 1100
        settings['image_size_height'] = 600
    return TFTGraphicsPlot(settings['image_size_height'], settings['image_size_width'])


def get_bounds(settings):
    """Gets the lower and upper bounds."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'lower_bounds' not in settings or 'upper_bounds' not in settings:
        print("Error: 'lower_bounds' or 'upper_bounds' key not found in settings.")
        return []
    return list(settings['lower_bounds'].values()), list(settings['upper_bounds'].values())


def get_tolerance_factor(settings):
    """Gets the tolerance factor."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'tolerance_factor' not in settings:
        print("Error: 'tolerance_factor' key not found in settings.")
        return []
    if not settings['tolerance_factor']:
        print("No tolerance factor loaded\n")
        return float(4e-6)
    return float(settings['tolerance_factor'])


def configure_bounds(settings):
    """Sets default limits if necessary."""
    if not isinstance(settings, dict):
        print("Error: settings must be a dictionary.")
        return []
    
    if 'default_bounds' not in settings or 'lw_bounds' not in settings or 'up_bounds' not in settings:
        print("Error: 'default_bounds' or 'lw_bounds' or 'up_bounds' key not found in settings.")
        return []
    if settings['default_bounds'] == 'yes':
        return None, None
    return settings['lw_bounds'], settings['up_bounds']


def instance_model(read, TFTModel, n_points, type_curve_plot, load_parameters, input_voltage, Vv, load_idleak, width_t,
                            count_transfer, tp_tst, experimental_data_scale_transfer, current_typic, resistance, current):
    """Creates an instance of the model with the provided data."""
    return read.create_models_datas(TFTModel, n_points, type_curve_plot, load_parameters, 
                                    input_voltage, Vv, load_idleak, width_t, count_transfer, 
                                    tp_tst=tp_tst, scale_factor=experimental_data_scale_transfer,
                                    current_typic=current_typic, res=resistance, curr=current)


def load_experimental_data(read, count_transfer, Vv, Id, model, count_output):
    """Loads experimental and model data for visualization."""
    in_model_data, in_exp_data = read.group_by_trasfer(count_transfer, Vv, Id, model)
    out_model_data, out_exp_data = read.group_by_output(count_output, count_transfer, Vv, Id, model)
    return in_model_data, in_exp_data, out_model_data, out_exp_data


def create_model_opt(TFTModel, input_voltage, n_points, type_curve_plot, current_typic,
                     experimental_data_scale_transfer, load_idleak, mode_idleak, count_transfer,
                                                                            resistance, current):
    """Creates an optimization model."""
    model_id = TFTModel( input_voltage, n_points, type_curve_plot, current_typic=current_typic,
                        scale_factor=experimental_data_scale_transfer, idleak=load_idleak,
                        mult_idleak=mode_idleak,  curv_transfer=count_transfer,
                        sr_resistance=resistance, curr_carry=current)
    return model_id


def create_optimizer(settings, path_voltages, type_curve_plot):
    """Creates and configures the optimizer instance."""
    lw_bounds, up_bounds = get_bounds(settings)
    

    optimizer = ModelOptmization(current_typic=settings['current_typic'], scale_transfer=settings['experimental_data_scale_transfer'], 
                                 scale_output=settings['experimental_data_scale_output'], path_voltages=path_voltages, 
                                 type_read=settings['type_read_data_exp'],
                                 type_curve=type_curve_plot, method=settings['optimization_method'], 
                                 bounds=(lw_bounds, up_bounds))
    return optimizer


def configure_optimizer(optimizer, settings):
    """Configures the optimizer parameters."""
    tlr_factor = get_tolerance_factor(settings)
    optimizer.set_default_bounds(settings['default_bounds'])
    optimizer.set_ftol_param(tlr_factor)


def optimize_model(optimizer, model_id, load_parameters, *path_voltages):
    """Performs model optimization."""
    coeff_opt, coeff_error, text_verbose = optimizer.optimize_all(model_id, load_parameters, *path_voltages)
    return coeff_opt, coeff_error, text_verbose


def show_model_parameters_optimized(menu, option, load_parameters, coeff_opt, 
                                    coeff_error, current_carry, current_typic, 
                                    resistance):
    '''
    Function to show the optimized parameters of the model.
    '''
    if option == 'Show the coeff values':
      menu.print_values(load_parameters)

    elif option == 'Show the initial values':
      menu.print_values(load_parameters)

    elif option == 'coeff opt':
      menu.print_values(coeff_opt)

    elif option == 'coeff error':
      menu.print_values(coeff_error)

    elif option == 'Show the table of values opt':
      menu.show_table_info(load_parameters, coeff_opt, 
                           coeff_error, current_typic, 
                           current_carry, resistance)

    print('\n\n\n')


def create_optimized_model(read, TFTModel, n_points, type_curve_plot, coeff_opt, 
                           input_voltage, Vv, load_idleak, width_t, count_transfer, 
                           tp_tst, experimental_data_scale_transfer, 
                           current_typic, resistance, current):
    """Creates the model with the optimized coefficients."""
    return read.create_models_datas(TFTModel, n_points, type_curve_plot, coeff_opt, 
                                    input_voltage, Vv, load_idleak, width_t, count_transfer, 
                                    tp_tst=tp_tst, scale_factor=experimental_data_scale_transfer,
                                    current_typic=current_typic, res=resistance, curr=current)
    

def get_model_data(read, count_transfer, count_output, Vv, Id, model_opt, model=None, compare=False):
    """Gets experimental and model data (transfer and output)."""
    in_model_data_opt, in_exp_data_opt = read.group_by_trasfer(count_transfer, Vv, Id, model_opt)
    out_model_data_opt, out_exp_data_opt = read.group_by_output(count_output, count_transfer, Vv, Id, model_opt)
    
    if compare and model is not None:
        in_model_data_comp, in_exp_data_comp = read.group_by_trasfer(count_transfer, Vv, Id, model, model_opt, compare=True)
        out_model_data_comp, out_exp_data_comp = read.group_by_output(count_output, count_transfer, Vv, Id, model, model_opt, compare=True)
        return in_model_data_opt, in_exp_data_opt, out_model_data_opt, out_exp_data_opt, in_model_data_comp, in_exp_data_comp, out_model_data_comp, out_exp_data_comp
    
    return in_model_data_opt, in_exp_data_opt, out_model_data_opt, out_exp_data_opt, None, None, None, None


def plot_curves(option, plot, list_tension, list_tension_shift, count_transfer, 
                in_model_data, out_model_data, in_exp_data, out_exp_data, shift_list, 
                select_files,current_typic, type_curve_plot, compare=False):
    """Plots the curves according to the selected option."""
    clear_output(wait=True)  # clear displayed content
    if option == 'Show transfer curve opt':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
    
    elif option == 'Show output curve opt':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, plot_type='linear')
    
    elif option == 'Show both curves opt':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
        print()
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic)
    
    elif option == 'Show transfer curve comp' and compare:
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot, 
                          compare=True)
    
    elif option == 'Show output curve comp' and compare:
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, compare=True)
    
    elif option == 'Show both curves comp' and compare:
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot, 
                          compare=True)
        print()
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, compare=True)
    
    elif option == 'Show transfer curve':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
    elif option == 'Show output curve':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, plot_type='linear')
    elif option == 'Show both curves':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
        print()
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, plot_type='linear')
    else:
        print("No option choice\n")
    print('\n\n\n')


def vtho_calculation(in_model_data, signal_of_data=1):

    tensions = in_model_data[0][0]
    currents = in_model_data[0][1]

    # Calculando as derivadas primeira e segunda em relação a V_GS
    dI_D_dVGS = np.gradient(currents, tensions)
    dI_D_dVGS = dI_D_dVGS*(signal_of_data)
    d2I_D_dVGS2 = np.gradient(dI_D_dVGS, tensions)

    # Encontrando o índice onde a derivada segunda é máxima (pico)
    index_vtho = np.argmin(d2I_D_dVGS2)
    Vtho = tensions[index_vtho]

    # Criando o gráfico com Plotly
    fig = go.Figure()

    # Adicionando as linhas para a 1ª e 2ª derivadas
    fig.add_trace(go.Scatter(x=tensions, y=currents, mode='lines', name='I_D vs V_GS', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=tensions, y=dI_D_dVGS, mode='lines', name='dI_D/dV_GS (1ª derivative)', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=tensions, y=d2I_D_dVGS2, mode='lines', name='d²I_D/dV_GS² (2ª derivative)', line=dict(color='red')))

    # Adicionando a linha vertical para Vtho
    if Vtho is not None:
        fig.add_vline(x=Vtho, line=dict(color='green', dash='dash'), annotation_text=f'<b>Vtho ~ {Vtho:.2f} V</b>', annotation_position='top left')

    # Adicionando título e labels
    fig.update_layout(
        title=dict(text=' Current vs. Tension whith Vtho value', x=0.5, y=0.95, font=dict(size=20, family='Arial', weight='bold')),
        xaxis_title='<b>VGS / V</b>',
        yaxis_title='<b>ID / A and Derivatives </b>',
        font=dict(family='Arial', size=18, color='black'),
        legend=dict(x=0.04, y=0.04),
        template='plotly',
        showlegend=True,
        width=1100,  # Definindo a largura do gráfico
        height=600  # Definindo a altura do gráfico

    )

    # Exibindo o gráfico
    fig.show()