# Kibana global parameters sync

Скрипт создаёт или обновляет global parameters в Kibana Synthetics.

## Быстрый старт

1. Создай конфигурацию из шаблона:

   ```bash
   cp config.env.example config.env
   ```

2. Заполни `config.env`:

   ```text
   KIBANA_URL=https://your-kibana-host
   KIBANA_API_KEY=your-api-key
   KIBANA_SPACE=your-space
   ```

3. Добавь исходные данные в `params.txt`:

   ```text
   # site:user_id
   example-site:12345
   another-site:67890
   ```

4. Сначала проверь изменения без запросов к Kibana:

   ```bash
   python3 sync_params.py --dry-run
   ```

5. Выполни синхронизацию:

   ```bash
   python3 sync_params.py
   ```

## Формат данных

Каждая непустая строка `params.txt` имеет формат `name:value`. Пустые строки и строки, начинающиеся с `#`, игнорируются.

Имя `name` используется как имя сайта. Например:

```text
example:12345
```

создаст параметр Kibana:

```text
key         = cm_example_user_id
value       = 12345
tags        = ["cm", "example"]
```

## Дополнительные параметры запуска

```bash
python3 sync_params.py --data-file other-params.txt
python3 sync_params.py --config another-config.env
python3 sync_params.py --space my-space
```

Переменные окружения имеют приоритет над значениями из файла конфигурации. `config.env` не добавляется в Git, потому что содержит API-ключ.
