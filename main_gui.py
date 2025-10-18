"""
--- MODELO GRAVITACIONAL DE VIAGENS (GUI) ---
Ponto de entrada para a Interface Gráfica do Utilizador (GUI).
Inicia a aplicação e expõe a API para a interface web.

Autores: Danilo Ferreira e Samuel Sousa
"""
import webview
import os
import sys
import json
from api import Api

SETTINGS_FILE = 'gui_settings.json'

def load_settings() -> dict:
    """ Carrega as definições da janela a partir de um ficheiro JSON. """
    try:
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def resource_path(relative_path: str) -> str:
    """ Obtém o caminho absoluto para o recurso. """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    settings = load_settings()
    caminho_html = resource_path('gui/index.html')
    api = Api()

    window = webview.create_window(
        'Dashboard Interativo - Modelo Gravitacional',
        caminho_html,
        width=settings.get('width', 1000),
        height=settings.get('height', 700),
        x=settings.get('x'),
        y=settings.get('y'),
        resizable=True,
        min_size=(1000, 700),
        js_api=api,
        fullscreen=settings.get('fullscreen', False)
    )

    # --- ALTERAÇÃO CRÍTICA PARA CORRIGIR O ERRO DE RECURSÃO ---
    api._window = window # Renomeado de api.window para api._window
    # --- FIM DA ALTERAÇÃO ---

    def on_closing():
        """ Guarda a posição, tamanho e estado de tela cheia da janela. """
        if not window.fullscreen: # Só guarda a geometria se não estiver em tela cheia
            window_settings = {
                'width': window.width, 'height': window.height,
                'x': window.x, 'y': window.y,
            }
        else:
            window_settings = settings # Mantém as configurações antigas

        window_settings['fullscreen'] = window.fullscreen

        with open(SETTINGS_FILE, 'w') as f:
            json.dump(window_settings, f)

    window.events.closing += on_closing
    webview.start(debug=False)