"""
Pacote de protocolos de domínio.

Este pacote define interfaces (protocolos) utilizando typing.Protocol
para estabelecer contratos que devem ser implementados por serviços
e repositórios.

Vantagens dos Protocols:
- Desacoplamento: Permite trocar implementações facilmente
- Testabilidade: Facilita criação de mocks
- Type hints: Fornece verificação de tipos em tempo de desenvolvimento

Protocolos disponíveis:
- ExampleIntegration: Contrato para integrações externas
- logging: Contrato para serviços de logging
- pubsub: Contrato para operações Pub/Sub
"""

