#!/usr/bin/env python3
import json, random, uuid, time, os, signal, sys
from datetime import date
from faker import Faker
from kafka import KafkaProducer

fake = Faker()

# -------- Kafka config (PLAINTEXT local by default; SASL_SSL via env) --------
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")  # or SASL_SSL
SASL_MECH = os.getenv("KAFKA_SASL_MECHANISM", "PLAIN")
SASL_USER = os.getenv("KAFKA_USER", "")
SASL_PASS = os.getenv("KAFKA_PASS", "")
SSL_CAFILE = os.getenv("KAFKA_SSL_CAFILE", "")  # path to cluster CA if using SASL_SSL

producer_kwargs = {
    "bootstrap_servers": BOOTSTRAP,
    "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
    "linger_ms": 50,
    "acks": "all",
}
if SECURITY_PROTOCOL.upper() == "SASL_SSL":
    producer_kwargs.update({
        "security_protocol": "SASL_SSL",
        "sasl_mechanism": SASL_MECH,
        "sasl_plain_username": SASL_USER,
        "sasl_plain_password": SASL_PASS,
    })
    if SSL_CAFILE:
        producer_kwargs["ssl_cafile"] = SSL_CAFILE
producer = KafkaProducer(**producer_kwargs)

# ---------------------- domain constants & helpers ---------------------------
CERTS = ["EMT","AEMT","Paramedic","Flight Nurse","Flight Paramedic"]
STATUS = ["active","probation","expired","revoked","pending"]

def _luhn_checksum(number: str) -> int:
    digits = [int(d) for d in number]
    odd_sum = sum(digits[-1::-2])
    even_sum = 0
    for d in digits[-2::-2]:
        d2 = d * 2
        if d2 > 9: d2 -= 9
        even_sum += d2
    return (odd_sum + even_sum) % 10

def _luhn_check_digit(number_without_check: str) -> int:
    chksum = _luhn_checksum(number_without_check + "0")
    return (10 - chksum) % 10

def gen_npi(rng: random.Random, entity_type: int = 1) -> str:
    # NPI check uses "80840" prefix in Luhn calc; published NPI is 10 digits
    if entity_type not in (1, 2): entity_type = 1
    base9 = f"{entity_type}{rng.randint(10**7, 10**8 - 1)}"
    check = _luhn_check_digit("80840" + base9)
    return base9 + str(check)

# ---------------------- language + DEA helpers ------------------------------
LANGUAGES = ["English","Spanish","Mandarin","Cantonese","Korean","Vietnamese","Arabic","Russian","French","Portuguese","Hindi","Tagalog"]

def choose_languages(rng: random.Random):
    primary = rng.choice(LANGUAGES)
    # ~40% of providers report a second language; ensure it's different
    if rng.random() < 0.40:
        choices = [l for l in LANGUAGES if l != primary]
        second = rng.choice(choices)
    else:
        second = None
    return primary, second

def gen_dea(rng: random.Random, last_name_initial: str = "X") -> str:
    """
    DEA number format: 2 letters + 7 digits (last digit is checksum).
    Checksum = (d1 + d3 + d5 + 2*(d2 + d4 + d6)) % 10
    First letter is registrant type (subset used here), second is prescriber's last-name initial.
    """
    registrant_types = "ABFGHMPR"  # common valid registrant types
    first = rng.choice(list(registrant_types))
    second = (last_name_initial or "X").upper()[0]
    digits = [rng.randint(0, 9) for _ in range(6)]
    checksum = (digits[0] + digits[2] + digits[4] + 2 * (digits[1] + digits[3] + digits[5])) % 10
    return f"{first}{second}{''.join(str(d) for d in digits)}{checksum}"

rng = random.Random(42)

def fake_provider():
    pid = str(uuid.uuid4())
    full_name = fake.name()
    # derive last-name initial for DEA
    try:
        last_initial = full_name.split()[-1][0]
    except Exception:
        last_initial = "X"
    primary_lang, second_lang = choose_languages(rng)
    # Concordance flag indicates provider reports a second language, which can support patient health-literacy concordance workflows
    hl_concordance = second_lang is not None
    return {
        "provider_id": pid,
        "full_name": full_name,
        "certification_level": rng.choice(CERTS),
        "license_status": rng.choice(STATUS),
        "expiration_date": fake.date_between(start_date="today", end_date="+730d").isoformat(),
        "patient_encounters": rng.randint(0, 1200),
        "patient_transports": rng.randint(0, 900),
        "agency_name": fake.company(),
        "is_compliant": rng.choice([True, False]),
        "npi": gen_npi(rng, 1),
        "dea_number": gen_dea(rng, last_initial),
        "primary_language": primary_lang,
        "second_language": second_lang,
        "health_literacy_concordance": hl_concordance
    }

def emit(topic, rec):
    producer.send(topic, rec)

# --------------- topics (ASCII only; no Unicode arrows) ---------------------
TOPICS = {
    "ems.licensing.events.compliance": "license_update",
    "ems.encounter.metadata.analytics": "encounter_metadata",
}

# --------------------------- main loop --------------------------------------
def main():
    catalog = [fake_provider() for _ in range(1000)]
    os.makedirs("payloads", exist_ok=True)
    with open("payloads/providers_seed.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print("Seeded payloads/providers_seed.json with 1000 providers")

    print(f"Producing to {list(TOPICS.keys())} via {BOOTSTRAP} ({SECURITY_PROTOCOL})")
    count = 0
    try:
        while True:
            pr = rng.choice(catalog)
            now_ms = int(time.time() * 1000)
            for topic, typ in TOPICS.items():
                evt = {
                    "event_id": str(uuid.uuid4()),
                    "ts": now_ms,
                    "provider_id": pr["provider_id"],
                    "type": typ,
                    # domain bits (license topic will care; harmless on others)
                    "license_status": rng.choice(STATUS),
                    # include full provider document (with DEA + languages)
                    "provider": pr
                }
                emit(topic, evt)
                count += 1
            if count % 500 == 0:
                producer.flush()
                print(f"sent {count} events…")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("⏹  interrupted by user (Ctrl+C)")
    finally:
        producer.flush()
        producer.close()
        print(f"stopped after {count} events")

if __name__ == "__main__":
    # graceful Ctrl+C on some shells
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    main()