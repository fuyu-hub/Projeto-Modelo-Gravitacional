"""
Módulo para carregar dados para o Modelo Gravitacional.
Responsável por ler dados de exemplo, de ficheiros Excel e de configurações de cenário.
"""
import logging
import pandas as pd
import numpy as np
import json
import os
import sys
from typing import Dict, Any, List

from core.data_models import InputData
from services.exceptions import DataLoaderException, FileStructureException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

EXCEL_SHEET_NAMES = {
    "zonas": "Zonas", "origens": "Origens", "destinos": "Destinos",
    "tempo": "Tempo", "distancia": "Distancia", "preco": "Preco",
}

def resource_path(relative_path: str) -> str:
    """ Obtém o caminho absoluto para o recurso, funciona para dev e para PyInstaller. """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def carregar_cenarios(caminho_ficheiro: str = 'cenarios.json') -> List[Dict[str, Any]]:
    """ Carrega os cenários de um ficheiro JSON externo ou usa um conjunto padrão. """
    caminho_final = resource_path(caminho_ficheiro)
    try:
        with open(caminho_final, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning(f"Ficheiro '{caminho_ficheiro}' não encontrado ou inválido. A usar cenários padrão.")
        return [
            {"alpha": 0.0, "beta": 0.0, "gamma": 0.0, "nome": "Caso 1 (Base)"},
            {"alpha": 1.0, "beta": 1.0, "gamma": 1.0, "nome": "Caso 2 (Mesmo peso)"},
            {"alpha": 2.0, "beta": 0.0, "gamma": 0.0, "nome": "Caso 3 (Foco em Tempo)"},
            {"alpha": 0.0, "beta": 2.0, "gamma": 0.0, "nome": "Caso 4 (Foco em Distância)"},
            {"alpha": 0.0, "beta": 0.0, "gamma": 2.0, "nome": "Caso 5 (Foco em Preço)"},
            {"alpha": 2.0, "beta": 2.0, "gamma": 2.0, "nome": "Caso 6 (Sensibilidade Alta)"}
        ]

def get_example_data() -> InputData:
    """ Retorna os dados de exemplo incorporados como uma instância de InputData. """
    logging.info("A usar conjunto de dados de exemplo.")
    return InputData(
        zonas=['Zona 1', 'Zona 2', 'Zona 3', 'Zona 4', 'Zona 5'],
        o=np.array([100, 150, 200, 98, 125]),
        d=np.array([111, 167, 139, 89, 167]),
        tempo=np.array([[1,2,3,2,1],[2,1,1,2,1],[3,2,2,1,3],[1,3,2,2,1],[3,2,1,1,1]], dtype=float),
        distancia=np.array([[10,12,18,7,5],[12,7,9,15,10],[15,8,15,9,7],[10,5,8,8,10],[20,20,10,15,15]], dtype=float),
        preco=np.array([[5,7,10,12,15],[20,15,18,25,10],[12,18,25,30,10],[10,15,20,25,15],[20,20,10,15,15]], dtype=float)
    )

def load_data_from_excel(filepath: str, config: Dict[str, str] = EXCEL_SHEET_NAMES) -> InputData:
    """ Carrega dados de um ficheiro Excel estruturado. """
    try:
        logging.info(f"A ler dados do ficheiro: {filepath}...")
        df_zonas = pd.read_excel(filepath, sheet_name=config["zonas"])
        input_data = InputData(
            zonas=df_zonas['Nome'].tolist(),
            o=pd.read_excel(filepath, sheet_name=config["origens"])['Viagens'].to_numpy(),
            d=pd.read_excel(filepath, sheet_name=config["destinos"])['Viagens'].to_numpy(),
            tempo=pd.read_excel(filepath, sheet_name=config["tempo"], index_col=0).to_numpy(),
            distancia=pd.read_excel(filepath, sheet_name=config["distancia"], index_col=0).to_numpy(),
            preco=pd.read_excel(filepath, sheet_name=config["preco"], index_col=0).to_numpy()
        )
        logging.info("[✔] Dados carregados e estruturados com sucesso!")
        return input_data
    except FileNotFoundError:
        raise DataLoaderException(f"Erro: O ficheiro '{filepath}' não foi encontrado.")
    except (KeyError, ValueError) as e:
        raise FileStructureException(f"Erro na estrutura do ficheiro Excel: {e}. Verifique as planilhas e colunas.")
    except Exception as e:
        raise DataLoaderException(f"Ocorreu um erro inesperado ao ler o ficheiro Excel: {e}")

def export_to_excel(filepath: str, input_data: InputData, config: Dict[str, str] = EXCEL_SHEET_NAMES):
    """ Exporta um objeto InputData para um ficheiro Excel. """
    try:
        with pd.ExcelWriter(filepath) as writer:
            pd.DataFrame({'Nome': input_data.zonas}).to_excel(writer, sheet_name=config["zonas"], index=False)
            pd.DataFrame({'Viagens': input_data.o}).to_excel(writer, sheet_name=config["origens"], index=False)
            pd.DataFrame({'Viagens': input_data.d}).to_excel(writer, sheet_name=config["destinos"], index=False)
            pd.DataFrame(input_data.tempo, index=input_data.zonas, columns=input_data.zonas).to_excel(writer, sheet_name=config["tempo"])
            pd.DataFrame(input_data.distancia, index=input_data.zonas, columns=input_data.zonas).to_excel(writer, sheet_name=config["distancia"])
            pd.DataFrame(input_data.preco, index=input_data.zonas, columns=input_data.zonas).to_excel(writer, sheet_name=config["preco"])
        logging.info(f"Dados exportados com sucesso para: {filepath}")
    except Exception as e:
        raise DataLoaderException(f"Ocorreu um erro ao exportar para Excel: {e}")

def generate_excel_template(filepath: str, num_zonas: int = 5, config: Dict[str, str] = EXCEL_SHEET_NAMES):
    """ Gera um modelo de planilha Excel vazio para preenchimento. """
    zonas = [f'Zona {i+1}' for i in range(num_zonas)]
    template_data = InputData(
        zonas=zonas,
        o=np.zeros(num_zonas),
        d=np.zeros(num_zonas),
        tempo=np.zeros((num_zonas, num_zonas)),
        distancia=np.zeros((num_zonas, num_zonas)),
        preco=np.zeros((num_zonas, num_zonas)),
    )
    export_to_excel(filepath, template_data, config)