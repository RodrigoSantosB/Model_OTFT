from ._imports import *

class TFTMenu:
  
  
    def __init__(self):
        pass
    

    def __convert_to_ampere_unit(self, scale):
        # Identify the data scale (mA or uA)
        convert_to_ampere_unit = 0
        unit = {
            'A': 1,
            'mA': 1e-3,
            'uA': 1e-6,
            'nA': 1e-9,
            'pA': 1e-12
        }

        # Check if the scale exists in the dictionary
        if scale in unit:
            convert_to_ampere_unit = unit[scale]
        else:
            raise ValueError("Invalid data scale!")
        
        return convert_to_ampere_unit

    def show_table_info(self, coeff, coeff_opt, coeff_error, curr_typic, curr_carry, resistance):

        name_par = ['VTHO [V]', 'DELTA', 'N', 'L', 'LAMBDA', 'VGCRIT [V]',
                    'JTH [μA cm^−1]', 'RS [kΩ]', 'JTH / LAMBDA * N [μA cm^−1]']

        print()
        print('---------------------------')
        print(" OPTIMIZED COEFFICIENTS:\n")
        data = []
        for name, initial, opt, error in zip(name_par, coeff, coeff_opt, coeff_error):
            data.append([name, initial, opt, error])

        curr_typic_ = self.__convert_to_ampere_unit(curr_typic)

        # Adjustments for JTH [μA cm^−1]
        data[6][1] = data[6][1] * (curr_carry / 1e-6)  # JTH = 2mA * curr_typic / 1e-6 (fixed uA)
        data[6][2] = data[6][2] * (curr_carry / 1e-6)  # scale / 1e-6

        # Adjustments for RS [kΩ]
        data[7][1] = data[7][1] * (resistance / 1e3)  # res / 1e3
        data[7][2] = data[7][2] * (resistance / 1e3)  # res / 1e3

        # Calculate and add the value of JTH / LAMBDA * N for Initial Value
        jth_lambda_n_initial = data[6][1] / (data[4][1] * data[2][1])

        # Calculate and add the value of JTH / LAMBDA * N
        jth_lambda_n = data[6][2] / (data[4][2] * data[2][2])

        # Calculate and add the value of JTH / LAMBDA * N for Associated Error
        jth_lambda_n_error = data[6][3] / (data[4][3] * data[2][3])

        data.append(['JTH / LAMBDA * N [μA cm^−1]',
                     jth_lambda_n_initial, jth_lambda_n, jth_lambda_n_error])

        # Function to wrap text in table cells
        def wrap_cell_text(text, width=20):
            return "\n".join(textwrap.wrap(text, width=width, subsequent_indent=" "*5))

        # Format values to 8 decimal places
        for row in data:
            for i in range(1, len(row)):
                if isinstance(row[i], float):
                    row[i] = "{:.8e}".format(row[i])

        # Center-align table values
        for row in data:
            for i in range(len(row)):
                row[i] = wrap_cell_text(str(row[i]))

        table = tabulate(data, headers=["Parameter", "Initial Value", "Optimized Value",
                                        "Associated Error (standard deviation)"], tablefmt="fancy_grid")
        print(table)

    def print_values(self, values):
        # Format and print stylized values
        formatted_values = ["{:.4e}".format(val) for val in values]
        formatted_output = " │ ".join(formatted_values)
        print('   VTHO     |    DELTA   |      N     |     L      |    LAMBDA  |   VGCRIT   |    JTH     |     RS    |')
        print('-'*103)
        print("[" + formatted_output + "]")
        print('-'*103)

    def view_path_reads(self, path_voltages, voltages):
        def extract_filename(path):
            return os.path.basename(path)

        print('-'*44)
        print('-'*44)
        print("|" + " "*16 + "READ FILES" + " "*16 + "|")
        print('-'*44)
        print('-'*44)

        new_curves = []

        for i, (path, voltage) in enumerate(zip(path_voltages, voltages)):
            filename = extract_filename(path[0])  # Assuming path_voltages[i][0] is a list of paths
            new_curves.append(filename)

            if len(filename) > 14:
                print('|' + ' '*(len(filename)-3) + f'{filename}' + ' '*( len(filename)-3) + '|')
                print('-'*44)
            else:
                print('|' + ' '*(len(filename)) + f'{filename}' + ' '*( len(filename)) + '|')
                print('-'*44)
        
        print('-'*44)
        return new_curves
