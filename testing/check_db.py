from pymilvus import Collection, connections, utility, FieldSchema, DataType

connections.connect("default", host="localhost", port="19530")

collection = Collection("video_embeddings_v2")

# Check if index exists, create it if not
if not collection.has_index():
    print("🔧 Creating index on embedding field...")
    collection.create_index(
        field_name="embedding",
        index_params={
            "metric_type": "L2",  # or "COSINE" if you're doing semantic search
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
    )
    print("✅ Index created.")

collection.load()

results = collection.query(
    expr="",
    output_fields=["guid", "title", "video_path", "transcript_path", "translation_path", "summary_path", "embedding"],
    limit=15
)

# for r in results:
#     print(r)

for count, r in enumerate(results):
    print(f"Embedding #{count}:")
    print("guid:", r["guid"])
    print("title:", r["title"])
    print("video_path:", r["video_path"])
    print("transcript_path:", r["transcript_path"])
    print("translation_path:", r["translation_path"])
    print("summary_path:", r["summary_path"])
    # print("embedding:", r["embedding"])
    print("="*50)

print("Total rows:", collection.num_entities)

# collection.drop()

# print("Database cleared and recreated with new schema.")
# print("Total rows after clearing:", collection.num_entities)
