
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
    print('A tabela acima mostra todos os arquivos que foram lidos no diretório, caso queira filtrar arquivos para que sejam')
    print('lidos apenas aqueles que sejam de seu interesse, faça isso trocando os números que correspondam a ordem das curvas dos experimentos,')
    print('separados por ,. Por exemplo: 0:tranfer-5v , 3:output-40v e assim por diante')
    print('---------------------------------')
    print()
