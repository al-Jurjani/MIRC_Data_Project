from pymilvus import Collection, connections, utility, FieldSchema, DataType

connections.connect("default", host="localhost", port="19530")

collection = Collection("video_embeddings")

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
    output_fields=["guid", "video_path", "transcript_path", "translation_path", "summary_path"],
    limit=10
)

for r in results:
    print(r)

print("Total rows:", collection.num_entities)
