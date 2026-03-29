import os
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
KB_ROOT = "./knowledge_base"

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


def collection_name_from_path(md_file: Path) -> str:
    rel = md_file.relative_to(KB_ROOT)
    parts = rel.parts[:-1]
    name = "_".join(parts)
    name = name.replace("-", "_").replace(" ", "_")
    return name[:63] if len(name) > 63 else name


def safe_meta_value(v):
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def ingest_all(kb_root: str = KB_ROOT, force: bool = False):
    kb_path = Path(kb_root)
    if not kb_path.exists():
        print(f"[ERROR] Knowledge base directory not found: {kb_root}")
        sys.exit(1)

    md_files = list(kb_path.rglob("*.md"))
    if not md_files:
        print(f"[WARN] No markdown files found under {kb_root}")
        return

    print(f"Found {len(md_files)} markdown files.")

    for md_file in md_files:
        meta, body = load_md(md_file)
        col_name = collection_name_from_path(md_file)

        if not col_name:
            print(f"[SKIP] Could not derive collection name for {md_file}")
            continue

        col = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        chunks = splitter.split_text(body)
        embeddings = model.encode(chunks).tolist()

        base_meta = {k: safe_meta_value(v) for k, v in meta.items()}
        base_meta["source"] = str(md_file)
        base_meta["collection"] = col_name

        global_col = client.get_or_create_collection(
            name="all_products",
            metadata={"hnsw:space": "cosine"},
        )

        ids = [f"{md_file.stem}_{i}" for i in range(len(chunks))]
        global_ids = [f"{col_name}_{md_file.stem}_{i}" for i in range(len(chunks))]

        if force:
            try:
                col.delete(ids=ids)
                global_col.delete(ids=global_ids)
            except Exception:
                pass

        col.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{**base_meta} for _ in chunks],
            ids=ids,
        )

        global_col.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{**base_meta} for _ in chunks],
            ids=global_ids,
        )

        print(f"  {len(chunks)} chunks -> {col_name}  [{meta.get('product_id', md_file.stem)}]")

    print("\nIngestion complete.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    ingest_all(force=force)
