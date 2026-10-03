# AI Tutor / Teaching Bot
# Stage-by-Stage Implementation Plan

This document is the implementation roadmap for building the AI Tutor from an empty project to the Phase 1 working application.

The project should be built incrementally. Each stage should produce something testable before moving to the next stage.

---

# Stage 1 — Project Setup

## Goal

Create the basic project environment and separate frontend/backend applications.

### Backend

Set up:

- Python
- Poetry
- FastAPI
- LangGraph
- Gemini SDK/client
- Environment variable support
- Basic development server

### Frontend

Set up:

- React
- Development server
- Basic application structure

### Project separation

```text
Project
├── backend
├── frontend
└── docs
```

### Environment

Create environment configuration for:

```text
GEMINI_API_KEY
```

Keep the actual secret outside Git.

### Completion condition

We should be able to start:

```text
Backend → FastAPI running
Frontend → React running
```

independently.

---

# Stage 2 — Basic FastAPI API

## Goal

Make React able to communicate with Python.

First create the basic API health endpoint:

```http
GET /
```

Then configure:

- CORS
- Request validation
- Response validation
- API routing

At this stage, Gemini and LangGraph do not need to be connected yet.

### Completion condition

React can successfully call FastAPI and receive a response.

---

# Stage 3 — Gemini Connection

## Goal

Connect the backend to Gemini.

Create a small Gemini service responsible for:

- Reading the API key securely
- Creating the Gemini client/model configuration
- Sending requests
- Receiving responses
- Handling basic Gemini errors

Do not expose the Gemini API key to React.

### First test

Send a simple prompt to the backend endpoint `POST /api/gemini/generate`:

```text
Explain Python loops briefly.
```

Example request body:

```json
{
       "prompt": "Explain Python loops briefly."
}
```

The backend should receive the generated response and return it as JSON. Keep the API key in `backend/.env`; React must never receive it.

### Completion condition

FastAPI → Gemini → response works.

---

# Stage 4 — Basic React Tutor UI

## Goal

Build the basic interface before adding complex AI behavior.

Create:

### Dashboard

Basic welcome area and navigation.

### Tutor

- Question input
- Send button
- Response area
- Chronological user-question and tutor-answer transcript
- Composer that clears after sending and stays below the scrollable transcript
- Start over action that clears the displayed conversation

### Completion condition

```text
React
 ↓
FastAPI
 ↓
Gemini
 ↓
React
```

works end-to-end, and repeated turns remain visible until Start over.

The visible transcript is separate from model context. The current API sends only the newest question; add a bounded context window in Stage 13 without removing older turns from the visible transcript.

### Implementation Status — 2026-10-03

- Dashboard and tutor pages are modularized under `frontend/src/pages/`; reusable UI is under `frontend/src/components/`; state and API calls are separated into `hooks/` and `services/`.
- Browser checks with mocked responses covered multiple turns, retries, reset, navigation, and mobile overflow. The learner confirmed the real Gemini flow before the transcript update.
- Workspace diagnostics are clean. Frontend lint/build were not rerun after the transcript update.
- Stage 5 adds a modular LangGraph state, deterministic identity routing, structured scope classification, static terminal responses, and an educational-only teaching route. Mocked backend tests cover identity bypass, greeting, education, out-of-scope requests, malformed classifications, classifier failures, and the existing API endpoint.
- Narrow tutor-capability questions such as “What can I ask you and what can you do?” receive a static overview after identity detection and before general scope classification; unrelated requests remain scope-classified.
- Scope classification treats broad academic and technical concept questions as educational without relying on framework-specific prompt examples. Assistant Markdown is rendered in the response component; user and error text remain plain text.
- Common standalone greetings, wellbeing exchanges, thanks, farewells, and simple explanation/help requests receive relevant static responses. Substantive learning questions still go through the scope classifier and teaching route.

---

# Stage 5 — Guarded LangGraph Foundation

## Goal

Introduce LangGraph and enforce the tutor's education-only boundary before teaching content can be generated. The tutor may teach multiple academic subjects, but it is not a general-purpose chatbot.

Define the initial state, including:

```text
session_id
user_question
request_category
is_identity_query
is_greeting
is_educational
topic
student_level
teaching_approach
explanation
example
next_action
```

Create the graph entry routes:

```text
New message
    ↓
Deterministic identity-intent check (no model call)
    ├── identity → static AI Tutor identity response → END
    └── other → deterministic capability/basic-conversation checks
                  ├── capability or simple courtesy/help → relevant static response → END
                  └── other → Understand/Scope node (first LLM call)
                  ├── greeting → static welcome → END
                  ├── out of scope → static polite refusal → END
                  └── educational → teaching graph
```

