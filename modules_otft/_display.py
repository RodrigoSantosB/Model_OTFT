
def display_settings(menu, settings, path_voltages, shift_list, list_tension_shift, read_instance=None):
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

    def format_range(range_info):
        if not isinstance(range_info, dict):
            return "-"
        low = range_info.get("min")
        high = range_info.get("max")
        if low is None or high is None:
            return "-"
        return f'[{low:.4g}, {high:.4g}]'

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

    if read_instance is not None and hasattr(read_instance, "get_last_load_data_diagnostics"):
        diagnostics = read_instance.get_last_load_data_diagnostics() or {}
        if diagnostics:
            print('Load diag     : ' + f'{diagnostics.get("read_mode", "-")}')
            print('Shared points : ' + f'{diagnostics.get("shared_points", "-")}')
            print('Orig counts   : ' + f'{diagnostics.get("unique_point_counts", [])}')
            print('VGS range fit : ' + f'{format_range(diagnostics.get("transfer_voltage_range"))}')
            print('VDS range fit : ' + f'{format_range(diagnostics.get("output_voltage_range"))}')
            if diagnostics.get("recommendation"):
                print('Load warning  : ' + f'{diagnostics["recommendation"]}')

    menu.view_path_reads(path_voltages, list_tension_shift)
    print()
    print('A tabela acima mostra todos os arquivos lidos no diretorio. Para filtrar, informe em selected_curves')
    print('os nomes das curvas que deseja MANTER, separados por virgula.')
    print('Exemplo: cnt-1VGS, cnt-3VDS ou qualquer outro nome listado na tabela.')
    print('---------------------------------')
    print()
