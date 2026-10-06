# AI Tutor / Teaching Bot
## Project Blueprint and Technical Specification

## 1. Project Overview

The AI Tutor is a domain-specific educational application. Its domain is teaching and learning: it helps learners understand academic concepts through explanations, examples, follow-up teaching, and optional quizzes.

The tutor may cover multiple educational subjects, including Python, mathematics, and computer science, but it is not a general-purpose chatbot. It must respond only to greetings and educational requests. Practical/commercial tasks, creative writing, recipes, and other non-educational requests are out of scope.

The tutor must consistently present itself as an **independent AI Tutor**. Identity questions receive a fixed response without calling the language model. The tutor must not identify itself as, or mention, Google, Gemini, or large language models in user-facing responses.

The system should:

- Classify each new request as a greeting, educational request, or out-of-scope request before teaching content is generated.
- Identify the educational topic and approximate learner level for in-scope learning requests.
- Select an appropriate teaching approach.
- Explain concepts clearly and provide relevant educational examples.
- Allow the learner to request more explanation, another example, or an optional quiz.
- Evaluate quiz answers and provide learning-focused feedback.
- Continue the learning interaction based on the learner's action without leaving the education-only boundary.
- Handle common conversational basics (greetings, brief wellbeing exchanges, thanks, farewells, and simple requests to clarify or explain) with relevant tutor responses without turning the application into a general-purpose chatbot.

---

# 2. Problem Statement

Traditional learning systems often provide static explanations without adapting to the learner's interaction. General-purpose chatbots, meanwhile, can answer unrelated requests and drift away from a consistent teaching role.

This project aims to create an interactive, education-only tutor that:

1. Handles simple greetings with a brief learning-oriented welcome.
2. Classifies educational requests and identifies the topic and approximate learner level.
3. Adapts teaching style, explains concepts, and provides relevant examples.
4. Responds to educational follow-ups, offers optional assessment, and evaluates answers.
5. Politely declines requests outside the educational domain.
6. Maintains a stable AI Tutor identity across the workflow.

The graph must enforce these boundaries through explicit routing, static responses for identity/greeting/out-of-scope paths, structured classification, and a shared tutor profile on every content-generation prompt. Prompt instructions complement graph routing; they do not replace it.

---

# 3. Initial Scope

### Included in Phase 1

- React frontend
- FastAPI backend
- Gemini API
- LangGraph workflow
- Poetry environment
- In-memory session state
- Greeting, educational, and out-of-scope classification before teaching
- Static identity response that bypasses model generation
- Static onboarding and out-of-scope responses
- AI Tutor identity and education-only guardrails on generated content
- Topic understanding
- Teaching approach selection
- Explanation generation
- Example generation
- Explain More action
- Another Example action
- Optional Quiz
- Quiz answer evaluation
- Basic session management
- Clear Chat functionality
- PDF, DOCX, XLS, and XLSX document ingestion and Markdown normalization
- Document chunking, embeddings, vector storage, retrieval, and grounded answers through the existing tutor
- Document processing and READY state before document questions can use retrieval

### Not included initially

- Authentication
- User accounts
- Persistent learning history
- Advanced analytics
- Multi-user production infrastructure
- Complex autonomous agents

These are future expansion points.

---

# 4. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Backend | Python + FastAPI |
| AI Model | Gemini API |
| AI Workflow | LangGraph |
| Python dependency management | Poetry |
| Session state | In-memory LangGraph state/checkpointing |
| Database | PostgreSQL 17 + pgvector 0.8.7 for RAG documents and chunks |
| Document parsers | PDF: PyMuPDF (`fitz`); DOCX: `python-docx`; XLS/XLSX: `pandas` + `openpyxl` |
| Embedding model | Local `BAAI/bge-small-en-v1.5` via `sentence-transformers` (384 dimensions) |
| Vector database | PostgreSQL + pgvector; separate backend DB host, port, name, user, and password settings |
| RAG | Stages 10–13 |

The frontend and backend should remain separate.

Conceptually:

React → FastAPI → LangGraph → Normal Tutor or Document Retrieval → Gemini

---

# 5. Responsibility of Each Technology

### React

Responsible for:

