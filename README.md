# AI Agriculture Advisor (Agri Voice System)

A voice-based advisory system designed to allow Ethiopian farmers to access agronomic advice and market prices using any basic mobile phone via a multi-turn Amharic spoken interface.

## Current Implementation Status

This repository contains the foundational backend logic for the advisory system, covering several core functional requirements from the SRS:

*   **Telephony & API Webhooks:** A FastAPI application prepared to accept incoming call webhooks (e.g., Twilio). Currently uses a mock telephony service for development.
*   **Dialogue & State Management:** Tracks multi-turn sessions, context (crop, location), and manages follow-up questions or missing slot clarifications.
*   **NLU & Decision Layer:** Identifies user intent and extracts entities. Chooses response strategies (RAG, Static, Fallback).
*   **Retrieval-Augmented Generation (RAG):** Retrieves relevant context from a validated knowledge base and market data repositories to construct grounded answers.
*   **Safety Guardrails:** Intercepts high-risk topics (e.g., chemical usage) to ensure the system provides safe, conservative advice or triggers confirmation prompts.
*   **Data Layer:** Ingests mock data for farmer profiles, market prices, and agronomy knowledge bases to simulate production databases.

## Project Structure

*   **`src/`**: Core application logic.
    *   **`core/`**: Dialogue manager, decision layer, safety guard, and response builder.
    *   **`services/`**: Implementations for NLU, RAG, and Telephony.
    *   **`data/`**: Repositories for farmers, knowledge base, market data, and session states.
    *   **`cli/`**: Command-line interfaces for testing without phone setups.
    *   **`models/`**: Pydantic data models.
*   **`data/`**: Storage for mock JSON data, audio, and documents.
*   **`tests/`**: Unit tests for RAG, Dialog Manager, and Data parsing.

## Installation

1. Make sure you have Python 3.9+ installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### 1. Web Service (FastAPI)
Run the API server which will act as the webhook endpoint for telephony providers (like Twilio):
```bash
uvicorn main:app --reload
```
*   **API Docs:** Once running, navigate to `http://localhost:8000/docs`.
*   **Health Check:** `http://localhost:8000/health`



### 2. CLI Mode
You can interact with the conversational logic locally via the terminal:
```bash
python src/cli/chatbot_cli.py
```



## Running Tests

Automated tests are built using `pytest`. They cover the dialogue manager rules, mock data loading, and RAG retrieval accuracy.

```bash
pytest tests/ -v
```
