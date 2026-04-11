"""Local LLM analysis: extract query-relevant information from scraped pages."""
import os

from lib.logging import progress, warn
from lib.settings import ROOT, settings

PROMPT_TEMPLATE = """Extract information relevant to the query from this page content.
Focus on: project names, features, technical details, URLs, and anything directly useful.
Skip: boilerplate, navigation, ads, unrelated content.
Be concise. Only include what's relevant.

Query: {query}

Content:
{content}

Relevant information:"""


class LLMAnalyzer:
    """Extract query-relevant information from pages using a local GGUF model."""

    def __init__(self):
        self._model = None

    def analyze_page(self, content: str, query: str) -> str | None:
        """Extract query-relevant information from a single page."""
        model = self._get_model()
        if model is None:
            return None

        llm_settings = settings.llm

        max_input = llm_settings.max_input_chars
        if len(content) > max_input:
            content = content[:max_input]

        prompt = PROMPT_TEMPLATE.format(query=query, content=content)

        try:
            output = model(
                prompt,
                max_tokens=llm_settings.max_tokens,
                temperature=llm_settings.temperature,
                stop=["Query:", "\n\n\n"],
            )
            text = output["choices"][0]["text"].strip()
            return text if text else None
        except Exception as err:
            warn(f"LLM error: {err}")
            return None

    def analyze_entries(self, entries: list[dict], queries: list[str]) -> list[dict]:
        """Run LLM analysis on all entries with content. Mutates entries in place."""
        query_str = " ".join(queries)
        analyzable = [e for e in entries if e.get("content") and len(e["content"]) > settings.scoring.min_text]

        if not analyzable:
            return entries

        model = self._get_model()
        if model is None:
            return entries

        with progress("Analyzing with LLM", total=len(analyzable)) as advance:
            for entry in analyzable:
                query = entry.get("query", query_str)
                analysis = self.analyze_page(entry["content"], query)
                if analysis:
                    entry["llm_analysis"] = analysis
                advance()

        return entries

    def _get_model(self):
        if self._model is not None:
            return self._model

        from llama_cpp import Llama

        llm_settings = settings.llm
        model_path = llm_settings.model_path

        if not os.path.isabs(model_path):
            model_path = os.path.join(ROOT, model_path)

        if not os.path.exists(model_path):
            warn(f"LLM model not found: {model_path}")
            warn("Download a GGUF model and set llm.model_path in config.yaml")
            return None

        self._model = Llama(
            model_path=model_path,
            n_ctx=llm_settings.context_length,
            n_threads=llm_settings.threads,
            verbose=False,
        )
        return self._model


analyzer = LLMAnalyzer()
