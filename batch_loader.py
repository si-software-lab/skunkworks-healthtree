#!/usr/bin/env python3
"""
Public Health Data Interoperability Demo —
colima
docker
python
opensearch
kafka streaming event service
mariaDB cloud to/from pathways
neo4j bolt-on analytics
wolfram counterfactual console
demo ai agent (task/event handler)
demo ai llm

Features:
- ASCII text console banner (always prints)
- Author metadata (handles flat and nested shapes)
- OpenSearch client with preflight auto-detect: HTTP/HTTPS + cert handling
- Optional Neo4j enrichment
- Optional MariaDB/MySQL persistence
- Optional Kafka HB loader (flag: --load-hb)

Env (common):
  AUTHOR_JSON           : path to author JSON (optional)
  REPORT_TITLE          : override title (optional)

OpenSearch (you can omit USE_SSL/VERIFY_CERTS; autodetect will pick):
  OS_HOST, OS_PORT, OS_USER, OS_PASS
  USE_SSL=true|false        (explicit override; otherwise auto)
  VERIFY_CERTS=true|false   (explicit override; otherwise auto)
  OS_TIMEOUT                (default 30)
  OS_DEMO_INDEX             (default vi_demo)

Neo4j (optional):
  NEO4J_URI, NEO4J_USER, NEO4J_PASS

MariaDB/MySQL (optional):
  MDB_HOST, MDB_PORT, MDB_USER, MDB_PASS, MDB_DB
"""

from __future__ import annotations
import os
import sys
import json
import time
import argparse
import logging
import logging.config
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ---------- kafka (optional) ----------
try:
    # provided by kafka-python-ng
    from kafka import KafkaProducer  # type: ignore
except Exception:
    KafkaProducer = None  # type: ignore

# ---------- banner ----------
try:
    import pyfiglet  # type: ignore
except ModuleNotFoundError:
    pyfiglet = None  # type: ignore

try:
    from colorama import Fore, Style, init as colorama_init  # type: ignore
    colorama_init(autoreset=True)
except ModuleNotFoundError:
    class _DummyFore:
        CYAN = GREEN = MAGENTA = YELLOW = RED = BLUE = WHITE = ""
    class _DummyStyle:
        BRIGHT = NORMAL = RESET_ALL = ""
    Fore = _DummyFore()
    Style = _DummyStyle()

# ---------- Requests for preflight ----------
try:
    import requests  # type: ignore
except ModuleNotFoundError:
    requests = None  # preflight will degrade gracefully

# ---------- OpenSearch ----------
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection, helpers  # type: ignore
except ModuleNotFoundError:
    OpenSearch = None  # type: ignore
    RequestsHttpConnection = None  # type: ignore
    helpers = None  # type: ignore

# ---------- Neo4j (optional) ----------
try:
    from neo4j import GraphDatabase  # type: ignore
except ModuleNotFoundError:
    GraphDatabase = None  # type: ignore

# ---------- MariaDB / MySQL (optional) ----------
_mariadb_mod = None
_mysql_mod = None
try:
    import mariadb as _mariadb_mod  # type: ignore
except ModuleNotFoundError:
    try:
        import mysql.connector as _mysql_mod  # type: ignore
    except ModuleNotFoundError:
        pass


# =============================================================================
# Logging
# =============================================================================

def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=level, format=fmt, datefmt=datefmt)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("opensearchpy").setLevel(logging.INFO)


# =============================================================================
# Author metadata + Banner
# =============================================================================

@dataclass
class Author:
    name: str = "Unknown Author"
    credential: Optional[str] = None
    affiliation: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None

    def display_line(self) -> str:
        cred = f", {self.credential}" if self.credential else ""
        ttl = f" — {self.title}" if self.title else ""
        aff = f" | {self.affiliation}" if self.affiliation else ""
        cmpy = f" @ {self.company}" if self.company else ""
        return f"{self.name}{cred}{ttl}{aff}{cmpy}"