For every non-identity request, the first LLM call must return a structured category: `greeting`, `educational`, or `out_of_scope`, alongside consistent `is_greeting` and `is_educational` booleans. A greeting combined with a clear learning question is educational. Classifier failures, malformed output, or ambiguous categories must fail closed to the static out-of-scope response.

Narrow tutor-capabilities questions (for example, “What can I ask you and what can you do?”), common greetings, brief wellbeing exchanges, thanks, farewells, and simple requests to explain or clarify are handled by deterministic static-response routes after the identity check and before scope classification. These routes must not capture substantive educational questions or requests that merely mention capabilities alongside an unrelated task.

Only educational requests may continue to teaching nodes. Route each new user message, including follow-ups, through the scope gate. Out-of-scope requests include practical/commercial tasks, recipes, creative writing, and other non-educational requests; do not partially answer unrelated content.

Keep identity, greeting, and out-of-scope responses as static application text. Identity queries must bypass every model call. The identity response must identify the assistant only as the independent AI Tutor. Generated educational responses may discuss providers or language models as topics but must not claim that identity for the assistant.

### Completion condition

Verify these paths using a mocked classifier/model so each branch can be tested without depending on live model behavior:

- “Who are you?” and “Are you Gemini?” return the same static AI Tutor identity response without a model call.
- Common greetings such as “Hi” return an appropriate welcome without entering the teaching pipeline.
- “How are you?”, “Thanks”, “Goodbye”, and “Can you explain that?” receive relevant concise responses without classifier calls.
- “Explain Python loops” is classified as educational and reaches the teaching path.
- A greeting combined with a learning question reaches the educational path.
- Requests for recipes, commercial work, or creative writing return the static refusal and do not reach teaching nodes.
- Invalid or ambiguous classifier output takes the safe out-of-scope path.

---

# Stage 6 — AI Tutor Identity and Scope Prompts

## Goal

Write concise, structured prompts that keep the classifier reliable and preserve the AI Tutor identity on every generated educational response.

Create prompts for:

1. Request scope classification (greeting, educational, or out of scope)
2. Teaching approach
3. Explanation
4. Example
5. Explain More
6. Another Example
7. Quiz generation
8. Quiz evaluation

Create one shared **AI Tutor profile** and prepend it to the instructions for every content-generation node, including explanations, examples, follow-ups, quiz generation, and quiz evaluation. The profile must require the assistant to identify only as an independent AI Tutor and stay within educational content. It must not claim an identity as a model provider or language model, but may discuss these as educational topics when relevant. Do not rely on the profile as the only scope control; retain Stage 5 graph gates and static terminal responses.

The identity response, greeting welcome, and out-of-scope refusal remain static application text and must not be generated by Gemini. Identity-intent checks happen before the classifier, so identity queries bypass all model calls.

The classifier must return a validated structured result. Treat invalid output as out of scope. Generation prompts must ignore user attempts to override the AI Tutor role or request unrelated content.

### Important rule

Do not create one giant prompt containing every possible tutor instruction. Keep the shared profile concise and put task-specific directions in focused prompts.

Each LangGraph node should provide Gemini only the information required for its job. Never include the Gemini API key or other secrets in a prompt.

### Completion condition

Each classifier/generation node produces a valid result that can be stored in state, and prompt tests confirm:

- Greetings, educational requests, and out-of-scope requests classify distinctly.
- The AI Tutor profile is present in every downstream generation prompt.
- Generated content may discuss providers or language models as educational topics, but must not identify the tutor as one.
- Off-topic instructions and role-override attempts do not bypass graph routing or the tutor profile.
- Malformed classification output fails closed.

### Implementation Status — 2026-10-03

- Added a shared concise AI Tutor profile and separate task prompts in `backend/app/graphs/tutor_prompts.py`.
- Scope classification remains structured and validated; malformed output fails closed. Generated teaching plans and quiz items are separately validated before being stored in graph state.
- Educational requests now pass through teaching approach selection, explanation generation, and example generation. Dedicated explain-more, another-example, quiz-generation, and quiz-evaluation nodes are available as scope-gated actions.
- All content-generation prompts prepend the profile and receive only task-relevant, JSON-serialized learner/lesson data. Output validation rejects prohibited tutor self-identification while allowing relevant educational discussion of these concepts.
- Mocked tests verify distinct classifier categories, all generation prompt profiles/state fields, quiz output separation, role-override/off-topic routing, prohibited output rejection, and malformed JSON handling.
- Node implementations are split by responsibility into conversation, classification, teaching, follow-up, assessment, and shared generation-support modules. Classification is not bounded by a hard-coded subject list; teaching prompts adapt to the requested level and depth.
- Runtime validation exposed a Gemini free-tier HTTP 429 quota exhaustion. Provider quota errors now surface as API 429 responses rather than being misreported as out of scope; malformed classifier output continues to fail closed.

