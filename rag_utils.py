import math
from collections import Counter

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into overlapping chunks.
    """
    if not text:
        return []
    words = text.split()
    if len(words) <= chunk_size:
        return [text]

    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += (chunk_size - overlap)
    return chunks

def _cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return numerator / denominator

def search_chunks(query: str, chunks: list[dict], top_k: int = 3) -> list[dict]:
    """
    RAG search over document chunks using TF-IDF / term frequency vector similarity.
    chunks should be a list of dicts: [{"source": str, "text": str}]
    """
    if not query or not chunks:
        return []

    query_vec = Counter(query.lower().split())
    scored_chunks = []

    for item in chunks:
        chunk_vec = Counter(item["text"].lower().split())
        score = _cosine_similarity(query_vec, chunk_vec)
        if score > 0:
            scored_chunks.append({
                "source": item.get("source", "Unknown"),
                "text": item["text"],
                "score": round(score, 4)
            })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]
