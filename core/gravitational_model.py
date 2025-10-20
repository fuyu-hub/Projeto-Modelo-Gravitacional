"""
Módulo contendo a classe GravitationalModel, o núcleo do cálculo
do modelo gravitacional duplamente restringido.

Modificado para suportar um número dinâmico de fatores de resistência.
"""
import numpy as np
import logging
from typing import Tuple, Dict

# Constantes
SUM_TOLERANCE = 1e-3 # Tolerância para a verificação da soma de origens e destinos

class GravitationalModel:
    """
    Encapsula a lógica do Modelo Gravitational Duplamente Restringido,
    suportando múltiplos fatores de resistência dinâmicos.
    """
    def __init__(self, o: np.ndarray, d: np.ndarray, resistencias: Dict[str, np.ndarray]):
        """
        Inicializa o modelo com os dados de entrada.

        Args:
            o (np.ndarray): Vetor de Origens (viagens geradas por zona).
            d (np.ndarray): Vetor de Destinos (viagens atraídas por zona).
            resistencias (Dict[str, np.ndarray]): Dicionário onde as chaves são os nomes
                dos fatores de resistência (ex: 'Tempo', 'Distancia') e os valores
                são as matrizes de custo correspondentes (n_zonas x n_zonas).
        """
        self.o = np.array(o, dtype=float).flatten()
        self.d = np.array(d, dtype=float).flatten()
        # Armazena as matrizes de resistência, garantindo que são float
        self.resistencias = {nome: np.array(matriz, dtype=float)
                             for nome, matriz in resistencias.items()}
        self.n_zonas = self.o.size

        # Pequena constante para evitar divisões por zero ou log(0) etc.
        self.EPSILON = 1e-9

        # Armazena a mensagem de balanceamento se for necessário
        self.balancing_message: str | None = None

        self._validar_e_balancear_dados()

    def _validar_e_balancear_dados(self):
        """
        Verifica a consistência dimensional e balança O/D se necessário.
        """
        # Validação inicial de O e D
        if self.o.size != self.d.size:
             raise ValueError("Vetores de Origens (O) e Destinos (D) têm tamanhos diferentes.")
        if self.o.size == 0:
             raise ValueError("Vetores de Origens (O) e Destinos (D) estão vazios.")
        self.n_zonas = self.o.size

        # Validar dimensões de todas as matrizes de resistência
        if not self.resistencias:
            logging.warning("Nenhuma matriz de resistência foi fornecida.")
            # Poderia levantar um erro aqui se uma resistência for obrigatória
            # raise ValueError("Pelo menos um fator de resistência deve ser fornecido.")

        for nome, matriz in self.resistencias.items():
            if not isinstance(matriz, np.ndarray) or matriz.ndim != 2:
                 raise ValueError(f"Resistência '{nome}' não é uma matriz 2D numpy válida.")
            if matriz.shape != (self.n_zonas, self.n_zonas):
                raise ValueError(
                    f"Dimensões da matriz de resistência '{nome}' {matriz.shape} "
                    f"são inconsistentes com o número de zonas ({self.n_zonas})."
                )

        # Verificar e balancear somas O/D
        sum_o = np.sum(self.o)
        sum_d = np.sum(self.d)

        if not np.isclose(sum_o, sum_d, rtol=SUM_TOLERANCE):
            logging.warning(f"Soma de origens ({sum_o}) e destinos ({sum_d}) não é igual. Realizando balanceamento.")

            if sum_d == 0:
                msg = "Erro: Soma dos destinos (D) é zero, mas a soma das origens (O) não é. Impossível balancear."
                logging.error(msg)
                raise ValueError(msg)

            scaling_factor = sum_o / sum_d
            self.d = self.d * scaling_factor
            new_sum_d = np.sum(self.d)

            self.balancing_message = (
                f"Aviso: Somas de O ({sum_o:,.0f}) e D ({sum_d:,.0f}) não bateram. "
                f"Destinos (D) foram ajustados (fator {scaling_factor:.4f}) "
                f"para um novo total de {new_sum_d:,.0f}."
            )
            logging.info(self.balancing_message)

    def _calcular_funcao_impedancia_inversa(self, params: Dict[str, float], config_impedancia: dict) -> np.ndarray:
        """
        Calcula a matriz de atratividade (inverso da função de impedância)
        com base nos parâmetros fornecidos para cada fator de resistência.

        Args:
            params (Dict[str, float]): Dicionário mapeando nomes de resistência
                                       aos seus respectivos expoentes/parâmetros.
                                       Ex: {'Tempo': 1.5, 'Distancia': 0.8}
            config_impedancia (dict): Configuração da função ('tipo': 'potencia' ou 'exponencial').

        Returns:
            np.ndarray: A matriz f_inv (n_zonas x n_zonas).
        """
        tipo_funcao = config_impedancia.get("tipo", "potencia")

        # Inicializa a impedância acumulada
        if tipo_funcao == "exponencial":
            # Para exponencial, acumulamos a soma ponderada dos custos no expoente
            impedancia_acumulada_no_expoente = np.zeros((self.n_zonas, self.n_zonas), dtype=float)
        else: # Potência
            # Para potência, acumulamos o produto das resistências elevadas aos parâmetros
            impedancia_total_produto = np.ones((self.n_zonas, self.n_zonas), dtype=float)

        # Verifica se todos os parâmetros relevantes são zero (caso especial para potência)
        all_params_zero = True
        for nome_resistencia in self.resistencias.keys():
            if params.get(nome_resistencia, 0.0) != 0.0:
                all_params_zero = False
                break

        # Itera sobre cada fator de resistência definido no modelo
        for nome, matriz_custo in self.resistencias.items():
            # Obtém o parâmetro para esta resistência; assume 0.0 se não fornecido
            param = params.get(nome, 0.0)

            if tipo_funcao == "exponencial":
                # Acumula Cij * parametro_j
                # Trata explicitamente valores infinitos no custo como impedância infinita
                custo_valido = np.where(np.isinf(matriz_custo), np.inf, matriz_custo * param)
                # Adiciona ao expoente, garantindo que inf + x = inf
                impedancia_acumulada_no_expoente = np.where(
                    np.isinf(impedancia_acumulada_no_expoente) | np.isinf(custo_valido),
                    np.inf,
                    impedancia_acumulada_no_expoente + custo_valido
                )

            else: # Potência (default)
                if not all_params_zero: # Só calcula se houver algum parâmetro não zero
                    # Tratar Cij = 0 ou Cij = inf antes de elevar à potência
                    # Cij = 0  -> Cij^param = 0 (se param > 0), inf (se param < 0), 1 (se param = 0)
                    # Cij = inf -> Cij^param = inf (se param > 0), 0 (se param < 0), 1 (se param = 0)
                    with np.errstate(divide='ignore', invalid='ignore'): # Ignora 0/0, inf/inf etc.
                        if param == 0:
                            termo_atual = np.ones_like(matriz_custo)
                            # Se o custo original era infinito, o termo deve refletir isso (depende do caso)
                            # Para f_inv = 1 / (prod(Cij^param)), Cij=inf -> f_inv=0
                            # Neste caso, param=0 torna Cij^0 = 1, então não precisamos tratar inf aqui.
                        elif param > 0:
                             matriz_c = np.where(matriz_custo < self.EPSILON, 0.0, matriz_custo) # 0^pos = 0, inf^pos = inf
                             termo_atual = matriz_c ** param
                        else: # param < 0
                             # Evita divisão por zero: 0^neg = inf, inf^neg = 0
                             matriz_c = np.where(matriz_custo < self.EPSILON, np.inf, matriz_custo)
                             termo_atual = matriz_c ** param # inf^neg = 0

                    # Multiplica pelo acumulado
                    # inf * 0 = 0 (consideramos que impedância infinita domina)
                    # inf * x = inf
                    termo_atual_valido = np.nan_to_num(termo_atual, nan=0.0, posinf=np.inf, neginf=0.0) # Trata NaN resultante de 0*inf
                    impedancia_total_produto = np.where(
                        (np.isinf(impedancia_total_produto) & (termo_atual_valido == 0)) | ((impedancia_total_produto == 0) & np.isinf(termo_atual_valido)),
                        0.0, # inf * 0 = 0
                        impedancia_total_produto * termo_atual_valido
                    )


        # Calcula o inverso da impedância final
        with np.errstate(divide='ignore', invalid='ignore'):
            if tipo_funcao == "exponencial":
                impedancia_final = np.exp(impedancia_acumulada_no_expoente)
                f_inv = 1.0 / impedancia_final
            else: # Potência
                if all_params_zero:
                    # Se todos params são 0, impedância total é 1, f_inv é 1
                    f_inv = np.ones_like(impedancia_total_produto)
                     # Mas onde *qualquer* custo original era inf, f_inv deve ser 0
                    for matriz_custo in self.resistencias.values():
                         f_inv[np.isinf(matriz_custo)] = 0.0
                else:
                    impedancia_final = impedancia_total_produto
                    f_inv = 1.0 / impedancia_final

        # Garante que infinitos ou NaNs resultantes sejam tratados como 0 (sem atração)
        f_inv[~np.isfinite(f_inv)] = 0.0
        return f_inv

    def calcular_matriz_viagens(self, params: Dict[str, float], config_furness: dict, config_impedancia: dict) -> Tuple[np.ndarray, int]:
        """
        Executa o algoritmo de Furness para estimar a matriz de viagens (Tij)
        usando os parâmetros e configurações fornecidas.

        Args:
            params (Dict[str, float]): Dicionário de parâmetros para a função de impedância.
            config_furness (dict): Configurações para o algoritmo de Furness ('max_iter', 'tolerancia').
            config_impedancia (dict): Configuração da função de impedância ('tipo').

        Returns:
            Tuple[np.ndarray, int]: A matriz de viagens estimada (Tij) e o número de iterações realizadas.
        """
        # 1. Calcula a matriz de atratividade (inverso da impedância)
        f_inv = self._calcular_funcao_impedancia_inversa(params, config_impedancia)

        # 2. Inicialização do Furness
        # Tij inicial pode ser baseado apenas em O*D*f_inv, mas vamos usar a abordagem iterativa padrão
        tij = f_inv.copy() # Começa com f_inv como base para a estrutura
        a = np.ones(self.n_zonas) # Fatores Ai inicializados em 1
        b = np.ones(self.n_zonas) # Fatores Bj inicializados em 1

        # Tratar casos onde O ou D são zero desde o início
        o_validos = self.o > self.EPSILON
        d_validos = self.d > self.EPSILON
        o_calculavel = self.o.copy()
        d_calculavel = self.d.copy()
        o_calculavel[~o_validos] = self.EPSILON # Evita divisão por zero no cálculo de Ai
        d_calculavel[~d_validos] = self.EPSILON # Evita divisão por zero no cálculo de Bj

        max_iter = config_furness.get("max_iter", 200)
        tolerancia = config_furness.get("tolerancia", 0.0005)
        num_iter = 0

        # 3. Loop Iterativo de Furness
        for i in range(1, max_iter + 1):
            num_iter = i
            # Armazena os fatores da iteração anterior para checar convergência
            a_prev = a.copy()
            b_prev = b.copy()

            # Calcula Ai = 1 / sum_j(Bj * Dj * f_inv_ij)
            den_a = np.sum(b * d_calculavel * f_inv, axis=1)
            a = np.where(den_a > self.EPSILON, 1.0 / den_a, 0.0)
             # Garante que Ai seja 0 se Oi for 0
            a[~o_validos] = 0.0


            # Calcula Bj = 1 / sum_i(Ai * Oi * f_inv_ij)
            den_b = np.sum(a[:, np.newaxis] * o_calculavel[:, np.newaxis] * f_inv, axis=0)
            b = np.where(den_b > self.EPSILON, 1.0 / den_b, 0.0)
            # Garante que Bj seja 0 se Dj for 0
            b[~d_validos] = 0.0

            # Verifica a convergência (comparando fatores a e b ou erro nas somas)
            # Usar erro relativo nas somas é geralmente mais robusto
            tij = a[:, np.newaxis] * self.o[:, np.newaxis] * b * self.d * f_inv
            soma_linhas_atual = tij.sum(axis=1)

            erro_relativo_linhas = np.abs(soma_linhas_atual - self.o) / o_calculavel # Usa o_calculavel para evitar /0
             # Considera erro 0 onde o=0 e soma_linhas=0
            erro_relativo_linhas[~o_validos & (np.abs(soma_linhas_atual) < self.EPSILON)] = 0.0
            erro_max_linhas = np.max(erro_relativo_linhas[o_validos]) if np.any(o_validos) else 0.0

            soma_colunas_atual = tij.sum(axis=0)
            erro_relativo_colunas = np.abs(soma_colunas_atual - self.d) / d_calculavel # Usa d_calculavel
            erro_relativo_colunas[~d_validos & (np.abs(soma_colunas_atual) < self.EPSILON)] = 0.0
            erro_max_colunas = np.max(erro_relativo_colunas[d_validos]) if np.any(d_validos) else 0.0

            erro_max = max(erro_max_linhas, erro_max_colunas)

            if erro_max < tolerancia:
                break # Convergiu

        # 4. Cálculo final de Tij e aviso se não convergiu
        tij = a[:, np.newaxis] * self.o[:, np.newaxis] * b * self.d * f_inv

         # Zera explicitamente linhas/colunas onde O/D originais eram zero
        tij[~o_validos, :] = 0.0
        tij[:, ~d_validos] = 0.0

        if num_iter == max_iter and erro_max >= tolerancia:
            logging.warning(
                f"Modelo não convergiu dentro da tolerância após {max_iter} iterações. "
                f"Erro relativo máximo atual: {erro_max:.6f}"
            )

        return np.nan_to_num(tij), num_iter # Retorna a matriz final e o número de iterações