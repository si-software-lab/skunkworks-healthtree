import json, os, time, logging, logging.config, yaml
from datetime import datetime
from kafka import KafkaConsumer
from opensearchpy import OpenSearch

if os.path.exists("logging.yaml"):
    with open("logging.yaml") as f:
        logging.config.dictConfig(yaml.safe_load(f))
log = logging.getLogger("indexer")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPICS = [t.strip() for t in os.getenv("KAFKA_TOPICS","").split(",") if t.strip()]
OS_URL = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
INDEX_PREFIX = os.getenv("OPENSEARCH_INDEX_PREFIX", "events-")

def daily_index():
    return f"{INDEX_PREFIX}{datetime.utcnow():%Y.%m.%d}"

def main():
    osclient = OpenSearch(OS_URL)
    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="opensearch-indexer"
    )
    log.info(f"Consuming topics={TOPICS} from {KAFKA_BOOTSTRAP}, indexing into {OS_URL}")
    for msg in consumer:
        doc = msg.value
        doc.setdefault("ts", int(time.time()*1000))
        idx = daily_index()
        try:
            osclient.index(index=idx, document=doc)
        except Exception as e:
            log.exception(f"Index error: {e} :: {doc}")

if __name__ == "__main__":
    main()
