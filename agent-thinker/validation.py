from openai import OpenAI
from config import config
import logging
import tiktoken

client = OpenAI(api_key=config["openai_api_key"])


class ValidationAgent:
    def validate(self, summary: str, sources: str) -> str:
        """Verify that factual claims in the summary have citations, using multiple passes if needed."""
        # Token limit for each chunk (leave buffer for prompt)
        MAX_TOKENS_PER_PASS = 100000
        encoding = tiktoken.encoding_for_model(config["model"])

        # Split summary into chunks
        summary_tokens = encoding.encode(summary)
        chunks = []
        current_chunk = []
        current_count = 0

        for token in summary_tokens:
            if current_count + 1 > MAX_TOKENS_PER_PASS:
                chunks.append(encoding.decode(current_chunk))
                current_chunk = [token]
                current_count = 1
            else:
                current_chunk.append(token)
                current_count += 1
        if current_chunk:
            chunks.append(encoding.decode(current_chunk))

        logging.info(f"Split summary into {len(chunks)} chunks for validation.")

        # Validate each chunk
        reports = []
        for i, chunk in enumerate(chunks, 1):
            prompt = (
                f"Check the following summary chunk for factual claims without citations. "
                f"A factual claim is any statement about players, teams, or ages that isn’t "
                f"general knowledge (e.g., 'The sky is blue'). Each claim should have a citation "
                f"like [n]. List any uncited claims in Markdown. If all claims are cited, say 'All claims cited.'\n\n"
                f"Chunk {i}:\n{chunk}"
            )
            try:
                response = client.chat.completions.create(
                    model=config["model"],
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,  # Adjust based on expected output size
                )
                report = response.choices[0].message.content
                reports.append(f"### Chunk {i} Validation\n{report}")
            except Exception as e:
                logging.error(f"Validation failed for chunk {i}: {e}")
                reports.append(f"### Chunk {i} Validation\nError: {str(e)}")

        # Combine reports
        final_report = "\n\n".join(reports)
        logging.info("Generated multi-pass validation report")
        return final_report
