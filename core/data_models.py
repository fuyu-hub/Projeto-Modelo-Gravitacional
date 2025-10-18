from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any

@dataclass
class InputData:
    """
    Representa todos os dados de entrada necessários para executar o modelo.
    Isto substitui os dicionários genéricos que eram lidos da GUI.
    """
    zonas: List[str]
    o: np.ndarray
    d: np.ndarray
    tempo: np.ndarray
    distancia: np.ndarray
    preco: np.ndarray

@dataclass
class ScenarioResult:
    """
    Contém todos os resultados de um único cenário de análise.
    """
    nome: str
    parametros: Dict[str, float]
    matriz_viagens: np.ndarray
    metricas: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AnalysisReport:
    """
    É o nosso objeto "fonte da verdade". Contém os dados de entrada
    e uma lista com os resultados de todos os cenários analisados.
    Este objeto será passado para o gerador de PDF e para a API.
    """
    input_data: InputData
    cenarios: List[ScenarioResult]