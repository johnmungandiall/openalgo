# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenAlgo is an open-source algorithmic trading platform that provides a unified API layer across 30+ Indian brokers. Built with Python Flask backend and React 19 frontend, it enables traders to automate strategies from multiple platforms (TradingView, Amibroker, Python, etc.) without being locked into a single broker.

## Development Commands

### Backend (Python Flask)

```bash
# Install dependencies (uv handles virtualenv automatically)
uv sync

# Run development server (auto-reloads on code changes)
uv run app.py

# Run with Gunicorn (Linux only, production mode)
uv run gunicorn --worker-class eventlet -w 1 app:app

# Linting and formatting
uv run ruff check .              # Check for issues
uv run ruff check --fix .        # Auto-fix issues
uv run ruff format .             # Format code

# Testing
uv run pytest test/ -v           # Run all tests
uv run pytest test/test_file.py -v  # Run specific test file
uv run pytest test/ --cov        # Run with coverage
```

### Frontend (React 19)

```bash
cd frontend

# Install dependencies
npm install

# Development server with hot reload (http://localhost:5173)
npm run dev

# Build for production (output to frontend/dist/)
npm run build

# Linting and formatting
npm run lint                     # Check for issues
npm run format                   # Format code
npm run check                    # Lint + format

# Testing
npm test                         # Run tests in watch mode
npm run test:run                 # Run tests once
npm run test:coverage            # Run with coverage
npm run e2e                      # Run Playwright E2E tests
```

### Environment Setup

```bash
# Copy sample environment file
cp .sample.env .env

# Generate secure keys for APP_KEY and API_KEY_PEPPER
uv run python -c "import secrets; print(secrets.token_hex(32))"

# Edit .env and configure:
# - APP_KEY and API_KEY_PEPPER (generated above)
# - VALID_BROKERS (comma-separated list)
# - Broker API credentials
```

## Architecture

### Backend Structure

