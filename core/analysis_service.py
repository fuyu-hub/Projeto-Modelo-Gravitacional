"""
Módulo do Serviço de Análise.
Contém a lógica de negócio para executar cenários do modelo gravitacional
e calcular métricas de desempenho.
"""
import numpy as np
from typing import List, Dict, Any

from core.data_models import InputData, ScenarioResult, AnalysisReport
from core.gravitational_model import GravitationalModel


class AnalysisService:
    """
    Orquestra a execução do modelo gravitacional e a análise de cenários.
    Esta classe não tem conhecimento da interface do utilizador ou de ficheiros.
    Ela apenas recebe dados estruturados e retorna resultados estruturados.
    """

    def __init__(self, cenarios_config: List[Dict]):
        """
        Inicializa o serviço com as configurações necessárias.
        """
        self.cenarios_config = cenarios_config

    def execute_full_analysis(self, input_data: InputData, furness_config: Dict, config_impedancia: Dict) -> AnalysisReport:
        """
        Executa a análise para uma lista de cenários pré-definidos.
        """
        model = GravitationalModel(
            o=input_data.o, d=input_data.d,
            tempo=input_data.tempo, distancia=input_data.distancia, preco=input_data.preco
        )

        lista_de_resultados = []
        for i, cenario_conf in enumerate(self.cenarios_config):
            alpha, beta, gamma = cenario_conf['alpha'], cenario_conf['beta'], cenario_conf['gamma']

            matriz_viagens, num_iter = model.calcular_matriz_viagens(alpha, beta, gamma, furness_config, config_impedancia)

            metricas = self._calculate_all_metrics(matriz_viagens, input_data, num_iter, model)

            # Adiciona a mensagem de balanceamento (se houver) apenas ao primeiro relatório (Base)
            if i == 0 and model.balancing_message:
                metricas['balancing_message'] = model.balancing_message

            resultado_cenario = ScenarioResult(
                nome=cenario_conf['nome'],
                parametros={'alpha': alpha, 'beta': beta, 'gamma': gamma},
                matriz_viagens=matriz_viagens,
                metricas=metricas
            )
            lista_de_resultados.append(resultado_cenario)

        self._add_comparison_metrics(lista_de_resultados)
        return AnalysisReport(input_data=input_data, cenarios=lista_de_resultados)

    def execute_interactive_scenario(self, input_data: InputData, params: Dict[str, float], furness_config: Dict, config_impedancia: Dict) -> ScenarioResult:
        """
        Executa um único cenário com parâmetros definidos pelo utilizador.
        """
        model = GravitationalModel(
            o=input_data.o, d=input_data.d,
            tempo=input_data.tempo, distancia=input_data.distancia, preco=input_data.preco
        )
        alpha, beta, gamma = params['alpha'], params['beta'], params['gamma']

        matriz_viagens, num_iter = model.calcular_matriz_viagens(alpha, beta, gamma, furness_config, config_impedancia)

        metricas = self._calculate_all_metrics(matriz_viagens, input_data, num_iter, model)

        if model.balancing_message:
            metricas['balancing_message'] = model.balancing_message

        return ScenarioResult(
            nome="Cenário Interativo",
            parametros=params,
            matriz_viagens=matriz_viagens,
            metricas=metricas
        )

    def calculate_accessibility(self, input_data: InputData, params: Dict[str, float], config_impedancia: Dict) -> List[Dict[str, Any]]:
        """
        Calcula um índice de acessibilidade para cada zona.
        Acessibilidade_i = Somatório_j (Atrações_j * 1 / f(C_ij))
        """
        model = GravitationalModel(
            o=input_data.o, d=input_data.d,
            tempo=input_data.tempo, distancia=input_data.distancia, preco=input_data.preco
        )

        balancing_message = model.balancing_message

        alpha, beta, gamma = params.get('alpha', 1.0), params.get('beta', 1.0), params.get('gamma', 1.0)

        f_inv = model._calcular_funcao_impedancia_inversa(alpha, beta, gamma, config_impedancia)

        accessibility_scores = []
        for i in range(input_data.o.size):
            score = np.sum(model.d * f_inv[i, :])
            accessibility_scores.append({'zona': input_data.zonas[i], 'score': score})

        max_score = max(item['score'] for item in accessibility_scores) if accessibility_scores else 1
        for item in accessibility_scores:
            item['score_normalizado'] = (item['score'] / max_score) * 100 if max_score > 0 else 0

        if accessibility_scores and balancing_message:
            accessibility_scores[0]['balancing_message'] = balancing_message

        return sorted(accessibility_scores, key=lambda x: x['score'], reverse=True)


    def _calculate_all_metrics(self, matriz_viagens: np.ndarray, input_data: InputData, num_iter: int, model: GravitationalModel) -> Dict:
        """Agrega o cálculo de todas as métricas para um cenário."""
        erro_o = self._calcular_erro_percentual(model.o, matriz_viagens.sum(axis=1))
        erro_d = self._calcular_erro_percentual(model.d, matriz_viagens.sum(axis=0))

        return {
            "iteracoes": num_iter,
            "erro_o_percentual": erro_o,
            "erro_d_percentual": erro_d,
            "custo_tempo": self._calcular_custo_total(matriz_viagens, input_data.tempo),
            "custo_distancia": self._calcular_custo_total(matriz_viagens, input_data.distancia),
            "custo_preco": self._calcular_custo_total(matriz_viagens, input_data.preco),
        }

    def _add_comparison_metrics(self, resultados: List[ScenarioResult]):
        """Calcula a variação percentual dos custos em relação ao cenário base."""
        if not resultados:
            return

        base_metrics = resultados[0].metricas
        base_costs = {
            'custo_tempo': base_metrics.get('custo_tempo', 1),
            'custo_distancia': base_metrics.get('custo_distancia', 1),
            'custo_preco': base_metrics.get('custo_preco', 1),
        }

        for k, v in base_costs.items():
            if v == 0:
                base_costs[k] = 1

        for resultado in resultados:
            if resultado is resultados[0]:
                resultado.metricas['custos_vs_base'] = {'tempo': 0, 'distancia': 0, 'preco': 0}
                continue

            cost_comparison = {}
            for cost_type, base_value in base_costs.items():
                current_value = resultado.metricas.get(cost_type, 0)
                percentage_change = ((current_value - base_value) / base_value) * 100
                cost_comparison[cost_type.replace('custo_', '')] = percentage_change

            resultado.metricas['custos_vs_base'] = cost_comparison

    @staticmethod
    def _calcular_erro_percentual(real: np.ndarray, estimado: np.ndarray) -> float:
        """Calcula o Erro Percentual Absoluto Médio (EPAM)."""
        mask = real != 0
        if not np.any(mask):
            return 0.0
        return np.mean(np.abs((real[mask] - estimado[mask]) / real[mask])) * 100

    @staticmethod
    def _calcular_custo_total(matriz_viagens: np.ndarray, matriz_custo: np.ndarray) -> float:
        """Calcula o custo total (e.g., tempo, distância) para um cenário."""
        custo_sem_inf = np.where(np.isinf(matriz_custo), 0, matriz_custo)
        return np.sum(matriz_viagens * custo_sem_inf)