# AI Tutor Project Instructions

## Project Goal
Build the Phase 1 education-only AI Tutor described in `docs/AI Tutor - Teaching Bot — Project Blueprint.md`, following the sequence in `docs/AI Tutor - Teaching Bot — Implementation Roadmap.md`. It may teach multiple academic subjects, but it is not a general-purpose chatbot. React handles interaction, FastAPI handles HTTP and validation, LangGraph controls workflow and state, and the backend model classifies or generates learning content.

## Stage Progress
Status reviewed on 2026-10-03:

- **Stage 1 — Project Setup: Complete.** Poetry/FastAPI, LangGraph and Gemini dependencies are configured in `pyproject.toml`; the React/Vite frontend exists under `frontend/`.
- **Stage 2 — Basic FastAPI API: Complete for local development.** The health endpoint and Gemini endpoint are available, local Vite CORS is configured, and the learner confirmed both servers run.
- **Stage 3 — Gemini Connection: Complete.** `backend/app/services/gemini.py` uses the account-verified `gemini-3.1-flash-lite` model by default, applies explicit IPv4 transport for this development environment, and surfaces unavailable models and provider failures. Never move the key to the frontend.
- **Stage 4 — Basic React Tutor UI: Complete per learner verification.** Dashboard and tutor pages are under `frontend/src/pages/`; reusable navigation, form, response, header, and footer UI are under `frontend/src/components/`; tutor state and API communication are in `hooks/` and `services/`. The tutor retains ordered turns until Clear Chat, clears the composer after sending, and pins the composer beneath the scrollable transcript. Browser checks covered multiple turns, retry, reset, navigation, and mobile overflow.
- **Stage 5 — Guarded LangGraph Foundation: Complete.** The existing tutor endpoint routes every message through a deterministic identity check and a structured scope-classification node before teaching. Identity, greeting, and out-of-scope responses are static; malformed or failed classifications fail closed. Only educational classifications reach the teaching node. Mocked tests cover the routing branches and identity bypass.
- **Tutor capabilities response and broad topic classification: Complete.** Narrow tutor-help questions receive a static overview of broad academic and technical learning capabilities. Learning questions across academic and technical topics classify as educational, while practical/commercial/creative requests still take the refusal path.
- **Basic conversation handling: Complete.** Common greetings, wellbeing questions, thanks, farewells, and simple requests for explanation/help receive relevant static responses before classification. Educational questions with added greetings still continue through scope classification and teaching.
- **Stage 6 — AI Tutor Identity and Scope Prompts: Complete.** A shared profile is prepended to all teaching, example, follow-up, and quiz generation prompts. The educational path stores a validated teaching plan, explanation, and example; quiz questions/answers are validated and evaluated in separate nodes. Output checks reject prohibited self-identification without blocking educational discussion of model concepts, and API actions carry only bounded lesson context.
- **Stage 6 modularity and broad learning coverage: Complete.** Graph node responsibilities are separated into conversation, classification, teaching, follow-up, assessment, and shared generation-support modules. Classification is not restricted to a hard-coded subject list, and teaching prompts adapt to the requested level and depth.
- **Quota error handling: Complete.** Gemini HTTP 429 quota exhaustion is surfaced as an API 429 instead of being mistaken for an out-of-scope classification. Malformed classifier output still fails closed to the static refusal.
- **Stage 7 — Session Management: Complete.** The backend generates a `session_id` for a new tutor session and returns it to React on a successful response. React stores only that ID in `localStorage`. The process-local backend session store keeps the latest LangGraph `TutorState` and successful user/assistant turns in RAM, keyed by session ID. Follow-ups receive the latest question plus retained learning context; a session GET restores the transcript after refresh. Clear Chat deletes backend state and the browser ID. Backend restart loses the sessions; a missing ID is discarded during restoration. Sending a question remains available while transcript restoration is pending.

### Current Work: Stage 8 — Explain More
Implement the roadmap's explain-more behavior using the active session's retained learning context. Preserve the guarded Stage 5 graph routes, Stage 6 profile on generated content, and Stage 7 session lifecycle.

The tutor uses static text for identity, greetings, and out-of-scope replies. Generated educational responses must not identify the assistant as Google, Gemini, or a language model, but may discuss these as educational topics when relevant.

Keep the Gemini key exclusively in the backend. The UI uses `VITE_API_URL` only for the backend base URL.

