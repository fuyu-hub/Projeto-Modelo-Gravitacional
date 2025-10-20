"""
Módulo para carregar dados para o Modelo Gravitacional.
Responsável por ler dados de exemplo, de ficheiros Excel e de configurações de cenário.
Adaptado para suportar múltiplos fatores de resistência dinâmicos.
"""
import logging
import pandas as pd
import numpy as np
import json
import os
import sys
from typing import Dict, Any, List, Tuple

# Importa o InputData atualizado
from core.data_models import InputData
from services.exceptions import DataLoaderException, FileStructureException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Nomes padrão para as planilhas essenciais
STANDARD_SHEET_NAMES = {
    "zonas": "Zonas",
    "origens": "Origens",
    "destinos": "Destinos",
}

# Nomes que NÃO devem ser interpretados como matrizes de resistência
RESERVED_SHEET_NAMES = list(STANDARD_SHEET_NAMES.values())


def resource_path(relative_path: str) -> str:
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller. """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def carregar_cenarios(caminho_ficheiro: str = 'cenarios.json') -> List[Dict[str, Any]]:
    """
    Carrega os cenários de um ficheiro JSON externo ou usa um conjunto padrão.
    Adaptado para o novo formato com 'params' como um dicionário.
    """
    caminho_final = resource_path(caminho_ficheiro)
    try:
        with open(caminho_final, 'r', encoding='utf-8') as f:
            cenarios = json.load(f)
            # Validação básica do formato esperado
            if not isinstance(cenarios, list) or not all('nome' in c and 'params' in c and isinstance(c['params'], dict) for c in cenarios):
                 raise ValueError("Formato inválido para cenarios.json. Espera lista de {'nome': str, 'params': dict}")
            logging.info(f"Cenários carregados de '{caminho_ficheiro}'.")
            return cenarios
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
        logging.warning(f"Ficheiro '{caminho_ficheiro}' não encontrado ou inválido ({e}). A usar cenários padrão.")
        # Retorna cenários padrão no novo formato
        return [
            {"nome": "Caso 1 (Base - Params 0)", "params": {"Resistencia1": 0.0}},
            {"nome": "Caso 2 (Params 1)", "params": {"Resistencia1": 1.0}},
            # Adicione mais cenários padrão conforme necessário, lembrando que
            # os nomes das resistências aqui ("Resistencia1") podem não corresponder
            # aos nomes que o usuário terá nos dados carregados. O AnalysisService
            # irá lidar com isso, usando apenas os parâmetros relevantes.
        ]


def get_example_data() -> InputData:
    """ Retorna os dados de exemplo incorporados como uma instância de InputData (adaptado). """
    logging.info("A usar conjunto de dados de exemplo.")
    zonas_exemplo = ['Zona 1', 'Zona 2', 'Zona 3', 'Zona 4', 'Zona 5']
    n = len(zonas_exemplo)
    return InputData(
        zonas=zonas_exemplo,
        o=np.array([100, 150, 200, 98, 125]),
        d=np.array([111, 167, 139, 89, 167]),
        # As resistências agora são um dicionário
        resistencias={
            'Tempo': np.array([[1,2,3,2,1],[2,1,1,2,1],[3,2,2,1,3],[1,3,2,2,1],[3,2,1,1,1]], dtype=float),
            'Distancia': np.array([[10,12,18,7,5],[12,7,9,15,10],[15,8,15,9,7],[10,5,8,8,10],[20,20,10,15,15]], dtype=float),
            'Preco': np.array([[5,7,10,12,15],[20,15,18,25,10],[12,18,25,30,10],[10,15,20,25,15],[20,20,10,15,15]], dtype=float)
        }
    )

def load_data_from_excel(filepath: str) -> InputData:
    """
    Carrega dados de um ficheiro Excel estruturado, identificando dinamicamente
    as planilhas de resistência.
    """
    try:
        logging.info(f"A ler dados do ficheiro: {filepath}...")
        excel_file = pd.ExcelFile(filepath)
        sheet_names = excel_file.sheet_names

        # --- Carregar Dados Padrão ---
        # Verifica se as planilhas padrão existem
        for key, name in STANDARD_SHEET_NAMES.items():
            if name not in sheet_names:
                raise FileStructureException(f"Planilha padrão '{name}' não encontrada no ficheiro Excel.")

        df_zonas = pd.read_excel(excel_file, sheet_name=STANDARD_SHEET_NAMES["zonas"])
        zonas = df_zonas['Nome'].tolist()
        num_zonas = len(zonas)

        o_data = pd.read_excel(excel_file, sheet_name=STANDARD_SHEET_NAMES["origens"])['Viagens'].to_numpy()
        d_data = pd.read_excel(excel_file, sheet_name=STANDARD_SHEET_NAMES["destinos"])['Viagens'].to_numpy()

        if len(o_data) != num_zonas or len(d_data) != num_zonas:
             raise FileStructureException(f"Número de Origens/Destinos ({len(o_data)}/{len(d_data)}) "
                                          f"inconsistente com o número de Zonas ({num_zonas}).")

        # --- Carregar Resistências Dinamicamente ---
        resistencias_data: Dict[str, np.ndarray] = {}
        resistance_sheet_names = [name for name in sheet_names if name not in RESERVED_SHEET_NAMES]

        if not resistance_sheet_names:
            logging.warning("Nenhuma planilha de resistência encontrada no ficheiro Excel.")
            # Você pode decidir lançar um erro aqui se pelo menos uma for necessária:
            # raise FileStructureException("Nenhuma planilha de resistência encontrada. Pelo menos uma é necessária.")

        for sheet_name in resistance_sheet_names:
            try:
                # Assume que a primeira coluna é o índice (nomes das zonas)
                df_resistencia = pd.read_excel(excel_file, sheet_name=sheet_name, index_col=0)
                # Validação básica de forma e nomes de índice/coluna
                if df_resistencia.shape != (num_zonas, num_zonas):
                    raise FileStructureException(
                        f"Planilha de resistência '{sheet_name}' tem formato {df_resistencia.shape}, "
                        f"esperado ({num_zonas}, {num_zonas})."
                    )
                if not all(idx in zonas for idx in df_resistencia.index) or \
                   not all(col in zonas for col in df_resistencia.columns):
                     logging.warning(f"Nomes de índice/coluna na planilha '{sheet_name}' "
                                     f"não correspondem exatamente aos nomes em '{STANDARD_SHEET_NAMES['zonas']}'. "
                                     f"Usando a ordem como está.")
                     # Poderia adicionar lógica mais estrita aqui se necessário

                resistencias_data[sheet_name] = df_resistencia.to_numpy(dtype=float)
                logging.info(f"  [+] Carregada resistência '{sheet_name}'.")
            except Exception as e:
                # Captura erros ao ler planilhas específicas de resistência
                 raise FileStructureException(f"Erro ao ler planilha de resistência '{sheet_name}': {e}")

        input_data = InputData(
            zonas=zonas,
            o=o_data,
            d=d_data,
            resistencias=resistencias_data
        )
        logging.info("[✔] Dados carregados e estruturados com sucesso!")
        return input_data

    except FileNotFoundError:
        raise DataLoaderException(f"Erro: O ficheiro '{filepath}' não foi encontrado.")
    except (KeyError, ValueError, FileStructureException) as e:
        # Re-levanta FileStructureException ou trata KeyError/ValueError como tal
        raise FileStructureException(f"Erro na estrutura do ficheiro Excel: {e}. Verifique as planilhas e colunas.")
    except Exception as e:
        # Erro genérico
        raise DataLoaderException(f"Ocorreu um erro inesperado ao ler o ficheiro Excel: {e}")


def export_to_excel(filepath: str, input_data: InputData):
    """
    Exporta um objeto InputData (com resistências dinâmicas) para um ficheiro Excel.
    """
    try:
        with pd.ExcelWriter(filepath) as writer:
            # Escreve as planilhas padrão
            pd.DataFrame({'Nome': input_data.zonas}).to_excel(writer, sheet_name=STANDARD_SHEET_NAMES["zonas"], index=False)
            pd.DataFrame({'Viagens': input_data.o}).to_excel(writer, sheet_name=STANDARD_SHEET_NAMES["origens"], index=False)
            pd.DataFrame({'Viagens': input_data.d}).to_excel(writer, sheet_name=STANDARD_SHEET_NAMES["destinos"], index=False)

            # Escreve cada planilha de resistência
            for nome_resistencia, matriz_resistencia in input_data.resistencias.items():
                # Usa os nomes das zonas como índice e colunas para melhor legibilidade
                pd.DataFrame(
                    matriz_resistencia,
                    index=input_data.zonas,
                    columns=input_data.zonas
                ).to_excel(writer, sheet_name=nome_resistencia)
                logging.info(f"  [+] Exportada resistência '{nome_resistencia}'.")

        logging.info(f"Dados exportados com sucesso para: {filepath}")
    except Exception as e:
        raise DataLoaderException(f"Ocorreu um erro ao exportar para Excel: {e}")

def generate_excel_template(filepath: str, num_zonas: int = 5, default_resistance_name: str = "Resistencia1"):
    """
    Gera um modelo de planilha Excel vazio (com resistências dinâmicas) para preenchimento.
    Cria uma planilha de resistência padrão.
    """
    zonas = [f'Zona {i+1}' for i in range(num_zonas)]
    # Cria dados vazios/zero
    template_data = InputData(
        zonas=zonas,
        o=np.zeros(num_zonas),
        d=np.zeros(num_zonas),
        resistencias={
            default_resistance_name: np.zeros((num_zonas, num_zonas))
        }
    )
    # Reutiliza a função de exportação
    export_to_excel(filepath, template_data)
    logging.info(f"Modelo Excel gerado com sucesso em: {filepath}")