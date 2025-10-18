"""
Módulo para exportar os resultados da análise para um relatório PDF.
"""
import logging
from datetime import datetime
import numpy as np
from typing import List

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

# Importações da nossa nova arquitetura
from core.data_models import AnalysisReport, ScenarioResult
from services.visualization import Visualization


class ReportGenerator:
    """
    Gera o relatório PDF a partir de um objeto AnalysisReport.
    Esta classe não executa cálculos, apenas renderiza os dados fornecidos.
    """

    def __init__(self):
        """Inicializa o gerador de relatórios e o serviço de visualização."""
        self.visualizer = Visualization()
        self.styles = self._setup_styles()

    def _setup_styles(self) -> dict:
        """Configura e retorna os estilos de parágrafo para o relatório."""
        styles = getSampleStyleSheet()
        cor_principal = colors.HexColor('#003366')
        styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=24,
                                  spaceAfter=20, textColor=cor_principal))
        styles.add(ParagraphStyle(name='CustomHeading1', parent=styles['h1'], fontName='Helvetica-Bold', fontSize=18,
                                  spaceAfter=10, textColor=cor_principal))
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, parent=styles['Normal']))
        styles.add(ParagraphStyle(name='InfoStyle', parent=styles['Normal'], fontSize=9))
        return styles

    def generate_report(self, report_data: AnalysisReport, output_path: str):
        """
        Gera o relatório PDF completo.
        Recebe um objeto AnalysisReport como única fonte de dados.
        """
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), topMargin=0.3 * inch,
                                bottomMargin=0.3 * inch, leftMargin=0.4 * inch, rightMargin=0.4 * inch)

        elementos = []
        elementos.extend(self._build_title_page())
        elementos.extend(self._build_summary_page(report_data))

        # Adiciona uma página detalhada para cada cenário
        img_legenda_str = self.visualizer.gerar_legenda_cores()
        for cenario in report_data.cenarios:
            elementos.extend(self._build_scenario_page(cenario, report_data, img_legenda_str))

        try:
            doc.build(elementos, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
            logging.info(f"[✔] Relatório PDF completo salvo em: {output_path}")
        except Exception as e:
            logging.error(f"Ocorreu um erro ao gerar o PDF: {e}")
            raise

    def _add_page_number(self, canvas, doc):
        """Adiciona o número da página no rodapé de cada página."""
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.setFont('Helvetica', 9)
        canvas.drawRightString(landscape(A4)[0] - 40, 20, text)

    # --- Métodos de Construção de Páginas (Função monolítica quebrada) ---

    def _build_title_page(self) -> list:
        """Constrói os elementos da página de título."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        return [
            Paragraph("MODELO GRAVITACIONAL DE VIAGENS", self.styles['CustomTitle']),
            Paragraph("Análise de Sensibilidade de Cenários", self.styles['CustomHeading1']),
            Spacer(1, 40),
            Paragraph("Autores: Danilo Ferreira e Samuel Sousa", self.styles['Normal']),
            Paragraph("Disciplina: Análise e Planejamento de Sistema de Transportes", self.styles['Normal']),
            Spacer(1, 150),
            Paragraph(f"Relatório Gerado em: {timestamp}", self.styles['Center'])
        ]

    def _build_summary_page(self, report: AnalysisReport) -> list:
        """Constrói os elementos da página de resumo."""
        # Extrai dados de entrada e do cenário base
        input_data = report.input_data
        cenario_base = report.cenarios[0] if report.cenarios else None
        if not cenario_base: return [PageBreak()]

        soma_o = int(np.sum(input_data.o))
        soma_d = int(np.sum(input_data.d))

        # Tabelas de informações da esquerda
        dados_entrada = [['Dados Gerais de Entrada', ''], ['Total de Zonas', f'{len(input_data.zonas)}'],
                         ['Soma de Geração (ΣO)', f'{soma_o}'], ['Soma de Atração (ΣD)', f'{soma_d}']]
        dados_resultados = [['Resultados e Análise de Erro (Base)', ''],
                            ['Total Estimado (ΣTij)', f'{int(np.sum(cenario_base.matriz_viagens))}'],
                            ['Nº de Iterações', f"{cenario_base.metricas.get('iteracoes', 'N/A')}"],
                            ['Erro O. (%)', f"{cenario_base.metricas.get('erro_o_percentual', 0):.2f}"],
                            ['Erro D. (%)', f"{cenario_base.metricas.get('erro_d_percentual', 0):.2f}"]]
        dados_parametros = [['Parâmetros do Cenário Base', ''],
                            ['Sensibilidade ao Tempo (α)', f"{cenario_base.parametros.get('alpha', 0):.1f}"],
                            ['Sensibilidade à Distância (β)', f"{cenario_base.parametros.get('beta', 0):.1f}"],
                            ['Sensibilidade ao Preço (γ)', f"{cenario_base.parametros.get('gamma', 0):.1f}"]]

        tabelas_esquerda = self._create_info_tables([dados_entrada, dados_resultados, dados_parametros])

        # Elementos da coluna da direita
        tabela_resumo_cenarios = self._create_summary_table(report.cenarios)
        heatmap_base_img_str = self.visualizer.gerar_mini_heatmap_base(cenario_base.matriz_viagens, input_data.zonas,
                                                                       'Matriz de Viagens - Cenário Base')
        col_direita_elementos = [Paragraph("<b>Resumo Comparativo de Cenários</b>", self.styles['Center']),
                                 Spacer(1, 8), tabela_resumo_cenarios, Spacer(1, 15),
                                 Image(heatmap_base_img_str, width=4.5 * inch, height=3.6 * inch)]

        # Layout final da página de resumo
        layout_resumo = Table([[tabelas_esquerda, Spacer(40, 0), col_direita_elementos]],
                              colWidths=[5.2 * inch, 0.6 * inch, 5.2 * inch], vAlign='TOP')
        return [PageBreak(), Paragraph("Resumo Geral e Cenário Base", self.styles['CustomHeading1']), layout_resumo]

    def _build_scenario_page(self, cenario: ScenarioResult, report: AnalysisReport, img_legenda_str: str) -> list:
        """Constrói os elementos para a página de detalhes de um cenário."""
        input_data = report.input_data

        # Gera todos os heatmaps necessários para a página
        img_heatmap_principal_str = self.visualizer.mostrar_heatmap_cenario(cenario.matriz_viagens, input_data.zonas,
                                                                            cenario.parametros['alpha'],
                                                                            cenario.parametros['beta'],
                                                                            cenario.parametros['gamma'])
        img_tempo_str = self.visualizer.gerar_heatmap_impedancia(input_data.tempo, input_data.zonas,
                                                                 'Impedância: Tempo (h)')
        img_dist_str = self.visualizer.gerar_heatmap_impedancia(input_data.distancia, input_data.zonas,
                                                                'Impedância: Distância (Km)')
        img_preco_str = self.visualizer.gerar_heatmap_impedancia(input_data.preco, input_data.zonas,
                                                                 'Impedância: Preço (R$)')

        # Tabela de informações do cenário (métricas)
        info_data = [
            [Paragraph(f"<b>Iterações:</b> {cenario.metricas.get('iteracoes', 'N/A')}", self.styles['InfoStyle']),
             Paragraph(f"<b>Total Estimado:</b> {int(np.sum(cenario.matriz_viagens))}", self.styles['InfoStyle'])],
            [Paragraph(f"<b>Erro Origem:</b> {cenario.metricas.get('erro_o_percentual', 0):.2f}%",
                       self.styles['InfoStyle']),
             Paragraph(f"<b>Erro Destino:</b> {cenario.metricas.get('erro_d_percentual', 0):.2f}%",
                       self.styles['InfoStyle'])]
        ]
        info_table = Table(info_data, colWidths=[2.5 * inch, 2.5 * inch]);
        info_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))

        # Grid com os heatmaps de impedância e a legenda
        grid_heatmaps_menores = Table(
            [[Image(img_tempo_str, width=2.5 * inch, height=2.1 * inch),
              Image(img_dist_str, width=2.5 * inch, height=2.1 * inch)],
             [Image(img_preco_str, width=2.5 * inch, height=2.1 * inch),
              Image(img_legenda_str, width=2.5 * inch, height=2.1 * inch)]]
        )
        coluna_direita = [info_table, Spacer(1, 15), grid_heatmaps_menores]

        # Layout final da página do cenário
        layout_final = Table(
            [[Image(img_heatmap_principal_str, width=5.8 * inch, height=4.8 * inch), coluna_direita]],
            colWidths=[6.0 * inch, 5.4 * inch], vAlign='TOP'
        )
        return [PageBreak(), Paragraph(f"Análise Detalhada - {cenario.nome}", self.styles['CustomHeading1']),
                layout_final]

    # --- Métodos Auxiliares de Criação de Tabelas ---

    def _create_info_tables(self, datasets: List[list]) -> list:
        """Cria as tabelas de informação da coluna esquerda da página de resumo."""
        elementos = []
        for dados in datasets:
            tabela = Table(dados, colWidths=[2.8 * inch, 2.2 * inch], hAlign='LEFT')
            tabela.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'), ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('SPAN', (0, 0), (1, 0)), ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (0, 0), 12),
                ('TEXTCOLOR', (0, 0), (0, 0), self.styles['CustomHeading1'].textColor),
                ('BOTTOMPADDING', (0, 0), (0, 0), 12), ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'), ('LINEABOVE', (0, 1), (-1, 1), 1, colors.black),
                ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
            ]))
            elementos.extend([tabela, Spacer(1, 20)])
        return elementos

    def _create_summary_table(self, cenarios: List[ScenarioResult]) -> Table:
        """Cria a tabela de resumo comparativo dos cenários."""
        header = ['Cenário', 'α', 'β', 'γ', 'Iterações', 'Erro O. (%)', 'Erro D. (%)']
        data = [header]
        for c in cenarios:
            data.append([
                c.nome, f"{c.parametros['alpha']:.1f}", f"{c.parametros['beta']:.1f}", f"{c.parametros['gamma']:.1f}",
                c.metricas['iteracoes'], f"{c.metricas['erro_o_percentual']:.2f}",
                f"{c.metricas['erro_d_percentual']:.2f}"
            ])

        tabela = Table(data, hAlign='CENTER',
                       colWidths=[1.3 * inch, 0.4 * inch, 0.4 * inch, 0.4 * inch, 0.7 * inch, 0.8 * inch, 0.8 * inch])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.styles['CustomHeading1'].textColor),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8), ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F4F4F4')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.darkgrey)
        ]))
        return tabela