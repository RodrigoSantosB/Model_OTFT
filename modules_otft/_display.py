
def display_settings(menu, settings, path_voltages, shift_list, list_tension_shift):
    def format_shift_entries(entries):
        if not entries or not isinstance(entries, list):
            return entries

        if not isinstance(entries[0], dict):
            return entries

        formatted = []
        for index, shift in enumerate(entries, start=1):
            formatted.append(
                f'curve_{index}: total={shift.get("total", 0.0):.4g}V '
                f'(global={shift.get("manual", 0.0):.4g}V, '
                f'auto={shift.get("automatic", 0.0):.4g}V)'
            )
        return formatted

    print()
    print('Settings:')
    print('---------------------------------')
    print('Type read data: ' + f'{settings["type_read_data_exp"]}')
    print('Current typic : ' + f'{settings["current_typic"]}')
    print('Scale transfer: ' + f'{settings["experimental_data_scale_transfer"]}')
    print('Scale output  : ' + f'{settings["experimental_data_scale_output"]}')
    if "enable_pre_processing" in settings:
        print('Pre-process   : ' + f'{settings["enable_pre_processing"]}')
    if "apply_local_output_shift" in settings:
        print('Local shift   : ' + f'{settings["apply_local_output_shift"]}')
    print('Shift value   : ' + f'{format_shift_entries(shift_list)}')
    print('List volt shift: ' +  f'{list_tension_shift}')
    menu.view_path_reads(path_voltages, list_tension_shift)
    print()
    print('A tabela acima mostra todos os arquivos lidos no diretorio. Para filtrar, informe em select_files')
    print('os indices das curvas que deseja MANTER, usando base 1 (primeira curva = 1), separados por virgula.')
    print('Exemplo: 1:org1_2VDS, 4:org1_40VGS ou qualquer outro nome listado na tabela.')
    print('---------------------------------')
    print()
