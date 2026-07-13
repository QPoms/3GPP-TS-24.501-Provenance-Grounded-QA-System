# API configuration

The application runtime uses the OpenAI Responses API with function calling. API credentials
must remain local and must never be committed to the repository.

## Official OpenAI API

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Set the key and a model available to your API account:

```dotenv
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=your_available_model
OPENAI_BASE_URL=
```

Run:

```powershell
uv run kg-agent ask "How is replay protection handled for NAS signalling?"
```

## Compatible custom endpoint

Do not share the API key in chat, issues, screenshots, commits, or logs. Configure only the
endpoint URL and model name in addition to the local key:

```dotenv
OPENAI_API_KEY=your_local_secret
OPENAI_MODEL=the_model_name_required_by_your_provider
OPENAI_BASE_URL=https://your-provider.example/v1
```

The endpoint should implement the OpenAI Responses API, including:

- `POST /v1/responses`
- Function tool definitions
- `function_call` response items
- `function_call_output` inputs
- `previous_response_id` continuation

Some compatible endpoints can create tool calls but fail on `previous_response_id`
continuation. The runtime includes a narrow fallback for the provider error that says a
requested item was created under a different Azure OpenAI resource. In that case, the QA
runtime retries the tool-output step without `previous_response_id` and sends only minimal
function-call metadata.

An endpoint that implements only `/v1/chat/completions` is still not sufficient for the
current adapter. A separate Chat Completions adapter can be added later without changing the
local tools.

## Safety behavior

- Missing keys or model names fail before an API request is made.
- Tool calls are capped at six by default.
- Graph hops are capped at three in the QA runtime tool schema.
- The model has no shell or filesystem tool.
- Specification excerpts and graph results are bounded.
- A `chunk_id` in the final answer is rejected if that ID was not returned by a tool during the
  current QA run.
- Tool traces show names and arguments, not private chain-of-thought.
