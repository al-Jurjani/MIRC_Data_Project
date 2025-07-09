# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# This file contains the backend logic for Part A (transcription, translation, summarization, embedding)

import os
import shutil
import uuid
import torch
import logging
import shutil
from datetime import datetime
from transformers import pipeline, AutoTokenizer, AutoModel
import whisper
from deep_translator import GoogleTranslator
from langdetect import detect
from pymilvus import Collection, connections, FieldSchema, CollectionSchema, DataType

# -------------------- Setup logging --------------------
logging.basicConfig(
    filename='video_pipeline.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# -------------------- Milvus Configuration --------------------
MILVUS_COLLECTION_NAME = "video_embeddings"
connections.connect("default", host="localhost", port="19530")

def clear_database():
    """Drop and recreate the Milvus collection to clear all data."""
    collection = Collection(MILVUS_COLLECTION_NAME)
    collection.drop()
    fields = [
        FieldSchema(name="guid", dtype=DataType.VARCHAR, max_length=36, is_primary=True, auto_id=False),
        FieldSchema(name="video_path", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="transcript_path", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="translation_path", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="summary_path", dtype=DataType.VARCHAR, max_length=500),
        FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),  # New title field
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
    ]
    schema = CollectionSchema(fields)
    collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema)
    logging.info("Milvus database cleared and recreated with new schema.")

fields = [
    FieldSchema(name="guid", dtype=DataType.VARCHAR, max_length=36, is_primary=True, auto_id=False),
    FieldSchema(name="video_path", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="transcript_path", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="translation_path", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="summary_path", dtype=DataType.VARCHAR, max_length=500),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
]
schema = CollectionSchema(fields)
# if MILVUS_COLLECTION_NAME not in list(Collection.list()):
#     collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema)
# else:
#     collection = Collection(name=MILVUS_COLLECTION_NAME)
collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema)

# -------------------- Step 1: Transcribe video using Whisper --------------------
def transcribe_video(video_path):
    print("Loading Whisper model...")
    model = whisper.load_model("base")
    print("Transcribing the video...")
    result = model.transcribe(video_path)
    transcript = result['text']
    return transcript

# -------------------- Step 2: Translate transcript to English if needed --------------------
def translate_to_english(text):
    try:
        lang = detect(text)
    except:
        lang = 'unknown'
    if lang != 'en':
        logging.info(f"Translating from {lang} to English.")
        return GoogleTranslator(source=lang, target='en').translate(text) # changed source from 'auto' to lang
    else:
        return text

# -------------------- Step 3: Summarize translated transcript --------------------
# def summarize_text(text):
#     summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6")  # Uses specific model
#     summarized = summarizer(text, max_length=100, min_length=25, do_sample=False)
#     return summarized[0]['summary_text']

import re
def clean_transcription(text):
    # Remove timestamps (e.g., [00:01:23]) and common filler words
    text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', text)
    text = re.sub(r'\b(um|uh|like|you know)\b', '', text, flags=re.IGNORECASE)
    return text.strip()

# Using Summa for extractive summarization rather than abstractive summarization
# Abstractive summarization just finds important sentences, less exhaustive
# abstractive summarization is more complex and requires more resources, generates a summary in its own words
# In addition, it has no strict length limit, so it can generate longer summaries
from summa import summarizer
def summarize_text(text):
    cleaned_text = clean_transcription(text)
    return summarizer.summarize(cleaned_text, ratio=0.25) # Summarize to 25% of original length

# -------------------- Step 4: Generate embedding using BGE --------------------
class BGEEmbedder:
    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en")
        self.model = AutoModel.from_pretrained("BAAI/bge-small-en")

    def get_embedding(self, text):
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        with torch.no_grad():
            model_output = self.model(**inputs)
        embedding = model_output.last_hidden_state[:, 0, :].squeeze().numpy()
        return embedding.tolist()

# -------------------- Step 5: Full processing pipeline --------------------
def process_video(video_path, base_save_dir, progress_callback=None):
    # generate a unique GUID for this video processing
    guid = str(uuid.uuid4())
    logging.info(f"Processing started for video: {video_path} with GUID: {guid}")

    print(f"Processing video: {video_path} with GUID: {guid}")
    # Prepare separate directories
    dirs = {
        'video': os.path.join(base_save_dir, 'videos'),
        'transcripts': os.path.join(base_save_dir, 'transcripts'),
        'translations': os.path.join(base_save_dir, 'translations'),
        'summaries': os.path.join(base_save_dir, 'summaries'),
        'embeddings': os.path.join(base_save_dir, 'embeddings')
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    # Step 0: Save renamed video
    print(f"Step 0: Renaming video to {guid}.mp4")
    new_video_path = os.path.join(dirs['video'], f"{guid}.mp4")
    # os.rename(video_path, new_video_path)
    # Move video file to new path
    # shutil.move(video_path, new_video_path)
    # video_path = os.path.abspath(video_path)
    # new_video_path = os.path.abspath(os.path.join(dirs['video'], f"{guid}.mp4"))
    shutil.copyfile(video_path, new_video_path)
    if progress_callback: progress_callback.emit(20)


    print(f"New video path: {new_video_path}")
    print(f"File exists: {os.path.exists(new_video_path)}")
    logging.info(f"Video saved at {new_video_path}")

    # Step 1: Transcription
    print(f"Step 1: Transcribing video {new_video_path}")
    transcript = transcribe_video(new_video_path)
    transcript_path = os.path.join(dirs['transcripts'], f"{guid}_transcript.txt")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(transcript)
    if progress_callback: progress_callback.emit(40)

    # Step 2: Translation
    print(f"Step 2: Translating transcript for GUID {guid}")
    translated = translate_to_english(transcript)
    translation_path = os.path.join(dirs['translations'], f"{guid}_translated_transcript.txt")
    with open(translation_path, "w", encoding="utf-8") as f:
        f.write(translated)
    if progress_callback: progress_callback.emit(60)

    # Step 3: 
    print(f"Step 3: Summarizing translated transcript for GUID {guid}")
    summary = summarize_text(translated)
    summary_path = os.path.join(dirs['summaries'], f"{guid}_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    if progress_callback: progress_callback.emit(80)

    # Step 4: Embedding
    print(f"Step 4: Generating embedding for summary for GUID {guid}")
    embedder = BGEEmbedder()
    embedding = embedder.get_embedding(summary)
    embedding_path = os.path.join(dirs['embeddings'], f"{guid}_embedding_vector.txt")
    with open(embedding_path, "w", encoding="utf-8") as f:
        f.write(",".join([str(x) for x in embedding]))

    # Step 5: Store all paths in Milvus
    print(f"Step 5: Storing GUID {guid} in Milvus")
    collection.insert([
        [guid],
        [new_video_path],
        [transcript_path],
        [translation_path],
        [summary_path],
        [embedding]
    ])
    collection.flush()
    logging.info(f"Stored GUID {guid} in Milvus with all file paths.")

    logging.info(f"Processing completed for GUID: {guid}")
    print(f"Processing completed for GUID: {guid}")
    return guid

# Example usage:
# process_video("sample.mp4", "processed")