def _coalesce_flat_or_nested(d: Dict[str, Any]) -> Tuple[str, Author]:
    """
    Handles three shapes:
    A) Flat keys:
       {"report title": "...", "author name": "Jane Doe", ...}
    B) Nested by author name:
       {"Jane Doe": {"author credential": "...", ...}, "report title": "..."}
    C) Nested under "author name":
       {"author name": {"Jane Doe": {...}}}
    """
    report_title = os.getenv("REPORT_TITLE") or d.get("report title") or "vi Demo"

    # Case A: simple flat
    flat_name = d.get("author name")
    if isinstance(flat_name, str):
        author = Author(
            name=flat_name,
            credential=d.get("author credential"),
            affiliation=d.get("author affiliation"),
            title=d.get("author title"),
            company=d.get("author company name"),
            address=d.get("author address"),
        )
        return report_title, author

    # Case C: nested under "author name"
    if isinstance(flat_name, dict):
        first_key = next(iter(flat_name.keys()), None)
        if first_key:
            sub = flat_name[first_key] or {}
            credential = sub.get("author credential")
            author = Author(
                name=f"{first_key}{', ' + credential if credential else ''}",
                credential=credential,
                affiliation=sub.get("author affiliation"),
                title=sub.get("author title"),
                company=sub.get("author company name"),
                address=sub.get("author address"),
            )
            return report_title, author

    # Case B: nested directly by author name at top level
    known = {"report title", "author name", "author credential", "author affiliation",
             "author title", "author company name", "author address"}
    nested_candidates = [k for k in d if k not in known and isinstance(d[k], dict)]
    if nested_candidates:
        display_name = nested_candidates[0]
        sub = d[display_name] or {}
        credential = sub.get("author credential")
        author = Author(
            name=f"{display_name}{', ' + credential if credential else ''}",
            credential=credential,
            affiliation=sub.get("author affiliation"),
            title=sub.get("author title"),
            company=sub.get("author company name"),
            address=sub.get("author address"),
        )
        return report_title, author

    # Fallback
    return report_title, Author(name="vi Team")


def load_author_metadata(path: Optional[str]) -> Tuple[str, Author]:
    # No logging here—banner prints before log setup.
    if not path:
        return "vi Demo", Author(name="vi Team")

    p = Path(path)
    if not p.exists():
        return "vi Demo", Author(name="vi Team")

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return _coalesce_flat_or_nested(data)
    except Exception:
        return "vi Demo", Author(name="vi Team")


def render_banner(report_title: str, author: Author) -> str:
    if pyfiglet:
        try:
            title_line = pyfiglet.Figlet(font="slant").renderText(report_title)
        except Exception:
            title_line = report_title
    else:
        title_line = report_title

    lines = [
        f"{Fore.CYAN}{Style.BRIGHT}{title_line}{Style.RESET_ALL}",
        f"{Fore.GREEN}{author.display_line()}{Style.RESET_ALL}",
        f"{Fore.MAGENTA}{author.address or ''}{Style.RESET_ALL}",
        f"{Fore.YELLOW}Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}",
    ]
    return "\n".join([ln for ln in lines if ln.strip()])


# =============================================================================
# Kafka HB demo loader (optional)
# =============================================================================

def load_demo():
    """Optionally load Hanna-Barbera events into Kafka."""
    if KafkaProducer is None:
        print("KafkaProducer not installed; skipping HB demo load.")
        return None, None

    BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        producer = KafkaProducer(
            bootstrap_servers=BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            linger_ms=50,
            acks="all",
        )
    except Exception as e:
        print(f"Kafka unavailable at {BOOTSTRAP}: {e}. Skipping HB demo load.")
        return BOOTSTRAP, None

    hb_path = Path("payloads/hb_demo.json")
    if not hb_path.exists():
        print("payloads/hb_demo.json not found; skipping HB demo load.")
        return BOOTSTRAP, producer

    with hb_path.open() as f:
        hb = json.load(f)

    # ASCII topic name (no Unicode arrows)
    topic = "ems.licensing.events.compliance"
    for series, chars in hb.items():
        for name, a in chars.items():
            evt = {
                "event_id": f"hb-{series}-{name}",
                "type": "license_update",
                "provider_id": f"hb-{name}",
                "license_status": "active"
            }
            producer.send(topic, evt)
    producer.flush()
    print("Loaded HB demo events.")
    return BOOTSTRAP, producer


