# Power BI Usage Monitor

Pipeline de governança e observabilidade para ambientes **Power BI / Microsoft Fabric**. A solução coleta inventário, eventos de acesso e histórico de atualização, preserva dados brutos, mantém uma camada histórica e disponibiliza modelos analíticos para consumo em Power BI.

Este repositório é uma versão pública e sanitizada de um caso de uso real. Todos os dados de demonstração são sintéticos e nenhuma credencial, identificação de tenant, usuário, workspace ou relatório corporativo foi publicada.

## Problema resolvido

A interface administrativa do Power BI mostra apenas parte da história operacional. Para responder perguntas como estas, é necessário construir uma camada histórica própria:

- quais relatórios são realmente utilizados;
- quais usuários e áreas adotaram os produtos de dados;
- quais itens permanecem publicados sem acesso;
- quais modelos semânticos estão falhando ou atrasados;
- quando um relatório foi atualizado pela última vez com sucesso;
- quais dashboards dependem de quais datasets;
- como o uso evolui ao longo do tempo.

O pipeline coleta essas informações diariamente e as transforma em um modelo relacional preparado para análise.

## Arquitetura

```text
Power BI Admin APIs / Activity Events
                  │
                  ▼
       Extração paginada em Python
                  │
          JSON bruto por execução
                  │
                  ▼
      Normalização e enriquecimento
                  │
          ┌───────┴────────┐
          ▼                ▼
   SQLite histórico   PostgreSQL analítico
          │                │
          └───────┬────────┘
                  ▼
       Views e CSVs para Power BI
                  │
                  ▼
 Dashboard de adoção, inventário e saúde
```

## Capacidades

- autenticação service-to-service com Microsoft Entra ID e `MSAL`;
- coleta paginada das APIs administrativas;
- divisão correta de um dia local em janelas UTC para `Activity Events`;
- retentativas com backoff para HTTP 429 e erros transitórios;
- inventário de workspaces, datasets, reports e dashboards;
- ponte entre dashboards, tiles, reports e datasets;
- histórico idempotente de acessos e atualizações;
- persistência local em SQLite;
- sincronização incremental opcional com PostgreSQL usando `ON CONFLICT`;
- views analíticas para adoção, inventário e saúde;
- exportação de CSVs em UTF-8;
- execução offline com dados sintéticos;
- testes automatizados das regras críticas.

## Estrutura

```text
.
├── src/powerbi_usage_monitor/
│   ├── api.py           # autenticação e chamadas ao Power BI
│   ├── config.py        # configuração por variáveis de ambiente
│   ├── pipeline.py      # orquestração das coletas e cargas
│   ├── postgres.py      # sincronização incremental
│   ├── storage.py       # modelo SQLite, normalização e views
│   └── __main__.py      # CLI
├── sample_data/         # dados exclusivamente sintéticos
├── tests/
├── docs/
│   └── dashboard-blueprint.md
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Executar a demonstração local

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
```

No Windows:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
python -m powerbi_usage_monitor demo
```

No Linux ou macOS:

```bash
source .venv/bin/activate
pip install -e '.[dev]'
python -m powerbi_usage_monitor demo
```

A demonstração cria:

```text
output/
├── powerbi_usage_monitor.db
├── raw/
└── csv/
    ├── access_detail.csv
    ├── adoption_daily.csv
    ├── inventory.csv
    ├── refresh_health.csv
    └── item_health.csv
```

## Configurar uma coleta real

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Preencha somente no seu ambiente:

```dotenv
PBI_TENANT_ID=
PBI_CLIENT_ID=
PBI_CLIENT_SECRET=
POSTGRES_URL=postgresql+psycopg2://user:password@localhost:5432/powerbi_monitor
PBI_MONITOR_SCHEMA=powerbi_monitor
PBI_TIMEZONE=America/Sao_Paulo
```

A aplicação registrada no Microsoft Entra ID precisa das permissões administrativas adequadas para as APIs utilizadas. A concessão deve seguir as regras de segurança e governança do tenant.

Executar a coleta do dia anterior:

```bash
python -m powerbi_usage_monitor collect
```

Executar backfill, respeitando a janela disponível pela API:

```bash
python -m powerbi_usage_monitor collect --history-days 28
```

Executar sem PostgreSQL:

```bash
python -m powerbi_usage_monitor collect --no-postgres
```

## PostgreSQL local opcional

```bash
docker compose up -d
```

O `docker-compose.yml` existe apenas para demonstração local. A arquitetura não depende de Docker em produção.

## Modelo de dados

| Objeto | Granularidade |
|---|---|
| `dim_workspace` | um workspace |
| `dim_dataset` | um modelo semântico/dataset |
| `dim_report` | um relatório |
| `dim_dashboard` | um dashboard clássico |
| `bridge_dashboard_dataset` | uma relação tile–dataset/report |
| `fact_access_event` | um evento de visualização |
| `fact_refresh_event` | um evento de atualização observado no log |
| `fact_refresh_snapshot` | um snapshot de saúde por dataset e execução |

## Views analíticas

| View | Finalidade |
|---|---|
| `vw_access_detail` | auditoria de acessos enriquecida com inventário |
| `vw_adoption_daily` | acessos e usuários únicos por item e dia |
| `vw_inventory` | inventário unificado, incluindo itens sem acesso |
| `vw_refresh_health` | última tentativa e último sucesso por dataset |
| `vw_item_health` | saúde de reports e dashboards ligada aos datasets |

## Qualidade e segurança

- credenciais são lidas somente de variáveis de ambiente;
- `.env`, bancos locais, JSONs reais, CSVs e arquivos Power BI são ignorados;
- eventos recebem identificadores determinísticos para evitar duplicidade;
- respostas brutas podem ser preservadas para auditoria e reprocessamento;
- o exemplo usa domínios `.invalid` e identificadores sintéticos;
- nenhum dado do ZIP original foi incorporado ao repositório.

## Limitações

- a retenção de `Activity Events` é limitada pelo serviço; a coleta precisa ser recorrente;
- endpoints administrativos podem exigir configurações específicas do tenant;
- datasets DirectQuery ou Live Connection podem não apresentar histórico tradicional de refresh;
- dashboards clássicos podem depender de múltiplos datasets;
- uma solução de produção deve incluir observabilidade externa, alertas, rotação de logs e gestão segura de segredos.

## Evolução sugerida

- orchestration com Airflow, Prefect ou Azure Data Factory;
- testes de contrato das respostas da API;
- alertas para falhas e itens sem uso;
- camada dbt para transformação no PostgreSQL;
- incremental materializado para grandes tenants;
- dashboard público construído apenas com dados sintéticos.
