# Code-review agents: Haystack vs LangChain

Демо для команды: один и тот же сценарий код-ревью в четырёх вариантах — single-agent и dispatcher+subagents на **Haystack** и **LangChain**. Инструменты замоканы (статический diff AdCP на Rust), модель — Hugging Face Inference.

## Аспекты ревью

1. `logic_defects` — сравнения, поток выполнения, вычисления  
2. `input_validation` — недопустимые значения, санитизация  
3. `interfaces_compatibility` — API/контракты между модулями  
4. `resources_error_handling` — ресурсы, ошибки, отказоустойчивость  
5. `concurrency_sync` — потоки, гонки, shared state  
6. `tests` — тесты есть, корректны и ловят регрессии  

## Модель и токен

- Модель по умолчанию: `Qwen/Qwen3.8-27B` (tool calling)
- Provider по умолчанию: `cerebras` (cheapest/fastest + Tools на Inference Providers; см. [provider selection](https://huggingface.co/docs/inference-providers/main/en/index#provider-selection))
- В `.env`: `HF_TOKEN`, опционально `HF_MODEL` / `HF_PROVIDER` (см. `.env.example`). Токен прокидывается в `HF_API_TOKEN` / `HUGGINGFACEHUB_API_TOKEN`.

Если router отвечает **402 Payment Required** — токен принят, но нет prepaid-кредитов Inference Providers. Пополнить: [Billing](https://huggingface.co/settings/billing). Провайдеры: [Inference Providers settings](https://huggingface.co/settings/inference-providers).

Для `Qwen/Qwen3.8-27B` в клиентах передаётся `reasoning_effort=none` (иначе модель съедает `max_tokens` на hidden reasoning и возвращает пустой ответ). В Haystack дополнительно патчится баг интеграции HF: tool calls с `arguments={}` иначе отбрасываются.

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Запуск

Из корня репозитория:

```bash
python haystack_single.py
python haystack_dispatcher.py
python langchain_single.py
python langchain_dispatcher.py
```

В логах видны вызовы инструментов (имя, аргументы, результат) и финальный отчёт.

## Инструменты (моки)

| Tool | Назначение |
|------|------------|
| `git_diff_tool` | unified diff по 3 файлам AdCP |
| `project_tree_map_tool` | дерево workspace |
| `task_description_tool` | описание задачи / acceptance |
| `review_aspect_tool` | checklist одного аспекта |
| `lsp_related_code_tool` | definition + usages символа |

Контекст: вымышленный Rust workspace **AdCP** (*Ad Delivery Control Plane*) — floor на auction path, shared `AuctionState`, redact publisher tokens. В diff намеренно заложены дефекты под все шесть аспектов.

## Паттерны

- **Single agent** — один агент со всеми инструментами, сам обходит аспекты.
- **Dispatcher** — оркестратор вызывает шесть специалистов (по одному на аспект), затем сливает отчёт. У Haystack — `AgentTool`; у LangChain — subagent, обёрнутый в `@tool`.

## Ограничения демо

- Вывод — черновик, не финальный verdict ревьюера.
- Моки ≠ настоящий git / rust-analyzer.
- Нет прогона тестов, истории коммитов, полноценного secret scanning.
- Модель должна поддерживать tool calling; иначе агент сломается.
- Dispatcher: выше latency/cost и риск дублирования findings.
