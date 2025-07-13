# Bismillah
# Starting project on 07-01-1447 - 03-07-2025

# File: chat_handler_service.py
# Ranks top-k results from Milvus using a local LLM based on transcript relevance

from main.llm_ranker import LocalLLMRanker

ranker = LocalLLMRanker()

def rerank_top_matches(user_query, retrieved_matches):
    # scored = []
    all_scored_chunks = []
    for item in retrieved_matches:
        guid = item["guid"]
        transcript_path = item["transcript_path"]
        translation_path = item["translation_path"]
        title = item["title"]

        try:
            with open(translation_path, encoding="utf-8") as f:
                transcript = f.read()
        except:
            transcript = ""

    #     score = ranker.score_pair(user_query, transcript)
    #     scored.append({
    #         "guid": guid,
    #         "title": title,
    #         "video_path": item["video_path"],
    #         "score": score
    #     })

    # # Sort by descending score
    # scored.sort(key=lambda x: x["score"], reverse=True)
    # return scored[:5]  # return top 5

        top_matches = ranker.score_pair(user_query, transcript, top_k=15)

        # scored.append({
        #     "guid": guid,
        #     "title": title,
        #     "video_path": item["video_path"],
        #     "matches": top_matches
        # })
        for match in top_matches:
            all_scored_chunks.append({
                "guid": guid,
                "title": title,
                "video_path": item["video_path"],
                "score": match["score"],
                "sentence": match["sentence"]
            })

    # # Sort by the best sentence score in each result
    # scored.sort(key=lambda x: x["matches"][0]["score"] if x["matches"] else 0, reverse=True)
    # Sort all matches across all videos
    all_scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return all_scored_chunks[:5]  # return top 5