import asyncio
import httpx
import os
import joblib
from sklearn.neighbors import KNeighborsClassifier

from config.settings import INTENT_CLASSIFIER_MODEL, pc_Ip

# ----------- Configuration ------------
<<<<<<< HEAD
OLLAMA_URL = "http://10.102.11.67:11434/api/embeddings"
=======
OLLAMA_URL = f"http://{pc_Ip}:11434/api/embeddings"
>>>>>>> raspberry_pi_2
MODEL_NAME = "granite-embedding:30m"
DEFAULT_CLASS = "stop"


# ----------- Embedding Functions ------------
async def _get_embedding(text: str, client: httpx.AsyncClient):
    try:
        response = await client.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": text})
        response.raise_for_status()
        return response.json().get("embedding", [])
    except Exception as e:
        print(f"❌ Error embedding '{text}': {e}")
        return []


async def _get_embeddings(texts: list[str]):
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [_get_embedding(text, client) for text in texts]
        return await asyncio.gather(*tasks)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return asyncio.run(_get_embeddings(texts))


def warm_up_ollama():
    try:
        print("⚙️ Warming up Ollama model...")
        response = httpx.post(OLLAMA_URL, json={"model": MODEL_NAME, "prompt": "warmup"})
        response.raise_for_status()
        print("✅ Ollama model is ready.")
    except Exception as e:
        print("❌ Failed to warm up Ollama:", e)


# ----------- Classifier ------------
class CommandClassifier:
    def __init__(self, commands=None, labels=None):
        self.clf = KNeighborsClassifier(n_neighbors=1)
        if os.path.exists(INTENT_CLASSIFIER_MODEL):
            print("📦 Loading pre-trained classifier...")
            self.clf = joblib.load(INTENT_CLASSIFIER_MODEL)
        else:
            if commands is None or labels is None:
                raise ValueError("Need training data to train classifier.")
            self._train(commands, labels)

    def _train(self, commands: list[str], labels: list[str]):
        print("🔍 Embedding training data...")
        embeddings = embed_texts(commands)

        valid = [(e, l) for e, l in zip(embeddings, labels) if isinstance(e, list) and len(e) > 0 and all(isinstance(x, float) for x in e)]
        if not valid:
            raise ValueError("No valid embeddings for training.")

        X, y = zip(*valid)
        if not all(len(vec) == len(X[0]) for vec in X):
            raise ValueError("Inconsistent embedding sizes.")

        print(f"📊 Training classifier on {len(X)} examples.")
        self.clf.fit(X, y)
        joblib.dump(self.clf, INTENT_CLASSIFIER_MODEL)
        print(f"💾 Classifier saved to {INTENT_CLASSIFIER_MODEL}.")

    def classify(self, text: str) -> str:
        embedding = embed_texts([text])[0]
        if not embedding or not isinstance(embedding, list):
            return DEFAULT_CLASS
        return self.clf.predict([embedding])[0]


# ----------- Run Example ------------
warm_up_ollama()

# transcribed_text = "can you tell me where i am"
# classifier = CommandClassifier(training_phrases, command_labels)
# label = classifier.classify(transcribed_text)
# print(f"\n🔮 Predicted Label: {label}")