- User interface
- Chat interaction
- Input handling
- Displaying explanations
- Displaying examples
- Follow-up buttons
- Quiz interface
- Clear Chat
- Maintaining the session identifier on the client

React should not contain the AI logic.

### FastAPI

Responsible for:

- API endpoints
- Request validation
- Response validation
- Connecting React with LangGraph
- Session handling
- Future authentication/security middleware

FastAPI should not contain the teaching logic itself.

### LangGraph

Responsible for:

- Workflow orchestration
- State management
- Node execution
- Conditional transitions
- Continuing the current learning interaction
- Deterministic identity-query routing before any model call
- Scope-classification routing to greeting, educational, or out-of-scope paths
- Preventing out-of-scope inputs from reaching teaching, example, or quiz generation nodes
- Routing document questions to retrieval only when the active document is READY
- Routing ordinary educational questions through the normal tutor path
- Supplying retrieval results as context to grounded generation

LangGraph decides **what operation happens next**. The graph, rather than the model alone, enforces which response path is allowed.

### Gemini

Responsible for:

- Classifying non-identity input as greeting, educational, or out of scope (first model call)
- Understanding the topic and learner level for educational input
- Selecting teaching approaches
- Generating explanations
- Generating examples
- Generating quiz questions
- Evaluating quiz answers
- Generating grounded answers from retrieved document context
- Creating document and query embeddings with local `BAAI/bge-small-en-v1.5`

The model generates or classifies content only when LangGraph routes to it. It must not choose or override application routing. LangGraph retains workflow orchestration, state, routing, and conditional decisions; Gemini provides language understanding, teaching, embeddings when requested by the workflow, and grounded response generation. All user-facing generated content must follow the shared AI Tutor profile and education-only boundary.

---

# 6. High-Level Architecture

```text
React → FastAPI → LangGraph
                       ↓
              Identity intent check
                ├── identity → static AI Tutor response → END
                └── other input → first model call: classify request
                                     ├── greeting → static welcome → END
                                     ├── out of scope → static refusal → END
                                     └── educational → determine request
                                          ├── normal tutor → teaching nodes → Gemini
                                          └── document question, document READY
                                               → query embedding → vector retrieval
                                               → retrieved context → Gemini grounded answer
```

LangGraph owns every branch and conditional decision. A document question whose document is not READY receives a processing/not-ready response and never enters retrieval. Without a loaded document, the normal tutor remains available.

---

# 7. Learning Workflow

Every incoming message follows this guarded workflow before any teaching content is generated:

```text
New user message
      ↓
Deterministic identity-intent check (no model call)
      ├── identity query → static AI Tutor identity response → END
      └── other input → Understand/Scope node (first model call)
                             ├── greeting → static welcome → END
                             ├── out of scope → static refusal → END
                             └── educational → Choose Teaching Approach
                                                   ↓
                                            Generate Explanation
                                                   ↓
                                            Generate Example
                                                   ↓
                                               Learner action
                            ┌──────────────────────┼─────────────────┐
                            ↓                      ↓                 ↓
                      Explain More          Another Example      Take Quiz
                                                                    ↓
                                                              Generate Quiz
                                                                    ↓
                                                              User Answer
                                                                    ↓
                                                             Evaluate Answer
                                                                    ↓
                                                                 Feedback
```

Identity, greeting, and out-of-scope routes return fixed application-owned text and do not enter the teaching generation pipeline. The quiz is **optional**.

The tutor should not automatically give a quiz after every explanation.

### Document ingestion and RAG

The Stage 10 ingestion pipeline accepts PDF, DOCX, XLS, and XLSX immediately and uses the selected parser for each format:

| Format | Parser and extraction |
|---|---|
| PDF | PyMuPDF (`fitz`): extract text, preserve headings/structure where possible, extract tables, and represent tables cleanly in Markdown. |
| DOCX | `python-docx`: extract paragraphs and tables, preserve headings where possible, and convert to Markdown. |
| XLS / XLSX | `pandas` + `openpyxl`: process workbook sheets, preserve sheet structure, and represent tabular data as Markdown tables where appropriate. |

