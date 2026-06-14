"""SQLite-backed persistence for the Second Brain (persistence pillar).

A small, dependency-free store over stdlib ``sqlite3``. It defaults to an
in-memory database so unit tests stay offline and deterministic; pass a file
path (e.g. under ``DATA_DIR/second_brain``) for a persistent runtime store.

The store is intentionally dumb: it persists nodes and edges and answers
campaign-scoped reads. All ranking/recall logic lives in ``recall.py`` and
``graph.py`` so the storage layer stays easy to swap or back with a real
vector DB later.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Iterable

from .models import KnowledgeEdge, KnowledgeNode

# Bump when the on-disk schema changes in a non-backward-compatible way.
SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS brain_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS knowledge_node (
    id            TEXT NOT NULL,
    campaign_id   TEXT NOT NULL,
    kind          TEXT NOT NULL,
    name          TEXT NOT NULL,
    text          TEXT NOT NULL,
    metadata      TEXT NOT NULL DEFAULT '{}',
    salience      REAL NOT NULL DEFAULT 0.5,
    canonical     INTEGER NOT NULL DEFAULT 1,
    embedding     TEXT,
    updated_turn  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (campaign_id, id)
);
CREATE TABLE IF NOT EXISTS knowledge_edge (
    campaign_id   TEXT NOT NULL,
    src_id        TEXT NOT NULL,
    dst_id        TEXT NOT NULL,
    relation      TEXT NOT NULL,
    weight        REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (campaign_id, src_id, dst_id, relation)
);
CREATE INDEX IF NOT EXISTS idx_node_campaign ON knowledge_node (campaign_id);
CREATE INDEX IF NOT EXISTS idx_edge_src ON knowledge_edge (campaign_id, src_id);
CREATE INDEX IF NOT EXISTS idx_edge_dst ON knowledge_edge (campaign_id, dst_id);
"""


def _dumps_embedding(embedding: tuple[float, ...] | None) -> str | None:
    if not embedding:
        return None
    return json.dumps([round(float(x), 6) for x in embedding])


def _loads_embedding(raw: str | None) -> tuple[float, ...] | None:
    if not raw:
        return None
    try:
        return tuple(float(x) for x in json.loads(raw))
    except (ValueError, TypeError):
        return None