# =============================================================================
# CLI
# =============================================================================

def parse_args():
    p = argparse.ArgumentParser(description="vi Demo")
    p.add_argument("--load-hb", action="store_true",
                   help="Load Hanna-Barbera demo events to Kafka (optional)")
    return p.parse_args()


# =============================================================================
# OpenSearch Preflight + Client
# =============================================================================

def _env_bool(name: str) -> Optional[bool]:
    v = os.getenv(name)
    if v is None:
        return None
    return v.strip().lower() in ("1", "true", "yes", "on")


def _is_localhost(host: str) -> bool:
    return host in ("localhost", "127.0.0.1", "::1")


def os_config_base() -> Dict[str, Any]:
    return {
        "host": os.getenv("OS_HOST", "localhost"),
        "port": int(os.getenv("OS_PORT", "9200")),
        "user": os.getenv("OS_USER", "admin"),
        "password": os.getenv("OS_PASS", "admin"),
        "timeout": int(os.getenv("OS_TIMEOUT", "30")),
    }


def preflight_detect_scheme(host: str, port: int, explicit_ssl: Optional[bool], explicit_verify: Optional[bool],
                            retries: int = 3, sleep_s: float = 0.7) -> Tuple[bool, bool]:
    """
    Decide (use_ssl, verify_certs). Respects explicit overrides if provided.
    Otherwise:
      - Try HTTP first for localhost, else try HTTPS first.
      - Fall back to the other scheme.
      - For HTTPS: if verify=True fails with SSLError but verify=False succeeds, use verify=False.
    """
    log = logging.getLogger("opensearch.preflight")

    if explicit_ssl is not None:
        # Honor explicit choice; default verify to True when SSL unless explicit_verify provided
        use_ssl = explicit_ssl
        verify_certs = explicit_verify if explicit_verify is not None else (True if use_ssl else False)
        log.info("Using explicit SSL settings: use_ssl=%s, verify_certs=%s", use_ssl, verify_certs)
        return use_ssl, verify_certs

    if requests is None:
        # No requests lib: simple heuristic
        use_ssl = not _is_localhost(host)
        verify_certs = use_ssl
        return use_ssl, verify_certs

    def _try(url: str, verify: bool) -> bool:
        try:
            r = requests.get(url, timeout=2.0, verify=verify, headers={"Accept": "application/json"})
            if r.status_code < 500:
                return True
        except requests.exceptions.SSLError:
            return False
        except Exception:
            return False
        return False

    schemes = (("http", False), ("https", True))
    order = schemes if _is_localhost(host) else (("https", True), ("http", False))

    for _attempt in range(retries):
        for scheme, _ssl_flag in order:
            base = f"{scheme}://{host}:{port}/"
            if scheme == "http":
                if _try(base, verify=False):
                    log.info("Detected OpenSearch over HTTP at %s", base)
                    return False, False
            else:
                # Try with verify=True first
                if _try(base, verify=True):
                    log.info("Detected OpenSearch over HTTPS (verified) at %s", base)
                    return True, True
                # Then with verify=False
                if _try(base, verify=False):
                    log.info("Detected OpenSearch over HTTPS (insecure, verify_certs=False) at %s", base)
                    return True, False
        time.sleep(sleep_s)

    # Fallback heuristic if nothing answered
    use_ssl = not _is_localhost(host)
    verify_certs = use_ssl
    log.warning("Preflight could not confirm endpoint; falling back to use_ssl=%s verify_certs=%s",
                use_ssl, verify_certs)
    return use_ssl, verify_certs


