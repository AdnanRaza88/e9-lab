# Architecture - E9

## Frontend
- HTML (app.html, login.html)
- CSS (style.css)
- JS (app.js, auth.js)

## Backend (Proposed)
- FastAPI / Flask

## Structure

Frontend → API → Backend → AI Engine

## Components

### Frontend
- Auth UI
- Dashboard UI
- Result Renderer

### Backend
- Auth routes
- Grading route
- Rubric manager

### AI Layer
- LLM scoring logic

## Data Flow

User Input → API → AI → Response → UI

## Future Scaling
- Microservices
- Database (PostgreSQL)
- Redis cache
