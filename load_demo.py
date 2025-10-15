import json, os
from kafka import KafkaProducer

BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
producer = KafkaProducer(bootstrap_servers=BOOTSTRAP,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

with open("payloads/hb_demo.json") as f:
    hb = json.load(f)

for series, chars in hb.items():
    for name, a in chars.items():
        evt = {
            "event_id": f"hb-{series}-{name}",
            "type": "license_update",
            "provider_id": f"hb-{name}",
            "license_status": "active"
        }
        producer.send("ems.licensing.events→compliance", evt)
producer.flush()
print("Loaded HB demo events.")
