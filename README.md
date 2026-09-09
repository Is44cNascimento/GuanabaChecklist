# Frontend

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 21.2.19.

## Rodando o projeto com Docker

O projeto inteiro (frontend, backend, dashboard, banco de dados e Nginx) roda via Docker Compose. Siga os passos abaixo a partir da raiz do repositório.

### 1. Pré-requisitos

- Docker e Docker Compose instalados
- Nenhum outro serviço ocupando as portas usadas pelo `docker-compose.yml` (por padrão, a porta `80` do Nginx)

### 2. Build e subida dos containers

```bash
docker compose up -d --build
```

Esse comando builda as imagens do `app` (Angular SSR + Express) e do `dashboard` (Python/Streamlit), e sobe todos os serviços: `checklist-app`, `checklist-dashboard`, `checklist-db` e `checklist-nginx`.

### 3. Verificar se tudo subiu corretamente

```bash
docker compose ps
```

Todos os containers devem aparecer com status `Up`/`running`. Para conferir os logs de um serviço específico:

```bash
docker logs checklist-app --tail=50
docker logs checklist-db --tail=50
```

### 4. Acessar a aplicação

Com o Nginx expondo a porta `80`, abra no navegador:

```
http://localhost/
```

### 5. Parar os containers

```bash
docker compose down
```

Isso remove os containers e a rede, mas preserva o volume `postgres_data` (o banco não é apagado). Para remover também os dados do banco:

```bash
docker compose down -v
```

### 6. Rebuild após alterações no código

Sempre que alterar código do frontend, backend ou dashboard, rode novamente:

```bash
docker compose up -d --build
```

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.

# GuanabaChecklist

## Banco de dados (PostgreSQL)

O projeto usa PostgreSQL 18 via Docker Compose, com o volume `postgres_data` montado em `/var/lib/postgresql/data`.

### Configuração correta no `docker-compose.yml`

```yaml
postgres:
  image: postgres:18.4
  container_name: checklist-db
  environment:
    POSTGRES_DB: checklist
    POSTGRES_USER: Usuario
    POSTGRES_PASSWORD: <sua_senha>
    PGDATA: /var/lib/postgresql/data
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

A variável `PGDATA: /var/lib/postgresql/data` é essencial. A partir da versão 18, a imagem oficial do Postgres passou a esperar um layout de dados versionado (estilo `pg_ctlcluster`, ex.: `/var/lib/postgresql/18/docker`) por padrão. Sem o `PGDATA` explícito apontando para o caminho do volume, o container pode:

- falhar ao reconhecer um cluster já existente montado no volume (erro "these Docker images are configured to store database data in a format which is compatible with pg_ctlcluster..."), ou
- inicializar um cluster novo em um subdiretório diferente do esperado, deixando o banco "vazio" mesmo com dados antigos ainda presentes em outro lugar do volume.

### Problema comum: `directory exists but is not empty`

Se o `docker logs checklist-db` mostrar:

```
initdb: error: directory "/var/lib/postgresql/data" exists but is not empty
```

geralmente significa que uma inicialização anterior (`initdb`) foi interrompida no meio do processo, deixando um cluster parcial/corrompido no volume. Antes de apagar qualquer coisa, vale inspecionar o conteúdo do volume para confirmar se há dados reais em risco:

```bash
docker run --rm -v guanabachecklist_postgres_data:/data alpine sh -c \
  "find /data -maxdepth 4 -exec ls -ld {} \;"
```

Procure por `PG_VERSION` e uma pasta `base/` com subpastas numéricas e arquivos de tamanho relevante (não apenas os bancos de sistema `template0`/`template1`/`postgres`). Se só houver um cluster vazio recém-criado (sem tabelas de dados reais), é seguro recriar o volume do zero:

```bash
docker compose down
docker volume rm guanabachecklist_postgres_data
docker compose up -d
```

Depois confira o log — deve terminar em `database system is ready to accept connections` sem erros de `initdb` repetidos:

```bash
docker logs checklist-db --tail=50
```

### Verificando se o schema foi criado

A tabela `checklist_submissions` é criada automaticamente pelo backend (`ensureDatabase()` em `server.ts`) na primeira requisição recebida em `/api/checklist/start` — não existe migração manual a rodar. Para confirmar que está tudo funcionando:

```bash
docker exec -it checklist-db psql -U Usuario -d checklist -c "\dt"
docker exec -it checklist-db psql -U Usuario -d checklist -c "SELECT * FROM checklist_submissions;"
```
