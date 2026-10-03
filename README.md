# AI Tutor / Teaching Bot

## Project
AI-powered teaching assistant using React, FastAPI, LangGraph and Gemini.

## Structure
- frontend/ -> React application
- backend/ -> FastAPI application
- pyproject.toml -> Python/Poetry configuration

## Architecture
React -> FastAPI -> LangGraph -> Gemini

## Tutor Sessions
- The backend keeps LangGraph learning context and successful conversation turns in process memory.
- The frontend stores only the current `session_id` in browser `localStorage` and restores the conversation after a refresh.
- **Clear Chat** deletes the backend session and browser session ID. Sessions otherwise remain until cleared or the backend process restarts.
- Restarting the backend discards all session state; a stale browser ID is discarded when the app attempts to restore it.

## Setup
Instructions for running frontend and backend.

## Environment Variables
GEMINI_API_KEY=...

## Development
Stage-by-stage implementation according to the project roadmap.