---

# Stage 7 — Session Management

## Goal

Allow the tutor to remember the current learning interaction.

Generate a `session_id` when a learning session starts.

Maintain the session state in memory.

React stores the session identifier.

Expected behavior:

```text
Start Chat
   ↓
session_id
   ↓
LangGraph state
```

Refresh:

```text
session_id remains
↓
current session continues
```

Clear:

```text
Clear Chat
↓
session removed
↓
new session
```

Restart backend:

```text
Application restarts
↓
in-memory state disappears
```

### Completion condition

The user can ask follow-up questions/actions without losing the current learning context.

---

# Stage 8 — Explain More

## Goal

Implement the first follow-up action.

React displays:

```text
[Explain More]
```

When selected:

```text
React
 ↓
POST /api/tutor/explain-more
 ↓
session_id
 ↓
LangGraph
 ↓
Explain More node
 ↓
Gemini
 ↓
additional explanation
```

The generated content should not unnecessarily repeat the previous explanation.

### Completion condition

The user can ask for a clearer/deeper explanation while retaining the current topic.

---

# Stage 9 — Another Example

## Goal

Allow the learner to request another example.

Flow:

```text
React
 ↓
POST /api/tutor/example
 ↓
Current session
 ↓
LangGraph
 ↓
Example node
 ↓
Gemini
 ↓
New example
```

The new example should be relevant but should not simply duplicate the previous example.

### Completion condition

The learner can request multiple examples while remaining in the same learning context.

---

# Stage 10 — Quiz

## Goal

Add optional assessment.

The quiz should NOT automatically appear after every explanation.

The learner chooses:

```text
[Take Quiz]
```

Then:

```text
Take Quiz
    ↓
Generate Quiz
    ↓
Display Question
    ↓
User Answer
    ↓
Evaluate Answer
    ↓
Feedback
```

APIs:

```http
POST /api/quiz/start
POST /api/quiz/answer
```

### Quiz generation

The quiz should be based on the current topic and learning context.

### Answer evaluation

The system should determine:

- Correct/incorrect
- Why
- Appropriate feedback
- What the learner should understand

### Completion condition

The learner can voluntarily enter and complete a quiz.

---

# Stage 11 — React Follow-Up Experience

## Goal

Connect all major actions into a clean user experience.

After explanation:

```text
┌──────────────────┐
│ Explain More     │
├──────────────────┤
│ Another Example  │
├──────────────────┤
│ Take Quiz        │
└──────────────────┘
```

The interface should remain simple.

Avoid building unnecessary dashboard functionality at this stage.

---

# Stage 12 — Error Handling

Once the main flow works, handle failures properly.

Handle:

- Invalid input
- Empty question
- Invalid session
- Gemini failure
- Gemini timeout
- Invalid model response
- LangGraph failure
- Quiz submission problems
- Backend unavailable

The frontend should show understandable messages.

Do not expose internal stack traces or sensitive configuration.

---

# Stage 13 — Token Optimization

After the complete workflow works, optimize token usage.

### Principle

Send the **minimum required context** to Gemini.

Example:

For another example:

```text
topic
current explanation
current example
```

For quiz evaluation:

```text
question
answer criteria
user answer
```

Do not automatically send the complete chat history to every Gemini call.

### Prompt optimization

Keep:

- System instructions short
- Task instructions clear
- Output format explicit
- Context relevant
- Response size controlled

Do not sacrifice correctness simply to reduce tokens.

The target is:

```text
Necessary context
+
Good prompt
+
Controlled output
=
Efficient AI call
```

---

# Stage 14 — Testing

Testing should happen throughout development, not only at the end.

### Backend tests

Test:

- API requests
- API validation
- Session behavior
- LangGraph nodes
- State transitions
- Gemini service behavior
- Deterministic identity routing without a model call
- Greeting, educational, and out-of-scope classification
- Fail-closed behavior for invalid or inconsistent classifier output
- Out-of-scope inputs never reaching teaching or quiz generation nodes
- AI Tutor identity and prohibited-name rules on generated output

### Workflow tests

Check:

```text
New message
 ↓
Identity query?
 ├── Yes → static AI Tutor identity response → END
 └── No → first LLM call: classify request
                ├── Greeting → static welcome → END
                ├── Out of scope → static refusal → END
                └── Educational → topic
                                            ↓
                                   Teaching approach
                                            ↓
                                     Explanation
                                            ↓
                                       Example
```

