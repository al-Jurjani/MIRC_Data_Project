# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# File: db_browser_backend.py
# Description: Provides full-database listing for PyQt frontend display

# from pymilvus import connections, Collection
# import os

# # Connect to Milvus
# connections.connect("default", host="127.0.0.1", port="19530")
# collection = Collection("video_embeddings_v2")
# collection.load()

# def get_all_documents():
#     # Perform a full search to fetch all metadata (limit to a reasonable number if needed)
#     num_docs = collection.num_entities
#     results = collection.query(
#         expr=None,
#         output_fields=["guid", "title", "video_path", "transcript_path", "translation_path", "summary_path"],
#         limit=num_docs
#     )
#     return results

# db_browser_backend.py

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
