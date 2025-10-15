import json, random, uuid, time, os
from faker import Faker
from kafka import KafkaProducer

fake = Faker()
bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
producer = KafkaProducer(bootstrap_servers=bootstrap,
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))

CERTS = ["EMT","AEMT","Paramedic","Flight Nurse","Flight Paramedic"]
STATUS = ["active","probation","expired","revoked","pending"]

def fake_provider():
    pid = str(uuid.uuid4())
    return {
        "provider_id": pid,
        "full_name": fake.name(),
        "certification_level": random.choice(CERTS),
        "license_status": random.choice(STATUS),
        "expiration_date": fake.date_between("+10d","+730d").isoformat(),
        "patient_encounters": random.randint(0, 1200),
        "patient_transports": random.randint(0, 900),
        "agency_name": fake.company(),
        "is_compliant": random.choice([True, False]),
        "npi_like": fake.msisdn()[0:10]
    }

def emit(topic, rec):
    producer.send(topic, rec)

if __name__ == "__main__":
    catalog = [fake_provider() for _ in range(1000)]
    os.makedirs("payloads", exist_ok=True)
    with open("payloads/providers_seed.json", "w") as f:
        json.dump(catalog, f)
    print("Seeded providers_seed.json with 1000 providers")

    topics = {
        "ems.licensing.events→compliance": "license_update",
        "ems.encounter.metadata→analytics": "encounter_metadata",
    }

    while True:
        pr = random.choice(catalog)
        for topic, typ in topics.items():
            evt = {
                "event_id": str(uuid.uuid4()),
                "ts": int(time.time()*1000),
                "provider_id": pr["provider_id"],
                "license_status": random.choice(STATUS),
                "type": typ
            }
            emit(topic, evt)
        producer.flush()
        time.sleep(0.05)
