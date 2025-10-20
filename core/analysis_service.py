"""
Módulo do Serviço de Análise.
Contém a lógica de negócio para executar cenários do modelo gravitacional
e calcular métricas de desempenho, agora com suporte a resistências dinâmicas.
"""
import numpy as np
from typing import List, Dict, Any
import logging # Adicionado para logging

# Importações dos data models atualizados
from core.data_models import InputData, ScenarioResult, AnalysisReport
# Importação do modelo atualizado
from core.gravitational_model import GravitationalModel


class AnalysisService:
    """
    Orquestra a execução do modelo gravitacional e a análise de cenários.
    Lida com múltiplos fatores de resistência dinâmicos.
    """

    def __init__(self, cenarios_config: List[Dict]):
        """
        Inicializa o serviço com as configurações de cenários.
        Espera que cenarios_config contenha dicionários com 'nome' e 'params' (outro dicionário).
        Ex: {"nome": "Cenario X", "params": {"Tempo": 1.0, "Distancia": 0.5}}
        """
        self.cenarios_config = cenarios_config

    def execute_full_analysis(self, input_data: InputData, furness_config: Dict, config_impedancia: Dict) -> AnalysisReport:
        """
        Executa a análise para uma lista de cenários pré-definidos.

        Args:
            input_data (InputData): Contém zonas, O, D e o dict de resistências.
            furness_config (Dict): Configurações para o algoritmo de Furness.
            config_impedancia (Dict): Configuração da função de impedância.

        Returns:
            AnalysisReport: O relatório completo da análise.
        """
        model = GravitationalModel(
            o=input_data.o, d=input_data.d,
            resistencias=input_data.resistencias # Passa o dicionário de resistências
        )

        lista_de_resultados = []
        for i, cenario_conf in enumerate(self.cenarios_config):
            # Obtém o dicionário de parâmetros do cenário
            params = cenario_conf.get('params', {})

            # Garante que apenas parâmetros correspondentes a resistências existentes sejam usados
            params_validos = {nome: valor for nome, valor in params.items() if nome in input_data.resistencias}
            if len(params_validos) < len(params):
                 nomes_ignorados = set(params.keys()) - set(params_validos.keys())
                 logging.warning(f"Cenário '{cenario_conf.get('nome','N/A')}': Parâmetros ignorados pois as resistências não existem nos dados de entrada: {nomes_ignorados}")


            matriz_viagens, num_iter = model.calcular_matriz_viagens(
                params_validos, # Passa o dicionário de parâmetros válidos
                furness_config,
                config_impedancia
            )

            metricas = self._calculate_all_metrics(matriz_viagens, input_data, num_iter, model)

            # Adiciona a mensagem de balanceamento (se houver) apenas ao primeiro relatório (Base)
            if i == 0 and model.balancing_message:
                metricas['balancing_message'] = model.balancing_message

            resultado_cenario = ScenarioResult(
                nome=cenario_conf.get('nome', f'Cenário {i+1}'),
                parametros=params_validos, # Guarda os parâmetros efetivamente usados
                matriz_viagens=matriz_viagens,
                metricas=metricas
            )
            lista_de_resultados.append(resultado_cenario)

        # Adiciona métricas comparativas após calcular todos os cenários
        self._add_comparison_metrics(lista_de_resultados, input_data.resistencias.keys())
        return AnalysisReport(input_data=input_data, cenarios=lista_de_resultados)

    def execute_interactive_scenario(self, input_data: InputData, params: Dict[str, float], furness_config: Dict, config_impedancia: Dict) -> ScenarioResult:
        """
        Executa um único cenário com parâmetros definidos pelo utilizador.

        Args:
            input_data (InputData): Contém zonas, O, D e o dict de resistências.
            params (Dict[str, float]): Dicionário com os parâmetros (ex: {'Tempo': 1.0}).
            furness_config (Dict): Configurações para o algoritmo de Furness.
            config_impedancia (Dict): Configuração da função de impedância.

        Returns:
            ScenarioResult: O resultado do cenário interativo.
        """
        model = GravitationalModel(
            o=input_data.o, d=input_data.d,
            resistencias=input_data.resistencias
        )

        # Garante que apenas parâmetros correspondentes a resistências existentes sejam usados
        params_validos = {nome: valor for nome, valor in params.items() if nome in input_data.resistencias}

        matriz_viagens, num_iter = model.calcular_matriz_viagens(
            params_validos,
            furness_config,
            config_impedancia
        )

        metricas = self._calculate_all_metrics(matriz_viagens, input_data, num_iter, model)

        # Adiciona mensagem de balanceamento se existir
        if model.balancing_message:
            metricas['balancing_message'] = model.balancing_message

        return ScenarioResult(
            nome="Cenário Interativo",
            parametros=params_validos,
            matriz_viagens=matriz_viagens,
            metricas=metricas
        )

    def calculate_accessibility(self, input_data: InputData, params: Dict[str, float], config_impedancia: Dict) -> List[Dict[str, Any]]:
        """
        Calcula um índice de acessibilidade para cada zona, adaptado para resistências dinâmicas.
        Acessibilidade_i = Somatório_j (Atrações_j * f_inv_ij)
        onde f_inv_ij é o inverso da função de impedância combinada.

        Args:
            input_data (InputData): Contém zonas, O, D e o dict de resistências.
            params (Dict[str, float]): Dicionário com os parâmetros (ex: {'Tempo': 1.0}).
            config_impedancia (Dict): Configuração da função de impedância.

        Returns:
            List[Dict[str, Any]]: Lista de dicionários com 'zona', 'score' e 'score_normalizado'.
        """
        model = GravitationalModel(
            o=input_data.o, d=input_data.d,
            resistencias=input_data.resistencias
        )

        # Garante que apenas parâmetros correspondentes a resistências existentes sejam usados
        params_validos = {nome: valor for nome, valor in params.items() if nome in input_data.resistencias}
        # Assume parâmetros padrão 1.0 para resistências existentes sem parâmetro fornecido? Ou 0.0?
        # Vamos assumir 0.0 por consistência com _calcular_funcao_impedancia_inversa
        params_completos = {nome: params_validos.get(nome, 0.0) for nome in input_data.resistencias}


        # Calcula f_inv usando o método do modelo já adaptado
        f_inv = model._calcular_funcao_impedancia_inversa(params_completos, config_impedancia)

        accessibility_scores = []
        for i in range(input_data.o.size):
            # Acessibilidade = Soma(D[j] * f_inv[i, j]) para todo j
            score = np.sum(model.d * f_inv[i, :])
            accessibility_scores.append({'zona': input_data.zonas[i], 'score': score})

        # Normalização do score
        max_score = max(item['score'] for item in accessibility_scores) if accessibility_scores else 1
        for item in accessibility_scores:
            item['score_normalizado'] = (item['score'] / max_score) * 100 if max_score > 0 else 0

        # Adiciona mensagem de balanceamento se existir (no primeiro item)
        if accessibility_scores and model.balancing_message:
            accessibility_scores[0]['balancing_message'] = model.balancing_message

        # Ordena por score descendente
        return sorted(accessibility_scores, key=lambda x: x['score'], reverse=True)


    def _calculate_all_metrics(self, matriz_viagens: np.ndarray, input_data: InputData, num_iter: int, model: GravitationalModel) -> Dict:
        """
        Agrega o cálculo de todas as métricas para um cenário, incluindo custos dinâmicos.
        """
        erro_o = self._calcular_erro_percentual(model.o, matriz_viagens.sum(axis=1))
        erro_d = self._calcular_erro_percentual(model.d, matriz_viagens.sum(axis=0))

        custos_totais = {}
        # Calcula o custo total para cada resistência dinamicamente
        for nome, matriz_custo in input_data.resistencias.items():
            # Renomeia a chave da métrica para incluir "custo_" para clareza
            chave_metrica = f"custo_{nome}"
            custos_totais[chave_metrica] = self._calcular_custo_total(matriz_viagens, matriz_custo)

        return {
            "iteracoes": num_iter,
            "erro_o_percentual": erro_o,
            "erro_d_percentual": erro_d,
            **custos_totais # Adiciona todos os custos calculados ao dicionário
        }

    def _add_comparison_metrics(self, resultados: List[ScenarioResult], nomes_resistencias: List[str]):
        """
        Calcula a variação percentual dos custos em relação ao cenário base,
        adaptado para nomes de custos dinâmicos.
        """
        if not resultados:
            return

        base_metrics = resultados[0].metricas
        # Identifica dinamicamente as chaves de custo no cenário base com base nos nomes das resistências
        base_costs = {}
        for nome in nomes_resistencias:
            chave_custo = f"custo_{nome}"
            custo = base_metrics.get(chave_custo, 1) # Default 1 para evitar divisão por zero
            base_costs[chave_custo] = custo if custo != 0 else 1 # Garante que não seja 0

        # Adiciona comparação para cada resultado (incluindo o base com 0%)
        for resultado in resultados:
            cost_comparison = {}
            # Compara cada tipo de custo encontrado no cenário base
            for cost_type_full, base_value in base_costs.items():
                current_value = resultado.metricas.get(cost_type_full, 0)
                percentage_change = ((current_value - base_value) / base_value) * 100
                # Usa o nome da resistência (sem "custo_") como chave no resultado final
                cost_name_only = cost_type_full.replace('custo_', '')
                cost_comparison[cost_name_only] = percentage_change

            resultado.metricas['custos_vs_base'] = cost_comparison


    @staticmethod
    def _calcular_erro_percentual(real: np.ndarray, estimado: np.ndarray) -> float:
        """Calcula o Erro Percentual Absoluto Médio (EPAM)."""
        # Evita divisão por zero e resultados inf/nan
        mask = real != 0
        if not np.any(mask):
            return 0.0 # Se o real é todo zero, o erro é zero

        erro_abs_percentual = np.zeros_like(real, dtype=float)
        np.divide(np.abs(real[mask] - estimado[mask]), real[mask], out=erro_abs_percentual[mask], where=mask)

        return np.mean(erro_abs_percentual[mask]) * 100

    @staticmethod
    def _calcular_custo_total(matriz_viagens: np.ndarray, matriz_custo: np.ndarray) -> float:
        """
        Calcula o custo total (ex: tempo, distância) para um cenário,
        ignorando custos infinitos na multiplicação.
        """
        # Cria uma cópia ou usa máscara para não modificar a matriz original
        custo_sem_inf = np.where(np.isinf(matriz_custo), 0, matriz_custo)
        # Garante que as viagens também não sejam NaN
        viagens_validas = np.nan_to_num(matriz_viagens)
        return np.sum(viagens_validas * custo_sem_inf)