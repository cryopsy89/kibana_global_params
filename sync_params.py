#!/usr/bin/env python3
"""
Синхронизация global parameters в Kibana Synthetics.

Для каждого сайта из файла params.txt создаёт/обновляет параметр:
  key   = cm_<site>_user_id
  value = <id>
  tags  = ["cm", "<site>"]

Логика идемпотентности:
  1. GET /api/synthetics/params — получить все текущие параметры
  2. Если ключ уже существует — PUT (обновление по id параметра)
  3. Если ключа нет — POST (создание)

Запуск:
    cp config.env.example config.env
    python3 sync_params.py
  # Добавь --dry-run чтобы посмотреть, что будет сделано, без реальных вызовов
"""

from pathlib import Path
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
import ssl

DEFAULT_DATA_FILE = Path(__file__).with_name("params.txt")
DEFAULT_CONFIG_FILE = Path(__file__).with_name("config.env")


def load_key_value_file(path, separator):
    """Читает пары name:value или KEY=VALUE, пропуская комментарии."""
    values = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise ValueError(f"Файл не найден: {path}") from None

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if separator not in line:
            raise ValueError(f"{path}:{line_number}: ожидается формат name{separator}value")
        name, value = (part.strip() for part in line.split(separator, 1))
        if not name or not value:
            raise ValueError(f"{path}:{line_number}: имя и значение не могут быть пустыми")
        values[name] = value
    return values


def load_config(path):
    """Загружает config.env, не перезаписывая уже заданные env-переменные."""
    if not path.exists():
        return
    for name, value in load_key_value_file(path, "=").items():
        os.environ.setdefault(name, value)


def load_user_ids(path):
    return load_key_value_file(path, ":")

# --- Вспомогательные функции -------------------------------------------------

def build_params(user_ids, base_tags):
    """Строит список параметров в формате Kibana Synthetics API."""
    result = []
    for site, uid in user_ids.items():
        key = f"cm_{site}_user_id"
        result.append({
            "key": key,
            "value": str(uid).strip(),
            "tags": [*base_tags, site],
            "description": f"user_id для {site}",
        })
    return result


def kibana_request(method, url, api_key, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("kbn-xsrf", "true")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"ApiKey {api_key}")
    req.add_header("User-Agent", "Mozilla/5.0 (compatible; kibana-global-params-sync/1.0)")
    req.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = raw.decode("utf-8", errors="replace")
        return e.code, parsed


def get_existing_params(kibana_url, api_key, space=None):
    """Возвращает {key: id} для всех существующих global parameters."""
    base = f"{kibana_url}/s/{space}" if space else kibana_url
    status, data = kibana_request("GET", f"{base}/api/synthetics/params", api_key)
    if status != 200:
        print(f"[ERROR] Не удалось получить список параметров: {status} {data}", file=sys.stderr)
        sys.exit(1)
    return {item["key"]: item["id"] for item in data}


def sync_params(kibana_url, api_key, params, dry_run=False, space=None):
    base = f"{kibana_url}/s/{space}" if space else kibana_url
    if dry_run:
        print("[DRY-RUN] Сеть не используется, показываю что было бы отправлено:\n")
        for p in params:
            print(f"[DRY-RUN] UPSERT {p['key']} -> value={p['value']} tags={p['tags']}")
        print(f"\nВсего параметров к синхронизации: {len(params)}")
        return

    existing = get_existing_params(kibana_url, api_key, space=space)

    created, updated, failed = 0, 0, 0

    for p in params:
        key = p["key"]
        if key in existing:
            param_id = existing[key]
            status, resp = kibana_request(
                "PUT",
                f"{base}/api/synthetics/params/{param_id}",
                api_key,
                body={"value": p["value"], "tags": p["tags"], "description": p["description"]},
            )
            if status in (200, 204):
                print(f"[OK] Updated {key}")
                updated += 1
            else:
                print(f"[FAIL] Update {key}: {status} {resp}", file=sys.stderr)
                failed += 1
        else:
            status, resp = kibana_request(
                "POST",
                f"{base}/api/synthetics/params",
                api_key,
                body=p,
            )
            if status in (200, 201):
                print(f"[OK] Created {key}")
                created += 1
            else:
                print(f"[FAIL] Create {key}: {status} {resp}", file=sys.stderr)
                failed += 1

    print(f"\nИтого: создано={created}, обновлено={updated}, ошибок={failed}")


def main():
    parser = argparse.ArgumentParser(description="Sync user_id params into Kibana Synthetics")
    parser.add_argument("--dry-run", action="store_true", help="Показать что будет сделано, без реальных вызовов API")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_FILE, help="Файл конфигурации (по умолчанию config.env)")
    parser.add_argument("--data-file", type=Path, default=DEFAULT_DATA_FILE, help="Файл параметров name:value (по умолчанию params.txt)")
    parser.add_argument("--space", help="Kibana space id (можно задать через KIBANA_SPACE)")
    args = parser.parse_args()

    try:
        load_config(args.config)
        user_ids = load_user_ids(args.data_file)
    except ValueError as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        sys.exit(1)

    space = args.space or os.environ.get("KIBANA_SPACE")
    kibana_url = os.environ.get("KIBANA_URL")
    api_key = os.environ.get("KIBANA_API_KEY")
    base_tags = [tag.strip() for tag in os.environ.get("KIBANA_TAGS", "").split(",") if tag.strip()]

    if not args.dry_run and (not kibana_url or not api_key):
        print("Задай переменные окружения KIBANA_URL и KIBANA_API_KEY", file=sys.stderr)
        sys.exit(1)
    if not base_tags:
        print("Задай KIBANA_TAGS в config.env, например KIBANA_TAGS=team", file=sys.stderr)
        sys.exit(1)

    params = build_params(user_ids, base_tags)
    sync_params(kibana_url or "https://dry-run.invalid", api_key or "dry-run", params, dry_run=args.dry_run, space=space)


if __name__ == "__main__":
    main()
