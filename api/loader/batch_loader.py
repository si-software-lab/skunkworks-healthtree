# loader/batch_loader.py
import json
import logging
from loader.config import setup_logging, get_env_var
from loader.kafka_client import publish_records

def run_batch_load():
    setup_logging()
    topic = get_env_var("DEMO_TOPIC", "data.load.mariadb.batch.v1")
    payload_file = get_env_var("BATCH_PAYLOAD_FILE", "payloads/batch.json")
    try:
        with open(payload_file, "r") as f:
            records = json.load(f)
    except Exception as e:
        logging.error(f"Failed reading payload file {payload_file}: {e}")
        return
    publish_records(topic, records)
    logging.info("Batch load completed")

if __name__ in("__main__"):
    run_batch_load()