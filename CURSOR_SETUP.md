# Настройка MCP сервера в Cursor

## Параметры конфигурации

В конфигурации MCP сервера для Cursor используются следующие параметры:

### `command`
Полный путь к исполняемому файлу Poetry или Python.

**Примеры:**
- Poetry из виртуального окружения: `/path/to/uptrace-mcp/.venv/bin/poetry`
- Python из виртуального окружения: `/path/to/uptrace-mcp/.venv/bin/python`
- Системный Poetry: `poetry` (если установлен глобально)

### `args`
Аргументы командной строки, передаваемые команде.

**Для Poetry:**
```json
"args": ["run", "uptrace-mcp"]
```

**Для Python:**
```json
"args": ["-m", "uptrace_mcp.server"]
```

### `cwd` (ВАЖНО!)
**Рабочая директория** - это директория, из которой запускается команда. 

⚠️ **Критически важно**: `cwd` должен указывать на корневую директорию проекта `uptrace-mcp`, где находится файл `pyproject.toml`.

**Правильно:**
```json
"cwd": "/path/to/uptrace-mcp"
```

**Неправильно:**
```json
"cwd": "/path/to"  // ❌ Poetry не найдет pyproject.toml
"cwd": "/home/user"  // ❌ Poetry не найдет pyproject.toml
```

Если `cwd` указан неправильно, вы увидите ошибку:
```
Poetry could not find a pyproject.toml file in /path/to or its parents
```

### `env`
Переменные окружения, которые будут доступны серверу.

**Обязательные переменные:**
- `UPTRACE_URL` - URL вашего инстанса Uptrace
- `UPTRACE_PROJECT_ID` - ID проекта
- `UPTRACE_API_TOKEN` - API токен

## Пример полной конфигурации

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "/path/to/uptrace-mcp/.venv/bin/poetry",
      "args": ["run", "uptrace-mcp"],
      "cwd": "/path/to/uptrace-mcp",
      "env": {
        "UPTRACE_URL": "https://uptrace.xxx",
        "UPTRACE_PROJECT_ID": "3",
        "UPTRACE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Как найти правильный путь

1. Откройте терминал
2. Перейдите в директорию проекта:
   ```bash
   cd /path/to/uptrace-mcp
   ```
3. Проверьте, что там есть `pyproject.toml`:
   ```bash
   ls pyproject.toml
   ```
4. Получите полный путь:
   ```bash
   pwd
   ```
5. Используйте этот путь в параметре `cwd`

## Альтернативный вариант с Python (рекомендуется)

Если Poetry не работает или вы видите ошибку "Poetry could not find a pyproject.toml", используйте Python напрямую:

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "/path/to/uptrace-mcp/.venv/bin/python",
      "args": ["-m", "uptrace_mcp.server"],
      "cwd": "/path/to/uptrace-mcp",
      "env": {
        "UPTRACE_URL": "https://uptrace.xxx",
        "UPTRACE_PROJECT_ID": "3",
        "UPTRACE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

**Преимущества:**
- Не зависит от Poetry для поиска проекта
- Более надежный запуск
- Переменные из `.env` файла загружаются автоматически

## Вариант с Poetry и явным указанием проекта

Если хотите использовать Poetry, можно явно указать директорию проекта:

```json
{
  "mcpServers": {
    "uptrace": {
      "command": "/path/to/uptrace-mcp/.venv/bin/poetry",
      "args": ["--directory", "/path/to/uptrace-mcp", "run", "uptrace-mcp"],
      "cwd": "/path/to/uptrace-mcp",
      "env": {
        "UPTRACE_URL": "https://uptrace.xxx",
        "UPTRACE_PROJECT_ID": "3",
        "UPTRACE_API_TOKEN": "your_token_here"
      }
    }
  }
}
```

## Проверка конфигурации

После настройки проверьте конфигурацию:

```bash
cd /path/to/uptrace-mcp
python check_config.py
```

Затем протестируйте запуск сервера:

```bash
export UPTRACE_URL="https://uptrace.xxx"
export UPTRACE_PROJECT_ID="3"
export UPTRACE_API_TOKEN="your_token"
.venv/bin/poetry run uptrace-mcp --help
```

Если команда выполняется без ошибок, конфигурация правильная.

