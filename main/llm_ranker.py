# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# File: llm_ranker.py
# Uses a local LLM to rank query relevance to transcript

# from transformers import AutoModelForCausalLM, AutoTokenizer
# from transformers import T5Tokenizer, T5ForConditionalGeneration
# from sentence_transformers import SentenceTransformer, util
# import torch
# import numpy as np

# class LocalLLMRanker:
#     def __init__(self, model_name="google/flan-t5-small"):
#         self.tokenizer = T5Tokenizer.from_pretrained(model_name)
#         self.model = T5ForConditionalGeneration.from_pretrained(model_name,
#             torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
#             device_map="auto"
#         )

#     def score_pair(self, query, transcript):
#         print(f"Scoring query: {query} with transcript length: {len(transcript)}")
#         print(f"Model device: {self.model.device}")
#         print(f"Model dtype: {self.model.dtype}")
#         print(f"Model Name: {self.model.name_or_path}")

#         prompt = (
#             f"You are a helpful assistant. Score how relevant the following transcript is to the given query.\n"
#             f"Query: {query}\n"
#             f"Transcript: {transcript}\n"
#             f"Give a single number between 0 (not related) and 1 (very relevant)."
#         )
#         inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
#         outputs = self.model.generate(**inputs, max_new_tokens=10)
#         decoded = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
#         score = self.extract_score(decoded)
#         print(f"Extracted score: {score} from output: {decoded}")
#         return score

#     def extract_score(self, text):
#         # Extract number between 0 and 1
#         import re
#         matches = re.findall(r"0(?:\\.\\d+)?|1(?:\\.0*)?", text)
#         if matches:
#             return float(matches[-1])
#         return 0.0

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