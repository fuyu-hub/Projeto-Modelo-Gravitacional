"""
Módulo contendo a classe GravitationalModel, o núcleo do cálculo
do modelo gravitacional duplamente restringido.
"""
import numpy as np
import logging
from typing import Tuple

# Constantes
SUM_TOLERANCE = 1e-3 # Tolerância para a verificação da soma de origens e destinos

class GravitationalModel:
    """
    Encapsula a lógica do Modelo Gravitational Duplamente Restringido.
    """
    def __init__(self, o: np.ndarray, d: np.ndarray,
                 tempo: np.ndarray, distancia: np.ndarray, preco: np.ndarray):
        """
        Inicializa o modelo com os dados de entrada.
        """
        self.o = np.array(o, dtype=float).flatten()
        self.d = np.array(d, dtype=float).flatten()
        self.tempo = np.array(tempo, dtype=float)
        self.distancia = np.array(distancia, dtype=float)
        self.preco = np.array(preco, dtype=float)
        self.n_zonas = self.o.size

        # Pequena constante para evitar divisões por zero.
        self.EPSILON = 1e-9

        # Armazena a mensagem de balanceamento se for necessário
        self.balancing_message: str | None = None

        self._validar_e_balancear_dados()

    def _validar_e_balancear_dados(self):
        """
        Verifica a consistência dimensional e balança O/D se necessário.
        """
        if not (self.o.size == self.d.size == self.tempo.shape[0] == self.tempo.shape[1]):
            raise ValueError("As dimensões dos vetores e matrizes de entrada são inconsistentes.")

        sum_o = np.sum(self.o)
        sum_d = np.sum(self.d)

        # Verifica se as somas são diferentes (usando tolerância para floats)
        if not np.isclose(sum_o, sum_d, rtol=SUM_TOLERANCE):
            logging.warning(f"A soma de origens ({sum_o}) e destinos ({sum_d}) não é igual. Realizando balanceamento.")

            if sum_d == 0:
                msg = "Erro: A soma dos destinos (D) é zero, mas a soma das origens (O) não é. Impossível balancear."
                logging.error(msg)
                raise ValueError(msg)

            # Escala o vetor D para que sua soma seja igual à soma de O
            scaling_factor = sum_o / sum_d
            self.d = self.d * scaling_factor
            new_sum_d = np.sum(self.d)

            # Armazena a mensagem para a API/Serviço poderem recuperá-la
            self.balancing_message = (
                f"Aviso: Somas de O ({sum_o:,.0f}) e D ({sum_d:,.0f}) não bateram. "
                f"Destinos (D) foram ajustados (fator {scaling_factor:.4f}) "
                f"para um novo total de {new_sum_d:,.0f}."
            )
            logging.info(self.balancing_message)

    def _calcular_funcao_impedancia_inversa(self, alpha: float, beta: float, gamma: float, config_impedancia: dict) -> np.ndarray:
        """
        Calcula a matriz de atratividade (inverso da função de impedância).
        Agora aceita uma configuração para o tipo de função.
        """
        tipo_funcao = config_impedancia.get("tipo", "potencia")

        if tipo_funcao == "exponencial":
            # Para a função exponencial, alpha, beta e gamma são os lambdas (λ)
            impedancia = np.exp(
                (self.tempo * alpha) +
                (self.distancia * beta) +
                (self.preco * gamma)
            )
            with np.errstate(divide='ignore', invalid='ignore'):
                f_inv = 1.0 / impedancia
        else:  # Padrão para "potencia"
            if alpha == 0 and beta == 0 and gamma == 0:
                f_inv = np.ones_like(self.tempo)
                f_inv[np.isinf(self.tempo)] = 0.0
                return f_inv

            with np.errstate(divide='ignore', invalid='ignore'):
                tempo_c = np.where(self.tempo > self.EPSILON, self.tempo, np.inf)
                dist_c = np.where(self.distancia > self.EPSILON, self.distancia, np.inf)
                preco_c = np.where(self.preco > self.EPSILON, self.preco, np.inf)

                f_inv = 1.0 / ((tempo_c ** alpha) * (dist_c ** beta) * (preco_c ** gamma))

        f_inv[~np.isfinite(f_inv)] = 0.0
        return f_inv

    def calcular_matriz_viagens(self, alpha: float, beta: float, gamma: float, config_furness: dict, config_impedancia: dict) -> Tuple[np.ndarray, int]:
        """
        Executa o algoritmo de Furness para estimar a matriz de viagens (Tij).
        AGORA TAMBÉM RECEBE a configuração da função de impedância.
        """
        f_inv = self._calcular_funcao_impedancia_inversa(alpha, beta, gamma, config_impedancia)

        tij = np.zeros((self.n_zonas, self.n_zonas), dtype=float)
        valid_o = self.o > self.EPSILON
        valid_d = self.d > self.EPSILON

        if np.any(valid_o) and np.any(valid_d):
            tij[np.ix_(valid_o, valid_d)] = np.outer(self.o[valid_o], self.d[valid_d]) * f_inv[np.ix_(valid_o, valid_d)]

        max_iter = config_furness.get("max_iter", 200)
        tolerancia = config_furness.get("tolerancia", 0.0005)

        for i in range(1, max_iter + 1):
            soma_linhas = tij.sum(axis=1)
            fatores_linhas = np.where(soma_linhas > self.EPSILON, self.o / soma_linhas, 0.0)
            tij = (tij.T * fatores_linhas).T

            soma_colunas = tij.sum(axis=0)
            fatores_colunas = np.where(soma_colunas > self.EPSILON, self.d / soma_colunas, 0.0)
            tij *= fatores_colunas

            soma_linhas_depois = tij.sum(axis=1)
            mask_o = self.o > self.EPSILON
            if np.any(mask_o):
                erro_max = np.max(np.abs(soma_linhas_depois[mask_o] - self.o[mask_o]) / self.o[mask_o])
                if erro_max < tolerancia:
                    return np.nan_to_num(tij), i

        logging.warning(f"Modelo não convergiu após {max_iter} iterações. Erro atual: {erro_max:.4f}")
        return np.nan_to_num(tij), max_iter