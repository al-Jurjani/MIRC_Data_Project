# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# File: query_backend.py
# Backend logic for Part B: Accept user query, embed, search Milvus, return results

from pymilvus import connections, Collection
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
import os

# Connect to Milvus
# connections.connect("default", host="localhost", port="19530")
connections.connect("default", host="127.0.0.1", port="19530")
collection = Collection("video_embeddings_v2")
collection.load()

# Load BGE embedding model
class BGEQueryEmbedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en")
        self.model = AutoModel.from_pretrained("BAAI/bge-small-en", trust_remote_code=True, from_tf=False)

    def embed(self, query):
        inputs = self.tokenizer(query, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()

        # Normalize for cosine
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.astype(np.float32).tolist()

embedder = BGEQueryEmbedder()

def search_similar(query, top_k=10):
    vector = embedder.embed(query)
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

    print("Performing search with query:", query)
    results = collection.search(
        data=[vector],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["guid", "title", "video_path", "transcript_path", "translation_path", "summary_path"]
    )

    output = []
    for hit in results[0]:
        item = hit.entity
        output.append({
            "guid": item["guid"],
            "title": item["title"],
            "video_path": item["video_path"],
            "transcript_path": item["transcript_path"],
            "translation_path": item["translation_path"],
            "summary_path": item["summary_path"],
            "L2_score": hit.distance
        })
    
    for item in output:
        print(f"Found item: {item['title']} with score: {item['L2_score']:.4f}")
    print(f"Total results found: {len(output)}")
    return output