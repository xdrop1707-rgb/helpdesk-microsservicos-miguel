# HelpDesk TI - Microsserviços

**Aluno:** Miguel
**Link do vídeo:** [COLE O LINK DO YOUTUBE/DRIVE AQUI]

## Arquitetura

O sistema foi dividido em 3 microsserviços independentes, cada um com seu próprio banco de dados, e um API Gateway para centralizar as requisições.

```mermaid
flowchart TB
    Tela[Tela do HelpDesk] --> Gateway[API Gateway :8000]
    Gateway --> SU[Serviço de Usuários :8001]
    Gateway --> SI[Serviço de Inventário :8002]
    Gateway --> SC[Serviço de Chamados :8003]
    SC -->|HTTP| SU
    SC -->|HTTP| SI
    SU --> BU[(Banco de usuários)]
    SI --> BI[(Banco de inventário)]
    SC --> BC[(Banco de chamados)]