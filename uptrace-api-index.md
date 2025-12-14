# Uptrace API & Documentation Index

> Индекс документации Uptrace с акцентом на JSON API, форматы запросов и конфигурацию
> Создано: 2025-12-08

---

## 📚 Основные разделы документации

| Раздел | URL | Описание |
|--------|-----|----------|
| Главная | https://uptrace.dev | Обзор возможностей |
| Начало работы | https://uptrace.dev/get | Установка и первичная настройка |
| Инжест данных | https://uptrace.dev/ingest | Отправка данных в Uptrace |
| Features | https://uptrace.dev/features | Каталог функций |
| OpenTelemetry | https://uptrace.dev/opentelemetry | Интеграция с OTel |

### Основные функции

- [JSON API](https://uptrace.dev/features/json-api) - Программный доступ к данным
- [Dashboards](https://uptrace.dev/features/dashboards) - Создание дашбордов
- [Alerting](https://uptrace.dev/features/alerting) - Настройка алертов
- [Service Graph](https://uptrace.dev/features/service-graph) - Граф зависимостей сервисов
- [Grafana Integration](https://uptrace.dev/features/grafana) - Использование как Prometheus datasource

### Запросы и фильтрация

- [Spans & Logs](https://uptrace.dev/features/querying/spans) - Запросы к трейсам и логам
- [Metrics](https://uptrace.dev/features/querying/metrics) - Запросы метрик (PromQL-compatible)
- [Searching](https://uptrace.dev/features/querying/searching) - Поиск
- [PromQL Compatibility](https://uptrace.dev/features/querying/promql-compat) - Совместимость с PromQL
- [Grouping & Systems](https://uptrace.dev/features/querying/grouping) - Группировка данных
- [Logs Grouping](https://uptrace.dev/features/querying/logs-grouping) - Группировка логов

---

## 🔐 Аутентификация API

### Получение токена
- Создать в профиле пользователя: User Profile → Auth Tokens
- Токен наследует права доступа пользователя к проектам
- **Важно**: Токены не работают с SSO (Single Sign-On)

### Формат запроса
```bash
curl https://api.uptrace.dev/api/v1/... \
  --header "Authorization: Bearer <user_token>"
```

### DSN формат (для инжеста данных)
```
http://project1_secret@localhost:14318?grpc=14317
```

Компоненты:
- `http/https` - протокол
- `project1_secret` - write-only токен проекта
- `localhost:14318` - HTTP endpoint
- `?grpc=14317` - опциональный gRPC endpoint

---

## 📊 JSON API Endpoints

### Base URL
- **Cloud**: `https://api.uptrace.dev`
- **Self-hosted**: настраивается в `uptrace.yml`

---

## 🔍 Spans API

### Список спанов

**Endpoint:** `GET /api/v1/tracing/<project_id>/spans`

**Обязательные параметры:**
- `time_gte` - начало временного диапазона (ISO 8601: `2023-07-10T00:00:00Z`)
- `time_lt` - конец временного диапазона

**Опциональные параметры:**
- `trace_id` - фильтр по trace ID
- `id` - фильтр по span ID
- `parent_id` - фильтр по parent span ID
- `limit` - максимальное количество результатов

**Пример запроса:**
```bash
curl 'https://api.uptrace.dev/api/v1/tracing/123/spans?time_gte=2023-07-10T00:00:00Z&time_lt=2023-07-11T00:00:00Z' \
  --header "Authorization: Bearer token_here"
```

**Формат ответа:**
```json
{
  "spans": [
    {
      "id": "span_id",
      "trace_id": "trace_id",
      "parent_id": "parent_span_id",
      "name": "operation_name",
      "duration": 1234567,
      "attributes": {...},
      "events": [...],
      "status_code": "ok|error",
      ...
    }
  ]
}
```

---

### Группировка спанов

**Endpoint:** `GET /api/v1/tracing/<project_id>/groups`

Агрегирует спаны используя UQL запросы.

**Обязательные параметры:**
- `time_gte`, `time_lt` - временной диапазон

**Опциональные параметры:**
- `query` - UQL запрос (например: `"group by host_name"`)
- `limit` - лимит результатов
- `search` - поиск спанов содержащих указанные термины
- `duration_gte` - минимальная длительность (микросекунды)
- `duration_lt` - максимальная длительность (микросекунды)

**Пример запроса:**
```bash
curl 'https://api.uptrace.dev/api/v1/tracing/123/groups?time_gte=2023-07-10T00:00:00Z&time_lt=2023-07-11T00:00:00Z&query=group+by+service_name' \
  --header "Authorization: Bearer token_here"
```

---

## 📈 Metrics API

### Формат запросов метрик

Метрики запрашиваются через dashboards или monitoring API.

**Структура запроса (YAML/JSON):**
```yaml
metrics:
  - metric_name as $alias
  - another_metric{label="value"} as $alias2
query:
  - sum($alias) by (dimension)
  - avg($alias2)
```

**Пример PromQL-совместимого запроса:**
```yaml
metrics:
  - node_cpu_seconds_total as $cpu
query:
  - rate($cpu{mode="idle"}[5m])
```

---

## 🔔 Alerting API

### Создать Metric Monitor

**Endpoint:** `POST /internal/v1/projects/<project_id>/monitors`

**Request body:**
```json
{
  "name": "High CPU Usage",
  "type": "metric",
  "params": {
    "metrics": [
      "system_cpu_utilization as $cpu"
    ],
    "query": [
      "avg($cpu) as cpu_avg"
    ],
    "column": "cpu_avg",
    "minAllowedValue": null,
    "maxAllowedValue": 0.9
  },
  "notifyEveryoneByEmail": true,
  "teamIds": [],
  "channelIds": [123],
  "repeatInterval": "15m"
}
```

**Обязательные поля:**
- `name` - название монитора
- `type` - тип (`"metric"` или `"error"`)
- `params.metrics` - массив метрик
- `params.query` - запрос агрегации
- `params.column` - название столбца для проверки
- `params.minAllowedValue` или `params.maxAllowedValue` - хотя бы один порог

**Опциональные поля:**
- `notifyEveryoneByEmail` - уведомлять всех по email
- `teamIds` - массив ID команд для уведомления
- `channelIds` - массив ID каналов уведомлений
- `repeatInterval` - интервал проверки (`"15m"`, `"1h"`, etc.)
- `params.nullsMode` - обработка null значений (`"allow"`, `"forbid"`, `"convert"`)

---

### Обновить Monitor

**Endpoint:** `PUT /internal/v1/projects/<project_id>/monitors/<monitor_id>`

Тот же формат body что и при создании.

---

### Удалить Monitor

**Endpoint:** `DELETE /internal/v1/projects/<project_id>/monitors/<monitor_id>`

---

### Создать Error Monitor

**Request body:**
```json
{
  "name": "Application Errors",
  "type": "error",
  "params": {
    "metrics": [
      "uptrace_tracing_logs as $logs"
    ],
    "query": [
      "where _system = 'log:all'",
      "where log_severity in ('ERROR', 'FATAL')",
      "count() as error_count"
    ],
    "column": "error_count",
    "minAllowedValue": 0,
    "maxAllowedValue": 10
  },
  "channelIds": [456]
}
```

---

## 🔤 UQL (Uptrace Query Language)

### Базовый синтаксис

UQL - SQL-подобный язык для фильтрации и агрегации данных.

**Структура запроса:**
```
WHERE условие | GROUP BY поля | SELECT поля, агрегации
```

### Операторы по типам данных

**Строки:**
- `=`, `!=` - точное совпадение
- `in (...)` - вхождение в список
- `like "pattern%"` - паттерн (case-insensitive)
- `contains "substring"` - содержит подстроку
- `~ "regex"` - регулярное выражение
- `exists` - проверка наличия атрибута

**Числа:**
- `=`, `!=`, `<`, `<=`, `>`, `>=`
- `exists`

**Булевы:**
- `=`, `!=`

### Единицы измерения

Поддерживаются временные и численные единицы:
- Время: `1ms`, `5s`, `10m`, `1h`
- Размер: `1KB`, `100MB`, `1GB`

**Примеры:**
```
where _dur_ms > 100ms
where response_size > 1MB
```

---

### Функции агрегации

| Функция | Описание |
|---------|----------|
| `count()` | Количество спанов |
| `p50()`, `p75()`, `p90()`, `p95()`, `p99()` | Перцентили |
| `avg()` | Среднее значение |
| `min()`, `max()` | Минимум/максимум |
| `sum()` | Сумма |
| `uniq()` | Количество уникальных значений |

---

### Функции трансформации

**Строковые:**
- `lower(attr)` - в нижний регистр
- `upper(attr)` - в верхний регистр
- `extract(haystack, pattern)` - извлечь по regex
- `replace(attr, old, new)` - заменить подстроку

**Временные:**
- `toStartOfDay(timestamp)` - начало дня
- `toStartOfHour(timestamp)` - начало часа
- `toStartOfMinute(timestamp)` - начало минуты

**Вычисления скорости:**
- `perSec(value)` - в секунду
- `perMin(value)` - в минуту

---

### Примеры запросов

**Найти ошибки по сервисам:**
```
where _status_code = "error"
| group by service_name, _name
| select service_name, _name, count(), p50(_dur_ms)
```

**HTTP запросы медленнее 1 секунды:**
```
where _system = "http" and _dur_ms > 1000ms
| group by http_route
| select http_route, count(), p99(_dur_ms), avg(_dur_ms)
```

**Логи уровня ERROR за последний час:**
```
where _system = "log:all"
  and log_severity in ("ERROR", "FATAL")
  and _time > now() - 1h
| group by service_name
| select service_name, count()
```

---

## 📊 PromQL для метрик

### Алиасы метрик

Все метрики требуют алиасы с префиксом `$`:

```yaml
metrics:
  - postgresql_commits as $commits
  - postgresql_rollbacks as $rollbacks
query:
  - sum($commits) as total_commits
  - sum($rollbacks) as total_rollbacks
```

---

### Фильтрация

PromQL-совместимые операторы:

```yaml
# Точное совпадение
node_cpu_seconds_total{cpu="0", mode="idle"}

# Отрицание
node_cpu_seconds_total{cpu!="0"}

# Regex
node_cpu_seconds_total{mode~"user|system"}

# Отрицание regex
node_cpu_seconds_total{mode!~"idle|iowait"}
```

---

### Группировка

```yaml
# На уровне метрики
metrics:
  - metric_name by (attr1, attr2) as $m

# На уровне функции
query:
  - sum($metric by (attr1, attr2))

# На уровне выражения
query:
  - (sum($metric) by (attr1, attr2))
```

---

### Функции агрегации

| Категория | Функции |
|-----------|---------|
| Статистика | `min`, `max`, `sum`, `avg`, `median` |
| Перцентили | `p50`, `p75`, `p90`, `p95`, `p99` |
| Подсчет | `count`, `count_values` |

---

### Rollup функции (time-series)

| Функция | Описание |
|---------|----------|
| `rate($m[5m])` | Скорость изменения за интервал |
| `irate($m[5m])` | Мгновенная скорость |
| `increase($m[1h])` | Прирост за период |
| `delta($m[5m])` | Разница значений |
| `min_over_time($m[10m])` | Минимум за период |
| `max_over_time($m[10m])` | Максимум за период |
| `avg_over_time($m[10m])` | Среднее за период |

---

### Математические функции

`abs`, `ceil`, `floor`, `round`, `sqrt`, `log`, `log2`, `log10`, `exp`, `ln`

---

### Условная логика

```yaml
query:
  - if(sum($hits) + sum($misses) >= 100,
       sum($misses) / (sum($hits) + sum($misses))
    )
```

---

### Time offset

```yaml
query:
  - sum($metric offset 5m)  # Данные 5 минут назад
  - sum($metric offset 1h)  # Данные час назад
```

---

### Типы инструментов метрик

| Тип | Рекомендуемые функции |
|-----|----------------------|
| Counter | `sum()`, `perMin()`, `perSec()`, `rate()` |
| Gauge | `avg()`, `min()`, `max()`, `delta()` |
| Histogram | `p50()`, `p90()`, `p99()`, `count()` |
| Additive | `sum()`, `avg()`, `delta()` |

---

## 🎯 Dashboards API

### Формат YAML дашборда

```yaml
name: "Service Dashboard"
table_metrics:
  - service_name
  - avg($latency) as avg_latency { unit: duration }
  - sum($requests) as request_rate { unit: per_min }
  - sum($errors) / sum($requests) as error_rate { unit: utilization }

table_query:
  - group by service_name

table_grouping:
  - service_name

grid_rows:
  - title: "Performance Metrics"
    charts:
      - name: "Request Rate"
        metrics:
          - uptrace_tracing_spans as $spans
        query:
          - where _system = 'http'
          - perMin(sum($spans)) by (service_name)
        type: stacked-area

monitors:
  - name: "High Latency Alert"
    params:
      metrics:
        - span_duration_millis as $dur
      query:
        - p99($dur) as p99_latency
      column: p99_latency
      maxAllowedValue: 1000
```

---

### Dashboard query структура

```yaml
metrics:
  - metric_name as $alias
  - another_metric{filter="value"} as $alias2

query:
  - where условие
  - group by атрибуты
  - агрегация($alias) as column_name
```

---

## 📥 Data Ingestion

### Эндпоинты OTLP

| Протокол | Cloud | Self-hosted (default) |
|----------|-------|----------------------|
| OTLP/gRPC | `api.uptrace.dev:4317` | `:4317` |
| OTLP/HTTP | `api.uptrace.dev:443` | `:80` |

### Конфигурация (uptrace.yml)

```yaml
listen:
  grpc:
    addr: ':4317'
  http:
    addr: ':80'

site:
  url: 'https://uptrace.example.com'
  ingest_url: 'https://ingest.uptrace.example.com'
```

---

### Поддерживаемые источники данных

**Traces, Metrics, Logs:**
- OpenTelemetry SDK (все языки)
- OpenTelemetry Collector
- OTel Arrow

**Metrics only:**
- Prometheus

**Logs only:**
- Vector
- FluentBit
- Loki

**Traces & Errors:**
- Sentry SDK

**Metrics & Logs:**
- AWS CloudWatch

**Legacy:**
- Jaeger (deprecated)

---

## 🔔 Notification Channels

### Поддерживаемые каналы

- Email (требует настройки mailer в self-hosted)
- Slack / Mattermost
- Telegram
- Microsoft Teams
- PagerDuty
- Opsgenie
- AlertManager
- Webhooks

### Условия для каналов (Expr)

```go
// Отправлять только для production
attr("deployment.environment") == "production"

// Конкретный монитор
monitorName() == "High CPU Alert"

// По типу алерта
alertType() == "metric"

// Комбинации
attr("service.name") == "api" && alertType() == "error"
```

---

## 🔍 Полезные системные метрики

| Метрика | Описание |
|---------|----------|
| `uptrace_tracing_spans` | Количество спанов |
| `uptrace_tracing_events` | События в спанах |
| `uptrace_tracing_logs` | Логи |
| `uptrace_tracing_services` | Информация о сервисах |

Все метрики с префиксом `uptrace_` - системные метрики Uptrace.

---

## 🎓 Semantic Conventions (атрибуты)

### HTTP spans

- `http.method` - HTTP метод
- `http.route` - маршрут
- `http.status_code` - код ответа
- `http.target` - путь запроса
- `http.url` - полный URL

### Service

- `service.name` - название сервиса
- `service.namespace` - namespace сервиса
- `service.version` - версия

### Deployment

- `deployment.environment` - окружение (prod, staging, dev)

### Host

- `host.name` - имя хоста
- `host.id` - ID хоста

### Database

- `db.system` - тип БД (postgresql, mysql, redis)
- `db.statement` - SQL запрос
- `db.name` - имя базы данных

### Messaging

- `messaging.system` - система (kafka, rabbitmq)
- `messaging.destination` - топик/очередь
- `messaging.operation` - операция (send, receive)

---

## 🚀 Quick Reference Commands

### Получить спаны за последний час
```bash
curl "https://api.uptrace.dev/api/v1/tracing/${PROJECT_ID}/spans?time_gte=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ)&time_lt=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Проверить подключение
```bash
curl "https://api.uptrace.dev/api/v1/tracing/${PROJECT_ID}/spans?time_gte=2023-01-01T00:00:00Z&time_lt=2023-01-01T00:01:00Z&limit=1" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Создать simple monitor
```bash
curl -X POST "https://api.uptrace.dev/internal/v1/projects/${PROJECT_ID}/monitors" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Monitor",
    "type": "metric",
    "params": {
      "metrics": ["system_cpu_utilization as $cpu"],
      "query": ["avg($cpu) as cpu_avg"],
      "column": "cpu_avg",
      "maxAllowedValue": 0.8
    }
  }'
```

---

## 📝 Best Practices

### Запросы
1. Сужайте временной диапазон для лучшей производительности
2. Используйте фильтры перед группировкой
3. Применяйте индексированные атрибуты (semantic conventions)
4. Используйте системные фильтры (`_system`)

### Метрики
1. Всегда указывайте алиасы с `$`
2. Выбирайте правильные агрегации для типа метрики
3. Группируйте по low-cardinality атрибутам
4. Используйте rollup функции для временных серий

### API Usage
1. API бесплатен для occasional use
2. Для высокой нагрузки - связаться с поддержкой
3. Кэшируйте результаты где возможно
4. Используйте batch запросы

### Алерты
1. Настройте repeatInterval адекватно частоте проверок
2. Используйте channel conditions для фильтрации
3. Группируйте похожие алерты
4. Тестируйте алерты в staging окружении

---

## 🔗 Дополнительные ссылки

- **GitHub**: https://github.com/uptrace/uptrace
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/
- **Community**: Telegram, GitHub Discussions
- **Cloud Sign Up**: https://app.uptrace.dev/join

---

## 📌 Ограничения и важные заметки

1. **SSO**: User auth tokens не работают с Single Sign-On
2. **API Stability**: Backward compatibility поддерживается, но изменения возможны
3. **Legacy**: Jaeger интеграция deprecated
4. **Free tier limits**: API бесплатен для occasional use, для больших объемов нужен контакт с поддержкой
5. **Notification frequency**:
   - Metric monitors: старт 15 мин, удваивается каждые 3 нотификации (макс 24 часа)
   - Error monitors: старт 1 час, удваивается каждые 2 нотификации (макс 1 неделя)

---

## 📅 Версия индекса

- Дата создания: 2025-12-08
- Источник: https://uptrace.dev
- Статус: Актуальный
