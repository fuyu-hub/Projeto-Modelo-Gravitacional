"""
Módulo da API que faz a ponte entre a Interface Gráfrica (GUI) e o backend.
Esta classe não contém lógica de negócio; ela apenas orquestra as chamadas
para os serviços apropriados e formata os dados para a comunicação.
"""
import webview
import json
import logging
import traceback
import numpy as np
import pandas as pd

# Importações da nossa nova arquitetura
from core.data_models import InputData, AnalysisReport
from core.analysis_service import AnalysisService
from services import data_loader
from services.exceptions import DataLoaderException
from services.pdf_exporter import ReportGenerator

# Importa as configurações de forma limpa
from config.app_config import FURNESS_CONFIG  # Manter para usar como default


class Api:
    """
    Encapsula as funções expostas à GUI. Atua como um controlador que
    direciona os pedidos para os serviços de backend corretos.
    """

    def __init__(self):
        """
        Inicializa a API, os serviços e o estado interno.
        """
        self._window = None
        self.current_report: AnalysisReport | None = None

        cenarios_config = data_loader.carregar_cenarios()

        # O furness_config é removido da inicialização, será passado em cada chamada
        self.analysis_service = AnalysisService(cenarios_config)
        self.pdf_exporter = ReportGenerator()

    def toggle_fullscreen(self):
        """
        Ativa ou desativa o modo de tela cheia da janela principal.
        """
        if self._window:
            self._window.toggle_fullscreen()

    # --- Funções de Notificação ---

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
        try:
            self._send_notification("A carregar dados...", "bi-hourglass-split")
            input_data = data_loader.load_data_from_excel(filepath) if filepath else data_loader.get_example_data()
            payload = {
                'zonas': input_data.zonas,
                'dados': {
                    'o': input_data.o.tolist(), 'd': input_data.d.tolist(),
                    'tempo': input_data.tempo.tolist(), 'distancia': input_data.distancia.tolist(),
                    'preco': input_data.preco.tolist()
                },
                'resistance_names': {'tempo': 'Tempo', 'distancia': 'Distância', 'preco': 'Preço'}
            }
            self._window.evaluate_js(f'populateEditableData({json.dumps(payload)})')
            self._send_success("Dados carregados com sucesso!")
        except DataLoaderException as e:
            self._send_error(str(e))
        except Exception as e:
            self._send_error(f"Ocorreu um erro inesperado ao carregar os dados: {e}")

    def download_excel_template_dialog(self):
        """ Pede ao utilizador um local para salvar o modelo de planilha Excel. """
        file_types = ('Ficheiros Excel (*.xlsx)',)
        result = self._window.create_file_dialog(webview.SAVE_DIALOG, file_types=file_types, save_filename='modelo_gravitacional.xlsx')
        if result:
            filepath = result[0] if isinstance(result, tuple) else result
            try:
                data_loader.generate_excel_template(filepath)
                self._send_success(f"Modelo salvo com sucesso em: {filepath}")
            except Exception as e:
                self._send_error(f"Erro ao gerar o modelo: {e}")

    def export_data_to_excel_dialog(self, data_from_gui: dict):
        """ Pede ao utilizador um local para salvar os dados atuais da UI em Excel. """
        file_types = ('Ficheiros Excel (*.xlsx)',)
        result = self._window.create_file_dialog(webview.SAVE_DIALOG, file_types=file_types, save_filename='dados_exportados.xlsx')
        if result:
            filepath = result[0] if isinstance(result, tuple) else result
            try:
                input_data = self._convert_gui_data_to_input_data(data_from_gui)
                data_loader.export_to_excel(filepath, input_data)
                self._send_success(f"Dados exportados com sucesso para: {filepath}")
            except Exception as e:
                self._send_error(f"Erro ao exportar os dados: {e}")

    # --- Funções de Análise ---

    @staticmethod
    def _convert_gui_data_to_input_data(data_from_gui: dict) -> InputData:
        dados_base = {k: np.array(v, dtype=float) for k, v in data_from_gui['dados'].items()}
        return InputData(
            zonas=data_from_gui['zonas'], o=dados_base['o'], d=dados_base['d'],
            tempo=dados_base['tempo'], distancia=dados_base['distancia'], preco=dados_base['preco']
        )

    def _apply_intrazonal_config(self, input_data: InputData, allow_intrazonal: bool):
        """
        Modifica os dados de entrada com base na configuração intrazonal.
        """
        if not allow_intrazonal:
            input_data.tempo = input_data.tempo.copy()
            input_data.distancia = input_data.distancia.copy()
            input_data.preco = input_data.preco.copy()

            np.fill_diagonal(input_data.tempo, np.inf)
            np.fill_diagonal(input_data.distancia, np.inf)
            np.fill_diagonal(input_data.preco, np.inf)
        return input_data

    def run_analysis(self, data_from_gui: dict):
        try:
            input_data = self._convert_gui_data_to_input_data(data_from_gui)

            config = data_from_gui.get('config', {})
            furness_config = config.get('furness', FURNESS_CONFIG)
            allow_intrazonal = config.get('allow_intrazonal', True)
            config_impedancia = config.get('impedancia', {"tipo": "potencia"})

            input_data = self._apply_intrazonal_config(input_data, allow_intrazonal)

            report = self.analysis_service.execute_full_analysis(input_data, furness_config, config_impedancia)

            self.current_report = report

            if report.cenarios and 'balancing_message' in report.cenarios[0].metricas:
                self._send_notification(report.cenarios[0].metricas['balancing_message'], "bi-exclamation-triangle-fill text-warning")

            results_for_gui = self._format_report_for_gui(report)
            self._window.evaluate_js(f'displayResults({json.dumps(results_for_gui)})')
        except (ValueError, KeyError) as e:
            self._send_error(f"Erro nos dados de entrada: {e}")
        except Exception as e:
            self._window.evaluate_js('toggleSpinner(false)')
            self._send_error(f"Ocorreu um erro inesperado na análise: {e}")

    def run_interactive_scenario(self, data_from_gui: dict):
        try:
            input_data = self._convert_gui_data_to_input_data(data_from_gui)

            config = data_from_gui.get('config', {})
            furness_config = config.get('furness', FURNESS_CONFIG)
            allow_intrazonal = config.get('allow_intrazonal', True)
            config_impedancia = config.get('impedancia', {"tipo": "potencia"})

            input_data = self._apply_intrazonal_config(input_data, allow_intrazonal)

            params = data_from_gui.get('params', {'alpha': 1.0, 'beta': 1.0, 'gamma': 1.0})

            result_scenario = self.analysis_service.execute_interactive_scenario(input_data, params, furness_config, config_impedancia)

            if 'balancing_message' in result_scenario.metricas:
                self._send_notification(result_scenario.metricas['balancing_message'], "bi-exclamation-triangle-fill text-warning")

            result_for_gui = {
                'matriz_viagens': result_scenario.matriz_viagens.tolist(),
                'num_iter': result_scenario.metricas.get("iteracoes"),
                'metrics': {
                    'Tempo Total': f"{result_scenario.metricas.get('custo_tempo', 0):,.0f} h",
                    'Distância Total': f"{result_scenario.metricas.get('custo_distancia', 0):,.0f} km",
                    'Preço Total': f"R$ {result_scenario.metricas.get('custo_preco', 0):,.2f}"
                }
            }
            self._window.evaluate_js(f'displayInteractiveResult({json.dumps(result_for_gui)})')
        except Exception as e:
            self._send_error(f"Erro no cenário interativo: {e}")

    def run_accessibility_analysis(self, data_from_gui: dict):
        """Executa a análise de acessibilidade e envia para a UI."""
        try:
            input_data = self._convert_gui_data_to_input_data(data_from_gui)

            config = data_from_gui.get('config', {})
            allow_intrazonal = config.get('allow_intrazonal', True)
            config_impedancia = config.get('impedancia', {"tipo": "potencia"})
            params = data_from_gui.get('params', {'alpha': 1.0, 'beta': 1.0, 'gamma': 1.0})

            input_data = self._apply_intrazonal_config(input_data, allow_intrazonal)

            accessibility_results = self.analysis_service.calculate_accessibility(input_data, params, config_impedancia)

            if accessibility_results and 'balancing_message' in accessibility_results[0]:
                self._send_notification(accessibility_results[0]['balancing_message'], "bi-exclamation-triangle-fill text-warning")
                del accessibility_results[0]['balancing_message']

            self._window.evaluate_js(f'displayAccessibilityResults({json.dumps(accessibility_results)})')
        except Exception as e:
            self._send_error(f"Ocorreu um erro na análise de acessibilidade: {e}")

    def export_to_pdf_dialog(self):
        if self.current_report is None:
            self._send_error("Nenhuma análise foi executada. Execute uma análise primeiro.")
            return

        file_types = ('Ficheiro PDF (*.pdf)',)
        result = self._window.create_file_dialog(webview.SAVE_DIALOG, file_types=file_types, save_filename='relatorio_analise.pdf')

        if result:
            try:
                output_path = result[0] if isinstance(result, tuple) else result
                self._send_notification("A gerar o relatório PDF...", "bi-hourglass-split")
                self.pdf_exporter.generate_report(self.current_report, output_path)
                self._send_success(f"Relatório salvo com sucesso em: {output_path}")
            except Exception as e:
                self._send_error(f"Ocorreu um erro ao gerar o PDF: {e}")

    # --- Funções de Formatação ---

    def _format_report_for_gui(self, report: AnalysisReport) -> dict:
        """ Formata o relatório completo como um dicionário JSON para a GUI. """
        summary_data = []
        for cenario in report.cenarios:
            summary_data.append({
                'Cenário': cenario.nome,
                'alpha': cenario.parametros['alpha'],
                'beta': cenario.parametros['beta'],
                'gamma': cenario.parametros['gamma'],
                'Iterações': cenario.metricas['iteracoes'],
                'Erro O. (%)': f"{cenario.metricas.get('erro_o_percentual', 0):.2f}",
                'Erro D. (%)': f"{cenario.metricas.get('erro_d_percentual', 0):.2f}",
            })

        detailed_scenarios = []
        for cenario in report.cenarios:
            detailed_scenarios.append({
                'Cenário': cenario.nome,
                'params': cenario.parametros,
                'matriz_viagens': cenario.matriz_viagens.tolist(),
                'metrics': {
                    'custos_vs_base': cenario.metricas.get('custos_vs_base', {}),
                    # MODIFICAÇÃO: Enviar custos como números brutos
                    'custo_tempo': cenario.metricas.get('custo_tempo', 0),
                    'custo_distancia': cenario.metricas.get('custo_distancia', 0),
                    'custo_preco': cenario.metricas.get('custo_preco', 0)
                }
            })

        return {
            'summary_data': summary_data,
            'detailed_scenarios': detailed_scenarios,
            'zonas': report.input_data.zonas,
            'resistance_names': {'tempo': 'Tempo', 'distancia': 'Distância', 'preco': 'Preço'},
            'dados_base': {
                'o': report.input_data.o.tolist(),
                'd': report.input_data.d.tolist(),
                'tempo': report.input_data.tempo.tolist(),
                'distancia': report.input_data.distancia.tolist(),
                'preco': report.input_data.preco.tolist(),
            }
        }