# I. FHIR US Core → OMOP Agent (FastAPI)
### _TABLE OF CONTENTS_
ToDo
#
### _PROJECT DESCRIPTION_ 
Minimal, extensible agent that maps a subset of US Core resources (Patient, Observation, Condition)
into OMOP tables (PERSON, MEASUREMENT, CONDITION_OCCURRENCE)_.
#
### _QUICKSTART_

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite:///./omop.db"  # or any SQLAlchemy URL (e.g., postgresql+psycopg2://user:pass@host/db)
uvicorn main:app --reload
```
#
### _SMOKE TEST (NEW TERMINAL)_

```bash
curl -s http://localhost:8000/health

curl -s -X POST http://localhost:8000/transform \
  -H "Content-Type: application/json" \
  --refs @sample_payloads/patient_uscore.json | jq .

curl -s -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  --refs '[{
    "resourceType":"Patient","id":"pat-001","gender":"male","birthDate":"1977-04-15"
  }, {
    "resourceType":"Observation","id":"obs-001","status":"final",
    "category":[{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/observation-category","code":"vital-signs"}]}],
    "code":{"coding":[{"system":"http://loinc.org","code":"85354-9"}]},
    "subject":{"refs":"Patient/pat-001"},
    "effectiveDateTime":"2023-10-21T12:34:56Z",
    "valueQuantity":{"value":120,"unit":"mmHg","code":"mm[Hg]"}
  }, {
    "resourceType":"Condition","id":"cond-001",
    "code":{"coding":[{"system":"http://snomed.info/sct","code":"44054006"}]},
    "subject":{"refs":"Patient/pat-001"},
    "onsetDateTime":"2015-01-01"
  }]'

curl -s http://localhost:8000/export/person | jq .
curl -s http://localhost:8000/export/measurement | jq .
curl -s http://localhost:8000/export/condition_occurrence | jq .
```

### HOW THIS IS AN "AGENT"

- **Planner**: chooses the OMOP table(s) per resource by matching `resourceType` and optional `match` filter.
- **Executor**: applies rule-based field transforms (`rules`) defined in `mapping_uscore_to_omop.json`.
- **Skills**: simple built-ins for gender/LOINC/SNOMED/UCUM and date parsing. Replace these with vocabulary services.

## NEXT STEPS (DROP-IN UPGRADES)

- Replace stub concept mappers with your vocab store (Athena/CPT/LOINC tables).
- Add Encounter, Procedure, MedicationRequest/Administration, Device, Immunization, etc.
- Implement ID strategy (surrogate sequences) matching your OMOP instance policy.
- Enforce US Core profiles with pydantic models or `fhir.resources`.
- Batch ingestion from NDJSON or FHIR server (Bulk Data $export).
- Add provenance logging and error DLQ (Kafka) if needed.



# _II. APPENDIX_
## _DEVELOPER NOTES_
### IPLL: IP Location (IP LL or IP Location Lookup)
IP Location (IP LL or IP Location Lookup)
IP Location Lookup, or IP LL, is a technique used to determine the geographic location of an internet user based on their IP address. It is widely used in cybersecurity and network management for various purposes. 
- In the context of infosec, IP Location data is critical for: 
  -[ ] Threat intelligence: Identifying the origin of malicious network traffic.
  -[ ] Fraud detection: Flagging suspicious login attempts or transactions coming from unexpected locations.
  -[ ] Geo-blocking: Restricting or allowing access to services based on the user's geographic region.
  -[ ] Digital forensics: Investigating cybercrime by tracing the IP address of an attacker. 

- Other less common meanings in technology 
The acronym "IPL" can also stand for other technical terms, though they are less common in the infosec field:
  International Private Line: A secure, point-to-point network circuit used to connect offices in different countries. It is used to securely transfer sensitive data and offers high reliability and dedicated bandwidth.
  Initial Program Load: The process of booting or rebooting a computer, particularly a mainframe, by loading the operating system into memory.
  Instruction-level parallelism: A computer architecture concept related to the parallel execution of multiple instructions. 


healthtree-demo/
├─ README.md
├─ .gitignore
├─ provider_directory/
│  ├─ requirements.txt
│  └─ generate_provider_directory.py
└─ k8s/
   └─ kafka/
      ├─ values.yaml
      ├─ create_namespace.sh
      ├─ create_kafka_secret.sh
      └─ install_kafka.sh