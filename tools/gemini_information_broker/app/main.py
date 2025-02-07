import os
import logging
from typing import List, Optional, Dict
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

# Import the Gemini client libraries.
from google import genai
from google.genai import types

# Configure logging.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gemini Microservice",
    description=(
        "A microservice API that wraps the Gemini API. It accepts a prompt, "
        "calls Gemini to generate content, formats the response with inline "
        "citations (if available) along with a sources list and search queries, "
        "and returns the result."
    ),
    version="1.0.0",
)

# Retrieve the Gemini API key from environment variables.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY environment variable must be set")
    raise Exception("GEMINI_API_KEY environment variable must be set")

# Instantiate the Gemini client.
client = genai.Client(api_key=GEMINI_API_KEY)

# Add cache for TinyURLs to avoid repeated API calls
tinyurl_cache: Dict[str, str] = {}


def get_tinyurl(long_url: str) -> str:
    """Convert a long URL to a TinyURL, using cache to avoid duplicate calls."""
    if long_url in tinyurl_cache:
        return tinyurl_cache[long_url]

    try:
        api_endpoint = "https://tinyurl.com/api-create.php"
        params = {"url": long_url}
        response = requests.get(api_endpoint, params=params, timeout=5)

        if response.status_code == 200:
            short_url = response.text
            tinyurl_cache[long_url] = short_url
            return short_url
    except Exception as e:
        logger.warning(f"Failed to create TinyURL for {long_url}: {e}")

    # Return original URL if TinyURL creation fails
    return long_url


class GenerateRequest(BaseModel):
    prompt: str


def optimize_citations(grounding_metadata, max_sources=5):
    """
    Optimize citation selection while ensuring all segments have citations.
    Only reduces citations when over max_sources limit.
    """
    # Track how many segments each source supports.
    source_usage = (
        {}
    )  # chunk_index -> {segment_count, confidence_sums, segment_indices, confidence_by_segment}

    # First pass: gather statistics about each source.
    for i, support in enumerate(grounding_metadata.grounding_supports):
        for j, chunk_index in enumerate(support.grounding_chunk_indices):
            if chunk_index not in source_usage:
                source_usage[chunk_index] = {
                    "segment_count": 0,
                    "confidence_sums": 0,
                    "segment_indices": set(),
                    "confidence_by_segment": {},  # segment_index -> confidence
                }
            source_usage[chunk_index]["segment_count"] += 1
            source_usage[chunk_index]["confidence_sums"] += support.confidence_scores[j]
            source_usage[chunk_index]["segment_indices"].add(i)
            source_usage[chunk_index]["confidence_by_segment"][i] = (
                support.confidence_scores[j]
            )

    # Calculate average confidence for each source.
    for chunk_index in source_usage:
        source_usage[chunk_index]["avg_confidence"] = (
            source_usage[chunk_index]["confidence_sums"]
            / source_usage[chunk_index]["segment_count"]
        )

    # Map segments to their citations.
    segment_citations = {}  # segment_index -> [chunk_indices]

    total_sources = len(
        set().union(
            *[
                set(support.grounding_chunk_indices)
                for support in grounding_metadata.grounding_supports
            ]
        )
    )

    # If we're under the max_sources limit, keep all citations.
    if total_sources <= max_sources:
        for i, support in enumerate(grounding_metadata.grounding_supports):
            if support.grounding_chunk_indices:
                segment_citations[i] = list(support.grounding_chunk_indices)
        return segment_citations, list(source_usage.keys())

    # Otherwise, optimize citations.
    sorted_sources = sorted(
        source_usage.items(),
        key=lambda x: (x[1]["segment_count"], x[1]["avg_confidence"]),
        reverse=True,
    )

    primary_sources = sorted_sources[:max_sources]
    primary_source_indices = {chunk_index for chunk_index, _ in primary_sources}

    # For each segment, select citations.
    for i, support in enumerate(grounding_metadata.grounding_supports):
        if not support.grounding_chunk_indices:
            continue

        citations_with_scores = list(
            zip(support.grounding_chunk_indices, support.confidence_scores)
        )

        # If the segment has only one source, keep it.
        if len(citations_with_scores) == 1:
            segment_citations[i] = [citations_with_scores[0][0]]
            primary_source_indices.add(citations_with_scores[0][0])
            continue

        # For multiple sources, try to use primary sources.
        primary_citations = [
            (idx, score)
            for idx, score in citations_with_scores
            if idx in primary_source_indices
        ]

        if primary_citations:
            # Use the best primary source.
            best_primary = max(primary_citations, key=lambda x: x[1])
            segment_citations[i] = [best_primary[0]]
        else:
            # If no primary source is available, use the best available source.
            best_source = max(citations_with_scores, key=lambda x: x[1])
            segment_citations[i] = [best_source[0]]
            primary_source_indices.add(best_source[0])

    return segment_citations, list(primary_source_indices)


