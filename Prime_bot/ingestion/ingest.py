import re
import sys
import yaml
import chromadb
from pathlib import Path
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import MarkdownTextSplitter

with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

MODEL_NAME = cfg["embeddings"]["model"]
CHROMA_DIR = cfg["chroma"]["persist_dir"]
DEFAULT_BANK_SLUG = str((cfg.get("knowledge_base") or {}).get("active_company") or "prime_bank")
BANKS_ROOT = Path("./banks")
KB_ROOT = BANKS_ROOT / DEFAULT_BANK_SLUG
COLLECTION_LIMIT = 63

model = SentenceTransformer(MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_DIR)
splitter = MarkdownTextSplitter(chunk_size=500, chunk_overlap=50)


def load_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return meta, body
    return {}, text


def _slugify(value: str, fallback: str = "bank") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")
    return cleaned or fallback


def _bounded_collection_name(bank_slug: str, suffix: str) -> str:
    raw = f"{bank_slug}_{suffix}"
    if len(raw) <= COLLECTION_LIMIT:
        return raw
    overflow = len(raw) - COLLECTION_LIMIT
    trimmed_slug = bank_slug[:-overflow].rstrip("_") or bank_slug[:8]
    return f"{trimmed_slug}_{suffix}"[:COLLECTION_LIMIT]


def collection_name_from_path(md_file: Path, kb_root: Path) -> str:
    rel = md_file.relative_to(kb_root)
    parts = rel.parts[:-1]
    suffix = "_".join(parts)
    suffix = suffix.replace("-", "_").replace(" ", "_")
    return _bounded_collection_name(_slugify(kb_root.name), suffix)


def safe_meta_value(v):
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _safe_delete_by_source(collection, source: str) -> None:
    try:
        collection.delete(where={"source": source})
    except Exception:
        pass


def _doc_key(meta: dict, col_name: str, md_file: Path) -> str:
    value = str(meta.get("product_id") or f"{col_name}_{md_file.stem}")
    return _slugify(value, fallback=md_file.stem)


def ingest_all(kb_root: str = KB_ROOT, force: bool = False):
    kb_path = Path(kb_root)
    if not kb_path.exists():
        print(f"[ERROR] Knowledge base directory not found: {kb_root}")
        sys.exit(1)

    md_files = list(kb_path.rglob("*.md"))
    if not md_files:
        print(f"[WARN] No markdown files found under {kb_root}")
        return

    bank_slug = _slugify(kb_path.name)
    global_col_name = _bounded_collection_name(bank_slug, "all_products")

    print(f"Found {len(md_files)} markdown files under {kb_path}.")

    for md_file in md_files:
        meta, body = load_md(md_file)
        col_name = collection_name_from_path(md_file, kb_path)

        if not col_name:
            print(f"[SKIP] Could not derive collection name for {md_file}")
            continue

        col = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        chunks = [chunk.strip() for chunk in splitter.split_text(body) if chunk.strip()]
        if not chunks:
            print(f"[SKIP] No ingestible chunks produced for {md_file}")
            continue
        embeddings = model.encode(chunks).tolist()

        base_meta = {k: safe_meta_value(v) for k, v in meta.items()}
        base_meta.setdefault("bank_slug", bank_slug)
        base_meta["source"] = str(md_file)

        global_col = client.get_or_create_collection(
            name=global_col_name,
            metadata={"hnsw:space": "cosine"},
        )

        doc_key = _doc_key(meta, col_name, md_file)
        ids = [f"{doc_key}_{i}" for i in range(len(chunks))]
        global_ids = [f"{global_col_name}_{doc_key}_{i}" for i in range(len(chunks))]

        if force:
            _safe_delete_by_source(col, str(md_file))
            _safe_delete_by_source(global_col, str(md_file))

        col.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{**base_meta, "collection": col_name} for _ in chunks],
            ids=ids,
        )

        global_col.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{**base_meta, "collection": global_col_name} for _ in chunks],
            ids=global_ids,
        )

        print(f"  {len(chunks)} chunks -> {col_name}  [{meta.get('product_id', md_file.stem)}]")

    print("\nIngestion complete.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    bank = DEFAULT_BANK_SLUG
    if "--bank" in sys.argv:
        try:
            bank = sys.argv[sys.argv.index("--bank") + 1]
        except IndexError:
            print("[ERROR] --bank requires a bank directory name, for example: --bank prime_bank")
            sys.exit(1)
    ingest_all(kb_root=str(BANKS_ROOT / _slugify(bank)), force=force)
