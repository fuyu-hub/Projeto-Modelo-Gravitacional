"""
Módulo da API que faz a ponte entre a Interface Gráfrica (GUI) e o backend.
Adaptado para suportar múltiplos fatores de resistência dinâmicos.
"""
import webview
import json
import logging
import traceback
import numpy as np
import pandas as pd # Mantido para ExcelWriter, mas não essencial aqui
from typing import Dict, Any # Adicionado Any

# Importações da nossa nova arquitetura
from core.data_models import InputData, AnalysisReport # ScenarioResult não é diretamente usado aqui
from core.analysis_service import AnalysisService
from services import data_loader
from services.exceptions import DataLoaderException
from services.pdf_exporter import ReportGenerator

# Importa as configurações de forma limpa
from config.app_config import FURNESS_CONFIG

class Api:
    """
    Encapsula as funções expostas à GUI. Atua como um controlador que
    direciona os pedidos para os serviços de backend corretos, agora com
    suporte a resistências dinâmicas.
    """

    def __init__(self):
        """
        Inicializa a API, os serviços e o estado interno.
        """
        self._window = None
        self.current_report: AnalysisReport | None = None

        # Carrega cenários no novo formato
        cenarios_config = data_loader.carregar_cenarios()

        self.analysis_service = AnalysisService(cenarios_config)
        self.pdf_exporter = ReportGenerator() # Precisa ser adaptado internamente

    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()

    # --- Funções de Notificação (sem alterações) ---
    def _send_notification(self, message: str, icon: str):
        js_code = f'showNotification({json.dumps(message)}, "{icon}")'
        if self._window:
            self._window.evaluate_js(js_code)

    def _send_error(self, message: str):
        logging.error(message)
        traceback.print_exc()
        self._send_notification(message, "bi-exclamation-triangle-fill text-danger")

    def _send_success(self, message: str):
        self._send_notification(message, "bi-check-circle-fill text-success")

    # --- Gestão de Dados e Exportação ---

    def open_excel_dialog(self):
        file_types = ('Ficheiros Excel (*.xlsx)',)
        result = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=False, file_types=file_types)
        if result:
            filepath = result[0] if isinstance(result, tuple) else result
            self.load_data(filepath)

    def load_data(self, filepath: str | None = None):
        """ Carrega dados do Excel ou exemplo e envia para a GUI no novo formato. """
        try:
            self._send_notification("A carregar dados...", "bi-hourglass-split")
            input_data = data_loader.load_data_from_excel(filepath) if filepath else data_loader.get_example_data()

            # Prepara o payload para o JS
            payload = {
                'zonas': input_data.zonas,
                'dados': {
                    'o': input_data.o.tolist(),
                    'd': input_data.d.tolist(),
                    # Adiciona o dicionário de resistências
                    'resistencias': {nome: matriz.tolist() for nome, matriz in input_data.resistencias.items()}
                }
                # 'resistance_names' não é mais necessário aqui, será derivado das chaves de 'resistencias' no JS
            }
            self._window.evaluate_js(f'populateEditableData({json.dumps(payload)})')
            self._send_success("Dados carregados com sucesso!")
        except DataLoaderException as e:
            self._send_error(str(e))
        except Exception as e:
            self._send_error(f"Ocorreu um erro inesperado ao carregar os dados: {e}")

    def download_excel_template_dialog(self):
        """ Salva um modelo Excel com uma resistência padrão. """
        file_types = ('Ficheiros Excel (*.xlsx)',)
        result = self._window.create_file_dialog(webview.SAVE_DIALOG, file_types=file_types, save_filename='modelo_gravitacional.xlsx')
        if result:
            filepath = result[0] if isinstance(result, tuple) else result
            try:
                # Pode definir um nome padrão para a primeira resistência no template
                data_loader.generate_excel_template(filepath, default_resistance_name="Resistencia1")
                self._send_success(f"Modelo salvo com sucesso em: {filepath}")
            except Exception as e:
                self._send_error(f"Erro ao gerar o modelo: {e}")

    def export_data_to_excel_dialog(self, data_from_gui: dict):
        """ Exporta os dados atuais da UI (com resistências dinâmicas) para Excel. """
        file_types = ('Ficheiros Excel (*.xlsx)',)
        result = self._window.create_file_dialog(webview.SAVE_DIALOG, file_types=file_types, save_filename='dados_exportados.xlsx')
        if result:
            filepath = result[0] if isinstance(result, tuple) else result
            try:
                # A conversão agora lida com o dicionário 'resistencias'
                input_data = self._convert_gui_data_to_input_data(data_from_gui)
                data_loader.export_to_excel(filepath, input_data)
                self._send_success(f"Dados exportados com sucesso para: {filepath}")
            except Exception as e:
                self._send_error(f"Erro ao exportar os dados: {e}")

    # --- Funções de Análise ---

    @staticmethod
    def _convert_gui_data_to_input_data(data_from_gui: dict) -> InputData:
        """ Converte os dados recebidos da GUI (JS) para o formato InputData. """
        try:
            dados_base = data_from_gui['dados']
            resistencias_gui = dados_base.get('resistencias', {})

            # Converte as matrizes de resistência para numpy arrays
            resistencias_np = {
                nome: np.array(matriz, dtype=float)
                for nome, matriz in resistencias_gui.items()
            }

            return InputData(
                zonas=data_from_gui['zonas'],
                o=np.array(dados_base['o'], dtype=float),
                d=np.array(dados_base['d'], dtype=float),
                resistencias=resistencias_np # Passa o dicionário convertido
            )
        except KeyError as e:
            raise ValueError(f"Estrutura de dados da GUI inválida. Chave faltando: {e}")
        except Exception as e:
            raise ValueError(f"Erro ao converter dados da GUI: {e}")


    def _apply_intrazonal_config(self, input_data: InputData, allow_intrazonal: bool):
        """ Modifica as matrizes de resistência com base na configuração intrazonal. """
        if not allow_intrazonal:
            # Modifica cada matriz no dicionário
            for nome in input_data.resistencias:
                # Cria cópia para não alterar o original se for reutilizado
                matriz = input_data.resistencias[nome].copy()
                np.fill_diagonal(matriz, np.inf)
                input_data.resistencias[nome] = matriz
        return input_data

    def run_analysis(self, data_from_gui: dict):
        """ Executa a análise completa com base nos dados e configurações da GUI. """
        try:
            input_data = self._convert_gui_data_to_input_data(data_from_gui)

            config = data_from_gui.get('config', {})
            furness_config = config.get('furness', FURNESS_CONFIG) # Usa default se não vier da GUI
            allow_intrazonal = config.get('allow_intrazonal', True)
            config_impedancia = config.get('impedancia', {"tipo": "potencia"}) # Usa default

            input_data = self._apply_intrazonal_config(input_data, allow_intrazonal)

            # O AnalysisService agora lida com os cenários e parâmetros dinâmicos
            report = self.analysis_service.execute_full_analysis(input_data, furness_config, config_impedancia)
            self.current_report = report # Guarda o relatório para exportação PDF

            # Verifica mensagem de balanceamento no primeiro cenário
            if report.cenarios and 'balancing_message' in report.cenarios[0].metricas:
                self._send_notification(report.cenarios[0].metricas['balancing_message'], "bi-exclamation-triangle-fill text-warning")

            # Formata para a GUI (a função _format_report_for_gui precisa ser adaptada)
            results_for_gui = self._format_report_for_gui(report)
            self._window.evaluate_js(f'displayResults({json.dumps(results_for_gui)})')
        except (ValueError, KeyError) as e:
             # Erros de conversão ou estrutura inválida
            self._window.evaluate_js('toggleSpinner(false)') # Garante desativar spinner
            self._send_error(f"Erro nos dados ou configuração: {e}")
        except Exception as e:
            self._window.evaluate_js('toggleSpinner(false)') # Garante desativar spinner
            self._send_error(f"Ocorreu um erro inesperado na análise: {e}")
            logging.exception("Erro detalhado na análise:") # Log completo no console Python

    def run_interactive_scenario(self, data_from_gui: dict):
        """ Executa um cenário interativo com parâmetros dinâmicos da GUI. """
        try:
            input_data = self._convert_gui_data_to_input_data(data_from_gui)

            config = data_from_gui.get('config', {})
            furness_config = config.get('furness', FURNESS_CONFIG)
            allow_intrazonal = config.get('allow_intrazonal', True)
            config_impedancia = config.get('impedancia', {"tipo": "potencia"})

            input_data = self._apply_intrazonal_config(input_data, allow_intrazonal)

            # 'params' agora é um dicionário vindo da GUI {nome_res: valor_slider, ...}
            params = data_from_gui.get('params', {})

            result_scenario = self.analysis_service.execute_interactive_scenario(
                input_data, params, furness_config, config_impedancia
            )

            # Verifica mensagem de balanceamento
            if 'balancing_message' in result_scenario.metricas:
                self._send_notification(result_scenario.metricas['balancing_message'], "bi-exclamation-triangle-fill text-warning")

            # Formata o resultado para a GUI (adaptado para custos dinâmicos)
            result_for_gui = {
                'matriz_viagens': result_scenario.matriz_viagens.tolist(),
                'num_iter': result_scenario.metricas.get("iteracoes"),
                'metrics': self._format_metrics_for_gui(result_scenario.metricas, list(input_data.resistencias.keys()))
            }
            self._window.evaluate_js(f'displayInteractiveResult({json.dumps(result_for_gui)})')
        except Exception as e:
            self._send_error(f"Erro no cenário interativo: {e}")
            logging.exception("Erro detalhado no cenário interativo:")

    def run_accessibility_analysis(self, data_from_gui: dict):
        """ Executa a análise de acessibilidade com parâmetros dinâmicos. """
        try:
            input_data = self._convert_gui_data_to_input_data(data_from_gui)

            config = data_from_gui.get('config', {})
            allow_intrazonal = config.get('allow_intrazonal', True)
            config_impedancia = config.get('impedancia', {"tipo": "potencia"})
            # Parâmetros vêm do estado atual dos sliders na GUI
            params = data_from_gui.get('params', {})

            input_data = self._apply_intrazonal_config(input_data, allow_intrazonal)

            accessibility_results = self.analysis_service.calculate_accessibility(input_data, params, config_impedancia)

            # Verifica e remove mensagem de balanceamento antes de enviar para JS
            balancing_msg = None
            if accessibility_results and 'balancing_message' in accessibility_results[0]:
                balancing_msg = accessibility_results[0].pop('balancing_message', None) # Remove e guarda

            if balancing_msg:
                 self._send_notification(balancing_msg, "bi-exclamation-triangle-fill text-warning")

            self._window.evaluate_js(f'displayAccessibilityResults({json.dumps(accessibility_results)})')
        except Exception as e:
            self._send_error(f"Ocorreu um erro na análise de acessibilidade: {e}")
            logging.exception("Erro detalhado na análise de acessibilidade:")

    def export_to_pdf_dialog(self):
        """ Exporta o relatório atual (current_report) para PDF. """
        if self.current_report is None:
            self._send_error("Nenhuma análise foi executada. Execute uma análise primeiro.")
            return

        file_types = ('Ficheiro PDF (*.pdf)',)
        result = self._window.create_file_dialog(webview.SAVE_DIALOG, file_types=file_types, save_filename='relatorio_analise.pdf')

        if result:
            try:
                output_path = result[0] if isinstance(result, tuple) else result
                self._send_notification("A gerar o relatório PDF...", "bi-hourglass-split")
                # O pdf_exporter precisa ser adaptado internamente para lidar com
                # os custos e parâmetros dinâmicos no AnalysisReport
                self.pdf_exporter.generate_report(self.current_report, output_path)
                self._send_success(f"Relatório salvo com sucesso em: {output_path}")
            except Exception as e:
                self._send_error(f"Ocorreu um erro ao gerar o PDF: {e}")
                logging.exception("Erro detalhado na geração do PDF:")

    # --- Funções de Formatação ---

    def _format_metrics_for_gui(self, metricas: Dict[str, Any], nomes_resistencias: list) -> Dict[str, str]:
         """Formata as métricas de um cenário para exibição na GUI (interativo)."""
         metrics_gui = {}
         for nome_res in nomes_resistencias:
             chave_custo = f"custo_{nome_res}"
             valor_custo = metricas.get(chave_custo, 0)
             # Formatação básica, pode ser melhorada (ex: unidades?)
             metrics_gui[f"{nome_res} Total"] = f"{valor_custo:,.0f}" # Assumindo valores numéricos grandes

         # Adicionar outras métricas se necessário (ex: iterações, erros)
         # metrics_gui["Iterações"] = str(metricas.get("iteracoes", "N/A"))
         return metrics_gui


    def _format_report_for_gui(self, report: AnalysisReport) -> dict:
        """ Formata o relatório completo (AnalysisReport) para a GUI (JS). """
        summary_data = []
        nomes_resistencias = list(report.input_data.resistencias.keys()) # Pega os nomes das resistências

        for cenario in report.cenarios:
            # Monta a linha do sumário dinamicamente
            row = {'Cenário': cenario.nome}
            # Adiciona os parâmetros usados neste cenário
            for nome_res in nomes_resistencias:
                 row[f'param_{nome_res}'] = cenario.parametros.get(nome_res, 0.0) # Usa 0.0 se não definido
            # Adiciona métricas fixas
            row['Iterações'] = cenario.metricas.get('iteracoes', 'N/A')
            row['Erro O. (%)'] = f"{cenario.metricas.get('erro_o_percentual', 0):.2f}"
            row['Erro D. (%)'] = f"{cenario.metricas.get('erro_d_percentual', 0):.2f}"
            summary_data.append(row)

        detailed_scenarios = []
        for cenario in report.cenarios:
            detailed_scenarios.append({
                'Cenário': cenario.nome,
                'params': cenario.parametros, # Dicionário {nome_res: valor}
                'matriz_viagens': cenario.matriz_viagens.tolist(),
                'metrics': {
                    # Mantém a comparação relativa como dicionário {nome_res: valor_percentual}
                    'custos_vs_base': cenario.metricas.get('custos_vs_base', {}),
                    # Envia os custos brutos como dicionário {custo_NomeRes: valor_numerico}
                    'custos_brutos': {k: v for k, v in cenario.metricas.items() if k.startswith('custo_')}
                }
            })

        # Prepara os dados base para a GUI
        dados_base_gui = {
            'o': report.input_data.o.tolist(),
            'd': report.input_data.d.tolist(),
            'resistencias': {nome: matriz.tolist() for nome, matriz in report.input_data.resistencias.items()}
        }

        return {
            'summary_data': summary_data, # Tabela resumo (adaptar JS para colunas dinâmicas de params)
            'detailed_scenarios': detailed_scenarios, # Detalhes por cenário
            'zonas': report.input_data.zonas,
            'resistance_names': nomes_resistencias, # Lista de nomes das resistências atuais
            'dados_base': dados_base_gui # Dados originais (O, D, matrizes de resistência)
        }