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
   KIBANA_TAGS=your-tag
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

## Режим dry-run

Команда `--dry-run` показывает параметры, которые будут созданы или обновлены, но не выполняет HTTP-запросы и не изменяет Kibana:

```bash
python3 sync_params.py --dry-run
```

Этот режим можно использовать для проверки `params.txt` и конфигурации перед настоящей синхронизацией.

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
   tags        = ["your-tag", "example"]
```

Базовые теги задаются в `config.env` через запятую:

```text
KIBANA_TAGS=your-tag,another-tag
```

Имя сайта из `params.txt` добавляется к ним автоматически.

## Дополнительные параметры запуска

```bash
python3 sync_params.py --data-file other-params.txt
python3 sync_params.py --config another-config.env
python3 sync_params.py --space my-space
```

Переменные окружения имеют приоритет над значениями из файла конфигурации. `config.env` не добавляется в Git, потому что содержит API-ключ.
