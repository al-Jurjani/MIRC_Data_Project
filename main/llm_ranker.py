# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# File: llm_ranker.py
# Uses a local LLM to rank query relevance to transcript

from sentence_transformers import SentenceTransformer, util
import nltk
import torch
nltk.download('punkt')
nltk.download('punkt_tab')
from nltk.tokenize import sent_tokenize

class LocalLLMRanker:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)

    def score_pair(self, query, transcript, top_k=5):
        sentences = sent_tokenize(transcript)
        if not sentences:
            return []

        query_embedding = self.model.encode(query, convert_to_tensor=True)
        sentence_embeddings = self.model.encode(sentences, convert_to_tensor=True)

        similarities = util.cos_sim(query_embedding, sentence_embeddings)[0]  # shape: [num_sentences]
        top_indices = torch.topk(similarities, k=min(top_k, len(sentences))).indices.tolist()

        top_results = [
            {
                "score": similarities[idx].item(),
                "sentence": sentences[idx]
            }
            for idx in top_indices
        ]

        return top_results