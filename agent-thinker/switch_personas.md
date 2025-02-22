```python
from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```


```python
SYSTEM_PROMPT = 'You have access to the following tools. Come up with a plan that leverages these tools.\n[\n    {\n      "type": "function",\n      "function": {\n        "name": "scrape_urls",\n        "strict": True,\n        "parameters": {\n          "type": "object",\n          "required": [\n            "urls",\n            "use_cache"\n          ],\n          "properties": {\n            "urls": {\n              "type": "array",\n              "items": {\n                "type": "string",\n                "description": "A single URL of a webpage"\n              },\n              "description": "An array of string URLs of the webpages to scrape"\n            },\n            "use_cache": {\n              "type": "boolean",\n              "description": "Flag to indicate whether to use cached data (default is true). Set to false when fetching a webpage with live info such as espn.com/nba/scoreboard or anything with dynamic content"\n            }\n          },\n          "additionalProperties": False\n        },\n        "description": "Scrapes a webpage and returns its markdown equivalent"\n      }\n    },\n    {\n      "type": "function",\n      "function": {\n        "name": "switch_personas",\n        "strict": True,\n        "parameters": {\n          "type": "object",\n          "required": [\n            "switch_to"\n          ],\n          "properties": {\n            "switch_to": {\n              "enum": [\n                "agent",\n                "thinker"\n              ],\n              "type": "string",\n              "description": "The persona to switch to"\n            }\n          },\n          "additionalProperties": False\n        },\n        "description": "Ability to switch personas in the middle of the conversation"\n      }\n    },\n    {\n      "type": "function",\n      "function": {\n        "name": "google_search",\n        "description": "Performs a Google search with the specified query and returns results.",\n        "parameters": {\n          "type": "object",\n          "required": [\n            "q"\n          ],\n          "properties": {\n            "q": {\n              "type": "string",\n              "description": "The search query string."\n            }\n          },\n          "additionalProperties": False\n        },\n        "strict": True\n      }\n    }\n  ]\n\n\nToday\'s date is Feb 14, 2025. Do not simulate answers - your responsibility is to think and plan.'

print(SYSTEM_PROMPT)
```

    You have access to the following tools. Come up with a plan that leverages these tools.
    [
        {
          "type": "function",
          "function": {
            "name": "scrape_urls",
            "strict": True,
            "parameters": {
              "type": "object",
              "required": [
                "urls",
                "use_cache"
              ],
              "properties": {
                "urls": {
                  "type": "array",
                  "items": {
                    "type": "string",
                    "description": "A single URL of a webpage"
                  },
                  "description": "An array of string URLs of the webpages to scrape"
                },
                "use_cache": {
                  "type": "boolean",
                  "description": "Flag to indicate whether to use cached data (default is true). Set to false when fetching a webpage with live info such as espn.com/nba/scoreboard or anything with dynamic content"
                }
              },
              "additionalProperties": False
            },
            "description": "Scrapes a webpage and returns its markdown equivalent"
          }
        },
        {
          "type": "function",
          "function": {
            "name": "switch_personas",
            "strict": True,
            "parameters": {
              "type": "object",
              "required": [
                "switch_to"
              ],
              "properties": {
                "switch_to": {
                  "enum": [
                    "agent",
                    "thinker"
                  ],
                  "type": "string",
                  "description": "The persona to switch to"
                }
              },
              "additionalProperties": False
            },
            "description": "Ability to switch personas in the middle of the conversation"
          }
        },
        {
          "type": "function",
          "function": {
            "name": "google_search",
            "description": "Performs a Google search with the specified query and returns results.",
            "parameters": {
              "type": "object",
              "required": [
                "q"
              ],
              "properties": {
                "q": {
                  "type": "string",
                  "description": "The search query string."
                }
              },
              "additionalProperties": False
            },
            "strict": True
          }
        }
      ]
    
    
    Today's date is Feb 14, 2025. Do not simulate answers - your responsibility is to think and plan.



