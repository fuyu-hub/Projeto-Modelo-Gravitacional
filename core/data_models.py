from dataclasses import dataclass, field
import numpy as np
from typing import List, Dict, Any

@dataclass
class InputData:
    zonas: List[str]
    o: np.ndarray
    d: np.ndarray
    resistencias: Dict[str, np.ndarray]

@dataclass
class ScenarioResult:
    nome: str
    parametros: Dict[str, float] # Ex: {'Tempo': 1.0, 'Distancia': 0.5}
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