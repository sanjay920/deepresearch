# Planning Assistant Microservice

This microservice uses FastAPI and OpenAI's API (using openai==1.61.1) to generate planning assistant responses in JSON format. The service accepts a user message and returns a JSON object that follows a strict schema.

## Features

- **Input:** A user message.
- **Processing:** Calls OpenAI's `o3-mini` model with a developer instruction and user message.
- **Output:** A JSON object following a predefined schema.

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key.

Use the provided `.env.sample` file as a template.

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
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
   ```

   The service will be available at [http://localhost:8003/generate](http://localhost:8003/generate).

## Docker

1. **Build the Docker image:**

   ```bash
   docker build -t planning-assistant .
   ```

2. **Run the Docker container:**

   ```bash
   docker run -d --name planning-assistant -p 8080:80 -e OPENAI_API_KEY="YOUR_OPENAI_API_KEY" planning-assistant
   ```

   The service will be accessible at [http://localhost:8080/generate](http://localhost:8080/generate).
