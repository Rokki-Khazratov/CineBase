# Development Guide

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Local Development

#### 1. Clone Repository

```bash
git clone https://github.com/Rokki-Khazratov/CineBase.git
cd CineBase
```

#### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with your settings
```

#### 3. Start Services

```bash
make up
make migrate
```

#### 4. Access Application

- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

## 🛠️ Available Commands

### Docker Commands

```bash
make up                    # Start all services
make down                  # Stop all services
make logs                  # View API logs
make restart               # Restart all services
```

### Database Commands

```bash
make migrate               # Run database migrations
make makemigration msg="description"  # Create new migration
make db-reset              # Reset database (dev only)
```

### Code Quality Commands

```bash
make fmt                   # Format code (ruff + black + isort)
make lint                  # Lint code
make typecheck             # Type checking with mypy
make test                  # Run all tests
make test-e2e              # Run E2E tests only
make test-unit             # Run unit tests only
make coverage              # Run tests with coverage
```

### Utility Commands

```bash
make clean                 # Clean cache files
make install               # Install dependencies
make shell                 # Open Python shell
make admin                 # Create admin user
```

## 🔄 Development Workflow

### 1. Start Development

```bash
make up
make migrate
```

### 2. Make Changes

- Edit code in your preferred editor
- Follow the project structure and conventions

### 3. Format & Lint

```bash
make fmt
make lint
```

### 4. Run Tests

```bash
make test
```

### 5. Create Migration (if DB changes)

```bash
make makemigration msg="Add new field"
make migrate
```

### 6. Commit Changes

```bash
git add .
git commit -m "feat: add new feature"
git push
```

## 📁 Project Structure

```
cinebase/
├── app/                    # Main application code
│   ├── api/               # API routes
│   ├── core/              # Core functionality
│   ├── db/                # Database configuration
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── repositories/      # Data access layer
│   └── utils/             # Utility functions
├── tests/                 # Test files
├── docs/                  # Documentation
├── docker/                # Docker configuration
└── alembic/               # Database migrations
```

## 🧪 Testing

### Test Structure

```
tests/
├── conftest.py            # Test configuration
├── e2e/                   # End-to-end tests
│   ├── test_auth.py
│   ├── test_movies_crud.py
│   └── test_movies_list.py
└── unit/                  # Unit tests
    ├── test_auth_service.py
    └── test_movie_service.py
```

### Running Tests

```bash
# All tests
make test

# Specific test types
make test-e2e              # E2E tests
make test-unit             # Unit tests

# With coverage
make coverage

# Specific test file
pytest tests/e2e/test_auth.py

# Specific test function
pytest tests/e2e/test_auth.py::test_register_user
```

### Test Coverage

- **Target**: 85% line coverage
- **E2E Tests**: Full API integration tests
- **Unit Tests**: Service and utility function tests

## 🐛 Debugging

### View Logs

```bash
make logs                  # View all logs
make logs api              # View API logs only
make logs db               # View database logs
make logs redis            # View Redis logs
```

### Debug Mode

```bash
# Set in .env
DEBUG=True
LOG_LEVEL=DEBUG
```

### Database Access

```bash
# Connect to database
docker exec -it cinebase_db psql -U cinebase -d cinebase

# View tables
\dt

# View data
SELECT * FROM users;
SELECT * FROM movies;
```

### Redis Access

```bash
# Connect to Redis
docker exec -it cinebase_redis redis-cli

# View keys
KEYS *

# View cache
GET cb:movies:list:abc123
```

## 🔧 Code Quality

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Code Formatting

- **Ruff**: Fast Python linter
- **Black**: Code formatter
- **isort**: Import sorter

### Type Checking

- **mypy**: Static type checker
- **Strict mode**: Enabled for better type safety

### Linting Rules

- **Line length**: 88 characters
- **Import sorting**: Black profile
- **Type hints**: Required for all functions

## 🚀 Performance

### Database Optimization

- **Indexes**: On frequently queried fields
- **Connection pooling**: Async SQLAlchemy
- **Query optimization**: Efficient joins and filters

### Caching Strategy

- **Redis**: For frequently accessed data
- **TTL**: 60 seconds for movies, 300 seconds for users
- **Cache invalidation**: On write operations

### API Performance

- **Pagination**: Limit response size
- **Filtering**: Reduce data transfer
- **Async operations**: Non-blocking I/O

## 🔒 Security

### Authentication

- **JWT tokens**: Stateless authentication
- **Password hashing**: bcrypt with 12 rounds
- **Token expiration**: 15 minutes (configurable)

### Authorization

- **Role-based access**: User/Admin roles
- **Route protection**: Dependency injection
- **Input validation**: Pydantic schemas

### Data Protection

- **SQL injection**: Protected by ORM
- **CORS**: Configurable origins
- **Environment variables**: Sensitive data

## 📊 Monitoring

### Health Checks

- **Database**: Connection status
- **Redis**: Cache availability
- **Application**: Service status

### Logging

- **Structured logging**: JSON format
- **Request tracking**: Correlation IDs
- **Error logging**: Stack traces

### Metrics

- **Response times**: Request duration
- **Cache hit rates**: Redis statistics
- **Error rates**: Exception tracking

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed

```bash
# Check if database is running
docker ps | grep postgres

# Restart database
docker-compose restart db

# Check logs
make logs db
```

#### Redis Connection Failed

```bash
# Check if Redis is running
docker ps | grep redis

# Restart Redis
docker-compose restart redis

# Check logs
make logs redis
```

#### Migration Failed

```bash
# Check migration status
alembic current

# Reset migrations (dev only)
make db-reset
make migrate
```

#### Tests Failing

```bash
# Check test database
docker exec -it cinebase_db psql -U cinebase -d cinebase_test

# Reset test database
make test-reset
```

### Getting Help

1. Check the logs: `make logs`
2. Verify environment variables
3. Check Docker services: `docker ps`
4. Review the documentation
5. Open an issue on GitHub

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)
- [Redis Documentation](https://redis.io/documentation)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
