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



def load_voltages(loaded_voltages):
  """Loads voltage values."""
  try:
      if isinstance(eval(loaded_voltages), int):
          return [int(loaded_voltages)]
      elif len(loaded_voltages) > 2:
          return list(eval(loaded_voltages))
  except SyntaxError:
      print("No parameters entered in --- loaded_voltages ---, please load them\n")
      return []



def get_type_plot(type_curve_plot):
  if type_curve_plot == 'logarithmic' or 'log':
    return 'log'
  else:
    return 'linear'


def calculate_shift_list(shift_volt_data, ld_voltages, curves_transfer):
  """Calculates the displacement list."""
  max_curves = len(ld_voltages) - curves_transfer
  try:
      if not shift_volt_data:
          return [0] * max_curves
      elif isinstance(eval(shift_volt_data), int):
          return [int(shift_volt_data)]
      elif len(shift_volt_data) > 1:
          return list(eval(shift_volt_data))
  except ValueError:
      print("No shift value passed, please enter a value\n")
      return []



def get_shift_list(read, curves_transfer, shift_list, ld_voltages):
  # Returns the shifted list with the passed voltage value [V]
  list_tension_shift = read.apply_shifts(curves_transfer ,shift_list, ld_voltages)
  return list_tension_shift


def filter_and_load_files(read, path, select_files, list_curves, list_tension_shift, ld_voltages):
    """Filters and loads files."""
    f_selection = []
    if select_files == "":
      return read.read_files_experimental(path, list_tension_shift), ld_voltages, list_tension_shift
 
    else:
        try:
            if isinstance(eval(select_files), int):
                f_selection.append(int(select_files))   
            elif len(select_files) > 1:
                f_selection = list(eval(select_files))
            else:
                print("No value available\n")
                return None
        except NameError:
            print("No value available, please enter a valid value\n")
            return None

        new_files_filter, new_values_tension, new_list_tension = read.filter_files(
            f_selection, list_curves, list_tension_shift, ld_voltages)
        path_voltages = read.read_files_experimental(path, new_values_tension, selected_files=new_files_filter)
        return  path_voltages, new_values_tension, new_list_tension



def get_transistor_type(type_of_transistor):
    """Gets the transistor type."""
    return 1 if type_of_transistor == 'nFET' else -1



def get_resistance(resistance_scale):
    """Gets the resistance value."""
    if not resistance_scale:
        print("No `RESISTANCE` value loaded\n")
        return None
    return float(resistance_scale)



def get_current(current_carry):
    """Gets the current value."""
    if not current_carry:
        print("No `CURRENT` value loaded\n")
        return None
    return float(current_carry)



def get_transistor_width(with_transistor):
    """Gets the width of the transistor."""
    return float(with_transistor) if with_transistor else 0.1000



def load_coefficients(loaded_parameters):
    """Load the parameters."""
    try:
        return list(loaded_parameters.values())
    except SyntaxError:
        print("No parameters entered, please load them\n")
        return []



def load_idleak_parameters(idleak_mode, loaded_idleak):
    """Loads idleak parameters."""
    mode_idleak = 0 if idleak_mode == 'unique idleak value' else 1
    try:
        if mode_idleak == 0:
            return mode_idleak, float(loaded_idleak)
        else:
            return mode_idleak, list(eval(loaded_idleak))
    except SyntaxError:
        print("No parameters entered, please load them\n")
        return mode_idleak, []



def initialize_graphics_plot(image_size_width, image_size_height):
    """Initializes the graphics class with the given dimensions."""
    if not image_size_width or not image_size_height:
        image_size_width = 1100
        image_size_height = 600
    return TFTGraphicsPlot(image_size_height, image_size_width)


def instance_model(read, TFTModel, n_points, type_curve_plot, load_parameters, input_voltage, Vv, load_idleak, width_t,
                            count_transfer, tp_tst, experimental_data_scale_transfer, current_typic, resistance, current):
    """Creates an instance of the model with the provided data."""
    return read.create_models_datas(TFTModel, n_points, type_curve_plot, load_parameters, input_voltage, Vv,
                                    load_idleak, width_t, count_transfer, tp_tst=tp_tst, scale_factor=experimental_data_scale_transfer,
                                    current_typic=current_typic, res=resistance, curr=current)