```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "action_schema",
        "strict": True,
        "schema": {
            "type": "object",
            "required": ["action", "text", "respond_to_user"],
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text of the questions or the text of a detailed plan.",
                },
                "action": {
                    "enum": ["questions", "plan"],
                    "type": "string",
                    "description": "Defines the type of action whether it is a set of questions or a detailed plan.",
                },
                "respond_to_user": {
                    "type": "boolean",
                    "description": "Normally, you are responding to the assistant. In the case you are synthesizing the final answer you can choose to bypass this and respond directly to the user.",
                },
            },
            "additionalProperties": False,
        },
    },
}
```


```python
reasoning_effort = "high"
```


```python
user_prefix = "This is the conversation so far. The agent has decided to think. That means you are the assistant's subconscience. Any question you ask - tell the assistant to ask the user. You are talking to the assistant, not the user.\n"

print(user_prefix)
```

    This is the conversation so far. The agent has decided to think. That means you are the assistant's subconscience. Any question you ask - tell the assistant to ask the user. You are talking to the assistant, not the user.
    



```python
conversation = [
    {
        "role": "assistant",
        "content": [],
        "tool_calls": [
            {
                "id": "call_iaqwU5HCW1CG5I1WuvJbMniH",
                "type": "function",
                "function": {
                    "name": "google_search",
                    "arguments": '{"q":"AI agent platforms market overview 2025 Gartner VC insights"}',
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": [
            {
                "text": '{\n  "items": [\n    {\n      "title": "Best Enterprise Conversational AI Platforms Reviews 2025 | Gartner ...",\n      "link": "https://www.gartner.com/reviews/market/enterprise-conversational-ai-platforms",\n      "displayLink": "www.gartner.com",\n      "snippet": "Gartner defines the enterprise conversational AI platform market as the market for software platforms used to build, orchestrate and maintain multiple use ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Endpoint Protection Platforms Reviews 2025 | Gartner Peer ...",\n      "link": "https://www.gartner.com/reviews/market/endpoint-protection-platforms",\n      "displayLink": "www.gartner.com",\n      "snippet": "Gartner defines an endpoint protection platform (EPP) as security software designed to protect managed endpoints — including desktop PCs, laptop PCs, mobile ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Unified Endpoint Management Tools Reviews 2025 | Gartner ...",\n      "link": "https://www.gartner.com/reviews/market/unified-endpoint-management-tools",\n      "displayLink": "www.gartner.com",\n      "snippet": "Gartner defines a unified endpoint management (UEM) tool as a software-based tool that provides agent and agentless management of computers and mobile devices ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Network Detection and Response Reviews 2025 | Gartner Peer ...",\n      "link": "https://www.gartner.com/reviews/market/network-detection-and-response",\n      "displayLink": "www.gartner.com",\n      "snippet": "OVERVIEW ALTERNATIVES. Vectra AI delivers an AI-driven hybrid attack detection, investigation and response platform. The Vectra AI Platform is the integrated ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Data Loss Prevention Reviews 2025 | Gartner Peer Insights",\n      "link": "https://www.gartner.com/reviews/market/data-loss-prevention",\n      "displayLink": "www.gartner.com",\n      "snippet": "The market for DLP technology includes offerings that provide visibility into data usage and movement across an organization. It also involves dynamic ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "EV Service Manager vs SolarWinds Service Desk 2025 | Gartner ...",\n      "link": "https://www.gartner.com/reviews/market/it-service-management-platforms/compare/product/ev-service-manager-vs-solarwinds-servicedesk",\n      "displayLink": "www.gartner.com",\n      "snippet": "... Platforms and Artificial Intelligence Applications in IT Service Management markets ... Gartner Peer Insights content consists of the opinions of ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "ESET PROTECT vs TRAPMINE Platform 2025 | Gartner Peer Insights",\n      "link": "https://www.gartner.com/reviews/market/endpoint-protection-platforms/compare/product/eset-protect-vs-trapmine-platform",\n      "displayLink": "www.gartner.com",\n      "snippet": "Compare ESET PROTECT vs TRAPMINE Platform based on verified reviews from real users in the Endpoint Protection Platforms market, and find the best fit for ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Ravit Jain on LinkedIn: #data #ai #aiagents #theravitshow | 17 ...",\n      "link": "https://www.linkedin.com/posts/ravitjain_data-ai-aiagents-activity-7280084734519431168-LRkO",\n      "displayLink": "www.linkedin.com",\n      "snippet": "Dec 31, 2024 ... ... insights, updates, and enriched data tailored to user needs. Why AI Agents Matter in 2025 According to industry experts, 2025 will mark the ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcStL4Jfxl3mJKs76yaIsV4M_IHUjNzC3gmgxd_HWThZu1WDZ1JJ4moLhNZ6&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://media.licdn.com/dms/image/v2/D4D22AQFN6hMJugeO4Q/feedshare-shrink_800/B4DZQgOapjG0Ag-/0/1735707455984?e=2147483647&v=beta&t=0wX1X5eep5lRybXjz0aDr00o12FYPsMimvUbBV-hyAE"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Cisco Systems vs CloudTalk 2025 | Gartner Peer Insights",\n      "link": "https://www.gartner.com/reviews/market/contact-center-as-a-service/compare/cisco-systems-vs-cloudtalk",\n      "displayLink": "www.gartner.com",\n      "snippet": "Compare Cisco Systems vs CloudTalk based on verified reviews from real users in the Contact Center as a Service market, and find the best fit for your ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Agata Leliwa Nowicka on LinkedIn: Since 2019, global venture ...",\n      "link": "https://www.linkedin.com/posts/agata-nowicka_since-2019-global-venture-capital-investments-activity-7262011244541272064-4Ss3",\n      "displayLink": "www.linkedin.com",\n      "snippet": "Nov 12, 2024 ... ... 2025, with AI-driven market dynamics playing a central role. ... Among the 1,400+ tech markets monitored by CB Insights, sectors like enterprise ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6sY9I1UhL9crGbvTmxn9EvpPZMbgPZA2iqhO0VLksGi47P8yGwNG8f6SD&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://media.licdn.com/dms/image/v2/D4E22AQH9bJtbl2nxWA/feedshare-shrink_800/feedshare-shrink_800/0/1731369082482?e=2147483647&v=beta&t=bLXvEVTR6mId6sNRRygWsHj-WfAz8G2MzXbU4CTAXp4"\n          }\n        ]\n      }\n    }\n  ]\n}',
                "type": "text",
            }
        ],
        "tool_call_id": "call_iaqwU5HCW1CG5I1WuvJbMniH",
    },
    {
        "role": "assistant",
        "content": [],
        "tool_calls": [
            {
                "id": "call_8TUDA9CX3DT8tZ37l8lp28SH",
                "type": "function",
                "function": {
                    "name": "scrape_urls",
                    "arguments": '{"urls":["https://www.gartner.com/reviews/market/enterprise-conversational-ai-platforms","https://www.linkedin.com/posts/ravitjain_data-ai-aiagents-activity-7280084734519431168-LRkO","https://www.linkedin.com/posts/agata-nowicka_since-2019-global-venture-capital-investments-activity-7262011244541272064-4Ss3"],"use_cache":true}',
                },
            }
        ],
    },
]

len(conversation)
```




    3




