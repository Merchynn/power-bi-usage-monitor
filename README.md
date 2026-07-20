# Power BI Usage Monitor

Pipeline público e sanitizado de governança para Power BI. A solução coleta inventário administrativo e eventos de acesso, preserva o histórico em SQLite e pode sincronizar o modelo analítico com PostgreSQL para consumo por outro relatório Power BI.

> Esta versão deriva de uma automação real, mas não contém dados, identificadores, credenciais, banco local, notebook executado ou arquivo Power BI do ambiente original.

## Problema resolvido

A retenção dos eventos administrativos do Power BI é limitada. Sem coleta recorrente, a organização perde a capacidade de analisar historicamente relatórios mais acessados, usuários únicos, adoção por workspace, itens sem uso e evolução do consumo.

## Arquitetura

```text
Power BI Admin APIs / Activity Events
                ↓
       Extração paginada em Python
                ↓
        SQLite operacional/histórico
                ↓
       PostgreSQL analítico opcional
                ↓
        Dashboard de governança
```

## Capacidades publicadas

- autenticação com Microsoft Entra ID e MSAL;
- paginação e retries para APIs administrativas;
- conversão de dias locais para janelas UTC;
- inventário de workspaces, datasets, reports e dashboards;
- ingestão incremental e deduplicação de eventos;
- modelo dimensional em SQLite;
- sincronização PostgreSQL com upsert;
- views de inventário e adoção diária;
- configuração por variáveis de ambiente;
- demonstração com dados sintéticos;
- testes de deduplicação, fuso horário e idempotência.

## Estrutura

```text
.
├── src/powerbi_usage_monitor/
│   ├── api.py
│   ├── config.py
│   ├── pipeline.py
│   ├── postgres.py
│   ├── storage.py
│   └── __main__.py
├── tests/test_core.py
├── .env.example
├── .gitignore
├── pyproject.toml
└── README.md
```

## Demonstração local

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
pip install -e .[dev]
python -m powerbi_usage_monitor demo
```

A demonstração cria `output/powerbi_usage_monitor.db`. Executá-la novamente não duplica os eventos.

## Coleta real

Copie `.env.example` para `.env`, preencha as configurações do Entra ID e, opcionalmente, do PostgreSQL.

```bash
python -m powerbi_usage_monitor collect
python -m powerbi_usage_monitor collect --date 2026-07-19
python -m powerbi_usage_monitor collect --history-days 28
python -m powerbi_usage_monitor collect --no-postgres
```

A aplicação registrada deve possuir as permissões administrativas exigidas pelos endpoints utilizados e estar autorizada nas configurações do tenant.

## Modelo de dados

| Objeto | Granularidade |
|---|---|
| `dim_workspace` | um workspace |
| `dim_dataset` | um modelo semântico |
| `dim_report` | um relatório |
| `dim_dashboard` | um dashboard clássico |
| `fact_access_event` | um evento de acesso |
| `vw_inventory` | inventário unificado |
| `vw_adoption_daily` | acessos e usuários por item e dia |

## Testes

```bash
pytest
```

## Segurança

Eventos administrativos podem conter dados pessoais e metadados internos. Uma implantação real deve aplicar controle de acesso, política de retenção, anonimização quando apropriada e gestão segura de secrets.

O repositório ignora arquivos de ambiente, bancos locais, CSVs, arquivos Power BI, ZIPs e outros artefatos que possam conter dados corporativos.

## Limitações e evolução

A retenção dos Activity Events exige execução recorrente. Mudanças nos endpoints podem exigir manutenção. O monitoramento público de refresh e a bridge entre dashboards, tiles, reports e datasets permanecem como próximas evoluções; essas capacidades existem na solução operacional que originou o case, mas não foram publicadas com dados corporativos.
