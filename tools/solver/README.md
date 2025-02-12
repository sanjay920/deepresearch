# Solver Microservice

This microservice takes an "objective" and "research_plan" and uses OpenAI to:

1. Construct a chat conversation using the `o3-mini` model from OpenAI.
2. If needed, it calls a `query_information_broker` function to fetch external data from a separate microservice at `<BROKER_HOST>:8081`.
3. Returns a **string** with the final result.

## Usage

1. **Set your environment variables**:
   - `OPENAI_API_KEY` (required)
   - `BROKER_HOST` (optional, defaults to `localhost`)

2. **Run with Docker**:

   ```bash
   docker build -t solver-service .
   docker run -d --name solver-service \
       -p 8086:8086 \
       -e OPENAI_API_KEY="your_openai_key_here" \
       solver-service
   ```

   The service is now available at `http://localhost:8086/solve`.

3. **POST /solve**  

   Request Body (JSON):

   ```json
   {
     "objective": "Retrieve NVIDIA's most recent 100 trading days ...",
     "research_plan": [
       "Access a reliable financial data source ...",
       "Retrieve the historical closing prices ...",
       "Ensure that the data spans exactly 100 trading days ...",
       "Organize the data ..."
     ]
   }
   ```

   Response: A **plain string** containing the solution from the model.

## Example

```bash
curl -X POST http://localhost:8086/solve \
  -H 'Content-Type: application/json' \
  -d '{
    "objective": "Retrieve NVIDIA's most recent 100 trading days detailed closing prices, including dates and corresponding closing values.",
    "research_plan": [
      "Access a reliable financial data source (e.g., Yahoo Finance)...",
      "Retrieve the historical closing prices and associated dates...",
      "Ensure the data spans exactly 100 trading days...",
      "Organize the data into a list and present it..."
    ]
  }'
```

Output might be (shortened):

```
"Below is the detailed list of NVIDIA’s (NVDA) closing prices for its 100 most
 recent trading days (based on the assembled historical data)..."
```

## Development

To run locally without Docker:

1. Create and activate a virtualenv:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Export your OpenAI API key:

   ```bash
   export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
   ```

4. Launch the server:

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8086 --workers 4
   ```

5. POST requests to `http://localhost:8086/solve`.
