"""harness-memory — semantic + investigation memory MCP server.

One Postgres (pgvector) database, two layers:
  * memories  — semantic notes with embeddings, FTS, tags, supersede-on-update
  * entities/flows/investigations — structured fund-flow graph for chain forensics

Search is hybrid: vector + full-text merged with RRF, plus exact/prefix address
matching that pulls in the linked flow graph.
"""
import math
import re
import sys
from datetime import datetime, date
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from mcp.server.mcpserver import MCPServer

import harness_env as env
from embeddings import embed, DIM

DB_URL = env.get("MEMORY_DB_URL", "postgresql://harness:harness@127.0.0.1:5433/harness_memory")
SUPERSEDE_SIM = float(env.get("MEM_SUPERSEDE_SIM", "0.90"))

mcp = MCPServer("harness-memory")


def try_embed(text, kind="passage"):
    """None instead of raising: memory must stay usable (FTS + flow graph)
    when the embedding provider is unavailable."""
    try:
        return embed(text, kind)
    except Exception as e:
        print(f"[harness-memory] embeddings unavailable ({e}); degraded mode: FTS-only", file=sys.stderr)
        return None

# ── DB plumbing ──────────────────────────────────────────────────────────

_conn = None


def db():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg.connect(DB_URL, autocommit=True, row_factory=dict_row)
    return _conn


def q(sql, params=None):
    global _conn
    try:
        with db().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else []
    except psycopg.OperationalError:
        _conn = None
        with db().cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else []


SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS investigations (
  id BIGSERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS entities (
  id BIGSERIAL PRIMARY KEY,
  chain TEXT NOT NULL,
  address TEXT NOT NULL,
  label TEXT,
  entity_type TEXT NOT NULL DEFAULT 'unknown',
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (chain, address)
);
CREATE INDEX IF NOT EXISTS entities_addr_trgm ON entities USING gin (address gin_trgm_ops);

CREATE TABLE IF NOT EXISTS memories (
  id BIGSERIAL PRIMARY KEY,
  content TEXT NOT NULL,
  topic TEXT NOT NULL DEFAULT 'general',
  mtype TEXT NOT NULL DEFAULT 'note',
  project TEXT,
  tags TEXT[] NOT NULL DEFAULT '{}',
  investigation_id BIGINT REFERENCES investigations(id) ON DELETE SET NULL,
  embedding vector(__DIM__),
  tsv tsvector GENERATED ALWAYS AS (to_tsvector('russian', content)) STORED,
  superseded_by BIGINT REFERENCES memories(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS chain TEXT;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS track TEXT;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS branch TEXT;
CREATE INDEX IF NOT EXISTS memories_track ON memories (project, track);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS source TEXT;
CREATE INDEX IF NOT EXISTS memories_chain ON memories (chain);
CREATE INDEX IF NOT EXISTS memories_content_trgm ON memories USING gin (content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS memories_tsv ON memories USING gin (tsv);
CREATE INDEX IF NOT EXISTS memories_tags ON memories USING gin (tags);
CREATE INDEX IF NOT EXISTS memories_hnsw ON memories USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS memory_entities (
  memory_id BIGINT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
  entity_id BIGINT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  PRIMARY KEY (memory_id, entity_id)
);

CREATE TABLE IF NOT EXISTS flows (
  id BIGSERIAL PRIMARY KEY,
  investigation_id BIGINT REFERENCES investigations(id) ON DELETE SET NULL,
  chain TEXT NOT NULL,
  tx_hash TEXT NOT NULL,
  from_entity BIGINT NOT NULL REFERENCES entities(id),
  to_entity BIGINT NOT NULL REFERENCES entities(id),
  asset TEXT NOT NULL,
  amount NUMERIC,
  usd_value NUMERIC,
  block_time TIMESTAMPTZ,
  note TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (chain, tx_hash, from_entity, to_entity, asset)
);
CREATE INDEX IF NOT EXISTS flows_from ON flows (from_entity);
CREATE INDEX IF NOT EXISTS flows_to ON flows (to_entity);
CREATE INDEX IF NOT EXISTS flows_inv ON flows (investigation_id);
"""


def ensure_schema():
    q(SCHEMA.replace("__DIM__", str(DIM)))
    empty = q("SELECT NOT EXISTS (SELECT 1 FROM memories) AS empty")[0]["empty"]

    row = q("""SELECT atttypmod AS dim FROM pg_attribute
               WHERE attrelid = 'memories'::regclass AND attname = 'embedding'""")
    if row and row[0]["dim"] not in (-1, DIM):
        if not empty:
            raise RuntimeError(
                f"memories.embedding has dim {row[0]['dim']}, but EMBED_DIM={DIM}. "
                "Restore EMBED_DIM, or clear/re-embed existing memories before switching provider."
            )
        q("DROP INDEX IF EXISTS memories_hnsw")
        q(f"ALTER TABLE memories ALTER COLUMN embedding TYPE vector({DIM})")
        q("CREATE INDEX memories_hnsw ON memories USING hnsw (embedding vector_cosine_ops)")

    cfg = q("""SELECT pg_get_expr(adbin, adrelid) AS expr FROM pg_attrdef d
               JOIN pg_attribute a ON a.attrelid = d.adrelid AND a.attnum = d.adnum
               WHERE d.adrelid = 'memories'::regclass AND a.attname = 'tsv'""")
    if cfg and "'russian'" not in cfg[0]["expr"] and empty:
        q("DROP INDEX IF EXISTS memories_tsv")
        q("ALTER TABLE memories DROP COLUMN tsv")
        q("ALTER TABLE memories ADD COLUMN tsv tsvector "
          "GENERATED ALWAYS AS (to_tsvector('russian', content)) STORED")
        q("CREATE INDEX memories_tsv ON memories USING gin (tsv)")


# ── helpers ──────────────────────────────────────────────────────────────


def js(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, list):
        return [js(x) for x in v]
    if isinstance(v, dict):
        return {k: js(x) for k, x in v.items()}
    return v


def vlit(vec):
    return "[" + ",".join(map(str, vec)) + "]"


CHAIN_ALIASES = {
    "eth": "ethereum", "mainnet": "ethereum", "evm": "ethereum", "erc20": "ethereum",
    "btc": "bitcoin", "xbt": "bitcoin",
    "sol": "solana", "spl": "solana",
    "trx": "tron", "trc20": "tron",
    "bsc": "bnb", "binance-smart-chain": "bnb", "bep20": "bnb",
    "matic": "polygon", "arb": "arbitrum", "op": "optimism", "avax": "avalanche",
    "ton": "ton", "atom": "cosmos", "dot": "polkadot", "ada": "cardano",
}


def norm_chain(chain):
    if not chain:
        return None
    c = chain.strip().lower().replace(" ", "-")
    return CHAIN_ALIASES.get(c, c)


def norm_project(project):
    return project.strip().lower() if project else None


def derive_track(track=None, branch=None):
    """Work track keeps parallel streams on one repo from overwriting each other.
    Explicit value wins; otherwise it is read off the git branch."""
    if track:
        return track.strip().lower()
    if branch and "opensource" in branch.lower():
        return "opensource"
    return "roadmap" if branch else None


def norm_addr(address):
    a = address.strip()
    return a.lower() if a.lower().startswith("0x") else a


def parse_chain_addr(s, default_chain=None):
    """Accept 'chain:address' or bare 'address' (needs default_chain)."""
    s = s.strip()
    if ":" in s:
        chain, _, addr = s.partition(":")
        return norm_chain(chain), norm_addr(addr)
    if not default_chain:
        raise ValueError(f"address '{s}' has no chain prefix and no default chain given")
    return norm_chain(default_chain), norm_addr(s)


def entity_id(chain, address, create=True):
    chain, address = norm_chain(chain), norm_addr(address)
    rows = q("SELECT id FROM entities WHERE chain=%s AND address=%s", (chain, address))
    if rows:
        return rows[0]["id"]
    if not create:
        return None
    return q(
        "INSERT INTO entities (chain, address) VALUES (%s,%s) RETURNING id",
        (chain, address),
    )[0]["id"]


def inv_id(slug, create=True, title=None):
    if slug is None:
        return None
    rows = q("SELECT id FROM investigations WHERE slug=%s", (slug,))
    if rows:
        return rows[0]["id"]
    if not create:
        raise ValueError(f"investigation '{slug}' not found; open it with case_open")
    return q(
        "INSERT INTO investigations (slug, title) VALUES (%s,%s) RETURNING id",
        (slug, title or slug),
    )[0]["id"]


_ADDR_PATTERNS = [
    re.compile(r"0x[0-9a-fA-F]{40}"),                                  # EVM
    re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b"),                      # TRON
    re.compile(r"\bbc1[0-9a-z]{20,60}\b"),                             # BTC bech32
    re.compile(r"\b[13][1-9A-HJ-NP-Za-km-z]{25,34}\b"),                # BTC legacy
    re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"),                    # Solana/base58
]


def extract_addresses(text):
    found = []
    for pat in _ADDR_PATTERNS:
        for m in pat.findall(text):
            a = norm_addr(m)
            if a not in found:
                found.append(a)
    return found


def memory_entities(memory_ids):
    if not memory_ids:
        return {}
    rows = q(
        """SELECT me.memory_id, e.id, e.chain, e.address, e.label, e.entity_type
           FROM memory_entities me JOIN entities e ON e.id = me.entity_id
           WHERE me.memory_id = ANY(%s)""",
        (memory_ids,),
    )
    out = {}
    for r in rows:
        out.setdefault(r["memory_id"], []).append(
            {k: r[k] for k in ("id", "chain", "address", "label", "entity_type")}
        )
    return out


# ── semantic memory tools ────────────────────────────────────────────────


@mcp.tool()
def remember(
    content: str,
    topic: str = "general",
    mtype: str = "note",
    project: str | None = None,
    tags: list[str] | None = None,
    addresses: list[str] | None = None,
    chain: str | None = None,
    source: str | None = None,
    track: str | None = None,
    branch: str | None = None,
    investigation: str | None = None,
    supersedes: int | None = None,
) -> dict:
    """Store a memory. If a very similar active memory exists (same topic+project),
    it is superseded instead of duplicated — this is how memories get UPDATED.

    topic: blockchain | trading | dev | investigation | general (free-form allowed)
    mtype: note | decision | fact | finding | preference
    chain: the chain this fact is about (ethereum, solana, bitcoin, tron, ...);
           aliases are normalized (eth->ethereum, sol->solana). Set it for ANY
           chain-specific knowledge — it makes "everything about X" queries exact.
    source: where the fact came from (docs URL, EIP number, PR, tx hash) — crypto
            facts go stale, provenance is how they get re-verified
    track: parallel work stream on the same repo (opensource | roadmap | free-form).
           Derived from `branch` when omitted. Facts NEVER supersede across tracks,
           so an open-source truth cannot silently overwrite a roadmap one.
    branch: git branch the fact came from (pass `git branch --show-current`)
    addresses: crypto addresses to link, as 'chain:address' (e.g. 'ethereum:0xabc…')
    investigation: case slug to attach this memory to (auto-created if missing)
    supersedes: explicitly replace memory with this id (skips similarity check)
    """
    raw = try_embed(content)
    vec = vlit(raw) if raw is not None else None
    iid = inv_id(investigation) if investigation else None

    project = norm_project(project)
    track = derive_track(track, branch)
    chain = norm_chain(chain)
    if chain is None and addresses:
        chains = {parse_chain_addr(s)[0] for s in addresses}
        if len(chains) == 1:
            chain = chains.pop()

    old_id, sim = supersedes, None
    if old_id is None and vec is not None:
        near = q(
            """SELECT id, 1 - (embedding <=> %(v)s::vector) AS sim FROM memories
               WHERE superseded_by IS NULL AND topic = %(t)s
                 AND project IS NOT DISTINCT FROM %(p)s
                 AND track IS NOT DISTINCT FROM %(tr)s
                 AND chain IS NOT DISTINCT FROM %(c)s
               ORDER BY embedding <=> %(v)s::vector LIMIT 1""",
            {"v": vec, "t": topic, "p": project, "tr": track, "c": chain},
        )
        if near and near[0]["sim"] is not None and float(near[0]["sim"]) >= SUPERSEDE_SIM:
            old_id, sim = near[0]["id"], float(near[0]["sim"])

    new_id = q(
        """INSERT INTO memories (content, topic, mtype, project, tags, chain, source,
                                 track, branch, investigation_id, embedding)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector) RETURNING id""",
        (content, topic, mtype, project, tags or [], chain, source, track, branch, iid, vec),
    )[0]["id"]

    linked = set()
    if old_id is not None:
        q("UPDATE memories SET superseded_by = %s WHERE id = %s", (new_id, old_id))
        for r in q("SELECT entity_id FROM memory_entities WHERE memory_id=%s", (old_id,)):
            linked.add(r["entity_id"])

    for s in addresses or []:
        chain, addr = parse_chain_addr(s)
        linked.add(entity_id(chain, addr))

    for eid in linked:
        q(
            "INSERT INTO memory_entities (memory_id, entity_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (new_id, eid),
        )

    return {"id": new_id, "superseded": old_id, "similarity": sim,
            "semantic": vec is not None, "chain": chain, "track": track, "project": project}


@mcp.tool()
def recall(
    query: str,
    k: int = 8,
    topic: str | None = None,
    project: str | None = None,
    chain: str | None = None,
    track: str | None = None,
    investigation: str | None = None,
    include_superseded: bool = False,
) -> dict:
    """Hybrid search over memories: vector similarity + full-text + exact identifier
    match, RRF-merged with a mild freshness boost. Filter by chain to get everything
    known about one network ('sol' and 'solana' are the same filter).
    If the query contains crypto addresses, matching entities and their fund flows
    are returned too, so investigations can be reconstructed from a single call."""
    filters, params = [], {}
    if not include_superseded:
        filters.append("superseded_by IS NULL")
    if topic:
        filters.append("topic = %(topic)s")
        params["topic"] = topic
    if project:
        filters.append("project = %(project)s")
        params["project"] = norm_project(project)
    if chain:
        filters.append("chain = %(chain)s")
        params["chain"] = norm_chain(chain)
    if track:
        filters.append("track = %(track)s")
        params["track"] = track.strip().lower()
    if investigation:
        filters.append("investigation_id = (SELECT id FROM investigations WHERE slug = %(inv)s)")
        params["inv"] = investigation
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    raw = try_embed(query, "query")
    vrows = []
    if raw is not None:
        vrows = q(
            f"""SELECT id, 1 - (embedding <=> %(vec)s::vector) AS sim FROM memories {where}
                ORDER BY embedding <=> %(vec)s::vector LIMIT %(kk)s""",
            {**params, "vec": vlit(raw), "kk": k * 3},
        )
    def fts(text):
        return q(
            f"""SELECT id, ts_rank(tsv, websearch_to_tsquery('russian', %(q)s)) AS rank
                FROM memories {where + (' AND ' if where else 'WHERE ')}
                    tsv @@ websearch_to_tsquery('russian', %(q)s)
                ORDER BY rank DESC LIMIT %(kk)s""",
            {**params, "q": text, "kk": k * 3},
        )

    # websearch_to_tsquery ANDs terms; fall back to OR so partial matches still surface
    frows = fts(query)
    words = [w for w in re.findall(r"[\w\-\.]{2,}", query) if not w.isdigit()]
    if not frows and len(words) > 1:
        frows = fts(" or ".join(words))

    # Third signal: rare technical identifiers (getFeeForMessage, EIP-1559, m/44')
    # that embeddings blur and stemming mangles.
    idents = [w for w in re.findall(r"[A-Za-z0-9_\-']{5,}", query)
              if any(c.isdigit() for c in w) or any(c.isupper() for c in w[1:])]
    irows = []
    if idents:
        irows = q(
            f"""SELECT id FROM memories {where + (' AND ' if where else 'WHERE ')}
                    content ILIKE ANY(%(pats)s) LIMIT %(kk)s""",
            {**params, "pats": [f"%{i}%" for i in idents], "kk": k * 3},
        )

    score = {}
    for rows, weight in ((vrows, 1.0), (frows, 1.0), (irows, 0.8)):
        for rank, r in enumerate(rows):
            score[r["id"]] = score.get(r["id"], 0) + weight / (60 + rank)

    # Crypto facts age fast: nudge fresher memories up without overriding relevance.
    if score:
        ages = q("SELECT id, EXTRACT(EPOCH FROM now() - created_at)/86400 AS days "
                 "FROM memories WHERE id = ANY(%s)", (list(score),))
        for a in ages:
            score[a["id"]] *= 1 + 0.10 * math.exp(-float(a["days"]) / 180.0)

    top = sorted(score, key=score.get, reverse=True)[:k]

    memories = []
    if top:
        rows = q(
            """SELECT id, content, topic, mtype, project, tags, chain, source,
                      track, branch, investigation_id, superseded_by, created_at
               FROM memories WHERE id = ANY(%s)""",
            (top,),
        )
        by_id = {r["id"]: r for r in rows}
        ents = memory_entities(top)
        sims = {r["id"]: float(r["sim"]) for r in vrows if r["sim"] is not None}
        for mid in top:
            r = by_id.get(mid)
            if not r:
                continue
            r["rrf_score"] = round(score[mid], 5)
            r["vector_sim"] = round(sims[mid], 4) if mid in sims else None
            r["entities"] = ents.get(mid, [])
            memories.append(js(r))

    entity_matches = []
    for addr in extract_addresses(query):
        rows = q(
            """SELECT id, chain, address, label, entity_type, notes FROM entities
               WHERE address = %s OR address ILIKE %s LIMIT 5""",
            (addr, addr + "%"),
        )
        for e in rows:
            fl = q(
                """SELECT f.chain, f.tx_hash, f.asset, f.amount, f.usd_value, f.block_time, f.note,
                          ef.address AS from_address, ef.label AS from_label,
                          et.address AS to_address, et.label AS to_label,
                          i.slug AS investigation
                   FROM flows f
                   JOIN entities ef ON ef.id = f.from_entity
                   JOIN entities et ON et.id = f.to_entity
                   LEFT JOIN investigations i ON i.id = f.investigation_id
                   WHERE f.from_entity = %(e)s OR f.to_entity = %(e)s
                   ORDER BY f.block_time NULLS LAST LIMIT 50""",
                {"e": e["id"]},
            )
            e["flows"] = fl
            entity_matches.append(js(e))

    return {"memories": memories, "entity_matches": entity_matches, "semantic": raw is not None}


@mcp.tool()
def forget(memory_id: int) -> dict:
    """Permanently delete a memory by id."""
    n = q("DELETE FROM memories WHERE id = %s RETURNING id", (memory_id,))
    return {"deleted": bool(n)}


@mcp.tool()
def reindex_embeddings(limit: int = 500) -> dict:
    """Embed memories stored while embeddings were unavailable (embedding IS NULL).
    Run once after adding an API key or switching EMBED_PROVIDER. Raises loudly
    if the provider is still misconfigured."""
    rows = q("SELECT id, content FROM memories WHERE embedding IS NULL ORDER BY id LIMIT %s", (limit,))
    for r in rows:
        q("UPDATE memories SET embedding = %s::vector WHERE id = %s", (vlit(embed(r["content"], "passage")), r["id"]))
    remaining = q("SELECT count(*) AS c FROM memories WHERE embedding IS NULL")[0]["c"]
    return {"embedded": len(rows), "remaining_null": remaining}


@mcp.tool()
def recent(n: int = 10, topic: str | None = None, project: str | None = None,
           chain: str | None = None, track: str | None = None) -> dict:
    """List the most recent active memories, scoped to topic/project/chain/track."""
    filters, params = ["superseded_by IS NULL"], {"n": n}
    if topic:
        filters.append("topic = %(topic)s")
        params["topic"] = topic
    if project:
        filters.append("project = %(project)s")
        params["project"] = project
    if chain:
        filters.append("chain = %(chain)s")
        params["chain"] = norm_chain(chain)
    if track:
        filters.append("track = %(track)s")
        params["track"] = track.strip().lower()
    rows = q(
        f"""SELECT id, content, topic, mtype, project, chain, source, track, branch, tags, created_at
            FROM memories
            WHERE {' AND '.join(filters)} ORDER BY created_at DESC LIMIT %(n)s""",
        params,
    )
    return {"memories": js(rows)}


# ── investigation tools ──────────────────────────────────────────────────


@mcp.tool()
def entity_upsert(
    chain: str,
    address: str,
    label: str | None = None,
    entity_type: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create or update a labeled on-chain entity.
    entity_type: wallet | exchange | mixer | bridge | contract | victim | attacker | service | unknown"""
    chain, address = norm_chain(chain), norm_addr(address)
    row = q(
        """INSERT INTO entities (chain, address, label, entity_type, notes)
           VALUES (%s,%s,%s,COALESCE(%s,'unknown'),%s)
           ON CONFLICT (chain, address) DO UPDATE SET
             label = COALESCE(EXCLUDED.label, entities.label),
             entity_type = CASE WHEN %s::text IS NULL THEN entities.entity_type ELSE EXCLUDED.entity_type END,
             notes = COALESCE(EXCLUDED.notes, entities.notes)
           RETURNING *""",
        (chain, address, label, entity_type, notes, entity_type),
    )[0]
    return js(row)


@mcp.tool()
def flow_add(
    chain: str,
    tx_hash: str,
    from_address: str,
    to_address: str,
    asset: str,
    amount: float | None = None,
    usd_value: float | None = None,
    block_time: str | None = None,
    investigation: str | None = None,
    note: str | None = None,
) -> dict:
    """Record one fund movement (an edge in the flow graph). Idempotent per
    (chain, tx_hash, from, to, asset). Addresses may be 'chain:address' to model
    cross-chain hops (bridges); bare addresses default to the tx chain.
    block_time: ISO 8601. amount: human units (e.g. 1.5 ETH -> 1.5)."""
    chain = norm_chain(chain)
    f_chain, f_addr = parse_chain_addr(from_address, chain)
    t_chain, t_addr = parse_chain_addr(to_address, chain)
    fid, tid = entity_id(f_chain, f_addr), entity_id(t_chain, t_addr)
    iid = inv_id(investigation) if investigation else None
    row = q(
        """INSERT INTO flows (investigation_id, chain, tx_hash, from_entity, to_entity,
                              asset, amount, usd_value, block_time, note)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (chain, tx_hash, from_entity, to_entity, asset) DO UPDATE SET
             investigation_id = COALESCE(EXCLUDED.investigation_id, flows.investigation_id),
             amount = COALESCE(EXCLUDED.amount, flows.amount),
             usd_value = COALESCE(EXCLUDED.usd_value, flows.usd_value),
             block_time = COALESCE(EXCLUDED.block_time, flows.block_time),
             note = COALESCE(EXCLUDED.note, flows.note)
           RETURNING id""",
        (iid, chain, tx_hash.strip(), fid, tid, asset.upper(), amount, usd_value, block_time, note),
    )[0]
    return {"id": row["id"], "from_entity": fid, "to_entity": tid}


@mcp.tool()
def trace(
    address: str,
    chain: str,
    direction: str = "out",
    max_hops: int = 4,
    investigation: str | None = None,
) -> dict:
    """Reconstruct fund movement from recorded flows: recursive multi-hop walk
    from an address. direction: out (where funds went) | in (where funds came
    from) | both. Follows cross-chain edges (bridges) automatically."""
    start = entity_id(chain, address, create=False)
    if start is None:
        return {"error": f"no entity {chain}:{address} in memory", "flows": []}

    inv_filter = ""
    params = {"start": start, "max_hops": max_hops}
    if investigation:
        inv_filter = "AND f.investigation_id = (SELECT id FROM investigations WHERE slug = %(inv)s)"
        params["inv"] = investigation

    def walk(src_col, dst_col):
        return q(
            f"""WITH RECURSIVE walk AS (
                  SELECT f.id, f.chain, f.tx_hash, f.from_entity, f.to_entity, f.asset,
                         f.amount, f.usd_value, f.block_time, f.note,
                         1 AS hop, ARRAY[f.id] AS path
                  FROM flows f
                  WHERE f.{src_col} = %(start)s {inv_filter}
                UNION ALL
                  SELECT f.id, f.chain, f.tx_hash, f.from_entity, f.to_entity, f.asset,
                         f.amount, f.usd_value, f.block_time, f.note,
                         w.hop + 1, w.path || f.id
                  FROM flows f JOIN walk w ON f.{src_col} = w.{dst_col}
                  WHERE w.hop < %(max_hops)s AND f.id <> ALL(w.path) {inv_filter}
                )
                SELECT DISTINCT ON (w.id) w.hop, w.chain, w.tx_hash, w.asset, w.amount,
                       w.usd_value, w.block_time, w.note,
                       ef.chain AS from_chain, ef.address AS from_address,
                       ef.label AS from_label, ef.entity_type AS from_type,
                       et.chain AS to_chain, et.address AS to_address,
                       et.label AS to_label, et.entity_type AS to_type
                FROM walk w
                JOIN entities ef ON ef.id = w.from_entity
                JOIN entities et ON et.id = w.to_entity
                ORDER BY w.id, w.hop""",
            params,
        )

    out = {"origin": {"chain": norm_chain(chain), "address": norm_addr(address)}}
    if direction in ("out", "both"):
        flows = sorted(walk("from_entity", "to_entity"), key=lambda r: r["hop"])
        senders = {(r["from_chain"], r["from_address"]) for r in flows}
        out["outgoing"] = js(flows)
        out["endpoints"] = js([
            {"chain": r["to_chain"], "address": r["to_address"], "label": r["to_label"],
             "entity_type": r["to_type"]}
            for r in flows if (r["to_chain"], r["to_address"]) not in senders
        ])
    if direction in ("in", "both"):
        out["incoming"] = js(sorted(walk("to_entity", "from_entity"), key=lambda r: r["hop"]))
    return out


@mcp.tool()
def case_open(slug: str, title: str | None = None, summary: str | None = None) -> dict:
    """Open (or fetch) an investigation case by slug."""
    rows = q("SELECT * FROM investigations WHERE slug=%s", (slug,))
    if rows:
        return js(rows[0])
    return js(q(
        "INSERT INTO investigations (slug, title, summary) VALUES (%s,%s,%s) RETURNING *",
        (slug, title or slug, summary),
    )[0])


@mcp.tool()
def case_close(slug: str, summary: str) -> dict:
    """Close a case with a final summary."""
    rows = q(
        """UPDATE investigations SET status='closed', summary=%s, updated_at=now()
           WHERE slug=%s RETURNING *""",
        (summary, slug),
    )
    return js(rows[0]) if rows else {"error": f"case '{slug}' not found"}


@mcp.tool()
def case_list(status: str | None = None) -> dict:
    """List investigation cases (optionally filtered by status: open | closed)."""
    if status:
        rows = q("SELECT * FROM investigations WHERE status=%s ORDER BY updated_at DESC", (status,))
    else:
        rows = q("SELECT * FROM investigations ORDER BY updated_at DESC")
    return {"cases": js(rows)}


@mcp.tool()
def case_report(slug: str) -> dict:
    """Full reconstruction of a case: metadata, all entities, the complete flow
    timeline, and every linked memory. Enough to rebuild the whole investigation."""
    inv = q("SELECT * FROM investigations WHERE slug=%s", (slug,))
    if not inv:
        return {"error": f"case '{slug}' not found"}
    iid = inv[0]["id"]
    flows = q(
        """SELECT f.chain, f.tx_hash, f.asset, f.amount, f.usd_value, f.block_time, f.note,
                  ef.chain AS from_chain, ef.address AS from_address, ef.label AS from_label,
                  ef.entity_type AS from_type,
                  et.chain AS to_chain, et.address AS to_address, et.label AS to_label,
                  et.entity_type AS to_type
           FROM flows f
           JOIN entities ef ON ef.id = f.from_entity
           JOIN entities et ON et.id = f.to_entity
           WHERE f.investigation_id = %s
           ORDER BY f.block_time NULLS LAST, f.id""",
        (iid,),
    )
    entities = q(
        """SELECT DISTINCT e.* FROM entities e
           WHERE e.id IN (
             SELECT from_entity FROM flows WHERE investigation_id = %(i)s
             UNION SELECT to_entity FROM flows WHERE investigation_id = %(i)s
             UNION SELECT me.entity_id FROM memory_entities me
                   JOIN memories m ON m.id = me.memory_id WHERE m.investigation_id = %(i)s
           ) ORDER BY e.id""",
        {"i": iid},
    )
    memories = q(
        """SELECT id, content, mtype, tags, created_at FROM memories
           WHERE investigation_id = %s AND superseded_by IS NULL ORDER BY created_at""",
        (iid,),
    )
    return {
        "investigation": js(inv[0]),
        "entities": js(entities),
        "flows": js(flows),
        "memories": js(memories),
    }


@mcp.tool()
def stats() -> dict:
    """Memory database statistics."""
    r = q(
        """SELECT
             (SELECT count(*) FROM memories WHERE superseded_by IS NULL) AS active_memories,
             (SELECT count(*) FROM memories) AS total_memories,
             (SELECT count(*) FROM entities) AS entities,
             (SELECT count(*) FROM flows) AS flows,
             (SELECT count(*) FROM investigations WHERE status='open') AS open_cases,
             (SELECT count(*) FROM investigations) AS total_cases"""
    )[0]
    r["by_topic"] = {x["topic"]: x["n"] for x in q(
        "SELECT topic, count(*) AS n FROM memories WHERE superseded_by IS NULL "
        "GROUP BY topic ORDER BY n DESC")}
    r["by_chain"] = {x["chain"]: x["n"] for x in q(
        "SELECT chain, count(*) AS n FROM memories WHERE superseded_by IS NULL "
        "AND chain IS NOT NULL GROUP BY chain ORDER BY n DESC")}
    r["by_track"] = {f'{x["project"] or "-"}/{x["track"]}': x["n"] for x in q(
        "SELECT project, track, count(*) AS n FROM memories WHERE superseded_by IS NULL "
        "AND track IS NOT NULL GROUP BY project, track ORDER BY n DESC")}
    r["by_project"] = {x["project"]: x["n"] for x in q(
        "SELECT project, count(*) AS n FROM memories WHERE superseded_by IS NULL "
        "AND project IS NOT NULL GROUP BY project ORDER BY n DESC")}
    return js(r)


if __name__ == "__main__":
    ensure_schema()
    mcp.run()
