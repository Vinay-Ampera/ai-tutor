# AI Tutor / Teaching Bot

## Project
AI-powered teaching assistant using React, FastAPI, LangGraph and Gemini.

## Structure
- frontend/ -> React application
- backend/ -> FastAPI application
- pyproject.toml -> Python/Poetry configuration

## Architecture
React -> FastAPI -> LangGraph -> Gemini

## Session behavior
- React persists the active session ID in browser local storage so refreshes reuse the same learning context.
- LangGraph session context is held in backend memory and is removed by Start over or when the backend process restarts.
- On reconnect, the frontend detects a backend restart and starts a fresh session rather than reusing an ID with missing context.

## Setup
Instructions for running frontend and backend.

## Environment Variables
GEMINI_API_KEY=...

## Development
Stage-by-stage implementation according to the project roadmap.