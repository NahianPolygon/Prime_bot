import yaml
import chromadb
from sentence_transformers import SentenceTransformer


with open("config.yaml") as f:
    cfg = yaml.safe_load(f)

model = SentenceTransformer(cfg["embeddings"]["model"])
client = chromadb.PersistentClient(path=cfg["chroma"]["persist_dir"])

QUERY = "Compare the two master cards prime bank offers"

ALL_COLLECTIONS = [
    "conventional_credit_i_need_a_credit_card",
    "islami_credit_i_need_a_credit_card",
    "conventional_credit_existing_cardholder",
    "islami_credit_existing_cardholder",
    "all_products",
]

SLIM_COLLECTIONS = [
    "conventional_credit_i_need_a_credit_card",
    "islami_credit_i_need_a_credit_card",
    "all_products",
]

embedding = model.encode(QUERY).tolist()


def search_collections(collections, top_k, label):
    print(f"\n{'=' * 80}")
    print(f"CONFIG: {label}")
    print(f"Collections: {len(collections)}, top_k: {top_k}")
    print(f"{'=' * 80}")

    all_items = []
    for col_name in collections:
        try:
            col = client.get_or_create_collection(
                name=col_name,
                metadata={"hnsw:space": "cosine"},
            )
            count = col.count()
            n = min(top_k, max(count, 1))
            results = col.query(query_embeddings=[embedding], n_results=n)

            chunks = (
                results["documents"][0]
                if results["documents"] and results["documents"][0]
                else []
            )
            metas = (
                results["metadatas"][0]
                if results["metadatas"] and results["metadatas"][0]
                else []
            )
            distances = results.get("distances", [[]])[0]

            print(f"\n--- {col_name} (corpus: {count}, returned: {len(chunks)}) ---")
            for i, (chunk, meta) in enumerate(zip(chunks, metas)):
                dist = distances[i] if i < len(distances) else 999
                pid = meta.get("product_id", "?")
                pname = meta.get("product_name", "?")
                preview = chunk[:150].replace("\n", " ")
                print(f"  [{i + 1}] dist={dist:.4f} | {pid} | {pname}")
                print(f"      {preview}...")
                all_items.append(
                    {
                        "text": chunk,
                        "distance": dist,
                        "product_id": pid,
                        "product_name": pname,
                        "collection": col_name,
                    }
                )
        except Exception as e:
            print(f"\n--- {col_name}: ERROR: {e} ---")

    seen = set()
    deduped = []
    for item in all_items:
        key = item["text"][:200]
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    deduped.sort(key=lambda x: x["distance"])

    print(f"\nTOTAL: {len(all_items)} raw, {len(deduped)} after dedup")

    for max_chars in [4000, 5000, 6000, 8000]:
        char_count = 0
        included = 0
        products_seen = set()
        for item in deduped:
            if char_count + len(item["text"]) > max_chars:
                break
            char_count += len(item["text"])
            included += 1
            products_seen.add(item["product_name"])
        print(
            f"  max_context_chars={max_chars}: {included} chunks, "
            f"{char_count} chars, products: {products_seen}"
        )

    mastercard_chunks = [
        item
        for item in deduped
        if "master" in item["product_name"].lower() or "master" in item["text"].lower()
    ]
    print(f"\nMastercard-relevant chunks: {len(mastercard_chunks)}")
    for item in mastercard_chunks[:6]:
        print(
            f"  dist={item['distance']:.4f} | {item['product_id']} | "
            f"{item['product_name']} | col={item['collection']}"
        )

    return deduped


print("\n\nTEST 1: SLIM (3 collections, top_k=4)")
slim = search_collections(SLIM_COLLECTIONS, 4, "SLIM")

print("\n\nTEST 2: MEDIUM (5 collections, top_k=3)")
medium = search_collections(ALL_COLLECTIONS, 3, "MEDIUM")

print("\n\nTEST 3: ORIGINAL (5 collections, top_k=6)")
original = search_collections(ALL_COLLECTIONS, 6, "ORIGINAL")

print("\n\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)
slim_mc = len(
    [
        i
        for i in slim
        if "master" in i.get("product_name", "").lower() or "master" in i["text"].lower()
    ]
)
medium_mc = len(
    [
        i
        for i in medium
        if "master" in i.get("product_name", "").lower() or "master" in i["text"].lower()
    ]
)
original_mc = len(
    [
        i
        for i in original
        if "master" in i.get("product_name", "").lower() or "master" in i["text"].lower()
    ]
)
print(
    f"Mastercard chunks - SLIM: {slim_mc}, MEDIUM: {medium_mc}, "
    f"ORIGINAL: {original_mc}"
)
print(
    f"Total chunks - SLIM: {len(slim)}, MEDIUM: {len(medium)}, "
    f"ORIGINAL: {len(original)}"
)