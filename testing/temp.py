# Test your milvus connection
from pymilvus import connections
connections.connect("default", host="localhost", port="19530")
print("Milvus connected successfully!")

import whisper
print(whisper.__file__)