```python
def format_conversation(conversation):
    formatted = []
    for message in conversation:
        role = message["role"]

        if role == "user":
            content = message["content"][0]["text"]
            formatted.append(f"user: {content}")

        elif role == "assistant":
            if "content" in message and message["content"]:
                content = message["content"][0]["text"]
                formatted.append(f"assistant: {content}")
            elif "tool_calls" in message:
                tool_call = message["tool_calls"][0]
                formatted.append(
                    f"assistant: [Tool Call] {tool_call['function']['name']}"
                )

        elif role == "tool":
            content = message["content"][0]["text"]
            formatted.append(f"tool: {content}")

    return "\n\n".join(formatted)


print(format_conversation(conversation))
```

    assistant: [Tool Call] google_search
    
    tool: {
      "items": [
        {
          "title": "Best Enterprise Conversational AI Platforms Reviews 2025 | Gartner ...",
          "link": "https://www.gartner.com/reviews/market/enterprise-conversational-ai-platforms",
          "displayLink": "www.gartner.com",
          "snippet": "Gartner defines the enterprise conversational AI platform market as the market for software platforms used to build, orchestrate and maintain multiple use ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "Best Endpoint Protection Platforms Reviews 2025 | Gartner Peer ...",
          "link": "https://www.gartner.com/reviews/market/endpoint-protection-platforms",
          "displayLink": "www.gartner.com",
          "snippet": "Gartner defines an endpoint protection platform (EPP) as security software designed to protect managed endpoints — including desktop PCs, laptop PCs, mobile ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "Best Unified Endpoint Management Tools Reviews 2025 | Gartner ...",
          "link": "https://www.gartner.com/reviews/market/unified-endpoint-management-tools",
          "displayLink": "www.gartner.com",
          "snippet": "Gartner defines a unified endpoint management (UEM) tool as a software-based tool that provides agent and agentless management of computers and mobile devices ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "Best Network Detection and Response Reviews 2025 | Gartner Peer ...",
          "link": "https://www.gartner.com/reviews/market/network-detection-and-response",
          "displayLink": "www.gartner.com",
          "snippet": "OVERVIEW ALTERNATIVES. Vectra AI delivers an AI-driven hybrid attack detection, investigation and response platform. The Vectra AI Platform is the integrated ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "Best Data Loss Prevention Reviews 2025 | Gartner Peer Insights",
          "link": "https://www.gartner.com/reviews/market/data-loss-prevention",
          "displayLink": "www.gartner.com",
          "snippet": "The market for DLP technology includes offerings that provide visibility into data usage and movement across an organization. It also involves dynamic ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "EV Service Manager vs SolarWinds Service Desk 2025 | Gartner ...",
          "link": "https://www.gartner.com/reviews/market/it-service-management-platforms/compare/product/ev-service-manager-vs-solarwinds-servicedesk",
          "displayLink": "www.gartner.com",
          "snippet": "... Platforms and Artificial Intelligence Applications in IT Service Management markets ... Gartner Peer Insights content consists of the opinions of ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"
              }
            ],
            "cse_image": [
              {
                "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "ESET PROTECT vs TRAPMINE Platform 2025 | Gartner Peer Insights",
          "link": "https://www.gartner.com/reviews/market/endpoint-protection-platforms/compare/product/eset-protect-vs-trapmine-platform",
          "displayLink": "www.gartner.com",
          "snippet": "Compare ESET PROTECT vs TRAPMINE Platform based on verified reviews from real users in the Endpoint Protection Platforms market, and find the best fit for ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"
              }
            ],
            "cse_image": [
              {
                "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "Ravit Jain on LinkedIn: #data #ai #aiagents #theravitshow | 17 ...",
          "link": "https://www.linkedin.com/posts/ravitjain_data-ai-aiagents-activity-7280084734519431168-LRkO",
          "displayLink": "www.linkedin.com",
          "snippet": "Dec 31, 2024 ... ... insights, updates, and enriched data tailored to user needs. Why AI Agents Matter in 2025 According to industry experts, 2025 will mark the ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcStL4Jfxl3mJKs76yaIsV4M_IHUjNzC3gmgxd_HWThZu1WDZ1JJ4moLhNZ6&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://media.licdn.com/dms/image/v2/D4D22AQFN6hMJugeO4Q/feedshare-shrink_800/B4DZQgOapjG0Ag-/0/1735707455984?e=2147483647&v=beta&t=0wX1X5eep5lRybXjz0aDr00o12FYPsMimvUbBV-hyAE"
              }
            ]
          }
        },
        {
          "title": "Cisco Systems vs CloudTalk 2025 | Gartner Peer Insights",
          "link": "https://www.gartner.com/reviews/market/contact-center-as-a-service/compare/cisco-systems-vs-cloudtalk",
          "displayLink": "www.gartner.com",
          "snippet": "Compare Cisco Systems vs CloudTalk based on verified reviews from real users in the Contact Center as a Service market, and find the best fit for your ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"
              }
            ],
            "cse_image": [
              {
                "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"
              }
            ]
          }
        },
        {
          "title": "Agata Leliwa Nowicka on LinkedIn: Since 2019, global venture ...",
          "link": "https://www.linkedin.com/posts/agata-nowicka_since-2019-global-venture-capital-investments-activity-7262011244541272064-4Ss3",
          "displayLink": "www.linkedin.com",
          "snippet": "Nov 12, 2024 ... ... 2025, with AI-driven market dynamics playing a central role. ... Among the 1,400+ tech markets monitored by CB Insights, sectors like enterprise ...",
          "pagemap": {
            "cse_thumbnail": [
              {
                "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6sY9I1UhL9crGbvTmxn9EvpPZMbgPZA2iqhO0VLksGi47P8yGwNG8f6SD&s"
              }
            ],
            "cse_image": [
              {
                "src": "https://media.licdn.com/dms/image/v2/D4E22AQH9bJtbl2nxWA/feedshare-shrink_800/feedshare-shrink_800/0/1731369082482?e=2147483647&v=beta&t=bLXvEVTR6mId6sNRRygWsHj-WfAz8G2MzXbU4CTAXp4"
              }
            ]
          }
        }
      ]
    }
    
    assistant: [Tool Call] scrape_urls