def os_config() -> Dict[str, Any]:
    base = os_config_base()
    explicit_ssl = _env_bool("USE_SSL")
    explicit_verify = _env_bool("VERIFY_CERTS")
    use_ssl, verify_certs = preflight_detect_scheme(base["host"], base["port"], explicit_ssl, explicit_verify)
    return {
        **base,
        "use_ssl": use_ssl,
        "verify_certs": verify_certs,
    }


def os_client() -> "OpenSearch":
    if OpenSearch is None or RequestsHttpConnection is None:
        raise SystemExit("Missing 'opensearch-py'. Install:\n  pip install opensearch-py")
    cfg = os_config()
    try:
        c = OpenSearch(
            hosts=[{"host": cfg["host"], "port": cfg["port"]}],
            http_auth=(cfg["user"], cfg["password"]),
            use_ssl=cfg["use_ssl"],
            verify_certs=cfg["verify_certs"],
            connection_class=RequestsHttpConnection,
            timeout=cfg["timeout"],
        )
        c.info()
        return c
    except Exception as e:
        hint = ""
        if _is_localhost(cfg["host"]):
            hint = " (Hint: ensure the container is up and port is mapped. Try: docker ps; and curl http://localhost:9200/ or curl -k https://localhost:9200/)"
        raise RuntimeError(f"Failed OpenSearch connection: {e}{hint}") from e


def os_demo_index_and_search(client: "OpenSearch") -> List[Dict[str, Any]]:
    log = logging.getLogger("opensearch.demo")
    index = os.getenv("OS_DEMO_INDEX", "vi_demo")

    if not client.indices.exists(index=index):
        log.info("Creating index '%s'", index)
        client.indices.create(
            index=index,
            body={
                "settings": {"number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "title": {"type": "text"},
                        "category": {"type": "keyword"},
                        "timestamp": {"type": "date"},
                        "score": {"type": "float"},
                    }
                },
            },
        )

    doc_id = "demo-1"
    client.index(
        index=index,
        id=doc_id,
        body={
            "title": "Edge Analytics for EMS",
            "category": "ems",
            "timestamp": datetime.utcnow().isoformat(),
            "score": 0.87,
        },
        refresh=True,
    )

    resp = client.search(
        index=index,
        size=5,
        body={"query": {"match": {"title": "EMS"}}, "sort": [{"timestamp": {"order": "desc"}}]},
    )
    hits = resp.get("hits", {}).get("hits", [])
    log.info("Search returned %d hits", len(hits))
    return hits


# =============================================================================
# Neo4j Bolt-on Analytics (Optional)
# =============================================================================

def neo4j_session():
    if GraphDatabase is None:
        logging.getLogger("neo4j").warning("neo4j not installed.")
        return None
    uri, user, pwd = os.getenv("NEO4J_URI"), os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASS")
    if not (uri and user and pwd):
        return None
    return GraphDatabase.driver(uri, auth=(user, pwd)).session()


