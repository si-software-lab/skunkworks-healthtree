import json, os, logging, time, logging.config, yaml
from kafka import KafkaConsumer
from neo4j import GraphDatabase

if os.path.exists("logging.yaml"):
    with open("logging.yaml") as f:
        logging.config.dictConfig(yaml.safe_load(f))
log = logging.getLogger("upserter")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPICS = [t.strip() for t in os.getenv("KAFKA_TOPICS","").split(",") if t.strip()]
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "test")

CYPHERS = {
"license_update": """
MERGE (p:Provider {provider_id:$provider_id})
ON CREATE SET p.createdTs = timestamp()
WITH p
MERGE (l:License {provider_id:$provider_id})
SET l.status = $license_status,
    l.updatedTs = timestamp()
MERGE (p)-[:HOLDS]->(l)
""",
"encounter_metadata": """
MERGE (e:Encounter {event_id:$event_id})
SET e.updatedTs = timestamp(), e.type = $type
WITH e
MERGE (p:Provider {provider_id:$provider_id})
MERGE (e)-[:HANDLED_BY]->(p)
"""
}

def route(evt: dict) -> str:
    t = (evt.get("type") or "").lower()
    if "license" in t: return "license_update"
    if "encounter" in t: return "encounter_metadata"
    return "license_update"

def main():
    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="neo4j-upserter"
    )
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    log.info(f"Consuming topics={TOPICS}; writing to Neo4j {NEO4J_URI}")

    with driver.session() as session:
        for msg in consumer:
            evt = msg.value
            evt.setdefault("event_id", evt.get("event_id") or f"evt-{int(time.time()*1000)}")
            cy = CYPHERS.get(route(evt))
            try:
                session.run(cy, **evt)
            except Exception as e:
                log.exception(f"Cypher error: {e} :: {evt}")

if __name__ == "__main__":
    main()
