# Blueprint do dashboard

O modelo gerado pelo pipeline foi pensado para um relatório de governança com cinco páginas.

## 1. Visão executiva

- itens publicados;
- itens acessados no período;
- usuários únicos;
- acessos totais;
- datasets com última tentativa em falha;
- percentual do inventário sem uso observado.

## 2. Adoção

Fonte principal: `vw_adoption_daily`.

- evolução diária de acessos e usuários;
- ranking de reports e dashboards;
- adoção por workspace;
- frequência de uso por usuário;
- novos usuários no período.

## 3. Inventário

Fonte principal: `vw_inventory`.

- reports e dashboards existentes;
- item com ou sem acesso;
- último acesso observado;
- quantidade de usuários;
- itens candidatos a revisão ou despublicação.

## 4. Saúde de atualização

Fontes: `vw_refresh_health` e `vw_item_health`.

- última tentativa;
- último sucesso;
- falhas atuais;
- erro mais recente;
- agenda habilitada;
- reports e dashboards afetados por um dataset com falha.

## 5. Auditoria

Fonte principal: `vw_access_detail`.

- usuário;
- horário UTC e data local;
- workspace;
- item;
- tipo de atividade.

Dados de auditoria podem conter informações pessoais. O acesso ao relatório e ao banco deve respeitar a política de privacidade e segurança da organização.
