"""
--- MODELO GRAVITACIONAL DE VIAGENS (GUI) ---
Ponto de entrada para a Interface Gráfica do Utilizador (GUI).
Inicia a aplicação e expõe a API para a interface web.

Autores: Danilo Ferreira e Samuel Sousa
"""
import webview
import os
import sys
# import json # Não é mais necessário para as configurações da janela
from api import Api

# SETTINGS_FILE = 'gui_settings.json' # Removido

# def load_settings() -> dict: # Removido
#     ...

def resource_path(relative_path: str) -> str:
    """ Obtém o caminho absoluto para o recurso. """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    # settings = load_settings() # Removido
    caminho_html = resource_path('gui/index.html')
    api = Api()

    window = webview.create_window(
        'Dashboard Interativo - Modelo Gravitacional',
        caminho_html,
        width=1000,  # Defina a largura desejada
        height=800, # Defina a altura desejada
        x=None , y=None ,
        resizable=True,
        min_size=(1000, 700),
        js_api=api,
        # fullscreen=False # Removido ou definido como False
    )

    api._window = window

    # def on_closing(): # Removido
    #     ...

    # window.events.closing += on_closing # Removido
    webview.start(debug=False)