class SecondBrainStore:
    """Campaign-scoped persistence for knowledge nodes and edges."""

    def __init__(self, path: str = ":memory:", *, wal: bool = False) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        # WAL helps concurrent readers on a real file; skip for :memory: where
        # it is meaningless. Opt-in so tests stay simple and deterministic.
        if wal and path != ":memory:":
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.Error:
                pass
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        # Stamp the schema version once, on first creation.
        if self.get_meta("schema_version") is None:
            self.set_meta("schema_version", str(SCHEMA_VERSION))

    def close(self) -> None:
        self._conn.close()

    # -- meta --------------------------------------------------------------
    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM brain_meta WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO brain_meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self._conn.commit()

    def all_meta(self) -> dict[str, str]:
        return {
            r["key"]: r["value"]
            for r in self._conn.execute("SELECT key, value FROM brain_meta")
        }

    @property
    def schema_version(self) -> int:
        try:
            return int(self.get_meta("schema_version") or 0)
        except (TypeError, ValueError):
            return 0

    def note_failed_job(self, detail: str = "") -> None:
        """Increment a small failure counter for the debug API. Never raises."""
        try:
            current = int(self.get_meta("failed_jobs") or 0)
        except (TypeError, ValueError):
            current = 0
        self.set_meta("failed_jobs", str(current + 1))
        if detail:
            self.set_meta("last_failure", detail[:200])

    def counts(self, campaign_id: str) -> dict[str, int]:
        """Per-campaign counts for the debug API. By node kind plus edges."""
        out: dict[str, int] = {}
        for row in self._conn.execute(
            "SELECT kind, COUNT(*) AS c FROM knowledge_node "
            "WHERE campaign_id=? GROUP BY kind",
            (campaign_id,),
        ):
            out[row["kind"]] = row["c"]
        out["edges"] = self._conn.execute(
            "SELECT COUNT(*) AS c FROM knowledge_edge WHERE campaign_id=?",
            (campaign_id,),
        ).fetchone()["c"]
        return out

    # -- writes ------------------------------------------------------------
    def upsert_nodes(self, nodes: Iterable[KnowledgeNode]) -> int:
        rows = [
            (
                n.id,
                n.campaign_id,
                n.kind,
                n.name,
                n.text,
                json.dumps(n.metadata or {}),
                float(n.salience),
                1 if n.canonical else 0,
                _dumps_embedding(n.embedding),
                int(n.updated_turn),
            )
            for n in nodes
            if n.id and n.campaign_id
        ]
        self._conn.executemany(
            """
            INSERT INTO knowledge_node
                (id, campaign_id, kind, name, text, metadata, salience,
                 canonical, embedding, updated_turn)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(campaign_id, id) DO UPDATE SET
                kind=excluded.kind, name=excluded.name, text=excluded.text,
                metadata=excluded.metadata, salience=excluded.salience,
                canonical=excluded.canonical,
                embedding=COALESCE(excluded.embedding, knowledge_node.embedding),
                updated_turn=MAX(excluded.updated_turn, knowledge_node.updated_turn)
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def upsert_edges(self, edges: Iterable[KnowledgeEdge]) -> int:
        rows = [
            (e.campaign_id, e.src_id, e.dst_id, e.relation, float(e.weight))
            for e in edges
            if e.campaign_id and e.src_id and e.dst_id and e.src_id != e.dst_id
        ]
        self._conn.executemany(
            """
            INSERT INTO knowledge_edge (campaign_id, src_id, dst_id, relation, weight)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(campaign_id, src_id, dst_id, relation) DO UPDATE SET
                weight=excluded.weight
            """,
            rows,
        )
        self._conn.commit()
        return len(rows)

    def set_salience(self, campaign_id: str, node_id: str, salience: float) -> None:
        self._conn.execute(
            "UPDATE knowledge_node SET salience=? WHERE campaign_id=? AND id=?",
            (max(0.0, min(1.0, float(salience))), campaign_id, node_id),
        )
        self._conn.commit()

    # -- reads -------------------------------------------------------------
    def _row_to_node(self, row: sqlite3.Row) -> KnowledgeNode:
        return KnowledgeNode(
            id=row["id"],
            campaign_id=row["campaign_id"],
            kind=row["kind"],
            name=row["name"],
            text=row["text"],
            metadata=json.loads(row["metadata"] or "{}"),
            salience=row["salience"],
            canonical=bool(row["canonical"]),
            embedding=_loads_embedding(row["embedding"]),
            updated_turn=row["updated_turn"],
        )

    def get_nodes(
        self, campaign_id: str, *, kinds: tuple[str, ...] = ()
    ) -> list[KnowledgeNode]:
        if not campaign_id:
            return []
        sql = "SELECT * FROM knowledge_node WHERE campaign_id=?"
        params: list[object] = [campaign_id]
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            sql += f" AND kind IN ({placeholders})"
            params.extend(kinds)
        sql += " ORDER BY id"
        return [self._row_to_node(r) for r in self._conn.execute(sql, params)]

    def get_node(self, campaign_id: str, node_id: str) -> KnowledgeNode | None:
        row = self._conn.execute(
            "SELECT * FROM knowledge_node WHERE campaign_id=? AND id=?",
            (campaign_id, node_id),
        ).fetchone()
        return self._row_to_node(row) if row else None

    def get_edges(self, campaign_id: str) -> list[KnowledgeEdge]:
        rows = self._conn.execute(
            "SELECT * FROM knowledge_edge WHERE campaign_id=? ORDER BY src_id, dst_id",
            (campaign_id,),
        )
        return [
            KnowledgeEdge(
                campaign_id=r["campaign_id"],
                src_id=r["src_id"],
                dst_id=r["dst_id"],
                relation=r["relation"],
                weight=r["weight"],
            )
            for r in rows
        ]

    def neighbors(self, campaign_id: str, node_ids: Iterable[str]) -> set[str]:
        """Undirected one-hop neighbor ids for the given node ids."""
        ids = [nid for nid in dict.fromkeys(node_ids) if nid]
        if not ids:
            return set()
        placeholders = ",".join("?" for _ in ids)
        found: set[str] = set()
        for col_a, col_b in (("src_id", "dst_id"), ("dst_id", "src_id")):
            rows = self._conn.execute(
                f"SELECT {col_b} AS n FROM knowledge_edge "
                f"WHERE campaign_id=? AND {col_a} IN ({placeholders})",
                [campaign_id, *ids],
            )
            found.update(r["n"] for r in rows)
        return found