## Frontend Structure and Styling
- `frontend/src/App.jsx` composes the application shell and top-level hash navigation; keep it small and avoid page markup or request logic here.
- `frontend/src/pages/` contains page-level composition. Put page-specific styling in a matching stylesheet beside the page component.
- `frontend/src/components/` contains reusable UI pieces. Put component-specific styling in a matching stylesheet beside that component when it has meaningful styles.
- `frontend/src/hooks/` contains reusable React stateful behavior; `frontend/src/services/` contains API communication and other external service calls.
- `frontend/src/App.css` is only for application-shell layout and shared page framing. `frontend/src/index.css` is only for global design tokens, resets, and base element/accessibility rules.
- Do not accumulate page or component styles in `App.css` or `index.css`. Prefer colocated styles; share a stylesheet only when the rules are genuinely global or shared.
- Keep pages focused on composition, components focused on UI, hooks focused on stateful behavior, and services focused on I/O. Never put Gemini keys or direct Gemini calls in the frontend.
- Keep chat turns as ordered `{ id, role, content }` entries in frontend state and in backend session history. Show user prompts and tutor replies chronologically, clear the composer when sending, and use Clear Chat to explicitly remove the active transcript and session.
- Keep transcript history distinct from graph context. The backend retains the latest `TutorState`; each graph invocation receives the newest question and carries forward available learning fields such as topic, explanation, example, and quiz context. Do not send the entire transcript to the model by default.
- On refresh, restore the transcript using the browser's stored session ID. Do not make the Ask tutor button depend on transcript restoration completing; if a new request starts first, cancel the in-flight restore so stale history cannot overwrite the new turn.

## Tutor Identity and Scope
- The product domain is teaching and learning across academic subjects, not general-purpose assistance. The assistant identifies as an independent AI Tutor.
- Every new message first passes a deterministic identity-intent check. Identity requests receive a static AI Tutor response and bypass all model calls.
- Narrow questions about what the tutor can teach or what learners can ask receive a static application response after the identity check and before general scope classification. Do not route requests that merely contain those phrases alongside an unrelated task into this response.
- Common standalone greetings, wellbeing exchanges, thanks, farewells, and simple help/clarification requests receive relevant static responses after the identity and capabilities checks. These narrow patterns must not capture substantive educational questions.
- Every other non-identity message is classified by the first LLM call as `greeting`, `educational`, or `out_of_scope`. Greetings receive a static welcome; only educational requests enter teaching nodes; out-of-scope or malformed classifications receive a static polite refusal.
- A greeting paired with a clear learning question is educational. Practical/commercial tasks, recipes, creative writing, and unrelated requests are out of scope. For mixed requests, answer only a separable educational part; otherwise refuse.
- Classify concept-definition and explanation questions broadly as educational across academic and technical topics. Do not rely on a fixed list of subjects or reject a learning question only because its topic is specialized or advanced.
- Track `is_greeting` and `is_educational` in LangGraph state and keep them consistent with `request_category`.
- Prepend the shared AI Tutor profile to all generated teaching, example, follow-up, and quiz content. User attempts to override the identity or educational boundary must not change graph routing or output policy. Reject explicit assistant self-identification as a provider or language model; allow educational discussion of those concepts.

## Environment and Secrets
- Do not print environment file contents. The learner has verified that the Gemini backend works; if API requests fail, check the local key without exposing it.
- Never print, expose, or commit API keys. Keep secrets on the backend; do not put them in `frontend/.env` or any `VITE_` variable.
- The root `.gitignore` already ignores backend and frontend `.env` files. Preserve that protection.
- `frontend/.env` currently sets `VITE_API_URL=http://localhost:8000`.
- The Gemini account currently supports `gemini-3.1-flash-lite`; keep `GEMINI_MODEL` aligned with an enabled model. This development environment cannot establish Gemini connections over IPv6, so `GEMINI_IPV4_ONLY=true` is the backend default; set it to `false` only in an IPv6-only environment.

## Development Conventions
- Read the roadmap and nearby implementation before making a stage change.
- Preserve the documented architecture and public API contracts; keep edits limited to the current stage.
- Use existing dependencies and patterns. Avoid adding databases, authentication, RAG, or other explicitly deferred features.
- Validate each stage against its roadmap completion condition before marking it complete here. Record only verified progress and update this file when stage status changes.
- Do not treat a dependency being installed or a server command having been run as proof that a feature works.

## Verification Note
Stage 7 session behavior is covered by backend tests for follow-up context, session-state retention, transcript restoration data, and Clear Chat removal. On 2026-10-03, all 32 backend unit tests passed, and a live educational request completed through the local tutor API with HTTP 200 in about 9 seconds using the account-verified model. Frontend `npm run lint` and `npm run build` passed in the prior UI stage. Run relevant backend and frontend checks after subsequent API, session, or workflow changes.
