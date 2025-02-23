from openai import OpenAI
from config import config
import logging

client = OpenAI(api_key=config["openai_api_key"])


class ValidationAgent:
    """Agent that validates the accuracy of synthesized summaries."""

    def validate(self, summary: str, sources: str) -> str:
        """Verify summary against sources using OpenAI."""
        prompt = (
            f"Verify the following summary against the provided sources. Identify any inaccuracies or unsupported claims.\n\n"
            f"Summary:\n{summary}\n\n"
            f"Sources:\n{sources}\n\n"
            "Provide a detailed validation report in Markdown format."
        )
        try:
            response = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5000,
            )
            report = response.choices[0].message.content
            logging.info("Generated validation report")
            return report
        except Exception as e:
            logging.error(f"Validation failed: {e}")
            raise Exception(f"Validation failed: {e}")
