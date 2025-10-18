"""
Módulo com a classe Visualization para gerar os gráficos e heatmaps do projeto.
"""
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from typing import List
import numpy as np
import matplotlib as mpl


class Visualization:
    """
    Encapsula a criação de todos os elementos visuais.
    """
    CMAP_SEQUENCIAL = 'viridis'

    def _fig_to_base64(self, fig: plt.Figure) -> str:
        """Converte uma figura matplotlib para uma string base64."""
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"

    def mostrar_heatmap_cenario(self, matriz: np.ndarray, zonas: List[str], alpha: float, beta: float,
                                gamma: float) -> str:
        """Gera o heatmap principal para uma matriz de viagens com uma legenda clara."""
        fig, ax = plt.subplots(figsize=(7.0, 5.0)) # Tamanho ajustado para a legenda

        cbar_kws = {
            'label': 'Número de Viagens',
            'orientation': 'vertical',
            'shrink': 0.9 # Ajusta o tamanho da barra para melhor ajuste
        }

        sns.heatmap(matriz, annot=True, fmt='.0f', cmap=self.CMAP_SEQUENCIAL,
                    xticklabels=zonas, yticklabels=zonas, linewidths=.5, ax=ax,
                    cbar_kws=cbar_kws, annot_kws={"size": 9})

        ax.set_title(f'Matriz de Viagens (α={alpha:.1f}, β={beta:.1f}, γ={gamma:.1f})', fontsize=14, pad=20)
        plt.xlabel('Zonas de Destino', fontsize=11)
        plt.ylabel('Zonas de Origem', fontsize=11)

        # O tight_layout garante que os elementos não se sobreponham
        fig.tight_layout()

        return self._fig_to_base64(fig)

    def gerar_heatmap_impedancia(self, matriz: np.ndarray, zonas: List[str], titulo: str) -> str:
        """Gera um heatmap pequeno para as matrizes de impedância."""
        fig, ax = plt.subplots(figsize=(2.8, 2.3))
        sns.heatmap(matriz, annot=True, fmt='.0f', cmap=self.CMAP_SEQUENCIAL + '_r',
                    xticklabels=zonas, yticklabels=zonas, linewidths=.5, ax=ax,
                    cbar=False, annot_kws={"size": 8})
        ax.set_title(titulo, fontsize=10)
        fig.tight_layout()
        return self._fig_to_base64(fig)

    def gerar_legenda_cores(self) -> str:
        """Cria uma imagem com a legenda de cores dos heatmaps."""
        fig, axes = plt.subplots(2, 1, figsize=(2.8, 2.3))
        fig.suptitle('Legenda de Cores', fontsize=10, weight='bold')

        cb1 = mpl.colorbar.ColorbarBase(axes[0], cmap=mpl.colormaps[self.CMAP_SEQUENCIAL],
                                        norm=mpl.colors.Normalize(vmin=0, vmax=100), orientation='horizontal')
        axes[0].set_title('Matriz de Viagens', fontsize=9)
        cb1.set_ticks([0, 100]);
        cb1.set_ticklabels(['Menor Volume', 'Maior Volume'])

        cb2 = mpl.colorbar.ColorbarBase(axes[1], cmap=mpl.colormaps[self.CMAP_SEQUENCIAL + '_r'],
                                        norm=mpl.colors.Normalize(vmin=0, vmax=100), orientation='horizontal')
        axes[1].set_title('Matrizes de Impedância', fontsize=9)
        cb2.set_ticks([0, 100]);
        cb2.set_ticklabels(['Menor Custo', 'Maior Custo'])

        fig.tight_layout(rect=[0, 0, 1, 0.9])
        return self._fig_to_base64(fig)

    def gerar_mini_heatmap_base(self, matriz: np.ndarray, zonas: List[str], titulo: str) -> str:
        """Gera um heatmap de tamanho médio para a página de resumo."""
        fig, ax = plt.subplots(figsize=(5, 4))
        sns.heatmap(matriz, annot=True, fmt='.0f', cmap=self.CMAP_SEQUENCIAL,
                    xticklabels=zonas, yticklabels=zonas, linewidths=.5, ax=ax,
                    cbar_kws={'label': 'Nº de Viagens'}, annot_kws={"size": 11})
        ax.set_title(titulo, fontsize=12)
        fig.tight_layout()
        return self._fig_to_base64(fig)