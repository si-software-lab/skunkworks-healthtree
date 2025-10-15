from kafka.admin import KafkaAdminClient, NewTopic
import os

bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
topics = [
  "ems.licensing.events→compliance",
  "ems.encounter.metadata→analytics",
  "ems.transport.status→dash",
  "ems.sanctions.events→compliance",
  "ems.vehicle.status→ops"
]

admin = KafkaAdminClient(bootstrap_servers=bootstrap, client_id="topic-setup")
existing = set(t if isinstance(t, str) else t.topic for t in admin.list_topics())
new = [NewTopic(name=t, num_partitions=1, replication_factor=1) for t in topics if t not in existing]

if new:
    admin.create_topics(new)
    print(f"Created: {[t.name for t in new]}")
else:
    print("All topics already exist.")
