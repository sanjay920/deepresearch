# Router Microservice

This microservice routes user queries based on their complexity using OpenAI's API (using the new client from openai==1.61.1). It determines whether a query is complex and should be routed to a planning assistant or if it is straightforward enough to be answered immediately.

## API Endpoint

### POST `/route`

- **Request Body:**

  ```json
  {
    "message": "Your user query here"
  }
  ```

- **Response Format:**

  The response will be a JSON object in the following format:

  ```json
  {
    "is_complex": true/false,
    "response/routing": "Response message or routing information"
  }
  ```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key.

You can set this variable directly or use the provided `.env.sample` file as a template.

## Running Locally

1. **Create a virtual environment & install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set the environment variable:**

   ```bash
   export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
   ```

3. **Run the service:**

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The service will be available at [http://localhost:8000/route](http://localhost:8000/route).

## Docker

To build and run the service using Docker:

1. **Build the Docker image:**

   ```bash
   docker build -t router-service .
   ```

2. **Run the Docker container:**

   ```bash
   docker run -d --name router-service -p 8080:80 -e OPENAI_API_KEY="YOUR_OPENAI_API_KEY" router-service
   ```

   The service will be accessible at [http://localhost:8080/route](http://localhost:8080/route).

## Notes

- Ensure you have a valid OpenAI API key.
- This service uses the `gpt-4o` model and the new OpenAI client interface from openai==1.61.1.
