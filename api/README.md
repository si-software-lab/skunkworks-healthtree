
```text
skunkworks/
├── api/
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── metrics.py
│   └── schemas.py
├── loader/
│   ├── __init__.py
│   ├── config.py
│   ├── kafka_client.py
│   └── batch_loader.py
├── cli/
│   ├── __init__.py
│   └── start_demo.py
├── data/
│   └── metric_defs.json    (auto-created if missing)
├── payloads/
│   └── (optional demo payload JSON files)
├── docker-compose.yml
├── .env
└── requirements.txt
```
