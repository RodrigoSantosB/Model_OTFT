from ._imports import *
from ._config import *
import json

def read_json_input(name_file):
    with open(name_file, 'r') as file:
        inputs = json.load(file)
    return inputs

# Retorna as variáveis usadas no código principal de forma global


inputs = read_json_input(PATH_JASON)

print('\n\n')

# Itera sobre cada bloco de dados no JSON
for block in inputs:
    # Itera sobre cada chave-valor no bloco de dados
    for key, value in block.items():
        # Atribui o valor à variável correspondente
        globals()[key] = value
      


def show_varibles():
    for block in inputs:
    # Itera sobre cada chave-valor no bloco de dados
        for key, value in block.items():
            # Atribui o valor à variável correspondente
            globals()[key] = value
            print('|' + ' ' + f'{key}: {value}')
            print('--' * 100)


