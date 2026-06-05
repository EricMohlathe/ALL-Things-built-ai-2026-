---
name: vertex-ai-sdk
description: >-
  Use Google Vertex AI from Python via the google-cloud-aiplatform SDK
  (installed under software/python-aiplatform). Use when the task involves
  Vertex AI, Gemini on Vertex, text/multimodal generation, embeddings,
  prediction endpoints, or deploying models on Google Cloud.
---

# Vertex AI SDK (google-cloud-aiplatform)

The `googleapis/python-aiplatform` SDK is installed live in this workspace at
`software/python-aiplatform/.venv`. This skill documents how to use it. The
upstream repo ships **no Claude skills**, so this skill is authored here to make
the SDK usable as a skill.

## Setup

```bash
# Use the workspace venv that already has the SDK installed:
source software/python-aiplatform/.venv/bin/activate

# Auth (one of):
export GOOGLE_CLOUD_PROJECT=your-project-id
export GOOGLE_CLOUD_LOCATION=us-central1
gcloud auth application-default login          # interactive
# or set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

## Text / multimodal generation (Gemini on Vertex)

```python
import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(project="your-project", location="us-central1")
model = GenerativeModel("gemini-2.0-flash")
print(model.generate_content("Summarize Vertex AI in one sentence.").text)
```

A runnable copy lives at `software/python-aiplatform/examples/quickstart.py`.

## Embeddings

```python
from vertexai.language_models import TextEmbeddingModel
emb = TextEmbeddingModel.from_pretrained("text-embedding-004")
vectors = emb.get_embeddings(["hello world"])
print(len(vectors[0].values))
```

## Custom prediction endpoints

```python
from google.cloud import aiplatform
aiplatform.init(project="your-project", location="us-central1")
endpoint = aiplatform.Endpoint("projects/.../locations/.../endpoints/...")
print(endpoint.predict(instances=[{"prompt": "hi"}]))
```

## Notes

- Verify the installed version: `python -c "import google.cloud.aiplatform as a; print(a.__version__)"`.
- Full SDK docs: https://cloud.google.com/python/docs/reference/aiplatform/latest
- This is a paid Google Cloud service; calls require a billing-enabled project.
