# Prime Bank Chatbot

Banking chatbot with LLM-powered intent detection, multi-agent orchestration, and comprehensive product knowledge base.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key
- LangFuse account (optional, for observability)

### Setup

1. **Clone & configure**
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. **Start services**
```bash
docker-compose up -d
```

3. **Verify health**
```bash
curl http://localhost:8000/health
```

4. **Access API**
- FastAPI docs: http://localhost:8000/docs
- LangFuse: http://localhost:3000

## Architecture

```
FastAPI (8000)
├── Intent Detector (OpenAI)
├── Conversation Manager (Redis)
├── Knowledge Base (JSON)
└── Domain Agents (LangGraph)

Services:
├── Redis (6379) - Session state
├── PostgreSQL (5432) - LangFuse (optional)
└── LangFuse (3000) - Observability
```

## API Usage

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "user_message": "Show me credit cards",
    "channel": "web",
    "language": "en"
  }'
```

## Testing

```bash
# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html

# Load testing
locust -f tests/load_test.py --host=http://localhost:8000
```

## Development

### Add new intent type
1. Update `app/models/intent.py::IntentType`
2. Add handling in `app/core/intent_detector.py`
3. Update `INTENT_DETECTION_PROMPT`

### Add new product
1. Update JSON in `app/knowledge/structured/`
2. Add markdown documentation
3. Update knowledge loader if needed

### Add new agent
1. Create agent file in `app/domains/`
2. Register in router
3. Update intent detection logic

## Monitoring

### LangFuse Dashboard
- Trace every LLM call
- Monitor agent routing
- Identify failures
- Track latency & costs

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Redis health
redis-cli ping
```

## Deployment

Production deployment uses multi-stage Docker build:
- Smaller image size
- No build dependencies in runtime
- Health checks enabled
- CORS configured for frontend

Edit docker-compose.yml for production environment variables.

## Structure

```
app/
├── main.py                 # FastAPI app
├── api/                    # REST endpoints
├── core/                   # Business logic
│   ├── config.py          # Settings
│   ├── intent_detector.py # Intent classification
│   ├── conversation.py    # Session state (Redis)
│   └── knowledge.py       # Knowledge base loader
├── models/                # Pydantic schemas
├── domains/               # Agent implementations
└── knowledge/             # Product JSON & markdown

tests/                      # Pytest suite
documentation/              # Architecture & guides
```

## Support

See documentation/ for:
- SYSTEM_ARCHITECTURE.md - Full design
- MODELS_SPECIFICATION.md - Pydantic schemas
- TESTING_STRATEGY.md - Testing guide
- API_SPECIFICATION.md - API details
