# Antigravity Bundle Status & Audit

## 1. Technical Audit

### Health & Status
The system is composed of **3 primary microservices** running in a unified Docker environment (`apps/` directory). 
- **Platform**: Linux (Ubuntu).
- **Orchestration**: Docker Compose (`version: '3.8'`).
- **Networking**: Bridged network `antigravity_net`.
- **Proxy**: Caddy (v2) handles SSL termination and reverse proxying (Ports 80/443).

### Component Breakdown
| Service | Technology | Port Config (Internal) | Status |
|:---|:---|:---|:---|
| **Portfolio** | Python 3.11 / Uvicorn | `8000` (Apps), `8001` (Compose hint) | **Functions Correctly**. Caddy points to `8000`. The `compose` expose of `8001` is a documentation error but harmless. |
| **Inventory** | Python 3.11 / Flask | `8010` | **Healthy**. Caddy and Container both agree on `8010`. |
| **AI Receptionist** | Python 3.11 / Uvicorn | **ERROR**: `8010` (Container) vs `8020` (Caddy) | **CRITICAL MISMATCH**. Container listens on `8010` (hardcoded in Dockerfile), but Caddy proxies to `8020`. **Service is likely unreachable**. |

### Infrastructure
- **Databases**:
  - `portfolio_db`: Postgres 15 Alpine.
  - `ai_receptionist_db`: Postgres 15.
  - `ai_receptionist_redis`: Redis 7 (Caching/Queues).
  - `ai_receptionist_qdrant`: Qdrant (Vector DB).
- **Secrets**: Managed via `.env` file. Safe.
- **Organization**: Monorepo structure (`apps/` for code, `testing/` for labs).

---

## 2. File Architecture

The codebase follows a "Monorepo" style structure:

```
/home/lex/antigravity_bundle/
├── apps/                          # Production Source Code
│   ├── portfolio/                 # Portfolio Website & Backend
│   ├── inventory_manager/         # Inventory Management System
│   └── ai_receptionist/           # AI Voice/Text Agent (Gemini)
├── testing/                       # Development & Experimental builds
├── data/                          # Persistent storage (if local mounts used)
├── docker-compose.yml             # Master Orchestration
├── Caddyfile                      # Reverse Proxy Configuration
└── .env                           # Environment Variables (Secrets)
```

**Key Files:**
- `docker-compose.yml`: defined the "State of the World". It spins up all 3 apps and their dependencies together.
- `Caddyfile`: Maps domains to internal containers. **Note**: Check `receptionist.lexmakesit.com` mapping; it directs to 8020 which is likely closed.

---

## 3. Future Plans & Performance Impact

Here are potential architectural additions and their estimated impact on system latency:

### A. Observability Suite (Prometheus + Grafana)
*   **Description**: Real-time metrics for CPU, RAM, and request rates.
*   **Latency Impact**: **~0ms**. Metrics are "scraped" asynchronously; it does not block user requests.
*   **Resource Cost**: ~500MB RAM.

### B. Centralized Logging (Loki or ELK)
*   **Description**: searchable logs for all services in one dashboard.
*   **Latency Impact**: **~0ms**. Logs are shipped asynchronously (e.g., via Docker drivers).
*   **Resource Cost**: Medium (High disk usage).

### C. Authentication Gateway (e.g., Keycloak)
*   **Description**: Centralized login/SSO for all internal tools.
*   **Latency Impact**: **~50-100ms** per login request; **~5-10ms** for subsequent token validation checks.

### D. Redis Caching Layer for Portfolio
*   **Description**: Cache common DB queries for the portfolio website.
*   **Latency Impact**: **-50ms to -200ms** (Reduces latency significantly and improves "Snap" feel).

### E. Service Mesh (Linkerd/Istio)
*   **Description**: Advanced mTLS security and traffic control.
*   **Latency Impact**: **+2-10ms** per service hop. (Likely overkill for current scale).

---

## 4. Documentation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local dev)

### Getting Started

1.  **Configure Environment**:
    Ensure `.env` exists in the root with all necessary API keys.

2.  **Start Services**:
    ```bash
    # Run in detached mode (background)
    docker-compose up -d
    ```

3.  **View Logs**:
    ```bash
    docker-compose logs -f
    ```

4.  **Fixing the AI Receptionist Port (Recommended)**:
    Open `docker-compose.yml` and change `expose` for `ai_receptionist_app` to `8010`, and update `Caddyfile` to proxy to `ai_receptionist_app:8010`.
