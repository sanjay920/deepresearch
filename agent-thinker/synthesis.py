from openai import OpenAI
from config import config
import logging

client = OpenAI(api_key=config["openai_api_key"])


class SynthesisAgent:
    """Agent that synthesizes retrieved data into a coherent summary."""

    def synthesize(self, query: str, data: str) -> str:
        """Generate a summary based on retrieved data using OpenAI."""
        prompt = (
            f"Based on the following information, provide a detailed summary for the query: '{query}'\n\n"
            f"Data:\n{data}\n\n"
            "Please format your response in Markdown with clear headings and bullet points where appropriate."
        )
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
            )
            summary = response.choices[0].message.content
            logging.info(f"Synthesized summary for query: {query}")
            return summary
        except Exception as e:
            logging.error(f"Synthesis failed for query '{query}': {e}")
            raise Exception(f"Synthesis failed: {e}")
