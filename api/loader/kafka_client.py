# loader/kafka_client.py
import json
import logging
from kafka import KafkaProducer
from loader.config import get_env_var

def get_kafka_producer():
    bootstrap = get_env_var("KAFKA_BOOTSTRAP", "localhost:9092")
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            linger_ms=50,
            acks="all",
        )
        logging.info(f"KafkaProducer connected to {bootstrap}")
        return producer
    except Exception as e:
        logging.error(f"Could not create KafkaProducer: {e}")
        return None

def publish_records(topic: str, records: list[dict]):
    producer = get_kafka_producer()
    if not producer:
        logging.warning("Producer unavailable: skipping publish")
        return
    for rec in records:
        producer.send(topic, rec)
    producer.flush()
    logging.info(f"Published {len(records)} records to topic: {topic}")