"""
Testes unitários para o GravitationalModel.
Garante que a lógica principal do modelo está a funcionar como esperado.
"""
import numpy as np
import pytest

from core.gravitational_model import GravitationalModel

FURNESS_CONFIG_TEST = {
    "max_iter": 200,
    "tolerancia": 0.0005,
}

@pytest.fixture
def sample_data():
    """
    Cria um conjunto de dados de teste simples e previsível.
    Esta é uma 'fixture' do pytest: uma função que prepara os dados para os testes.
    """
    return {
        'o': np.array([100, 200]),
        'd': np.array([150, 150]),
        'tempo': np.array([[1, 2], [2, 1]]),
        'distancia': np.array([[10, 20], [20, 10]]),
        'preco': np.array([[5, 10], [10, 5]]),
    }

def test_model_initialization(sample_data):
    """
    Testa se o modelo é inicializado corretamente com os dados.
    """
    model = GravitationalModel(**sample_data)
    assert model.n_zonas == 2
    assert np.array_equal(model.o, np.array([100, 200]))
    assert np.array_equal(model.d, np.array([150, 150]))

def test_model_calculation_preserves_totals(sample_data):
    """
    Testa a propriedade mais importante do modelo de fator duplo:
    As somas das linhas e colunas da matriz resultante devem ser iguais
    aos vetores de origem (O) e destino (D) de entrada.
    """
    model = GravitationalModel(**sample_data)
    matriz_viagens, _ = model.calcular_matriz_viagens(1.0, 0.0, 0.0, FURNESS_CONFIG_TEST)

    soma_origens_calculada = matriz_viagens.sum(axis=1)
    assert np.allclose(soma_origens_calculada, sample_data['o'], rtol=1e-3)

    soma_destinos_calculada = matriz_viagens.sum(axis=0)
    assert np.allclose(soma_destinos_calculada, sample_data['d'], rtol=1e-3)

def test_model_with_zero_impedance(sample_data):
    """
    Testa o que acontece se a impedância for zero, o que deve ser tratado
    sem causar erros de divisão por zero.
    """
    sample_data['tempo'] = np.array([[1, 0], [2, 1]])
    model = GravitationalModel(**sample_data)
    matriz_viagens, _ = model.calcular_matriz_viagens(1.0, 0.0, 0.0, FURNESS_CONFIG_TEST)
    assert np.all(np.isfinite(matriz_viagens))

def test_impedance_function_with_zeros(sample_data):
    """Testa se a função de impedância lida corretamente com zeros."""
    model = GravitationalModel(**sample_data)
    f_inv = model._calcular_funcao_impedancia_inversa(1.0, 0.0, 0.0)
    expected = 1 / sample_data['tempo']
    assert np.allclose(f_inv, expected)

def test_impedance_with_alpha_beta_gamma_zero(sample_data):
    """Se todos os expoentes são zero, a função de impedância deve ser 1."""
    model = GravitationalModel(**sample_data)
    f_inv = model._calcular_funcao_impedancia_inversa(0.0, 0.0, 0.0)
    assert np.all(f_inv == 1.0)

def test_inconsistent_dimensions_raises_error():
    """Testa se um ValueError é levantado com dimensões inconsistentes."""
    with pytest.raises(ValueError, match="As dimensões dos vetores e matrizes de entrada são inconsistentes."):
        GravitationalModel(
            o=np.array([100, 200]),
            d=np.array([150, 150, 100]), # Vetor 'd' com dimensão errada
            tempo=np.array([[1, 2], [2, 1]]),
            distancia=np.array([[10, 20], [20, 10]]),
            preco=np.array([[5, 10], [10, 5]]),
        )