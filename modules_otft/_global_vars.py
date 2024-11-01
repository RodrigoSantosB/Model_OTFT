from ._imports import *
from ._config import *
import json

def read_json_input():
    print(200 * '-')
    json_path = input('Enter the JSON file path, for example: "/content/gdrive/your/path/json": \n\n')
    print(200 * '-')
    
    with open(json_path, 'r') as file:
        inputs = json.load(file)
    return inputs

inputs = read_json_input()

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


