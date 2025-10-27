## Skunkworks Demo: Provider Directory + Kafka (Helm)






Why it qualifies as a bootstrap demo - 
Bootstrap in this context means:
  -	Each service spins up in isolation but is immediately production-patterned (Kafka, Neo4j, OpenSearch, API, etc.);
  - The cluster can “self-host” analytics and streaming pipelines without any external managed dependencies;
  - Minimal but complete infrastructure: message bus + search + graph + compute + persistence + orchestration.


Let’s unpack the data architecture carefully:
⸻






  -	We use app.include_router, which is good — you’re modularising the routing.
  -	The business logic (reading/writing JSON file) is present and works.
  -	For a small API with only a few endpoints, this layout is perfectly fine.







This repo contains:
- A **synthetic MCO-style provider directory** generator (`provider_directory/generate_provider_directory.py`)
- A **Kafka Helm deployment** (Bitnami chart) configured for **SASL + TLS** with external access.

## Quickstart

### 1) Generate synthetic provider directory
```bash
cd provider_directory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python generate_provider_directory.py --out ./out --seed 42
ls -1 ./out
```

Project Structure
```text
demo/
├─ README.md
├─ .gitignore
├─ provider_directory/
│  ├─ requirements.txt
│  └─ generate_provider_directory.py
├─ tools/
│  ├─ seed_providers_to_kafka.py
│  └─ setup_topics.py
├─ services/
│  └─ wolfram_scorer/
│     ├─ Dockerfile
│     ├─ requirements.txt
│     └─ app.py                 # FastAPI
├─ opensearch/
│  ├─ docker-compose.opensearch.yml
│  └─ demo.py
└─ k8s/
   └─ kafka/
      ├─ values.yaml
      ├─ create_namespace.sh
      ├─ create_kafka_secret.sh
      └─ install_kafka.sh
```

⸻

README.md

# Demo: Provider Directory + Kafka (Helm)

This repo contains:
- A **synthetic MCO-style provider directory** generator (`provider_directory/generate_provider_directory.py`)
- A **Kafka Helm deployment** (Bitnami chart) configured for **SASL + TLS** with external access.

## Quickstart

### 1) Generate synthetic provider directory
```bash
cd provider_directory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python generate_provider_directory.py --out ./out --seed 42
ls -1 ./out

2) Deploy Kafka to Kubernetes (namespace: ems-core)

cd k8s/kafka
./create_namespace.sh               # idempotent
./create_kafka_secret.sh            # provide STRONG passwords
./install_kafka.sh                  # installs/updates Bitnami Kafka with values.yaml

Produced payloads files
	•	networks.csv
	•	organizations.csv
	•	practices.csv
	•	providers.csv
	•	affiliations.csv
	•	network_participation.csv
	•	provider_directory_flat.ndjson

Notes
	•	Helm values expect a Secret named kafka-sasl in namespace ems-core.
	•	External access: set your real DNS in values.yaml at listeners.advertisedListeners.

---

# `.gitignore`

```gitignore
# Python
__pycache__/
*.pyc
.venv/
.env

