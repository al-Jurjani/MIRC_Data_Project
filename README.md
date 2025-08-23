# 🎥 MIRC Data Project – Video Transcription & Search Platform

[**MIRC – Machine Intelligence Research Center (Pakistan)**](https://mirc.org.pk/)  
[Milvus Vector Database](https://milvus.io/) • [OpenAI Whisper](https://github.com/openai/whisper) • [Hugging Face Transformers](https://huggingface.co/transformers/)  

---

## 📌 Overview
This project is a desktop application (built with **PyQt5**) that allows users to **ingest videos, transcribe, translate, summarize, and search them efficiently** using modern NLP and vector search techniques.

It is developed as part of MIRC’s research efforts to make multimedia archives searchable with **AI + Vector Databases**.

---

## 🚀 Features
- Upload and process videos locally:
  - **Transcription** with Whisper
  - **Translation** to English (Deep Translator)
  - **Summarization** (DistilBART)
  - **Embeddings** via [BAAI/bge-small-en](https://huggingface.co/BAAI/bge-small-en)
- Store processed data in **Milvus** vector database
- **Semantic query search** across video summaries
- **Re-ranking** of results with [MiniLM](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- Integrated **GUI**:
  - Video upload tab (with progress tracking)
  - Query search tab (with thumbnail previews and Play button)
  - Database browser tab (inspect stored metadata)

---

## 📂 Repository Structure
```
MIRC_Data_Project/
├─ docker-compose.yml        # Launch Milvus (etcd + MinIO + standalone)
├─ main/
│  ├─ frontend.py            # PyQt5 GUI
│  ├─ pipeline.py            # Video → Text → Embedding pipeline
│  ├─ query_backend.py       # Query → Embed → Milvus search
│  ├─ chat_handler_service.py# Re-ranking service
│  ├─ llm_ranker.py          # MiniLM scoring
│  ├─ db_browser_backend.py  # Metadata fetch + DB browser support
│  └─ mirc_logo.jpg
├─ testing/
│  ├─ check_db.py            # Milvus test queries
│  └─ temp.py                # Connection smoke test
└─ Project_Sequence_Diagram.jpg
```

---

## 🛠️ Setup & Installation

### 1. Clone this repo
```bash
git clone https://github.com/al-Jurjani/MIRC_Data_Project.git
cd MIRC_Data_Project
```

### 2. Start Milvus via Docker
Make sure Docker & docker-compose are installed. Then:
```bash
docker compose up -d
```
Services exposed:
- Milvus: `localhost:19530`
- MinIO: `localhost:9000`
- Dashboard: `localhost:9091`

### 3. Install Python dependencies
> Python 3.9–3.11 recommended. Install [ffmpeg](https://ffmpeg.org/) for Whisper.
```bash
pip install -r requirements.txt
```

Example `requirements.txt`:
```txt
pyqt5
numpy
opencv-python
torch
transformers
sentence-transformers
openai-whisper
deep-translator
langdetect
pymilvus>=2.4.3
nltk
```

### 4. Run the app
```bash
python main/frontend.py
```

---

## 💡 How It Works

### Upload / Processing Pipeline
1. Copy video to local `videos/`
2. Generate transcript (Whisper)
3. Translate transcript to English (if needed)
4. Summarize with DistilBART
5. Create embeddings (BGE-small-en)
6. Store all metadata + files in Milvus

### Query Search
1. User enters query
2. Query embedded (BGE-small-en)
3. Vector search in Milvus (top-K)
4. Re-rank results with MiniLM sentence similarity
5. Results displayed in GUI with thumbnails and play option

---

## 📸 Screenshots
_(add GUI screenshots here if available)_

---

## ⚠️ Notes & Gotchas
- First run downloads large models (Whisper, DistilBART, BGE) → expect several GBs of downloads.
- `ffmpeg` **must** be installed and on PATH.
- Ensure collection name is consistent (`video_embeddings_v8`).
- For large transcripts, summarization may need chunking.

---

## 🧭 Roadmap
- [ ] Add requirements.txt (currently inlined above)
- [ ] Add `.env` config for Milvus host/port
- [ ] Optimize summarization (chunk + merge)
- [ ] Package into installer (PyInstaller)
- [ ] Add test fixtures (small videos) for CI

---

## 📜 License
MIT License. See [LICENSE](LICENSE) file.

---

## 🤝 Acknowledgements
- [MIRC Pakistan](https://mirc.org.pk/)
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Hugging Face Transformers](https://huggingface.co/transformers)
- [Milvus Vector DB](https://milvus.io/)
