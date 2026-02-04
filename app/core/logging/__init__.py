"""
Pacote do sistema de logging de requisições HTTP.

Este pacote implementa um sistema completo de logging que captura:
- Dados de requisições HTTP (método, path, headers)
- Dados de respostas (status, body)
- Métricas de performance (tempo de execução)
- Informações de erros e exceções

Componentes:
- logger: Serviço de logging
- middleware: Middleware para captura automática
- request: Modelos de dados de log
"""