Normalize extracted content into clean Markdown and save it using the original uploaded filename plus a collision-safe timestamp, for example `lecture_notes_20261006_143522.md`. If two same-named files arrive within one second, use sufficient timestamp precision or a unique timestamp component to prevent overwriting. This saved Markdown is the normalized document representation for later stages. Do not substitute a generic parser unless a concrete technical problem is found.

Stage 11 transforms the Markdown as follows:

```text
Markdown → structure-aware chunks → local BAAI/bge-small-en-v1.5 embeddings
         → PostgreSQL 17 + pgvector 0.8.7
```

Chunk by Markdown structure (headings, sections, paragraphs, and tables); split only oversized sections further and repeat enough heading/page/sheet context for each chunk to stand alone. Do not use pure fixed-size character splitting as the primary strategy.

Use the local `BAAI/bge-small-en-v1.5` model through `sentence-transformers` for both document chunks and future query embeddings. Its actual embedding dimension is 384 and must be checked against the `vector(384)` column. Do not substitute BERT, OpenAI/Gemini embeddings, or another embedding service/model.

PostgreSQL + pgvector is the selected vector database (local PostgreSQL 17.11 and pgvector 0.8.7). Configure `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, and `DB_PASSWORD` separately in `backend/.env` (see `.env.example`). Pass them as individual driver arguments, not a connection URL; reserved characters such as `@` in passwords then require no URL encoding. Never hard-code credentials. Store document identity/source/Markdown path/upload timestamp/status plus chunk content, embedding, and page/heading/sheet metadata. Link chunks to documents with a foreign key, allow nullable future ownership, and create a cosine HNSW index for Stage 12 search.

Stage 11 provides document indexing and the shared local query-embedding function. It does not add RAG routing, retrieve chunks for tutor questions, or send retrieved context to Gemini; those belong to Stage 12.

When a document is READY, document-related questions follow LangGraph routing, query embedding, retrieval, and Gemini grounded generation using retrieved context. If context is insufficient, Gemini must say the information could not be found in the document rather than inventing an answer. Identity, greeting, scope, and out-of-scope protections remain in the existing LangGraph path and cannot be bypassed by retrieval. Normal tutor questions continue to work without a document and alongside a READY document.

The document lifecycle is:

```text
Upload → Parse → Markdown → Chunk → Embedding → Vector DB indexing
       → successful verification → READY
```

Only a verified indexed document is READY. Before then, normal tutor questions remain available, document questions receive a clear processing/not-ready response and are not sent to retrieval, and the user is told when processing has failed rather than being shown a success state. Once READY, show: “Your document is loaded. You can now ask questions about it.” Initially allow one active document per session unless the existing project already has a different document model.

---

# 8. LangGraph State

The initial state should remain small.

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
active_document_status
active_document_metadata
retrieved_chunks
```

`request_category` is one of `identity`, `greeting`, `educational`, or `out_of_scope`. The three classification booleans must agree with the category. Identity intent is detected before the first model call; for every other message, the Understand/Scope node is the first LLM call. A malformed or ambiguous classification must fail closed to the static out-of-scope response.

Quiz-related information is used only when the learner requests a quiz:

```text
quiz_question
user_answer
evaluation
feedback
```

The `example` field should be appropriate to the educational subject and should not assume Python code.

For example:

- Python → code example
- Mathematics → worked problem
- Computer networks → practical scenario
- Theory → real-world example

This supports multiple subjects within the education domain; it does not make the product a general-purpose chatbot.

---

# 9. LangGraph Nodes

### Check Identity Intent

Runs before any model call. Match identity questions such as “Who are you?”, “What are you?”, “Are you Gemini?”, or equivalent requests about the tutor's identity. Route matches directly to the static Identity Response node. Do not send identity-query text through the teaching pipeline.

### Understand Topic / Classify Scope

Input:

- non-identity user message

Output:

- `request_category`: `greeting`, `educational`, or `out_of_scope`
- `is_greeting`
- `is_educational`
- topic and student level only for educational requests

This is the first LLM call for every non-identity input. Return structured output and use conditional graph edges based on the category. A greeting combined with a clear learning question is educational. Practical/commercial requests, recipes, creative writing, and unrelated tasks are out of scope. For a mixed request, answer only a clearly separable educational part; otherwise use the out-of-scope response.

### Static Terminal Responses