- **app.py**: Main Flask application entry point with blueprint registration
- **blueprints/**: Flask route handlers organized by feature (auth, orders, telegram, etc.)
- **restx_api/**: REST API endpoints (`/api/v1/`) with Flask-RESTX for Swagger docs
- **services/**: Business logic layer separated from route handlers
- **broker/**: Broker integrations - each broker has its own directory with standardized structure:
  - `api/`: Authentication, orders, market data, funds
  - `database/`: Master contract management
  - `mapping/`: Data transformation between OpenAlgo and broker formats
  - `streaming/`: WebSocket adapter for real-time data
  - `plugin.json`: Broker configuration metadata
- **database/**: SQLAlchemy models and database utilities (5 separate SQLite databases)
- **websocket_proxy/**: Unified WebSocket server (port 8765) with ZeroMQ message bus
- **utils/**: Shared utilities and helpers

### Frontend Structure

- **frontend/src/components/**: React components built with shadcn/ui (Radix UI + Tailwind)
- **frontend/src/pages/**: Route-level page components
- **frontend/src/api/**: API client functions for backend communication
- **frontend/src/stores/**: Zustand state management stores
- **frontend/src/hooks/**: Custom React hooks
- **frontend/dist/**: Production build output (gitignored, auto-built by CI)

### Key Technologies

**Backend**: Flask 3.1, SQLAlchemy 2.0, Flask-SocketIO 5.6, ZeroMQ, Argon2 (password hashing), Cryptography (token encryption)

**Frontend**: React 19, TypeScript 5.9, Vite 7, TailwindCSS 4, shadcn/ui, TanStack Query 5, Zustand 5, Socket.IO Client

**Data**: SQLite (4 databases: main, logs, latency, sandbox), DuckDB (historical data via Historify)

### Database Architecture

OpenAlgo uses 5 separate SQLite databases for isolation:
- **openalgo.db**: Main application data (users, settings, strategies)
- **logs.db**: API traffic logs and monitoring data
- **latency.db**: Order execution latency tracking
- **sandbox.db**: API Analyzer mode with virtual trading (₹1 Crore capital)
- **historify.db**: DuckDB for historical market data storage

### Real-Time Communication

- **WebSocket Proxy Server**: Runs on port 8765, provides unified WebSocket interface across all brokers
- **ZeroMQ Message Bus**: High-performance message distribution for market data
- **Socket.IO**: Real-time updates for orders, trades, positions, and logs in the React frontend

## Development Workflow

### Two-Terminal Setup (Recommended for Frontend Work)

**Terminal 1 - React Dev Server:**
```bash
cd frontend
npm run dev  # Hot reload at http://localhost:5173
```

**Terminal 2 - Flask Backend:**
```bash
uv run app.py  # API at http://127.0.0.1:5000
```

The React dev server proxies API requests to Flask. For production testing, build frontend with `npm run build` and access via Flask at port 5000.

### Access Points

- Main app: http://127.0.0.1:5000
- React frontend: http://127.0.0.1:5000/react
- Swagger API docs: http://127.0.0.1:5000/api/docs
- API Analyzer: http://127.0.0.1:5000/analyzer

### First-Time Setup

1. Navigate to http://127.0.0.1:5000/setup
2. Create admin user account
3. Login and configure broker in Settings

## Code Style and Standards

### Python

- Follow PEP 8 style guide
- Use 4 spaces for indentation
- Maximum 100 characters line length (configured in Ruff)
- Use Google-style docstrings
- Imports order: Standard library → Third-party → Local
- Always use `uv run` for Python commands (never use global Python)

### TypeScript/React

- Use functional components with hooks
- Component files use PascalCase: `MyComponent.tsx`
- Follow Biome.js rules (configured in `frontend/biome.json`)
- Use TanStack Query for server state, Zustand for client state
- Prefer shadcn/ui components for UI consistency

### Commit Messages

Follow Conventional Commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

## Testing

### Backend Testing

- Write pytest tests in `test/` directory
- Test files: `test_*.py`
- Test functions: `test_*`
- Use fixtures for common setup
- Mock external broker API calls

### Frontend Testing

- Write Vitest tests in `__tests__/` directories
- Use React Testing Library for component tests
- Write Playwright tests in `frontend/e2e/` for E2E scenarios
- Test accessibility with axe-core

## Security Considerations

- Never commit `.env` file or sensitive credentials
- Use environment variables for all secrets
- Validate all inputs at system boundaries (user input, external APIs)
- Use SQLAlchemy ORM with parameterized queries (never raw SQL with string interpolation)
- CSRF protection is enabled via Flask-WTF
- Rate limiting is configured per endpoint via Flask-Limiter
- Passwords use Argon2 hashing, tokens use Fernet encryption

## Broker Integration

When adding a new broker, create directory structure under `broker/your_broker_name/`:
- `api/auth_api.py`: Authentication and session management
- `api/order_api.py`: Order placement, modification, cancellation
- `api/data.py`: Market data, quotes, historical data
- `api/funds.py`: Account balance and margin
- `database/master_contract_db.py`: Symbol master contract management
- `mapping/order_data.py`: Transform OpenAlgo format to broker format
- `streaming/broker_adapter.py`: WebSocket adapter for live data
- `plugin.json`: Broker configuration metadata

Reference implementations: `broker/zerodha/` (most complete), `broker/dhan/` (modern API design)

## Important Notes

- **Always use `uv run`** for Python commands - never use global Python or manually manage virtual environments
- **WebSocket compatibility**: Use `-w 1` (one worker) with Gunicorn for WebSocket support
- **Frontend builds**: `frontend/dist/` is gitignored and auto-built by CI - do not commit it
- **Static IP whitelisting**: Many Indian brokers require whitelisting your public IP for API access
- **Python version**: Requires Python 3.12+ (supports 3.12, 3.13, 3.14)
- **Node.js version**: Requires Node.js 20, 22, or 24

## Contribution Guidelines

- Submit one feature or one fix per pull request
- Break large features into small, self-contained PRs
- Exception: New broker integrations may be submitted as a single PR
- Test thoroughly before submitting (run linters, tests, manual testing)
- Include screenshots for UI changes
- Update documentation if adding new features

## Common Patterns

### API Response Format

All REST API endpoints return consistent JSON:
```python
{
    'status': 'success' | 'error',
    'message': 'Human-readable message',
    'data': {...}  # Optional payload
}
```

### Database Queries

Use SQLAlchemy ORM with eager loading to avoid N+1 queries:
```python
from sqlalchemy.orm import joinedload
users = User.query.options(joinedload(User.orders)).all()
```

### React Component Pattern

```tsx
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

function MyComponent() {
  const { data, isLoading } = useQuery({
    queryKey: ['key'],
    queryFn: () => api.fetchData(),
  });

  if (isLoading) return <div>Loading...</div>;
  return <Card>...</Card>;
}
```

## Performance Optimization

- Use caching for frequently accessed data (e.g., symbol lookups)
- Batch API calls when possible (use broker batch endpoints)
- Optimize database queries with eager loading
- Use TanStack Query for automatic caching and deduplication
- Minimize WebSocket subscriptions (subscribe only to needed symbols)

## Troubleshooting

### Frontend Build Errors
```bash
cd frontend
rm -rf node_modules
npm install
npm run build
```

### Python Dependency Issues
```bash
rm -rf .venv
uv sync
```

### WebSocket Connection Issues
- Ensure `WEBSOCKET_HOST='127.0.0.1'` and `WEBSOCKET_PORT='8765'` in `.env`
- Use only one worker with Gunicorn: `uv run gunicorn --worker-class eventlet -w 1 app:app`
- Check firewall settings for port 8765