def enhance_with_neo4j(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    log = logging.getLogger("neo4j.enhance")
    if not hits:
        return hits
    sess = neo4j_session()
    if not sess:
        return hits
    try:
        enhanced = []
        for h in hits:
            src = h.get("_source", {})
            title = src.get("title")
            cypher = """
            MATCH (t:Topic {name: $title})-[:BELONGS_TO]->(c:Cluster)
            RETURN c.name AS cluster, coalesce(t.rank, 0) AS rank
            LIMIT 1
            """
            res = sess.run(cypher, title=title).single()
            h["enrichment"] = {
                "neo_cluster": res.get("cluster") if res else None,
                "neo_rank": res.get("rank") if res else None,
            }
            enhanced.append(h)
        log.info("Neo4j enrichment applied to %d hits", len(enhanced))
        return enhanced
    except Exception as e:
        log.warning("Neo4j enrichment skipped: %s", e)
        return hits
    finally:
        try:
            sess.close()
        except Exception:
            pass


# =============================================================================
# MariaDB To/From
# =============================================================================

def mariadb_connect():
    log = logging.getLogger("mariadb")
    host, user, pwd, db = os.getenv("MDB_HOST"), os.getenv("MDB_USER"), os.getenv("MDB_PASS"), os.getenv("MDB_DB")
    port = int(os.getenv("MDB_PORT", "3306"))
    if not (host and user and pwd and db):
        return None
    try:
        if _mariadb_mod:
            c = _mariadb_mod.connect(host=host, user=user, password=pwd, database=db, port=port)
            log.info("Connected MariaDB %s:%s/%s", host, port, db)
            return c
        elif _mysql_mod:
            c = _mysql_mod.connect(host=host, user=user, password=pwd, database=db, port=port)
            log.info("Connected MySQL %s:%s/%s", host, port, db)
            return c
        else:
            log.warning("No MariaDB/MySQL driver.")
            return None
    except Exception as e:
        log.error("DB connect fail: %s", e)
        return None


def persist_hits_to_mariadb(conn, hits: List[Dict[str, Any]]) -> None:
    if not conn or not hits:
        return
    log = logging.getLogger("mariadb.persist")
    create = """
    CREATE TABLE IF NOT EXISTS os_hits (
        id VARCHAR(128) PRIMARY KEY,
        index_name VARCHAR(128),
        title TEXT,
        category VARCHAR(64),
        score FLOAT,
        neo_cluster VARCHAR(128),
        neo_rank FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    insert = """
    INSERT INTO os_hits (id, index_name, title, category, score, neo_cluster, neo_rank)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        title=VALUES(title), category=VALUES(category),
        score=VALUES(score), neo_cluster=VALUES(neo_cluster), neo_rank=VALUES(neo_rank);
    """
    try:
        cur = conn.cursor()
        cur.execute(create)
        rows = []
        for h in hits:
            src, enr = h.get("_source", {}), h.get("enrichment", {}) or {}
            rows.append((
                h.get("_id"), h.get("_index"),
                src.get("title"), src.get("category"), float(src.get("score") or 0),
                enr.get("neo_cluster"), float(enr.get("neo_rank") or 0)
            ))
        cur.executemany(insert, rows)
        conn.commit()
        log.info("Persisted %d hits", len(rows))
    except Exception as e:
        log.error("Persist fail: %s", e)
    finally:
        try:
            cur.close()
        except Exception:
            pass


# =============================================================================
# Main
# =============================================================================

def main_engine() -> None:
    # ---- Always print the banner FIRST (before any logs)
    author_json = os.getenv("AUTHOR_JSON", "payloads/author.json")
    title, author = load_author_metadata(author_json)
    print(render_banner(title, author))

    # ---- Now configure logging (logs appear after banner)
    setup_logging()
    log = logging.getLogger("main")

    args = parse_args()

    # OpenSearch
    try:
        os_cli = os_client()
        hits = os_demo_index_and_search(os_cli)
    except Exception as e:
        log.error("%s", e)
        sys.exit(2)

    # Neo4j enrichment (optional)
    hits = enhance_with_neo4j(hits)

    # MariaDB persistence (optional)
    db = mariadb_connect()
    if db:
        persist_hits_to_mariadb(db, hits)
        try:
            db.close()
        except Exception:
            pass

    # Optional: load HB events to Kafka (only when asked)
    if args.load_hb:
        print("Loading HB demo events to Kafka (optional step)…")
        load_demo()

    # print summary
    print(f"\n{Fore.BLUE}{Style.BRIGHT}Search Results (top {len(hits)}):{Style.RESET_ALL}")
    for i, h in enumerate(hits, 1):
        src, enr = h.get("_source", {}), h.get("enrichment", {}) or {}
        print(f" {i}. {src.get('title')} | category={src.get('category')} | score={src.get('score')}")
        if enr:
            print(f"    ↳ neo_cluster={enr.get('neo_cluster')} neo_rank={enr.get('neo_rank')}")
    print(f"\n{Fore.GREEN}Done.{Style.RESET_ALL}")


if __name__ in("__main__"):
    try:
        main_engine()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)