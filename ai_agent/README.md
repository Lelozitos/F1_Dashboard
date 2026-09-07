# F1 AI Agent

Chat separado do dashboard principal. Pergunta qualquer coisa sobre F1 (sessões, tempos de volta, standings, pit stops) e o Claude busca o dado real via tool use antes de responder — não é um chatbot que "sabe" F1 de cor, ele chama as mesmas fontes que o resto do projeto usa (FastF1, Ergast, OpenF1).

Roda como app Streamlit independente, na sua própria pasta, sem entrar na navegação multipage do `home.py`.

## Setup

```bash
python -m pip install -r ai_agent/requirements.txt
```

Precisa de uma chave da API da Anthropic:

```bash
setx ANTHROPIC_API_KEY "sk-ant-..."
```

(ou exporta a env var do jeito que preferir — o SDK lê `ANTHROPIC_API_KEY` do ambiente sozinho, não tem chave hardcoded em lugar nenhum do código)

## Rodar

```bash
streamlit run ai_agent/app.py
```

Abre em uma porta separada do dashboard principal. Pode rodar os dois ao mesmo tempo.

## Custo

Cada pergunta gera 1+ chamadas à API da Anthropic (modelo `claude-opus-5`), cobradas por token. Perguntas que precisam carregar telemetria de sessão (`get_session_results`, `get_driver_lap_times`, `compare_fastest_laps`) demoram mais na primeira vez (FastF1 baixa e cacheia localmente em `%TEMP%/fastf1`).

## Estrutura

```
ai_agent/
├── app.py       chat Streamlit (UI, histórico de mensagens)
├── agent.py     loop de tool use com o SDK da Anthropic
├── tools.py     as 8 funções que o Claude pode chamar
└── requirements.txt
```

### `app.py`

Interface de chat (`st.chat_input` / `st.chat_message`). Mantém duas listas em `session_state`:

- `display_messages` — só texto, pra renderizar na tela
- `api_messages` — histórico completo mandado pra API, incluindo os blocos `tool_use`/`tool_result` de cada pergunta anterior

Mostra em um expander quais tools foram chamadas pra responder cada pergunta. Botão de limpar conversa reseta os dois.

### `agent.py`

Monta o system prompt (data de hoje, formato dos identificadores de sessão, instrução de nunca inventar número) e roda `client.beta.messages.tool_runner(...)` com todas as tools de `tools.py`. `run_turn()` itera o runner até acabar, reconstrói o histórico completo turno a turno (necessário pra manter contexto entre perguntas) e devolve o texto final.

Modelo fixo: `claude-opus-5`, thinking adaptativo ligado.

### `tools.py`

Cada função abaixo é decorada com `@beta_tool` — o Claude só vê nome, docstring e assinatura, e decide sozinho qual chamar e com quais argumentos.

| Tool | Parâmetros | Fonte | Retorna |
|---|---|---|---|
| `get_event_schedule` | `year` | FastF1 (`get_event_schedule`) | Calendário do ano: rodada, nome do evento, país, local, data, formato |
| `get_session_results` | `year`, `event`, `session` | FastF1 (`get_session`) | Classificação da sessão, volta mais rápida de cada piloto, resumo de clima (temp ar/pista, umidade, chuva) |
| `get_driver_lap_times` | `year`, `event`, `session`, `driver` | FastF1 | Volta a volta de um piloto: tempo, composto, stint, entrada/saída de pit, status da pista |
| `compare_fastest_laps` | `year`, `event`, `session`, `drivers` (lista) | FastF1 | Melhor volta, composto e tempos de setor de vários pilotos lado a lado |
| `get_driver_standings` | `year`, `round` (opcional) | Ergast | Classificação de pilotos do campeonato, pontos e vitórias |
| `get_constructor_standings` | `year`, `round` (opcional) | Ergast | Classificação de construtores, pontos e vitórias |
| `get_race_results` | `year`, `round` | Ergast | Classificação completa da corrida, com pontos de sprint somados quando o fim de semana teve sprint |
| `get_pit_stops` | `year`, `event`, `session` | OpenF1 | Paradas nos boxes: volta, duração, piloto — **fonte instável**, igual ao resto do projeto (ver limitação abaixo) |

`session` sempre é um destes: `"FP1"`, `"FP2"`, `"FP3"`, `"Q"`, `"S"` (sprint), `"R"` (corrida). Dado só existe a partir de 2018.

Sessões carregadas via FastF1 ficam em cache de processo (`functools.lru_cache`) — a mesma sessão não é recarregada duas vezes na mesma execução do app.

## Limitações conhecidas

- **Pit stops via OpenF1 são não-confiáveis** — mesma ressalva do `graph_teams_pitstop` comentado no dashboard principal. Se voltar vazio, avisa isso ao invés de inventar dado.
- Toda tool devolve `{"error": "..."}` em vez de lançar exceção — se o Claude receber um erro de tool, ele conta isso pro usuário em vez de chutar número.
- Sem streaming token-a-token: a resposta aparece de uma vez quando o loop de tools termina.
