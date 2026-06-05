"""Minimal Vertex AI quickstart using google-cloud-aiplatform.

Set up auth first:
    export GOOGLE_CLOUD_PROJECT=your-project
    gcloud auth application-default login
"""
import os
import vertexai
from vertexai.generative_models import GenerativeModel

def main():
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.0-flash")
    resp = model.generate_content("In one sentence, what is Vertex AI?")
    print(resp.text)

if __name__ == "__main__":
    main()