- **Identity Response:** “I’m your independent AI Tutor. I can help you learn educational topics through explanations, examples, and practice.”
- **Greeting Response:** a brief welcome that invites an educational question.
- **Out-of-Scope Response:** a polite, concise reminder that the tutor can help with greetings and educational topics only.

These responses are static, do not call the model, and must not mention Google, Gemini, or large language models.

### Choose Teaching Approach

Input:

- topic
- student level
- user question

Output:

- teaching approach

### Generate Explanation

Input:

- topic
- student level
- teaching approach

Output:

- explanation
- important points if required

Prepend the shared AI Tutor profile to the generation instructions. The explanation must remain educational, respect the allowed identity, and not comply with off-topic instructions embedded in learner input.

### Generate Example

Input:

- topic
- explanation
- student level

Output:

- relevant example
- example explanation

Prepend the shared AI Tutor profile. Generate an example only after the request has been classified as educational.

### Explain More

Input:

- current topic
- current explanation
- learner request

Output:

- additional or clearer explanation

The node should avoid simply repeating the previous explanation.

Prepend the shared AI Tutor profile. Do not route a new off-topic request directly to this node; reapply scope routing to each new user message.

### Another Example

Input:

- current topic
- current explanation/example

Output:

- a new relevant example

It should avoid returning the exact same example.

Prepend the shared AI Tutor profile and only execute for an educational topic.

### Generate Quiz

Executed only when the learner chooses Quiz.

Input:

- topic
- student level
- relevant learning context

Output:

- quiz question
- answer/options where applicable
- correct answer internally

Prepend the shared AI Tutor profile. Quiz generation is educational content and is reachable only from an educational session when the learner requests a quiz.

### Evaluate Answer

Input:

- quiz question
- correct answer or evaluation criteria
- user's answer

Output:

- correctness
- feedback
- explanation where necessary

Prepend the shared AI Tutor profile. Evaluate only the submitted educational quiz answer; do not follow unrelated instructions included in the answer.

### Route Document Questions and Retrieve Context

LangGraph first preserves the existing identity, greeting, and educational-scope protections. It then chooses the normal tutor path or, for a document-related educational question with a READY active document, the retrieval path. If the document is processing or otherwise not READY, return a clear application-owned not-ready response without querying the vector database.

On the retrieval path, create a query embedding with the same local `BAAI/bge-small-en-v1.5` model used to embed document chunks, retrieve relevant chunks from PostgreSQL + pgvector, and pass those chunks as context to Gemini. Gemini generates the grounded answer; LangGraph remains the workflow controller. If retrieved context is insufficient, the answer must clearly state that the requested information could not be found in the document.

---

# 10. API Design

The initial API should remain small and clearly separated by responsibility.

### Health/API check

```http
GET /
```

Purpose:

Confirm that the backend is running.

### Start Tutor Session

```http
POST /api/tutor/start
```

Example request:

```json
{
  "question": "Explain Python loops"
}
```

Example response:

```json
{
  "session_id": "abc123",
  "topic": "Python loops",
  "explanation": "...",
  "example": "..."
}
```

### Explain More

```http
POST /api/tutor/explain-more
```

Example request:

```json
{
  "session_id": "abc123",
  "instruction": "Explain this more simply"
}
```

### Another Example

```http
POST /api/tutor/example
```

Example request:

```json
{
  "session_id": "abc123"
}
```

### Start Quiz

```http
POST /api/quiz/start
```

Example request:

```json
{
  "session_id": "abc123"
}
```

### Submit Quiz Answer

```http
POST /api/quiz/answer
```

Example request:

```json
{
  "session_id": "abc123",
  "answer": "..."
}
```

---

# 11. API Separation

Tutor operations and quiz operations should be separated.

```text
Tutor API
├── start
├── explain-more
└── example

Quiz API
├── start
└── answer
```

This makes the system easier to understand and easier to protect later.

Future authentication can be added at the API layer without rewriting the LangGraph workflow.

---

# 12. Session Management

Phase 1 does not use a database.

The current session is maintained in memory.

The browser stores the `session_id`.

```text
React
 ↓
session_id
 ↓
FastAPI
 ↓
LangGraph state
```

Expected behavior:

| Action | Result |
|---|---|
| Refresh browser | Session remains |
| Continue learning | Current state remains |
| Explain More | Current state is reused |
| Another Example | Current topic/context is reused |
| Clear Chat | Current session is removed |
| Stop/restart backend | In-memory sessions disappear |
| Start new chat | New session |

This is intentionally temporary.

When a database is introduced, session persistence can become permanent.

---

# 13. Clear Chat

The UI should provide a **Clear Chat** action.

Clear Chat should:

1. Remove the current session from the client.
2. Request backend session cleanup where appropriate.
3. Reset the React conversation state.
4. Allow a new session to start.

This is different from restarting the application.

---

# 14. React UI

The initial React interface should remain simple.

### Dashboard

- Application title
- Short introduction
- Start/continue learning
- Basic current-session information

### AI Tutor

- User question input
- Conversation area
- AI explanation
- Example section
- Follow-up buttons

```text
[Explain More]
[Another Example]
[Take Quiz]
```

### Quiz

Only displayed when the learner chooses Quiz.

- Question
- Answer input/options
- Submit
- Evaluation
- Feedback

### Document upload and readiness

Document upload and processing status are part of Stages 10–13. Accept the supported PDF, DOCX, XLS, and XLSX files; show a clear processing/not-ready state while parsing and indexing; and show the loaded message only after indexing has been verified. Do not route document questions to retrieval before READY. Keep normal tutor questions available during processing and after readiness. Initially show one active document per session unless the existing project already uses a different document model.

Do not build login, profile, history, analytics, or unrelated screens yet.

---

# 15. Project Structure

Keep frontend and backend separate.

```text
ai-tutor/
│
├── backend/
│   └── Python/FastAPI/LangGraph application
│
├── frontend/
│   └── React application
│
├── docs/
│   └── Project documentation
│
└── README
```

The backend should conceptually separate:

```text
API routes
LangGraph workflow
LangGraph state
AI/Gemini service
Request/response schemas
```

The frontend should conceptually separate:

```text
Pages
Reusable components
API communication
Application state
```

Do not create unnecessary abstractions before they are needed.

---

# 16. Environment Configuration

Use Poetry for the backend environment and dependency management.

Sensitive configuration should be provided through environment variables.

Example:

```text
GEMINI_API_KEY=...
```

A safe example configuration should be documented separately.

The real API key must never be committed to Git.

---

# 17. Gemini Prompt Design

Prompts should be separated according to responsibility.

Do not use one enormous prompt for the entire application.

The major prompt responsibilities are:

```text
Request scope classification
Teaching approach
Explanation
Example
Explain More
Another Example
Quiz generation
Answer evaluation
```

Define one concise shared **AI Tutor profile** and prepend it to every downstream content-generation prompt: explanations, examples, follow-ups, quiz generation, and quiz evaluation. The profile must keep the assistant in the AI Tutor role, limit output to educational help, and prohibit user-facing mentions of Google, Gemini, or large language models. This profile supplements, but does not replace, the Stage 5 identity and scope graph routes.

The scope-classification prompt must return only a validated category (`greeting`, `educational`, or `out_of_scope`) and associated classification fields. Identity queries are routed to a static response before any model call. Greeting, identity, and out-of-scope responses are static application text, not model-generated content.

The classifier is the first model call only for non-identity input. It classifies and returns structured fields; it does not write the greeting, identity, refusal, or lesson response. Only educational requests continue to downstream teaching-generation prompts.

Prompts should:

- Clearly define the task.
- Provide only required context.
- Specify the expected output.
- Avoid unnecessary instructions.
- Prevent unnecessary repetition.
- Encourage technically accurate answers.
- Keep generated content appropriate to the learner's level.

---

# 18. Structured Gemini Responses

Where practical, Gemini should return structured data rather than unpredictable free-form output.

For example:

```json
{
  "request_category": "educational",
  "is_greeting": false,
  "is_educational": true,
  "topic": "Python loops",
  "student_level": "beginner"
}
```

The category is one of `greeting`, `educational`, or `out_of_scope`. For `greeting`, set `is_greeting` true and `is_educational` false. For `educational`, set `is_greeting` false and `is_educational` true. For `out_of_scope`, set both false. Reject inconsistent or malformed output and route it to the static out-of-scope response.