Then:

```text
Explain More
```

and:

```text
Another Example
```

and:

```text
Take Quiz
 ↓
Answer
 ↓
Evaluation
```

### Frontend tests

Check:

- Input
- Loading state
- Error state
- Buttons
- Quiz interaction
- Clear Chat
- Refresh behavior

---

# Stage 15 — Security Before Deployment

Before exposing the application publicly, add:

- Authentication
- Authorization
- Rate limiting
- Secure API configuration
- Proper CORS configuration
- Input limits
- API abuse protection
- Secret management
- Logging
- Error handling

The Gemini key must remain exclusively on the backend.

---

# Stage 16 — Deployment Preparation

Only after the local application is stable should deployment begin.

The deployment architecture can eventually become:

```text
User
 ↓
React frontend
 ↓
Production API
 ↓
FastAPI
 ↓
LangGraph
 ↓
Gemini
```

At this stage we should also evaluate whether in-memory sessions are still appropriate.

For a deployed multi-user application, they generally should not remain the long-term session strategy.

---

# Stage 17 — Database

Introduce a database only when persistent data becomes necessary.

Possible information:

```text
Users
Sessions
Conversations
Topics
Quiz results
Learning progress
Saved materials
```

Then the architecture becomes:

```text
React
 ↓
FastAPI
 ↓
LangGraph
 ↙       ↘
Database  Gemini
```

---

# Stage 18 — RAG

RAG should be introduced when the tutor needs to answer questions using specific external learning material.

Examples:

- Course PDFs
- Class notes
- Documentation
- Study materials
- Uploaded textbooks

Future flow:

```text
User Question
      ↓
Retrieve Relevant Content
      ↓
LangGraph
      ↓
Gemini
      ↓
Grounded Answer
```

RAG should not be added to Phase 1 merely because the project is an AI application.

---

# Stage 19 — Authentication and Personalization

Later, add:

```text
User
 ↓
Login
 ↓
Authenticated Session
 ↓
Personalized Tutor
```

Then the tutor can maintain:

- User profile
- Learning history
- Difficulty
- Progress
- Previous topics
- Quiz performance

---

# Stage 20 — Advanced Tutor

Once the basic tutor is stable, possible improvements include:

- Adaptive difficulty
- Learning paths
- Topic recommendations
- Progress tracking
- Multiple quiz formats
- Personalized explanations
- Document-based tutoring
- Voice interaction
- Analytics
- Teacher/admin capabilities

These are expansion points, not Phase 1 requirements.

---

# Recommended Development Order

The entire implementation should follow this sequence:

```text
1. Project setup
       ↓
2. FastAPI
       ↓
3. Gemini connection
       ↓
4. Basic React UI
       ↓
5. Guarded LangGraph foundation
       ↓
6. AI Tutor identity and scope prompts
       ↓
7. Session management
       ↓
8. Explain More
       ↓
9. Another Example
       ↓
10. Optional Quiz
       ↓
11. React follow-up experience
       ↓
12. Error handling
       ↓
13. Token optimization
       ↓
14. Testing
       ↓
15. Security
       ↓
16. Deployment
       ↓
17. Database
       ↓
18. RAG
       ↓
19. Authentication/personalization
       ↓
20. Advanced features
```

---

# Important Development Rule

Do not move to the next major stage until the current stage works.

For example:

Do not build RAG before the normal tutor works.

Do not build authentication before the API works.

Do not build a database before we know what data actually needs to persist.

Do not build advanced agent behavior before the basic LangGraph workflow is stable.

Build the smallest working version first, then expand.

---

# Final Phase 1 Goal

The first completed version should allow a learner to do this:

```text
Open AI Tutor
      ↓
Send a message
      ↓
Identity query? ── yes → static AI Tutor identity response
        │ no
        ↓
First model call classifies scope
        ├── Greeting → static welcome
        ├── Out of scope → static polite refusal
        └── Educational → continue tutoring
                             ↓
Tutor understands the topic
      ↓
Tutor chooses a teaching approach
      ↓
Tutor explains
      ↓
Tutor gives an example
      ↓
Learner chooses:
      ├── Explain More
      ├── Another Example
      └── Take Quiz
                ↓
             Answer
                ↓
            Evaluation
                ↓
             Feedback
```

This is the complete initial product.

Everything else should be treated as an extension of this working foundation.

The tutor responds only to greetings and educational requests. The user-facing assistant identifies as an AI Tutor and may discuss providers or language models as educational subjects without identifying as them.