def format_text_with_optimized_citations(response, max_sources=5):
    """Format text with citations and include sources and search queries."""
    text = response.candidates[0].content.parts[0].text
    grounding_metadata = response.candidates[0].grounding_metadata

    # If no grounding metadata or no grounding supports are present, return the original text
    if not grounding_metadata or not grounding_metadata.grounding_supports:
        return text

    # Get optimized citations per segment
    segment_citations, selected_chunks = optimize_citations(
        grounding_metadata, max_sources
    )

    modified_text = text
    citation_references = {}  # Map chunk_index to a reference number
    used_chunks = set()
    for citations in segment_citations.values():
        used_chunks.update(citations)

    # Assign reference numbers
    for i, chunk_index in enumerate(sorted(used_chunks), 1):
        citation_references[chunk_index] = i

    # Process each segment in reverse order (to preserve string indices)
    segments = [
        (support.segment, i)
        for i, support in enumerate(grounding_metadata.grounding_supports)
    ]
    segments.sort(
        key=lambda x: x[0].start_index if x[0].start_index is not None else 0,
        reverse=True,
    )

    for segment, segment_index in segments:
        if segment_index in segment_citations:
            citations = segment_citations[segment_index]
            citation_nums = sorted([citation_references[idx] for idx in citations])
            citation_string = f"[{', '.join(str(num) for num in citation_nums)}]"
            if segment.start_index is not None and segment.end_index is not None:
                modified_text = (
                    modified_text[: segment.end_index]
                    + citation_string
                    + modified_text[segment.end_index :]
                )
            else:
                modified_text = modified_text.replace(
                    segment.text, f"{segment.text}{citation_string}"
                )

    # Build the sources list with TinyURLs
    sources = []
    for chunk_index, ref_num in sorted(citation_references.items(), key=lambda x: x[1]):
        web_info = grounding_metadata.grounding_chunks[chunk_index].web
        if web_info:
            # Convert vertexaisearch URLs to TinyURLs
            if "vertexaisearch.cloud.google.com" in web_info.uri:
                short_url = get_tinyurl(web_info.uri)
                sources.append(f"{ref_num}. [{web_info.title}]({short_url})")
            else:
                sources.append(f"{ref_num}. [{web_info.title}]({web_info.uri})")

    # Combine everything
    output = [modified_text, "\nSources:"]
    output.extend(sources)

    # Add search queries if they exist
    if grounding_metadata.web_search_queries:
        output.extend(
            [
                "\nSearch Queries:",
                *[f"- {query}" for query in grounding_metadata.web_search_queries],
            ]
        )

    return "\n".join(output)


@app.post("/generate", summary="Generate text using Gemini API")
def generate_text(request: GenerateRequest):
    """
    Generate text from a given prompt using the Gemini API.
    Returns the generated text with inline citations (if available).
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-pro-exp-02-05",
            contents=request.prompt,
            config=types.GenerateContentConfig(
                system_instruction=f"You are a helpful assistant. Today's date is {datetime.now().strftime('%Y-%m-%d')}",
                tools=[types.Tool(google_search=types.GoogleSearchRetrieval)],
            ),
        )
    except Exception as e:
        logger.exception("Error calling Gemini API")
        raise HTTPException(status_code=500, detail="Error generating text")

    formatted_text = format_text_with_optimized_citations(response, max_sources=5)
    return {"response": formatted_text}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=80, reload=True)
