import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Router Microservice",
    description="A microservice API that routes user queries based on complexity.",
    version="1.0.0",
)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


class RouteRequest(BaseModel):
    message: str


@app.post("/route", summary="Route user query")
async def route_query(request: RouteRequest):
    """
    Analyze the user's query and route it accordingly.
    The response must follow this JSON format:

    ```json
    {
      "is_complex": [true/false],
      "response/routing": [response or indicate routing to planning assistant]
    }
    ```
    """
    # Define the system message as a list of content items (each with text and type)
    system_message_content = [
        {
            "text": (
                "You are a routing agent tasked with determining the complexity of user queries and providing appropriate responses. "
                "If the user's query is complex and challenging, route it to the planning assistant. For less complex queries, utilize available functions to provide an immediate response. "
                "If you choose to use the query_information_broker tool, the query you give it must consist of complete sentences - you dont want to disrespect your colleague. "
                "If you do call query_information_broker, make sure to include citations in your final response back to the user the same way the query_information_broker does citations - here's an example:\n\n"
                "*   **Dried or Dehydrated Products:** Including items specifically marked as dehydrated.[1, 2, 3, 4]\n"
                "*   **Frozen or Chilled Products:** Including items in the Frozen/Chilled section.[1, 3, 5]\n\n"
                'The search results indicate that you can request copies of these standards from the "Processed Products Standardization and Inspection Branch, '
                'Fruit and Vegetable Division, AMS, U. S. Department of Agriculture, Washington 25, D. C."[1]\n\n\n'
                "Sources:\n"
                "1. [wikimedia.org](https://tinyurl.com/2cobgzpz)\n"
                "2. [ncrfsma.org](https://tinyurl.com/269njje2)\n\n\n"
                "# Steps\n\n"
                "1. Analyze the user's query:\n"
                "   - Determine if the query is complex or straightforward.\n"
                "   - Use complexity cues (e.g., open-ended questions, ambiguous terms).\n\n"
                "2. Route or respond:\n"
                "   - If complex, forward the query to the planning assistant.\n"
                '   - If straightforward, attempt to answer using available functions (e.g., "what is the date today?").\n\n'
                "# Output Format\n\n"
                "Your output must be in the following JSON format (and nothing else):\n\n"
                "```json\n"
                "{\n"
                '  "is_complex": [true/false],\n'
                '  "response/routing": [response or indicate routing to planning assistant]\n'
                "}\n"
                "```\n\n"
                "# Notes\n\n"
                "- Ensure clarity and precision in determining the complexity of queries.\n"
                "- Adjust the response based on the complexity assessment."
            ),
            "type": "text",
        }
    ]

    # Construct the messages list
    messages = [
        {
            "role": "system",
            "content": system_message_content,
        },
        {
            "role": "user",
            "content": [
                {
                    "text": request.message,
                    "type": "text",
                }
            ],
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"},
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "query_information_broker",
                        "strict": True,
                        "parameters": {
                            "type": "object",
                            "required": ["query"],
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "The query/ask for the information broker. Must be a complete sentence - something descriptive enough for them to get context",
                                }
                            },
                            "additionalProperties": False,
                        },
                        "description": "An information broker that takes in a query and searches the web using Google to provide an answer.",
                    },
                }
            ],
            temperature=0.07,
            max_completion_tokens=10831,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        # The response is already a JSON object per the response_format.
        parsed_response = response
    except Exception as e:
        logger.exception("Error processing query")
        raise HTTPException(status_code=500, detail="Error processing query")

    return parsed_response
