# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

from pymilvus import connections, Collection
import shutil
import os

connections.connect("default", host="127.0.0.1", port="19530")
collection = Collection("video_embeddings_v8")
collection.load()

def fetch_all_entries():
    results = collection.query(
        expr="",
        output_fields=[
            "guid", "title", "video_path", "transcript_path", 
            "translation_path", "summary_path"
        ],
        limit=10000
    )
    return results

def get_file_path(entry, key):
    return entry.get(key, None)
