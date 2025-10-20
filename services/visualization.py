"""
Módulo com a classe Visualization para gerar os gráficos e heatmaps do projeto.
Adaptado para títulos dinâmicos baseados em parâmetros.
"""
import matplotlib

matplotlib.use('Agg') # Usa backend não interativo, essencial para pywebview/servidores
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from typing import List, Dict
import numpy as np
import matplotlib as mpl

# Define um colormap padrão (pode ser configurável se desejado)
DEFAULT_CMAP = 'viridis'

class Visualization:
    """
    Encapsula a criação de todos os elementos visuais,
    adaptado para parâmetros e resistências dinâmicas.
    """

    def _fig_to_base64(self, fig: plt.Figure) -> str:
        """Converte uma figura matplotlib para uma string base64 PNG."""
        buf = BytesIO()
        # Salva com alta resolução e ajusta o bounding box
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig) # Fecha a figura para liberar memória
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"

    def mostrar_heatmap_cenario(self, matriz: np.ndarray, zonas: List[str], params: Dict[str, float]) -> str:
        """
        Gera o heatmap principal para uma matriz de viagens com título dinâmico.

        Args:
            matriz (np.ndarray): A matriz de viagens Tij.
            zonas (List[str]): Lista com os nomes das zonas.
            params (Dict[str, float]): Dicionário com os parâmetros usados (ex: {'Tempo': 1.0}).

        Returns:
            str: Imagem do heatmap em formato base64.
        """
        fig, ax = plt.subplots(figsize=(7.0, 5.0)) # Tamanho ajustado

        cbar_kws = {
            'label': 'Número de Viagens',
            'orientation': 'vertical',
            'shrink': 0.9
        }

        # Formata os parâmetros para o título de forma concisa
        params_str = ", ".join([f"{k}={v:.1f}" for k, v in params.items()])
        if not params_str:
            params_str = "Parâmetros 0" # Caso params seja vazio

        sns.heatmap(matriz, annot=True, fmt='.0f', cmap=DEFAULT_CMAP,
                    xticklabels=zonas, yticklabels=zonas, linewidths=.5, ax=ax,
                    cbar_kws=cbar_kws, annot_kws={"size": 9})

        ax.set_title(f'Matriz de Viagens ({params_str})', fontsize=14, pad=20)
        plt.xlabel('Zonas de Destino', fontsize=11)
        plt.ylabel('Zonas de Origem', fontsize=11)

        fig.tight_layout() # Ajusta layout para evitar sobreposições
        return self._fig_to_base64(fig)

    def gerar_heatmap_impedancia(self, matriz: np.ndarray, zonas: List[str], nome_resistencia: str) -> str:
        """
        Gera um heatmap pequeno para uma matriz de custo/resistência específica.

        Args:
            matriz (np.ndarray): A matriz de custo (ex: tempo, distância).
            zonas (List[str]): Lista com os nomes das zonas.
            nome_resistencia (str): O nome do fator de resistência (usado no título).

        Returns:
            str: Imagem do heatmap em formato base64.
        """
        fig, ax = plt.subplots(figsize=(2.8, 2.3))

        # Usa colormap reverso para impedância (valores menores são "melhores"/mais escuros)
        sns.heatmap(matriz, annot=True, fmt='.1f', cmap=DEFAULT_CMAP + '_r', # '.1f' para ver decimais
                    xticklabels=zonas, yticklabels=zonas, linewidths=.5, ax=ax,
                    cbar=False, annot_kws={"size": 8},
                    # Trata infinitos para exibição
                    mask=np.isinf(matriz))

        ax.set_title(f'Impedância: {nome_resistencia}', fontsize=10)
        fig.tight_layout()
        return self._fig_to_base64(fig)

    def gerar_legenda_cores(self) -> str:
        """Cria uma imagem com a legenda de cores dos heatmaps."""
        fig, axes = plt.subplots(2, 1, figsize=(2.8, 2.3))
        fig.suptitle('Legenda de Cores', fontsize=10, weight='bold')

        # Legenda para Matriz de Viagens (valores maiores são mais intensos)
        cb1 = mpl.colorbar.ColorbarBase(axes[0], cmap=mpl.colormaps[DEFAULT_CMAP],
                                        norm=mpl.colors.Normalize(vmin=0, vmax=100), orientation='horizontal')
        axes[0].set_title('Matriz de Viagens', fontsize=9)
        cb1.set_ticks([0, 100]);
        cb1.set_ticklabels(['Menor Volume', 'Maior Volume'])

        # Legenda para Matrizes de Impedância (valores menores são mais intensos no mapa _r)
        cb2 = mpl.colorbar.ColorbarBase(axes[1], cmap=mpl.colormaps[DEFAULT_CMAP + '_r'],
                                        norm=mpl.colors.Normalize(vmin=0, vmax=100), orientation='horizontal')
        axes[1].set_title('Matrizes de Impedância', fontsize=9)
        cb2.set_ticks([0, 100]);
        cb2.set_ticklabels(['Menor Custo', 'Maior Custo']) # Menor custo terá cor mais escura no heatmap _r

        fig.tight_layout(rect=[0, 0, 1, 0.9]) # Ajusta para o título principal
        return self._fig_to_base64(fig)

    def gerar_mini_heatmap_base(self, matriz: np.ndarray, zonas: List[str], titulo: str) -> str:
        """Gera um heatmap de tamanho médio para a página de resumo."""
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(matriz, annot=True, fmt='.0f', cmap=DEFAULT_CMAP,
                    xticklabels=zonas, yticklabels=zonas, linewidths=.5, ax=ax,
                    cbar_kws={'label': 'Nº de Viagens'}, annot_kws={"size": 10}) # Tamanho da anotação ajustado
        ax.set_title(titulo, fontsize=12)
        fig.tight_layout()
        return self._fig_to_base64(fig)