or:

```json
{
  "explanation": "...",
  "key_points": ["...", "..."]
}
```

This allows LangGraph and FastAPI to work predictably with the model output.

---

# 19. Token Reduction Strategy

Token efficiency should be considered from the beginning.

### Do not send the complete conversation to Gemini every time.

Instead, send only the context required by the current node.

For example:

**Another Example**

Send:

```text
topic
current explanation
current example
```

rather than the entire conversation.

**Quiz Evaluation**

Send:

```text
question
answer criteria
user answer
```

rather than the entire teaching session.

### Other principles

- Keep system prompts concise.
- Avoid repeated instructions.
- Avoid unnecessary conversation history.
- Do not generate quizzes unless requested.
- Do not regenerate an entire explanation for Explain More.
- Keep response sizes appropriate.
- Use structured responses.
- Add explicit output limits where appropriate.
- Monitor token usage once the system is running.

The goal is:

```text
Minimum necessary context
+
Clear prompt
+
Correct output
```

rather than simply making every prompt longer.

---

# 20. Security Considerations

Security is not the main Phase 1 feature, but the architecture should allow it later.

Important future protections include:

- API authentication
- Authorization
- Rate limiting
- API key protection
- Request validation
- Input size limits
- Abuse protection
- Logging
- Error handling
- Secure CORS configuration
- Protection of user/session data
- Prompt-injection resistance and strict scope enforcement
- Fail-closed validation of classifier output
- Regression tests for identity leakage and off-topic answers

The Gemini API key must remain on the backend and must never be exposed to React.

---

# 21. Error Handling

The system should eventually handle:

- Gemini API failure
- Invalid request
- Empty question
- Invalid session ID
- Expired/missing session
- Invalid quiz answer
- LangGraph failure
- Timeout
- Rate limit
- Unexpected model response

The frontend should show useful user-facing messages instead of raw backend errors.

---

# 22. Future Expansion

The architecture should allow the following later:

### Database

Add persistent:

- Users
- Sessions
- Conversation history
- Learning progress
- Quiz results
- Saved topics

### RAG

RAG is part of the current Phase 1 plan (Stages 10–13), not a future expansion. The parser choices, Markdown normalization, local BGE embeddings, PostgreSQL + pgvector storage, retrieval, and readiness gate are defined in Section 7. Later expansion may add support for additional document formats or multiple active documents if needed.

### Authentication

Add:

```text
Login
 ↓
Authenticated API
 ↓
User-specific sessions
 ↓
Persistent learning history
```

### Advanced Learning

Potential additions:

- Difficulty adjustment
- Personalized learning plans
- Progress tracking
- Topic recommendations
- Multiple quiz types
- Learning analytics
- Saved learning sessions
- Multiple educational subjects (the product remains limited to teaching and learning)
- Teacher/admin features

---

# 23. What We Deliberately Do Not Build Yet

Do not add a technology simply because it may be useful later.

For Phase 1:

```text
No PostgreSQL relational database initially
No Redis
No authentication
No complex autonomous agent
No production scaling infrastructure
```

The vector database is a required Stage 11 component, but its implementation must wait for the user's explicit choice. The initial objective includes the **interactive teaching workflow and document-grounded tutoring**.

---

# 24. Final Phase 1 Architecture

```text
                    React
                      ↓
                  FastAPI
                      ↓
          Tutor / Quiz / Document APIs
                      ↓
       LangGraph (workflow, state, routing)
            ┌────────┴─────────┐
            ↓                  ↓
      Normal Tutor       Document question
            │             (only if READY)
            │                  ↓
            │          BAAI/bge-small-en-v1.5
            │                  ↓
            │        PostgreSQL + pgvector
            │                  ↓
            └──────────→ Gemini grounded answer
                       (retrieved context)
            ↓
       In-memory State
```

Document ingestion uses format-specific parsers (PyMuPDF, `python-docx`, and `pandas` + `openpyxl`) to create collision-safe timestamped Markdown before structure-aware chunking and indexing with local BGE embeddings in PostgreSQL + pgvector.

The core principle remains:

> **React handles interaction, FastAPI handles APIs, LangGraph handles workflow/state, and Gemini handles AI generation.**

This is the baseline architecture for implementation.