def load_experimental_data(read, count_transfer, Vv, Id, model, count_output):
    """Loads experimental and model data for visualization."""
    in_model_data, in_exp_data = read.group_by_trasfer(count_transfer, Vv, Id, model)
    out_model_data, out_exp_data = read.group_by_output(count_output, count_transfer, Vv, Id, model)
    return in_model_data, in_exp_data, out_model_data, out_exp_data


def get_bounds(lower_bounds, upper_bounds):
    """Gets the lower and upper bounds."""
    return list(lower_bounds.values()), list(upper_bounds.values())


def get_tolerance_factor(tolerance_factor):
    """Gets the tolerance factor."""
    if not tolerance_factor:
        print("No tolerance factor loaded\n")
        return float(4e-6)
    return float(tolerance_factor)


def configure_bounds(default_bounds, lw_bounds, up_bounds):
    """Sets default limits if necessary."""
    if default_bounds == 'yes':
        return None, None
    return lw_bounds, up_bounds


def create_model_opt(TFTModel, input_voltage, n_points, type_curve_plot, current_typic,
                     experimental_data_scale_transfer, load_idleak, mode_idleak, count_transfer,
                                                                            resistance, current):
    """Creates an optimization model."""
    model_id = TFTModel( input_voltage, n_points, type_curve_plot, current_typic=current_typic,
                        scale_factor=experimental_data_scale_transfer, idleak=load_idleak,
                        mult_idleak=mode_idleak,  curv_transfer=count_transfer,
                        sr_resistance=resistance, curr_carry=current)
    return model_id



def create_optimizer(current_typic, experimental_data_scale_transfer, experimental_data_scale_output, 
                    type_read_data_exp, path_voltages, type_curve_plot, optimization_method, bounds):
    """Creates and configures the optimizer instance."""
    optimizer = ModelOptmization(current_typic=current_typic, scale_transfer=experimental_data_scale_transfer, 
                                 scale_output=experimental_data_scale_output,type_read=type_read_data_exp,
                                 path_voltages = path_voltages, type_curve=type_curve_plot, method=optimization_method, 
                                 bounds=bounds)
    return optimizer


def configure_optimizer(optimizer, default_bounds, tlr_factor):
    """Configures the optimizer parameters."""
    optimizer.set_default_bounds(default_bounds)
    optimizer.set_ftol_param(tlr_factor)


def optimize_model(optimizer, model_id, load_parameters, *path_voltages):
    """Performs model optimization."""
    coeff_opt, coeff_error, text_verbose = optimizer.optimize_all(model_id, load_parameters, *path_voltages)
    return coeff_opt, coeff_error, text_verbose



def show_model_parameters_optimized(menu, option, load_parameters, coeff_opt, 
                                    coeff_error, current_typic, current_carry, 
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
    if option == 'Show Transfer curve opt':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
    
    elif option == 'Show output curve opt':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic)
    
    elif option == 'show both curves opt':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
        print()
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic)
    
    elif option == 'Show Transfer curve comp' and compare:
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot, 
                          compare=True)
    
    elif option == 'Show output curve comp' and compare:
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, compare=True)
    
    elif option == 'show both curves comp' and compare:
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot, 
                          compare=True)
        print()
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, compare=True)
    
    elif option == 'Show Transfer curve':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
    elif option == 'Show output curve':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, plot_type='linear')
    elif option == 'show both curves':
        plot.plot_vgs_vds(list_tension, list_tension_shift, 0, count_transfer, 
                          in_model_data, shift_list, select_files, *in_exp_data, 
                          sample_unit=current_typic, plot_type=type_curve_plot)
        print()
        plot.plot_vgs_vds(list_tension, list_tension_shift, 1, count_transfer, 
                          out_model_data, shift_list, select_files, *out_exp_data, 
                          sample_unit=current_typic, plot_type='linear')
    else:
        print("No option choice\n")
    print('\n\n\n\n\n')

