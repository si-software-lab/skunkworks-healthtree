# HealthTree Demo Architecture

Kafka producers emit EMS events which are consumed by two services:
- **OpenSearch Indexer** stores all events in a daily index (`events-YYYY.MM.DD`)
- **Neo4j Upserter** maintains relationships (Provider→License, Encounter→Provider)

A FastAPI microservice (wolfram-scorer) stubs a risk score endpoint.