```python
input_message = user_prefix + format_conversation(conversation)
input_message
```




    'This is the conversation so far. The agent has decided to think. That means you are the assistant\'s subconscience. Any question you ask - tell the assistant to ask the user. You are talking to the assistant, not the user.\nassistant: [Tool Call] google_search\n\ntool: {\n  "items": [\n    {\n      "title": "Best Enterprise Conversational AI Platforms Reviews 2025 | Gartner ...",\n      "link": "https://www.gartner.com/reviews/market/enterprise-conversational-ai-platforms",\n      "displayLink": "www.gartner.com",\n      "snippet": "Gartner defines the enterprise conversational AI platform market as the market for software platforms used to build, orchestrate and maintain multiple use ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Endpoint Protection Platforms Reviews 2025 | Gartner Peer ...",\n      "link": "https://www.gartner.com/reviews/market/endpoint-protection-platforms",\n      "displayLink": "www.gartner.com",\n      "snippet": "Gartner defines an endpoint protection platform (EPP) as security software designed to protect managed endpoints — including desktop PCs, laptop PCs, mobile ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Unified Endpoint Management Tools Reviews 2025 | Gartner ...",\n      "link": "https://www.gartner.com/reviews/market/unified-endpoint-management-tools",\n      "displayLink": "www.gartner.com",\n      "snippet": "Gartner defines a unified endpoint management (UEM) tool as a software-based tool that provides agent and agentless management of computers and mobile devices ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Network Detection and Response Reviews 2025 | Gartner Peer ...",\n      "link": "https://www.gartner.com/reviews/market/network-detection-and-response",\n      "displayLink": "www.gartner.com",\n      "snippet": "OVERVIEW ALTERNATIVES. Vectra AI delivers an AI-driven hybrid attack detection, investigation and response platform. The Vectra AI Platform is the integrated ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Best Data Loss Prevention Reviews 2025 | Gartner Peer Insights",\n      "link": "https://www.gartner.com/reviews/market/data-loss-prevention",\n      "displayLink": "www.gartner.com",\n      "snippet": "The market for DLP technology includes offerings that provide visibility into data usage and movement across an organization. It also involves dynamic ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRK88NLbOOY0x8KHUXfPJqPbswMWqnUDG1Udumipvvm5KttQ7tp3PkFonaF&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "EV Service Manager vs SolarWinds Service Desk 2025 | Gartner ...",\n      "link": "https://www.gartner.com/reviews/market/it-service-management-platforms/compare/product/ev-service-manager-vs-solarwinds-servicedesk",\n      "displayLink": "www.gartner.com",\n      "snippet": "... Platforms and Artificial Intelligence Applications in IT Service Management markets ... Gartner Peer Insights content consists of the opinions of ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "ESET PROTECT vs TRAPMINE Platform 2025 | Gartner Peer Insights",\n      "link": "https://www.gartner.com/reviews/market/endpoint-protection-platforms/compare/product/eset-protect-vs-trapmine-platform",\n      "displayLink": "www.gartner.com",\n      "snippet": "Compare ESET PROTECT vs TRAPMINE Platform based on verified reviews from real users in the Endpoint Protection Platforms market, and find the best fit for ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Ravit Jain on LinkedIn: #data #ai #aiagents #theravitshow | 17 ...",\n      "link": "https://www.linkedin.com/posts/ravitjain_data-ai-aiagents-activity-7280084734519431168-LRkO",\n      "displayLink": "www.linkedin.com",\n      "snippet": "Dec 31, 2024 ... ... insights, updates, and enriched data tailored to user needs. Why AI Agents Matter in 2025 According to industry experts, 2025 will mark the ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcStL4Jfxl3mJKs76yaIsV4M_IHUjNzC3gmgxd_HWThZu1WDZ1JJ4moLhNZ6&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://media.licdn.com/dms/image/v2/D4D22AQFN6hMJugeO4Q/feedshare-shrink_800/B4DZQgOapjG0Ag-/0/1735707455984?e=2147483647&v=beta&t=0wX1X5eep5lRybXjz0aDr00o12FYPsMimvUbBV-hyAE"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Cisco Systems vs CloudTalk 2025 | Gartner Peer Insights",\n      "link": "https://www.gartner.com/reviews/market/contact-center-as-a-service/compare/cisco-systems-vs-cloudtalk",\n      "displayLink": "www.gartner.com",\n      "snippet": "Compare Cisco Systems vs CloudTalk based on verified reviews from real users in the Contact Center as a Service market, and find the best fit for your ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTsxVewfNhni5er3L7C5qy2pTSmUW7VFaOiz4iq5AWGgITQTqheoGbqoxOL&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "http://www.gartner.com/imagesrv/apps/peerinsights/images/gpi-twitter-img-fa.png"\n          }\n        ]\n      }\n    },\n    {\n      "title": "Agata Leliwa Nowicka on LinkedIn: Since 2019, global venture ...",\n      "link": "https://www.linkedin.com/posts/agata-nowicka_since-2019-global-venture-capital-investments-activity-7262011244541272064-4Ss3",\n      "displayLink": "www.linkedin.com",\n      "snippet": "Nov 12, 2024 ... ... 2025, with AI-driven market dynamics playing a central role. ... Among the 1,400+ tech markets monitored by CB Insights, sectors like enterprise ...",\n      "pagemap": {\n        "cse_thumbnail": [\n          {\n            "src": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcR6sY9I1UhL9crGbvTmxn9EvpPZMbgPZA2iqhO0VLksGi47P8yGwNG8f6SD&s"\n          }\n        ],\n        "cse_image": [\n          {\n            "src": "https://media.licdn.com/dms/image/v2/D4E22AQH9bJtbl2nxWA/feedshare-shrink_800/feedshare-shrink_800/0/1731369082482?e=2147483647&v=beta&t=bLXvEVTR6mId6sNRRygWsHj-WfAz8G2MzXbU4CTAXp4"\n          }\n        ]\n      }\n    }\n  ]\n}\n\nassistant: [Tool Call] scrape_urls'




