# LinkTracker

Тг-бот для отслеживания изменений на GitHub и StackOverflow с интеллектуальной обработкой через AI-агент.

## Возможности

- Отслеживание GitHub (релизы, PR, issues) и StackOverflow (новые ответы)
- AI-обработка: фильтрация по стоп-словам/авторам, суммаризация, приоритизация (HIGH/MEDIUM/LOW), группировка по временному окну
- Отказоустойчивость: Timeout, Retry, Circuit Breaker, Rate Limiting, Fallback HTTP→Kafka
- Kafka-кластер из 3 брокеров с отказоустойчивостью
- Docker-оркестрация всего стека

## Технологии

**Backend:** Python 3.12, FastAPI, SQLAlchemy, APScheduler  
**Telegram:** python-telegram-bot  
**Message Broker:** Apache Kafka 7.5.0 (3 брокера + ZooKeeper)  
**Database:** PostgreSQL 15  
**Resilience:** tenacity, pybreaker, slowapi  
**Testing:** pytest, testcontainers  
**DevOps:** Docker Compose, Poetry

### Требования для запуска

- Docker 24.0+ и Docker Compose v2
- Poetry 1.8+ (для локальной разработки)

### 1. Настройка

```bash
# Создайте .env
cat > .env << EOF
DB_USER=postgres
DB_PASSWORD=123456
DB_NAME=linktracker
BOT_TOKEN=your_telegram_bot_token
PROXY=https://your-proxy-url
NOTIFICATION_BACKEND=kafka
MESSAGE_SOURCE=kafka
EOF
```

### 2. Запуск через Docker

```bash
# Собрать и запустить весь стек
docker compose up -d --build

# Проверить статус
docker compose ps

# Логи
docker compose logs -f
docker compose logs -f scrapper
docker compose logs -f bot
docker compose logs -f ai-agent
```

### 3. Локальный запуск

```bash
poetry install

# Запустить сервисы
poetry run uvicorn src.scrapper_service.main:app --host 0.0.0.0 --port 8080
poetry run uvicorn src.bot_service.main:fastapi_app --host 0.0.0.0 --port 8000
poetry run uvicorn src.ai_agent_service.main:app --host 0.0.0.0 --port 8001
```

## API Endpoints

### Scrapper Service (:8080)

- `POST /tg-chat/{id}` — регистрация чата
- `POST /links` — добавление ссылки
- `GET /links` — список отслеживаемых ссылок
- `DELETE /links` — удаление ссылки

**Swagger:** http://localhost:8080/docs

### Bot Service (:8000)

- `POST /api/updates` — приём обновлений

**Swagger:** http://localhost:8000/docs

## AI Agent Service

### Фильтрация

- Стоп-слова (spam, ads, promo)
- Исключённые авторы (bot-user)
- Минимальная длина текста (20 символов)

### Суммаризация

Обрезка длинных текстов до 500 символов

### Приоритизация

- **HIGH** — содержит critical, urgent, breaking, security
- **LOW** — содержит minor, typo, chore, docs
- **MEDIUM** — остальные

### Группировка

Обновления для одного tgChatId в пределах 30 секунд объединяются в одно сообщение с нумерованным списком


## Конфигурация

Основные переменные окружения (`.env`):

**Database:** `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`  
**Bot:** `BOT_TOKEN`, `PROXY`, `MESSAGE_SOURCE`  
**Kafka:** `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`  
**Resilience:** `HTTP_TIMEOUT`, `RETRY_MAX_ATTEMPTS`, `CB_FAILURE_THRESHOLD`, `RATE_LIMIT_MAX_REQUESTS`  
**AI Agent:** `FILTER_STOP_WORDS`, `SUMMARIZATION_THRESHOLD`, `PRIORITIZATION_HIGH_KEYWORDS`, `GROUPING_WINDOW_MS`

---
