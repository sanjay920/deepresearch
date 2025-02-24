# Deep Research

```mermaid
sequenceDiagram
    participant U as User
    participant CLI as cli.py
    participant Convo as conversation.py
    participant LLM as llm_client.py
    participant TD as tool_dispatcher.py
    participant O as orchestrator.py
    participant R as retrieval.py
    participant G as google_search.py
    participant SU as scrape_urls.py
    participant SP as switch_personas.py
    participant S as synthesis.py
    participant V as validation.py

    U->>CLI: "Create a 50-page research report on AI agent platforms..."
    CLI->>Convo: Store user message in conversation
    CLI->>LLM: Send conversation to LLM
    Note over LLM: LLM decides to plan a complex multi-step task
    LLM->>TD: Tool call: switch_personas(switch_to="thinker")
    TD->>SP: switch_personas_call("thinker", conversation)
    SP->>Convo: Retrieve conversation history
    SP-->>TD: Returns JSON plan with steps (e.g., google_search, scrape_urls)
    TD-->>LLM: Plan forwarded to LLM
    LLM->>CLI: Assistant message with tool call result
    CLI->>Convo: Store assistant message with plan

    Note over CLI: CLI processes thinker’s plan steps
    CLI->>O: Add retrieval tasks from plan (e.g., google_search "AI agent platforms 2025")
    O->>R: Calls RetrievalAgent.search(query)
    R->>G: google_search_call(query)
    G-->>R: JSON search results
    R-->>O: Return search results
    CLI->>O: Add retrieval tasks (e.g., scrape_urls for Gartner pages)
    O->>R: Calls RetrievalAgent.retrieve_webpages(urls)
    R->>SU: scrape_urls_call(urls)
    SU-->>R: Markdown content
    R-->>O: Return scraped content

    Note over O: Orchestrator queues synthesis after retrievals
    O->>S: Calls SynthesisAgent.synthesize(query, retrieval_results)
    S->>LLM: Request summary generation
    LLM-->>S: JSON with status, summary, and possibly additional_tasks
    Note over S: If incomplete, suggest more retrievals
    S-->>O: Return synthesis result (e.g., incomplete with new tasks)
    O->>R: Add new retrieval tasks (e.g., scrape blogs, tweets)
    R->>SU: scrape_urls_call(new_urls)
    SU-->>R: New content
    R-->>O: Return new data

    Note over O: Second synthesis iteration
    O->>S: Synthesize again with all data
    S->>LLM: Generate final 50-page report summary
    LLM-->>S: JSON with status="complete", Markdown summary
    S-->>O: Return complete synthesis

    O->>V: Calls ValidationAgent.validate(summary)
    V->>LLM: Verify citations in summary
    LLM-->>V: Validation report
    V-->>O: Return validation result

    O-->>CLI: Final validated summary
    CLI->>U: Display 50-page report in Markdown
```
