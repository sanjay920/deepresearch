from openai import OpenAI
from config import config
import logging
import json

client = OpenAI(api_key=config["openai_api_key"])


class SynthesisAgent:
    """Agent that synthesizes retrieved data into a coherent summary."""

    def synthesize(self, query: str, retrieval_results: list, iteration: int) -> str:
        """
        Generate a summary based on retrieved data using OpenAI.

        Args:
            query (str): The user's query.
            retrieval_results (list): List of retrieval results, each with 'type' and data.
            iteration (int): Current synthesis iteration number.

        Returns:
            str: JSON string containing 'status', 'summary', and optionally 'additional_tasks'.
        """
        logging.info(f"Starting synthesis for iteration {iteration}")
        logging.info(f"Number of retrieval results: {len(retrieval_results)}")

        # Format the retrieved data into the prompt
        data_str = ""
        for idx, retrieval in enumerate(retrieval_results, 1):
            try:
                if retrieval["type"] == "search":
                    data_str += (
                        f"[Source {idx}] Search Results for '{retrieval['query']}':\n"
                    )
                    for item in retrieval["results"]["items"]:
                        data_str += (
                            f"- {item['title']} ({item['link']})\n  {item['snippet']}\n"
                        )
                    data_str += "\n"
                elif retrieval["type"] == "scrape":
                    data_str += f"[Source {idx}] Scraped Content from {retrieval['url']}:\n{retrieval['content'][:1000]}...\n\n"
            except Exception as e:
                logging.error(f"Error processing retrieval result {idx}: {e}")
                continue

        logging.info("Formatted data, calling OpenAI API")

        # Define the synthesis prompt
        prompt = (
            f"This is synthesis iteration {iteration}. If iteration >= 3, generate the best possible summary with available data, noting any missing information.\n"
            f"Based on the following information, provide a detailed summary for the query: '{query}'\n\n"
            f"Data:\n{data_str}\n"
            "Respond with a JSON object containing:\n"
            "- 'status': ('complete' or 'incomplete')\n"
            "- 'summary': (formatted in Markdown)\n"
            "- 'additional_tasks': (array of objects with 'tool' and 'parameters' if status is 'incomplete')\n\n"
            "For 'complete', format the summary in Markdown with clear headings and bullet points. Include citations [1], [2], etc.\n"
            "For 'incomplete', include additional_tasks for more information needed."
        )

        try:
            # Call the OpenAI API with a timeout
            response = client.chat.completions.create(
                model=config["model"],
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=2000,
                timeout=30,  # Add timeout
            )

            logging.info("Received response from OpenAI API")
            synthesis_output = json.loads(response.choices[0].message.content)
            return json.dumps(synthesis_output)

        except Exception as e:
            logging.error(f"Synthesis failed for query '{query}': {e}")
            # Return a valid JSON response even in case of error
            error_response = {
                "status": "complete",
                "summary": f"Error during synthesis: {str(e)}",
                "additional_tasks": [],
            }
            return json.dumps(error_response)
