"""
Módulo para exportar os resultados da análise para um relatório PDF.
Adaptado para resistências e parâmetros dinâmicos.
"""
import logging
from datetime import datetime
import numpy as np
from typing import List, Dict, Tuple # Adicionado Dict, Tuple
from core.gravitational_model import GravitationalModel

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_RIGHT # Adicionado TA_RIGHT

# Importações da nossa nova arquitetura (já devem estar corretas)
from core.data_models import AnalysisReport, ScenarioResult
from services.visualization import Visualization # Usa a Visualization atualizada

class ReportGenerator:
    """
    Gera o relatório PDF a partir de um objeto AnalysisReport,
    adaptado para resistências e parâmetros dinâmicos.
    """

    def __init__(self):
        """Inicializa o gerador de relatórios e o serviço de visualização."""
        self.visualizer = Visualization()
        self.styles = self._setup_styles()

    def _setup_styles(self) -> dict:
        """Configura e retorna os estilos de parágrafo para o relatório."""
        styles = getSampleStyleSheet()
        cor_principal = colors.HexColor('#003366') # Azul escuro
        styles.add(ParagraphStyle(name='CustomTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=24,
                                  spaceAfter=20, textColor=cor_principal))
        styles.add(ParagraphStyle(name='CustomHeading1', parent=styles['h1'], fontName='Helvetica-Bold', fontSize=18,
                                  spaceAfter=10, textColor=cor_principal))
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, parent=styles['Normal']))
        styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, parent=styles['Normal']))
        styles.add(ParagraphStyle(name='InfoStyle', parent=styles['Normal'], fontSize=9))
        styles.add(ParagraphStyle(name='SmallBold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold'))
        styles.add(ParagraphStyle(name='SmallNormal', parent=styles['Normal'], fontSize=8))
        return styles

    def generate_report(self, report_data: AnalysisReport, output_path: str):
        """
        Gera o relatório PDF completo a partir do AnalysisReport.
        """
        doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), topMargin=0.3 * inch,
                                bottomMargin=0.3 * inch, leftMargin=0.4 * inch, rightMargin=0.4 * inch)

        elementos = []
        elementos.extend(self._build_title_page())
        elementos.extend(self._build_summary_page(report_data))

        # Adiciona uma página detalhada para cada cenário
        img_legenda_str = self.visualizer.gerar_legenda_cores()

        # Obtém os nomes das resistências dos dados de entrada
        nomes_resistencias = list(report_data.input_data.resistencias.keys())

        for cenario in report_data.cenarios:
            elementos.extend(self._build_scenario_page(cenario, report_data, img_legenda_str, nomes_resistencias))

        try:
            doc.build(elementos, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
            logging.info(f"[✔] Relatório PDF completo salvo em: {output_path}")
        except Exception as e:
            logging.error(f"Ocorreu um erro ao gerar o PDF: {e}")
            raise # Re-levanta a exceção para a API tratar

    def _add_page_number(self, canvas, doc):
        """Adiciona o número da página no rodapé."""
        page_num = canvas.getPageNumber()
        text = f"Página {page_num}"
        canvas.setFont('Helvetica', 9)
        # Ajusta posição para landscape
        canvas.drawRightString(landscape(A4)[0] - 0.5*inch, 0.3*inch, text)

    # --- Métodos de Construção de Páginas ---

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
            Paragraph(f"Relatório Gerado em: {timestamp}", self.styles['Center']),
            PageBreak() # Adiciona quebra de página após o título
        ]

    def _build_summary_page(self, report: AnalysisReport) -> list:
        """Constrói os elementos da página de resumo (adaptado)."""
        input_data = report.input_data
        if not report.cenarios: return [PageBreak()] # Se não houver cenários, pula
        cenario_base = report.cenarios[0]

        soma_o = int(np.sum(input_data.o))
        soma_d_original = int(np.sum(input_data.d)) # Soma D original pode ser útil
        soma_d_balanceada = int(np.sum(model.d for model in [GravitationalModel(input_data.o, input_data.d, input_data.resistencias)])) # Recalcula soma D balanceada

        # Tabela de Dados Gerais
        dados_entrada = [
            [Paragraph('<b>Dados Gerais de Entrada</b>', self.styles['CustomHeading1'])],
            [Paragraph(f'Total de Zonas: {len(input_data.zonas)}', self.styles['InfoStyle'])],
            [Paragraph(f'Soma de Geração (ΣO): {soma_o:,}', self.styles['InfoStyle'])],
            [Paragraph(f'Soma de Atração (ΣD Original): {soma_d_original:,}', self.styles['InfoStyle'])],
        ]
        if not np.isclose(soma_o, soma_d_original):
             dados_entrada.append([Paragraph(f'Soma de Atração (ΣD Balanceada): {soma_d_balanceada:,}', self.styles['InfoStyle'])])
        tabela_entrada = Table(dados_entrada, colWidths=[5.0 * inch])
        tabela_entrada.setStyle(TableStyle([('BOTTOMPADDING', (0, 0), (0, 0), 12)]))


        # Tabela de Resultados do Cenário Base
        linhas_resultados_base = [
            [Paragraph('<b>Resultados do Cenário Base</b>', self.styles['CustomHeading1'])],
            [Paragraph(f"Nome: {cenario_base.nome}", self.styles['InfoStyle'])],
            [Paragraph(f"Total Estimado (ΣTij): {int(np.sum(cenario_base.matriz_viagens)):,}", self.styles['InfoStyle'])],
            [Paragraph(f"Nº de Iterações: {cenario_base.metricas.get('iteracoes', 'N/A')}", self.styles['InfoStyle'])],
            [Paragraph(f"Erro O (%): {cenario_base.metricas.get('erro_o_percentual', 0):.2f}", self.styles['InfoStyle'])],
            [Paragraph(f"Erro D (%): {cenario_base.metricas.get('erro_d_percentual', 0):.2f}", self.styles['InfoStyle'])],
            [Paragraph("Parâmetros:", self.styles['SmallBold'])]
        ]
        # Adiciona parâmetros dinamicamente
        for nome_param, valor_param in cenario_base.parametros.items():
            linhas_resultados_base.append([Paragraph(f"   • {nome_param}: {valor_param:.2f}", self.styles['InfoStyle'])])
        tabela_resultados_base = Table(linhas_resultados_base, colWidths=[5.0 * inch])
        tabela_resultados_base.setStyle(TableStyle([('BOTTOMPADDING', (0, 0), (0, 0), 12)]))


        # Elementos da coluna da esquerda
        col_esquerda_elementos = [tabela_entrada, Spacer(1, 20), tabela_resultados_base]


        # Elementos da coluna da direita
        tabela_resumo_cenarios = self._create_summary_table(report.cenarios)
        heatmap_base_img_str = self.visualizer.gerar_mini_heatmap_base(
            cenario_base.matriz_viagens, input_data.zonas,
            f'Matriz de Viagens - {cenario_base.nome}' # Usa nome do cenário no título
        )
        col_direita_elementos = [
            Paragraph("<b>Resumo Comparativo de Cenários</b>", self.styles['Center']),
            Spacer(1, 8),
            tabela_resumo_cenarios,
            Spacer(1, 15),
            Image(heatmap_base_img_str, width=4.5 * inch, height=3.6 * inch)
        ]

        # Layout final da página de resumo
        layout_resumo = Table([[col_esquerda_elementos, Spacer(40, 0), col_direita_elementos]],
                              colWidths=[5.2 * inch, 0.6 * inch, 5.2 * inch], vAlign='TOP')
        layout_resumo.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')])) # Garante alinhamento vertical

        return [Paragraph("Resumo Geral e Cenário Base", self.styles['CustomHeading1']), layout_resumo, PageBreak()]


    def _build_scenario_page(self, cenario: ScenarioResult, report: AnalysisReport, img_legenda_str: str, nomes_resistencias: List[str]) -> list:
        """Constrói os elementos para a página de detalhes de um cenário (adaptado)."""
        input_data = report.input_data

        # Gera heatmap principal com parâmetros dinâmicos no título
        img_heatmap_principal_str = self.visualizer.mostrar_heatmap_cenario(
            cenario.matriz_viagens, input_data.zonas, cenario.parametros
        )

        # Gera heatmaps de impedância dinamicamente (máximo de 3 para caber no grid)
        heatmaps_impedancia = []
        for i, nome_res in enumerate(nomes_resistencias):
            if i >= 3: # Limita a 3 heatmaps de impedância no PDF por layout
                logging.warning(f"Relatório PDF: Mais de 3 resistências. Exibindo apenas as 3 primeiras: {nomes_resistencias[:3]}")
                break
            if nome_res in input_data.resistencias:
                img_str = self.visualizer.gerar_heatmap_impedancia(
                    input_data.resistencias[nome_res], input_data.zonas, nome_res
                )
                heatmaps_impedancia.append(Image(img_str, width=2.5 * inch, height=2.1 * inch))
            else:
                 heatmaps_impedancia.append(Spacer(2.5*inch, 2.1*inch)) # Espaço vazio se não encontrar

        # Preenche com espaços vazios se houver menos de 3 resistências
        while len(heatmaps_impedancia) < 3:
             heatmaps_impedancia.append(Spacer(2.5*inch, 2.1*inch))

        # Tabela de informações do cenário (métricas)
        info_data = [
            [Paragraph(f"<b>Iterações:</b> {cenario.metricas.get('iteracoes', 'N/A')}", self.styles['InfoStyle']),
             Paragraph(f"<b>Total Estimado:</b> {int(np.sum(cenario.matriz_viagens)):,}", self.styles['InfoStyle'])],
            [Paragraph(f"<b>Erro Origem:</b> {cenario.metricas.get('erro_o_percentual', 0):.2f}%", self.styles['InfoStyle']),
             Paragraph(f"<b>Erro Destino:</b> {cenario.metricas.get('erro_d_percentual', 0):.2f}%", self.styles['InfoStyle'])]
        ]
        # Adiciona custos totais dinamicamente
        for nome_res in nomes_resistencias:
             chave_custo = f"custo_{nome_res}"
             custo_valor = cenario.metricas.get(chave_custo, 0)
             # Formatação básica, pode precisar de ajuste dependendo da unidade
             custo_formatado = f"{custo_valor:,.1f}" if custo_valor > 100 else f"{custo_valor:,.2f}"
             info_data.append([Paragraph(f"<b>Custo {nome_res}:</b> {custo_formatado}", self.styles['InfoStyle']), '']) # Adiciona em uma coluna
        info_data = [row[:2] for row in info_data] # Garante que só temos 2 colunas

        info_table = Table(info_data, colWidths=[2.5 * inch, 2.5 * inch]);
        info_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('SPAN', (-1,-len(nomes_resistencias)), (-1,-1))])) # Span na segunda coluna para os custos


        # Grid com os heatmaps de impedância e a legenda
        grid_heatmaps_menores = Table(
            [
                [heatmaps_impedancia[0], heatmaps_impedancia[1]],
                [heatmaps_impedancia[2], Image(img_legenda_str, width=2.5 * inch, height=2.1 * inch)]
            ],
            colWidths=[2.7 * inch, 2.7 * inch],
            rowHeights=[2.2 * inch, 2.2 * inch]
        )

        coluna_direita = [info_table, Spacer(1, 15), grid_heatmaps_menores]

        # Layout final da página do cenário
        layout_final = Table(
            [[Image(img_heatmap_principal_str, width=5.8 * inch, height=4.8 * inch), Spacer(20,0), coluna_direita]],
            colWidths=[6.0 * inch, 0.3 * inch, 5.4 * inch], vAlign='TOP'
        )
        layout_final.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))

        return [Paragraph(f"Análise Detalhada - {cenario.nome}", self.styles['CustomHeading1']),
                layout_final, PageBreak()]

    # --- Métodos Auxiliares de Criação de Tabelas ---

    # _create_info_tables foi removido pois a informação foi incorporada diretamente
    # nas tabelas da página de resumo para maior clareza.

    def _create_summary_table(self, cenarios: List[ScenarioResult]) -> Table:
        """Cria a tabela de resumo comparativo dos cenários (adaptado)."""
        if not cenarios: return Table([[]]) # Retorna tabela vazia se não houver cenários

        # Identifica todos os nomes de parâmetros usados em todos os cenários
        todos_nomes_params = sorted(list(set(p for c in cenarios for p in c.parametros.keys())))

        # Cabeçalho dinâmico
        header = [Paragraph('Cenário', style=self.styles['SmallBold'])]
        header.extend([Paragraph(nome_p, style=self.styles['SmallBold']) for nome_p in todos_nomes_params])
        header.extend([Paragraph('Iterações', style=self.styles['SmallBold']),
                       Paragraph('Erro O (%)', style=self.styles['SmallBold']),
                       Paragraph('Erro D (%)', style=self.styles['SmallBold'])])
        data = [header]

        # Preenche os dados da tabela
        for c in cenarios:
            row = [Paragraph(c.nome, style=self.styles['SmallNormal'])]
            # Adiciona valores dos parâmetros (ou 'N/A')
            for nome_p in todos_nomes_params:
                valor = c.parametros.get(nome_p, None)
                row.append(Paragraph(f"{valor:.1f}" if valor is not None else '-', style=self.styles['SmallNormal']))
            # Adiciona métricas
            row.append(Paragraph(str(c.metricas.get('iteracoes', '-')), style=self.styles['SmallNormal']))
            row.append(Paragraph(f"{c.metricas.get('erro_o_percentual', 0):.2f}", style=self.styles['SmallNormal']))
            row.append(Paragraph(f"{c.metricas.get('erro_d_percentual', 0):.2f}", style=self.styles['SmallNormal']))
            data.append(row)

        # Ajusta larguras das colunas (pode precisar de ajuste manual fino)
        num_params = len(todos_nomes_params)
        col_width_params = 0.4 * inch # Largura para cada coluna de parâmetro
        total_width_params = col_width_params * num_params
        # Larguras restantes distribuídas
        width_cenario = 1.5 * inch
        width_iter = 0.6 * inch
        width_erro = 0.7 * inch
        total_width_fixo = width_cenario + width_iter + 2 * width_erro
        # Garante que não exceda o limite da página (aprox 11 inch landscape - margens)
        max_total_width = 10.5 * inch
        total_calculated_width = total_width_fixo + total_width_params

        if total_calculated_width > max_total_width:
             # Reduz proporcionalmente se exceder
             scale_factor = max_total_width / total_calculated_width
             width_cenario *= scale_factor
             col_width_params *= scale_factor
             width_iter *= scale_factor
             width_erro *= scale_factor
             total_width_params = col_width_params * num_params # Recalcula

        colWidths = [width_cenario] + [col_width_params] * num_params + [width_iter, width_erro, width_erro]

        tabela = Table(data, hAlign='CENTER', colWidths=colWidths)
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.styles['CustomHeading1'].textColor),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), # Estilo já aplicado no Paragraph
            # ('FONTSIZE', (0, 0), (-1, 0), 8), # Estilo já aplicado no Paragraph
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            # ('FONTSIZE', (0, 1), (-1, -1), 7.5), # Estilo já aplicado no Paragraph
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F4F4F4')),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.darkgrey)
        ]))
        return tabela