from __future__ import annotations

from functools import lru_cache

from google import genai
from langchain_core.embeddings import Embeddings


@lru_cache(maxsize=1)
def _get_client(api_key: str | None) -> genai.Client:
    return genai.Client(api_key=api_key)


class GeminiEmbeddings(Embeddings):
    def __init__(self, model_name: str, api_key: str | None = None):
        self._model_name = model_name
        self._api_key = api_key

    @property
    def _client(self) -> genai.Client:
        return _get_client(self._api_key)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        # Batch in chunks of 100 to stay within API limits
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self._client.models.embed_content(
                model=self._model_name,
                contents=batch,
            )
            for emb in response.embeddings:
                results.append(list(emb.values))
        return results

    def embed_query(self, text: str) -> list[float]:
        response = self._client.models.embed_content(
            model=self._model_name,
            contents=[text],
        )
        return list(response.embeddings[0].values)


# Keep MiniLMEmbeddings as alias so existing imports in metrics.py continue to work
MiniLMEmbeddings = GeminiEmbeddings
