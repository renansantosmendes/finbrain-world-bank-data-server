# FinBrain World Bank Data Server

API HTTP sem estado sobre os dados abertos do **Banco Mundial**, construída com a
biblioteca [`wbdata`](https://github.com/OliverSherouse/wbdata) e FastAPI. Cada
requisição é respondida pela API do Banco Mundial no momento da chamada. O
servidor **não usa cache** e não grava nada em disco, o que permite rodar como
função serverless na Vercel.

A documentação completa, em inglês, fica no Swagger: `/docs` (ou `/redoc`).

## Rotas

| Método | Rota | O que faz |
|---|---|---|
| GET | `/health` | Verificação de vida do processo (não consulta o Banco Mundial) |
| GET | `/version` | Versão do servidor e do `wbdata` |
| GET | `/sources` | Fontes de dados (WDI, Doing Business, ...) |
| GET | `/sources/{source_id}` | Uma fonte pelo id |
| GET | `/topics` | Tópicos temáticos |
| GET | `/topics/{topic_id}` | Um tópico pelo id |
| GET | `/countries` | Países e agregados, com filtros `country_id`, `query`, `incomelevel`, `lendingtype` |
| GET | `/countries/{country_id}` | Um país ou agregado pelo código ISO3 |
| GET | `/income-levels` | Grupos de renda |
| GET | `/lending-types` | Tipos de empréstimo (IBRD, IDA, blend) |
| GET | `/indicators` | Busca de indicadores por código, nome, fonte ou tópico |
| GET | `/indicators/{code}` | Metadados de um indicador |
| GET | `/data/{code}` | Observações de um indicador (lista de registros) |
| GET | `/series/{code}` | Série temporal de um indicador para um país (`date`/`value`) |
| POST | `/data/table` | Vários indicadores em uma tabela (um registro por período) |

## Erros

Todas as respostas de erro têm o mesmo corpo, `{"code": "...", "message": "..."}`:

| Status | Código | Quando |
|---|---|---|
| 400 | `invalid_request` | Parâmetro inválido (frequência, período sem início, filtro recusado pela API) |
| 404 | `not_found` | Nada corresponde à requisição, ou o id/código não existe, ou não há dados para a frequência pedida |
| 502 | `upstream_unavailable` | A API do Banco Mundial não respondeu |

## Arquitetura

```
world_bank_api/
├── __init__.py      # move o cache do wbdata para o diretório temporário (antes de qualquer import)
├── config.py        # título, versão, descrição do Swagger e tags
├── errors.py        # erros da aplicação e o status HTTP de cada um
├── gateway.py       # ÚNICO módulo que chama o wbdata; cliente sem cache
├── service.py       # regras de negócio: validação, normalização, 404
├── schemas.py       # modelos de resposta (documentam o Swagger)
├── dependencies.py  # como as rotas recebem o serviço (substituível nos testes)
├── main.py          # fábrica da aplicação, tratamento de erros, OpenAPI
└── routers/         # rotas finas: system, catalogue, indicators, data
api/index.py         # entrada do Vercel
tests/               # testes unitários de todas as rotas e de todas as camadas
```

Cada camada só conhece a de baixo: as rotas chamam o serviço, o serviço chama o
gateway, e só o gateway conhece o `wbdata`. Assim, os testes de rota usam um
gateway falso e não fazem chamadas de rede.

### Por que não há cache

O `wbdata` mantém um cache de respostas em arquivo. No Vercel, o sistema de
arquivos é somente leitura, exceto `/tmp`, e a criação desse arquivo causava
falhas. Por isso:

- `world_bank_api/__init__.py` aponta o cache padrão da biblioteca para o diretório
  temporário, antes de o `wbdata` ser importado (a importação já cria um cliente
  padrão);
- `gateway.py` usa um `UncachedClient`, cujo cache é um `NoCache` que nunca guarda
  nada. Todas as chamadas vão à API do Banco Mundial;
- os testes verificam que o cliente usa `NoCache` e que nenhum arquivo novo aparece
  no diretório de cache.

## Configuração

Não há variáveis de ambiente obrigatórias. O servidor não guarda estado.

## Executar localmente

```bash
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv\Scripts\python.exe -m uvicorn api.index:app --port 8200
```

Depois abra `http://127.0.0.1:8200/docs`.

## Testes

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -v
```

Os testes não precisam de internet: o gateway é substituído por um falso nas rotas,
e o cliente HTTP do `wbdata` é substituído nos testes do gateway.

## Deploy na Vercel

1. Importe o repositório no Vercel (framework: *Other*).
2. O `vercel.json` declara a função `api/index.py` (`maxDuration` 30 segundos).
   Não há variáveis de ambiente a configurar.
3. Cada push em `main` gera um deploy.

## Dados

Os dados pertencem ao Banco Mundial e são publicados sob os termos de dados
abertos dele. Mantenha o campo `source` das respostas ao republicar os dados.