# Output
/provider_directory/out/
/*.zip

# OS
.DS_Store


⸻

provider_directory/requirements.txt

pandas>=2.1
faker>=24.8


⸻

provider_directory/generate_provider_directory.py

#!/usr/bin/env python3
"""
Generate a synthetic MCO-style provider directory using Faker (with a fallback).
Hierarchy:
  MCO Network -> Organization (Type-2 NPI) -> Practice/Location -> Provider (Type-1 NPI)
Plus:
  - Provider↔Practice affiliations
  - Network participation (panel status, effective/term dates)
Outputs:
  CSVs + a flattened NDJSON stream suitable for demos / ingestion.

Usage:
  python generate_provider_directory.py --out ./out --seed 42
"""

from __future__ import annotations
import os, json, uuid, string, argparse, random
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Optional, List, Dict
import pandas as pd

# ---------------- CLI ----------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="./out", help="Output directory")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p.add_argument("--networks", type=int, default=3)
    p.add_argument("--orgs", type=int, default=6)
    p.add_argument("--practices-min", type=int, default=2)
    p.add_argument("--practices-max", type=int, default=5)
    p.add_argument("--providers-min", type=int, default=4)
    p.add_argument("--providers-max", type=int, default=12)
    return p.parse_args()

# ---------------- Faker w/ fallback ----------------
try:
    from faker import Faker
    def make_fakers(seed: int):
        fk = Faker("en_US"); fk.seed_instance(seed)
        return fk
except Exception:
    Faker = None
    def make_fakers(seed: int):
        return None

# ---------------- Helpers ----------------
def luhn_checksum(number: str) -> int:
    digits = [int(d) for d in number]
    odd_sum = sum(digits[-1::-2])
    even_sum = 0
    for d in digits[-2::-2]:
        d2 = d * 2
        if d2 > 9: d2 -= 9
        even_sum += d2
    return (odd_sum + even_sum) % 10

def compute_luhn_check_digit(number_without_check: str) -> int:
    chksum = luhn_checksum(number_without_check + "0")
    return (10 - chksum) % 10

def gen_npi(rng: random.Random, entity_type: int = 1) -> str:
    # CMS convention: use "80840" prefix in Luhn calc; published NPIs do not include the prefix
    if entity_type not in (1,2): entity_type = 1
    base9 = f"{entity_type}{rng.randint(10**7, 10**8 - 1)}"
    check = compute_luhn_check_digit("80840" + base9)
    return base9 + str(check)

def rand_digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.digits) for _ in range(n))

SPECIALTIES = [
    ("207Q00000X","Family Medicine"),
    ("207R00000X","Internal Medicine"),
    ("208000000X","Pediatrics"),
    ("207P00000X","Emergency Medicine"),
    ("207N00000X","Dermatology"),
    ("207T00000X","Neurology"),
    ("207X00000X","Orthopedic Surgery"),
    ("207ZP0102X","Sports Medicine"),
    ("207RG0100X","Geriatric Medicine"),
]

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL","IN","KS","KY","LA","MA","MD",
          "ME","MI","MN","MO","MS","MT","NC","ND","NE","NH","NJ","NM","NV","NY","OH","OK","OR","PA","RI","SC",
          "SD","TN","TX","UT","VA","VT","WA","WI","WV","WY"]

def date_between(rng: random.Random, start_year=2018, end_year=date.today().year) -> date:
    start = date(start_year,1,1); end = date(end_year,12,31)
    return start + timedelta(days=rng.randint(0, (end - start).days))

def random_hours(rng: random.Random) -> str:
    days = ["Mon","Tue","Wed","Thu","Fri"]
    open_hr = rng.choice([7,8,9]); close_hr = rng.choice([17,18,19])
    return "; ".join([f"{d} {open_hr}:00-{close_hr}:00" for d in days])

# ---------------- Data classes ----------------
@dataclass
class Network:
    network_id: str
    mco_name: str
    network_name: str

@dataclass
class Organization:
    org_id: str
    org_npi: str
    org_name: str
    fein: str
    address1: str
    city: str
    state: str
    zip: str
    phone: str

@dataclass
class Practice:
    practice_id: str
    org_id: str
    location_id: str
    practice_name: str
    address1: str
    city: str
    state: str
    zip: str
    phone: str
    hours: str

@dataclass
class Provider:
    provider_id: str
    npi: str
    first_name: str
    last_name: str
    gender: str
    degree: str
    primary_taxonomy_code: str
    primary_specialty: str
    secondary_specialty: Optional[str]
    email: str
    license_state: str
    license_number: str
    accepts_new_patients: bool
    languages: str
    status: str  # Active, On Leave, Termed

@dataclass
class Affiliation:
    provider_id: str
    practice_id: str
    start_date: str
    end_date: Optional[str]

@dataclass
class NetworkParticipation:
    provider_id: str
    practice_id: str
    network_id: str
    panel_status: str  # Open, Closed, Limited
    effective_date: str
    termination_date: Optional[str]

# ---------------- Main gen ----------------
def main():
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(args.seed)
    fk = make_fakers(args.seed)

    def F(v, fallback): return v if v else fallback
    def fake_name():
        return fk.name() if fk else f"Dr. {rng.choice(['Alex','Jordan','Taylor','Morgan'])} {rng.choice(['Smith','Johnson','Lee'])}"
    def fake_org():
        return fk.company() if fk else f"{rng.choice(['Sunrise','Evergreen','Summit'])} Health Group"
    def fake_addr():
        if fk:
            return fk.street_address(), fk.city(), fk.state_abbr(), fk.postcode()
        return f"{rng.randint(100,9999)} Main St", "Denver", "CO", "80205"
    def fake_phone():
        return fk.phone_number() if fk else f"({rng.randint(200,999)}) {rng.randint(100,999)}-{rng.randint(1000,9999)}"
    def fake_email(first, last):
        dom = rng.choice(["examplehealth.org","communitycare.com","medgroup.net","clinicpartners.org"])
        return f"{first.lower()}.{last.lower()}@{dom}"

    mco_name = "Signal3 Health Plan"
    networks: List[Network] = []
    orgs: List[Organization] = []
    practices: List[Practice] = []
    providers: List[Provider] = []
    affils: List[Affiliation] = []
    net_parts: List[NetworkParticipation] = []

    for i in range(args.networks):
        lvl = ["Preferred","Standard","Value","Medicaid","Medicare Advantage","Commercial"][i % 6]
        networks.append(Network(str(uuid.uuid4()), mco_name, lvl))

    for _ in range(args.orgs):
        org_id = str(uuid.uuid4())
        addr, city, state, zipc = fake_addr()
        org = Organization(
            org_id=org_id,
            org_npi=gen_npi(rng, 2),
            org_name=fake_org(),
            fein=f"{rng.randint(10,99)}-{rng.randint(1000000,9999999)}",
            address1=addr, city=city, state=state, zip=zipc, phone=fake_phone()
        )
        orgs.append(org)

        n_pract = rng.randint(args.practices_min, args.practices_max)
        for _p in range(n_pract):
            practice_id = str(uuid.uuid4())
            p_addr, p_city, p_state, p_zip = fake_addr()
            pr = Practice(
                practice_id=practice_id, org_id=org_id,
                location_id=rand_digits(rng, 8),
                practice_name=f"{org.org_name.split()[0]} Clinic",
                address1=p_addr, city=p_city, state=p_state, zip=p_zip,
                phone=fake_phone(), hours=random_hours(rng)
            )
            practices.append(pr)

            n_prov = rng.randint(args.providers_min, args.providers_max)
            for _r in range(n_prov):
                prov_id = str(uuid.uuid4())
                nm = fake_name().split()
                first, last = nm[0], nm[-1]
                tax1, spec1 = rng.choice(SPECIALTIES)
                sec = rng.choice([None, None, None, rng.choice(SPECIALTIES)[1]])
                lang_sample = rng.sample(["English","Spanish","Mandarin","Korean","Vietnamese","Russian","Arabic","French"], rng.randint(1,3))
                lic_state = rng.choice(STATES)
                status = random.choices(["Active","On Leave","Termed"], weights=[0.82,0.06,0.12], k=1)[0]

                prov = Provider(
                    provider_id=prov_id, npi=gen_npi(rng, 1),
                    first_name=first, last_name=last,
                    gender=rng.choice(["male","female","nonbinary","unspecified"]),
                    degree=rng.choice(["MD","DO","PA","NP","PhD"]),
                    primary_taxonomy_code=tax1, primary_specialty=spec1,
                    secondary_specialty=sec,
                    email=fake_email(first, last),
                    license_state=lic_state, license_number=f"{lic_state}-{rand_digits(rng,6)}",
                    accepts_new_patients=bool(rng.getrandbits(1)),
                    languages=";".join(lang_sample),
                    status=status
                )
                providers.append(prov)

                # affiliation
                start = date_between(rng)
                end = None
                if status == "Termed" and rng.random() < 0.8:
                    t = start + timedelta(days=rng.randint(200, 1600))
                    end = min(t, date.today()).isoformat()
                affils.append(Affiliation(prov_id, practice_id, start.isoformat(), end))

                # network participation
                for nw in networks:
                    panel = random.choices(["Open","Closed","Limited"], weights=[0.6,0.25,0.15], k=1)[0]
                    eff = date_between(rng)
                    term = None
                    if status == "Termed" and rng.random() < 0.7:
                        t = eff + timedelta(days=rng.randint(180, 1400))
                        term = t.isoformat() if t <= date.today() else None
                    net_parts.append(NetworkParticipation(
                        provider_id=prov_id, practice_id=practice_id, network_id=nw.network_id,
                        panel_status=panel, effective_date=eff.isoformat(), termination_date=term
                    ))

    def to_df(objs, cols): return pd.DataFrame([asdict(o) for o in objs])[cols]

    files = {
        "networks.csv": to_df(networks, ["network_id","mco_name","network_name"]),
        "organizations.csv": to_df(orgs, ["org_id","org_npi","org_name","fein","address1","city","state","zip","phone"]),
        "practices.csv": to_df(practices, ["practice_id","org_id","location_id","practice_name","address1","city","state","zip","phone","hours"]),
        "providers.csv": to_df(providers, ["provider_id","npi","first_name","last_name","gender","degree","primary_taxonomy_code","primary_specialty","secondary_specialty","email","license_state","license_number","accepts_new_patients","languages","status"]),
        "affiliations.csv": to_df(affils, ["provider_id","practice_id","start_date","end_date"]),
        "network_participation.csv": to_df(net_parts, ["provider_id","practice_id","network_id","panel_status","effective_date","termination_date"]),
    }

    for name, df in files.items():
        df.to_csv(os.path.join(args.out, name), index=False)

    # emit flattened NDJSON
    org_map = files["organizations.csv"].set_index("org_id").to_dict(orient="index")
    pract_map = files["practices.csv"].set_index("practice_id").to_dict(orient="index")
    prov_map = files["providers.csv"].set_index("provider_id").to_dict(orient="index")
    nets = files["networks.csv"].to_dict(orient="records")
    net_map = {n["network_id"]: n for n in nets}

    with open(os.path.join(args.out, "provider_directory_flat.ndjson"), "w", encoding="utf-8") as f:
        for np_row in files["network_participation.csv"].to_dict(orient="records"):
            prov = prov_map[np_row["provider_id"]]
            prac = pract_map[np_row["practice_id"]]
            org = org_map[prac["org_id"]]
            net = net_map[np_row["network_id"]]
            rec = {
                "mco": net["mco_name"],
                "network": net["network_name"],
                "network_id": net["network_id"],
                "organization": {
                    "org_id": org["org_id"],
                    "org_name": org["org_name"],
                    "org_npi": org["org_npi"],
                    "fein": org["fein"],
                },
                "practice": {
                    "practice_id": prac["practice_id"],
                    "practice_name": prac["practice_name"],
                    "location_id": prac["location_id"],
                    "address": {
                        "address1": prac["address1"], "city": prac["city"],
                        "state": prac["state"], "zip": prac["zip"], "phone": prac["phone"]
                    },
                    "hours": prac["hours"]
                },
                "provider": {
                    "provider_id": prov["provider_id"],
                    "npi": prov["npi"],
                    "name": f"{prov['first_name']} {prov['last_name']}",
                    "degree": prov["degree"],
                    "gender": prov["gender"],
                    "email": prov["email"],
                    "taxonomy": prov["primary_taxonomy_code"],
                    "specialties": [prov["primary_specialty"]] + ([prov["secondary_specialty"]] if prov["secondary_specialty"] else []),
                    "license": {"state": prov["license_state"], "number": prov["license_number"]},
                    "accepts_new_patients": bool(prov["accepts_new_patients"]),
                    "languages": str(prov["languages"]).split(";"),
                    "status": prov["status"]
                },
                "panel": {
                    "status": np_row["panel_status"],
                    "effective_date": np_row["effective_date"],
                    "termination_date": np_row["termination_date"]
                }
            }
            f.write(json.dumps(rec) + "\n")

    print(f"Wrote {len(files)} files + NDJSON to: {args.out}")

if __name__ == "__main__":
    main()


⸻

k8s/kafka/values.yaml

This is the same config we discussed: SASL + TLS (SASL_SSL), internal/external listeners, and a single secret kafka-sasl. Replace kafka.mycorp.example.com with your real DNS.

# Kafka (Bitnami) with SASL + TLS and external access
# Namespace assumed: ems-core

controller:
  replicaCount: 3
broker:
  replicaCount: 3

listeners:
  client:
    name: CLIENT
    containerPort: 9092
    protocol: SASL_SSL
  controller:
    name: CONTROLLER
    containerPort: 9093
    protocol: SASL_PLAINTEXT
  interbroker:
    name: INTERNAL
    containerPort: 9094
    protocol: SASL_PLAINTEXT
  external:
    name: EXTERNAL
    containerPort: 9095
    protocol: SASL_SSL

  securityProtocolMap: "CONTROLLER:SASL_PLAINTEXT,INTERNAL:SASL_PLAINTEXT,CLIENT:SASL_SSL,EXTERNAL:SASL_SSL"

  # Adjust to your environment:
  overrideListeners: ""
  advertisedListeners: >
    CLIENT://kafka.ems-core.svc.cluster.local:9092,
    INTERNAL://kafka-internal.ems-core.svc.cluster.local:9094,
    EXTERNAL://kafka.mycorp.example.com:443

sasl:
  enabledMechanisms: "PLAIN"
  interBrokerMechanism: "PLAIN"
  controllerMechanism: "PLAIN"

  client:
    users:
      - ems_app
      - ops_tooling
    passwords: ""  # from existingSecret
  existingSecret: kafka-sasl

  interbroker:
    user: inter_broker_user
    password: ""  # from existingSecret
  controller:
    user: controller_user
    password: ""  # from existingSecret

tls:
  type: PEM
  autoGenerated:
    enabled: true
    engine: helm
    customAltNames:
      - kafka.ems-core.svc.cluster.local
      - kafka-internal.ems-core.svc.cluster.local
      - kafka.mycorp.example.com

controller:
  logPersistence:
    enabled: true
    size: 20Gi
broker:
  logPersistence:
    enabled: true
    size: 100Gi

controller:
  resourcesPreset: "small"
broker:
  resourcesPreset: "medium"

metrics:
  jmx:
    enabled: true
  kafka:
    enabled: true


⸻

k8s/kafka/create_namespace.sh

#!/usr/bin/env bash
set -euo pipefail
NS="ems-core"

if ! kubectl get ns "${NS}" >/dev/null 2>&1; then
  kubectl create namespace "${NS}"
else
  echo "Namespace ${NS} already exists."
fi


⸻

k8s/kafka/create_kafka_secret.sh

#!/usr/bin/env bash
set -euo pipefail
NS="ems-core"
SECRET="kafka-sasl"

# EDIT THESE: supply strong secrets or pass as env vars before running
CLIENT_PASSWORDS="${CLIENT_PASSWORDS:-EMS_APP_PASSWORD,OPS_TOOLING_PASSWORD}"
INTER_BROKER_PASSWORD="${INTER_BROKER_PASSWORD:-INTER_BROKER_PASSWORD}"
CONTROLLER_PASSWORD="${CONTROLLER_PASSWORD:-CONTROLLER_PASSWORD}"

if kubectl -n "${NS}" get secret "${SECRET}" >/dev/null 2>&1; then
  echo "Secret ${SECRET} exists in ${NS}. Patching..."
  kubectl -n "${NS}" delete secret "${SECRET}"
fi

kubectl -n "${NS}" create secret generic "${SECRET}" \
  --from-literal=client-passwords="${CLIENT_PASSWORDS}" \
  --from-literal=inter-broker-password="${INTER_BROKER_PASSWORD}" \
  --from-literal=controller-password="${CONTROLLER_PASSWORD}"

echo "Created secret ${SECRET} in ${NS}."


⸻

k8s/kafka/install_kafka.sh

#!/usr/bin/env bash
set -euo pipefail
NS="ems-core"
RELEASE="kafka"
CHART="bitnami/kafka"

helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm upgrade --install "${RELEASE}" "${CHART}" \
  --namespace "${NS}" \
  -f values.yaml


⸻

# ToDo	•	add a topic bootstrapper job (Kubernetes Job + kafka-topics.sh args)
# ToDo	•	add an example producer/consumer pod to validate SASL_SSL connectivity
# ToDo	•	add a tiny FastAPI microservice that publishes to your topics using these SASL settings

```zsh
mariadb --host serverless-eu-central-1.sysp0000.db1.skysql.com --port 4026 --user dbpwf04095684 -p --ssl-verify-server-cert
Enter password:
```
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MySQL connection id is 442
Server version: 10.4.32 21.06.17-maxscale MariaDB Server

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MySQL [(none)]> 


# _Use Case: FHIR-to-OMOP Mini Agent_ 

_A **self-contained mini demo** of FHIR, OMOP, and OpenSearch capacity._ 

---

Implementing dbt models and automation pipelines requires:
1. Building standardized transformations (e.g., FHIR → OMOP mappings, deduplication, normalization).
1. Running those transformations automatically as new payloads arrives.
1. Testing and documenting each step for traceability and reproducibility.
1. Scaling that logic to multiple sites or datasets safely.
#

### _PROJECT STRUCTURE_
```text


















                ┌───────────────────────────────────────────┐
                │              Helm (Umbrella)              │
                │-------------------------------------------│
                │  Deploys:                                 │
                │   • Kafka / Zookeeper                     │
                │   • OpenSearch                             │
                │   • Neo4j                                  │
                │   • Wolfram Scorer (FastAPI microservice)  │
                │   • Indexer (Kafka → OpenSearch)           │
                │   • Upserter (Kafka → Neo4j)               │
                └───────────────────────────────────────────┘
                                │
                                │  (via Helm → K8s API)
                                ▼
            ┌────────────────────────────────────────────┐
            │          Kubernetes (Colima cluster)       │
            │--------------------------------------------│
            │ Namespace: ems-core                        │
            │                                            │
            │  ┌─────────────────────────────────────┐   │
            │  │ Kafka Broker                         │◄────┐
            │  │  Topics:                              │     │
            │  │   - ems.licensing.events→compliance   │     │
            │  │   - ems.encounter.metadata→analytics   │     │
            │  │   - ...                               │     │
            │  └─────────────────────────────────────┘   │
            │                 ▲                          │
            │                 │  (JSON events)            │
            │                 │                          │
            │  ┌─────────────────────────────────────┐   │
            │  │ Seed Job (Python/Faker)             │───┘
            │  │  Generates 1,000 Providers &        │
            │  │  Streams Events into Kafka          │
            │  └─────────────────────────────────────┘
            │
            │  ┌─────────────────────────────────────┐
            │  │ Event Indexer (Python)              │
            │  │  Consumes Kafka → Indexes in        │
            │  │  OpenSearch (time-series index)     │
            │  └─────────────────────────────────────┘
            │
            │  ┌─────────────────────────────────────┐
            │  │ Graph Upserter (Python)             │
            │  │  Consumes Kafka → Upserts nodes &   │
            │  │  relationships in Neo4j             │
            │  └─────────────────────────────────────┘
            │
            │  ┌─────────────────────────────────────┐
            │  │ Wolfram Scorer (FastAPI)            │
            │  │  REST: POST /score → risk_score     │
            │  │  (Future: call Mathematica kernel)  │
            │  └─────────────────────────────────────┘
            │
            │  ┌─────────────────────────────────────┐
            │  │ OpenSearch                          │
            │  │  Indexes events-* (daily pattern)   │
            │  │  Query: _cat/indices                │
            │  └─────────────────────────────────────┘
            │
            │  ┌─────────────────────────────────────┐
            │  │ Neo4j                               │
            │  │  Graph: Provider→License→Agency      │
            │  │  Query: MATCH (p)-[:HOLDS]->(l)     │
            │  └─────────────────────────────────────┘
            └────────────────────────────────────────────┘
                                ▲
                                │
                                │ (kubectl / helm CLI)
                                │
                     ┌────────────────────────────┐
                     │     macOS / Colima host    │
                     │     PyCharm + .venv        │
                     │     Helm / kubectl / Colima│
                     └────────────────────────────┘

skunkworks/
├── Chart.yaml                         # ← Umbrella Helm chart (root, not inside indexer/)
├── values.yaml                        # Global defaults (OpenSearch, Neo4j, Kafka, etc.)
├── docker-compose.yml                 # Local all-in-one demo
├── README.md
│
├── charts/                            # Individual Helm subcharts (K8s deployables)
│   └── kafka/
│       ├── Chart.yaml               ← helm metadata and k8s for orchestration, microservices: event-driven architecture inside kube  
│       ├── values.yaml              ← configuration for Bitnami Kafka + SASL, helm k8s (chart dir) for apache
│       └── templates/               ← guidance
│           ├── deployment.yaml      ← StatefulSet for Kafka broker
│           ├── service.yaml         ← Internal ClusterIP Kafka service
│           └── kafka-deployment.yaml
│   ├── opensearch/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       └── opensearch-deployment.yaml
│   ├── neo4j/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       └── neo4j-statefulset.yaml
│   ├── wolfram-scorer/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       └── deployment.yaml
│   ├── indexer/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   │       └── deployment.yaml
│   └── upserter/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           └── deployment.yaml
│
├── services/
│   ├── opensearch_indexer/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── indexer.py                 # Consumes Kafka → indexes JSON to OpenSearch
│   ├── neo4j_upserter/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── upserter.py                # Consumes Kafka → Cypher MERGE into Neo4j
│   └── wolfram_scorer/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── app.py                     # Flask microservice → Wolfram risk scoring
│
├── payloads/
│   ├── providers_seed.json            # Generated synthetic provider directory
│   ├── hb_demo.json                   # Hanna-Barbera toy dataset
│   └── index_template.json            # OpenSearch mapping / template
│
├── tools/
│   ├── siUtils_seed_providers.py              # Faker-based generator + Kafka producer
│   ├── load_demo.py                # Small loader for cartoon cohort
│   └── setup_topics.py                # Create Kafka topics programmatically
│
├── notebooks/
│   ├── analytics_demo.ipynb           # OpenSearch + Neo4j query demo notebook
│   └── risk_dashboard.ipynb           # Wolfram scoring visualization
│
├── config/
│   ├── kafka_topics.yaml              # List of topics → compliance, analytics, ops
│   ├── logging.yaml                   # Shared logging config
│   └── env.example                    # Example env vars for local run
│
└── docs/
    ├── architecture.md                # Stack overview + dataflow diagram
    ├── api_endpoints.md               # REST endpoints (Wolfram scorer, etc.)
    └── helm_deploy.md                 # K8s deployment guide
├── logs/                            ← logging  
├── utils/                           ← mini utilities for semantic interoperability  
│   ├── logging_config.py            ← logging configuration as a json dictionary
│   ├── siUtils_gen_bulk_heavy.py    ← convert complex json files to ndjson (handles NaNs, Inf, text, etc.)
│   ├── siUtils_gen_bulk_lite.py     ← convert simple json files to ndjson (handles text and ints only)
│   ├── siUtils_git_init.sh          ← initialize git repository to use .git/ as file walk anchorpoint
│   ├── siUtils_markdown_maker.py    ← converts voc data dictionary into reader-friendly markdown
│   ├── siUtils_toc_generator.py     ← mini module that creates table of contents from url-friendly slugs
│   ├── siUtils_slugify.py           ← mini module that creates url-friendly slugs from headers
│   ├── siUtils_table_maker.py       ← converts voc data dictionary into reader-friendly tables for cutting, pasting and markdown
│   └── siUtils_snakeify.sh          ← .zsh only: apply snakecase to repo filenames (except my siUtils, hidden, docker, helm, k8s) 
├── .gitignore                       ← tells git which entities to ignore
├── .requirements                    ← python package index dependencies  
├── opensearch_demo.py               ← python script creates an index, ingests the NDJSON, and runs sample queries
├── docker-compose.opensearch.yml    ← local OpenSearch + dashboards for quick demo.
├── LICENSE.md                       ← software licensing info
└── README.md                        ← app repository standard reference 





```

## _Quickstart_
> Prereqs: Docker + Python 3.10+, `pip install opensearch-py==2.*`
> # HealthTree Demo: Provider Directory + Kafka (Helm)
>
This repo contains:
- A **synthetic MCO-style provider directory** generator (`provider_directory/generate_provider_directory.py`)
- A **Kafka Helm deployment** (Bitnami chart) configured for **SASL + TLS** with external access.


### _1) GENERATE SYNTHETIC PROVIDER DIRECTORY_
```bash
cd provider_directory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python generate_provider_directory.py --out ./out --seed 42
ls -1 ./out


### _1) START OPEN SEARCH LOCALLY FROM SHELL_
```ZSH
docker compose -f docker-compose.mini-demo.yml up -d
# wait ~10-20s for green health
```

Open Dashboards at http://localhost:5601 (no auth, dev-only).

### 2) _RUN THE PYTHON DEMO_
```bash
# bash
python3 start_demo.py
```

Expected output includes:
- index creation
- bulk ingest count
- sample query results
- facet counts (series/species)

### _3) EXPLORE IN DASHBOARDS_
- Create an index pattern: `hb_characters`
- Build a data table showing counts by `series` and `species`
- Try filters: `species: "human"` and add a range filter on `appearances >= 50`

### _NOTES_
- Security is disabled in Docker for simplicity **(demo only)**. For a real deployment, enable SSL/TLS and auth.
- You can override env vars for the Python script: `OS_HOST`, `OS_PORT`, `OS_USER`, `OS_PASS`, `HB_INDEX`, `HB_BULK_FILE`.

#### _TALKING POINTS_
- **Mapping choices**: `keyword` with `lc_keyword` normalizer for case-insensitive faceting; `text`+`keyword` for `character` to support both search and exact sort.
- **Bulk ingestion** using `helpers.bulk` from `opensearch-py`.
- **Faceting/aggregations**: series/species examples; can add `age`, `gender`, etc.
- **Scaling**: raise shards/replicas; enable security; move to managed OpenSearch with snapshots; index templates + ILM for real data.
- **Extensibility**: add analyzers for multilingual data; add vector fields for semantic search; use ingestion pipelines for data cleanup.
- **Electronic Medical Records (EMRs)** are observational data sources.
- They record what actually happened in clinical practice, not what was dictated by a research protocol.


#### _WHY THEY’RE CONSIDERED OBSERVATIONAL_

Category	EMR	Experimental (e.g., RCT)
Data origin	Captured during routine clinical care	Collected under controlled conditions
Purpose	Clinical documentation, billing, compliance	Research question testing
Control over variables	None — physicians act independently	High — study protocol dictates treatment
Causality	Inferred retrospectively (observational)	Assigned prospectively (experimental)
Data structure	Event-driven (visits, labs, vitals, notes)	Protocol-driven (cohorts, endpoints)

Because EMR data are not randomized, not standardized in collection timing, and often biased by real-world workflows, they fall under the observational category of biomedical data — alongside registries, claims data, and health information exchanges.

### _REFERENCES_
⸻


If you’re transforming EMR data into a research or analytic environment (e.g. OMOP CDM, NEMSIS, or FHIR → OMOP conversions):
	•	You’re working with observational databases that can support retrospective studies, quality improvement, or causal inference (with appropriate statistical adjustments like propensity scores, etc.).
	•	But they are not clinical trial databases — they observe, not assign, interventions.

⸻

Would you like me to show how an EMR dataset maps into the OMOP “observation” and “condition_occurrence” tables to illustrate this distinction concretely?