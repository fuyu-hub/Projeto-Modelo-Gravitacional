"""
Módulo para exceções customizadas da aplicação.
"""

class DataLoaderException(Exception):
    """Exceção base para erros durante o carregamento de dados."""
    pass

class FileStructureException(DataLoaderException):
    """Lançada quando a estrutura do arquivo (ex: planilhas) está incorreta."""
    pass