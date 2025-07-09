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
connections.connect("default", host="localhost", port="19530")
collection = Collection("video_embeddings")
collection.load()

# Load BGE embedding model
class BGEQueryEmbedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en")
        self.model = AutoModel.from_pretrained("BAAI/bge-small-en")

    def embed(self, query):
        inputs = self.tokenizer(query, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
        return embedding.astype(np.float32).tolist()

embedder = BGEQueryEmbedder()

def search_similar(query, top_k=10):
    vector = embedder.embed(query)
    search_params = {"metric_type": "L2", "params": {"nprobe": 10}}

    results = collection.search(
        data=[vector],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["guid", "video_path", "transcript_path", "translation_path", "summary_path"]
    )

    output = []
    for hit in results[0]:
        item = hit.entity
        output.append({
            "guid": item["guid"],
            "video_path": item["video_path"],
            "transcript_path": item["transcript_path"],
            "translation_path": item["translation_path"],
            "summary_path": item["summary_path"],
            "score": hit.distance
        })
    return output