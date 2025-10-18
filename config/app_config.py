"""
Módulo de configuração estática para o Modelo Gravitacional.
Centraliza os parâmetros do algoritmo e constantes.
"""

# 1. CONFIGURAÇÕES DO ALGORITMO DE FURNESS
FURNESS_CONFIG = {
    "max_iter": 200,          # Número máximo de iterações
    "tolerancia": 0.0005,     # Critério de parada baseado no erro relativo
}

# 2. CONSTANTES E VALORES PADRÃO
EPSILON = 1e-9 # Pequena constante para evitar divisões por zero.