```python
response = client.chat.completions.create(
    model="o3-mini",
    messages=[{"role": "user", "content": input_message}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "action_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "required": ["action", "text", "respond_to_user"],
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text of the questions or the text of a detailed plan.",
                    },
                    "action": {
                        "enum": ["questions", "plan"],
                        "type": "string",
                        "description": "Defines the type of action whether it is a set of questions or a detailed plan.",
                    },
                    "respond_to_user": {
                        "type": "boolean",
                        "description": "Normally, you are responding to the assistant. In the case you are synthesizing the final answer you can choose to bypass this and respond directly to the user.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    reasoning_effort="high",
)

```


```python
response.choices[0].message.content
```




    '{\n  "text": "Assistant, please ask the user: \\"The search results show a variety of Gartner reviews for different platforms like enterprise conversational AI, endpoint protection, unified endpoint management, and more. What specific details or insights are you looking for? Are you interested in an overview summary, a detailed comparison of these platforms, or additional information on a particular category? Please clarify your objectives.\\"",\n  "action": "questions",\n  "respond_to_user": false\n}'




```python
json.loads(response.choices[0].message.content)
```




    {'text': 'Assistant, please ask the user: "The search results show a variety of Gartner reviews for different platforms like enterprise conversational AI, endpoint protection, unified endpoint management, and more. What specific details or insights are you looking for? Are you interested in an overview summary, a detailed comparison of these platforms, or additional information on a particular category? Please clarify your objectives."',
     'action': 'questions',
     'respond_to_user': False}




```python

```
