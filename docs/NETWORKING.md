# 🌐 SAGA GRAPH NETWORKING ARCHITECTURE

## **Overview**

SAGA Graph uses NGINX as a single entry point (port 80) to route all external traffic. The `/api` prefix is used as a routing signal to distinguish between frontend assets and backend API calls.

**CRITICAL DESIGN DECISIONS:**

1. **`/api` Prefix Preservation:** NGINX does NOT strip the `/api` prefix - backend routes include `/api/` in their paths
2. **Three Authentication Methods:** API Key (workers) OR `session_token` cookie (backend) OR `user` cookie (frontend)
3. **Login Exception:** `/api/login` bypasses auth check (must be defined BEFORE `/api/` in NGINX)
4. **Dual-Cookie System:** Backend sets `session_token`, Frontend sets `user` - NGINX accepts EITHER
5. **Cookie Path:** All cookies use `path="/"` to apply to all routes

---

## **Quick Reference**

### **Authentication Methods**

| Method | Used By | Header/Cookie | Purpose |
|--------|---------|---------------|---------|
| API Key | Workers, External clients | `X-API-Key: <key>` | Machine-to-machine auth |
| session_token | Backend | Cookie: `session_token=<hash>` | Backend-managed sessions |
| user | Frontend | Cookie: `user=<json>` | Frontend state + auth |

### **Key Endpoints**

| Endpoint | Auth Required | Purpose |
|----------|---------------|---------|
| `/api/login` | ❌ NO | Login endpoint (exception) |
| `/api/*` | ✅ YES | All other API endpoints |
| `/` | ❌ NO | Frontend assets |
| `/neo4j/` | ❌ NO | Neo4j browser |

### **Cookies Set During Login**

```
POST /api/login
  ↓
Backend validates credentials
  ↓
Backend sets: session_token (HttpOnly, 24h, path=/, SameSite=lax)
Frontend sets: user (HttpOnly, 24h, path=/)
  ↓
Browser has TWO cookies for subsequent requests
```

---

## **Architecture Diagram**

```
External Client (Browser/Mac)
    ↓
http://SERVER-IP:80
    ↓
┌─────────────────────────────────────────────────────────┐
│                    NGINX (Port 80)                      │
│                  Single Entry Point                     │
│                                                         │
│  Routes:                                                │
│  - /api/*  → Backend (with API key check)              │
│  - /neo4j/ → Neo4j Browser                             │
│  - /*      → Frontend                                   │
└─────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Frontend   │   │   Backend    │   │   Neo4j      │
│  (Port 5173) │   │  (Port 8000) │   │ (7474, 7687) │
│  Internal    │   │  Internal    │   │  Exposed     │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                    ┌───────┴───────┬──────────────┐
                    │               │              │
                    ▼               ▼              ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ Worker Main  │ │ Worker Src   │ │ External     │
            │ (internal)   │ │ (internal)   │ │ Worker (Mac) │
            │ With API key │ │ With API key │ │ With API key │
            └──────────────┘ └──────────────┘ └──────────────┘
```

---

## **Exposed Ports**

| Port | Service | Access | Purpose | Routes |
|------|---------|--------|---------|--------|
| 80 | NGINX | External | Single entry point for all HTTP traffic | `/`, `/api/*`, `/neo4j/*` |
| 7687 | Neo4j Bolt | External | Database access for external workers | N/A (Bolt protocol) |
| 7474 | Neo4j Browser | External (via /neo4j) | Database browser UI | `/neo4j/*` |
| 5173 | Frontend | Internal only | Svelte dev server | `/*` (assets) |
| 8000 | Backend API | **Exposed for dev** | FastAPI backend | `/health`, `/api/*` |
| 8001 | Graph API | Internal only | Neo4j graph operations | `/neo/*` |

**Note:** Port 8000 is exposed in `docker-compose.yml` for local development. In production, only port 80 should be exposed externally.

---

## **Routing Rules**

### **1. Frontend Assets (No API Key Required)**

**Pattern:** `/*` (anything NOT starting with `/api`)

**Examples:**
```
http://localhost/                    → Frontend homepage
http://localhost/login               → Frontend login page
http://localhost/dashboard           → Frontend dashboard
http://localhost/styles.css          → Frontend CSS
http://localhost/app.js              → Frontend JavaScript
```

**NGINX Config:**
```nginx
location / {
    proxy_pass http://frontend;
}
```

---

### **2. Backend API Calls (Cookie OR API Key Required)**

**Pattern:** `/api/*`

**Examples:**
```
http://localhost/api/login                  → Backend /api/login endpoint (NO AUTH)
http://localhost/api/strategies             → Backend /api/strategies endpoint
http://localhost/api/articles/ingest        → Backend /api/articles/ingest endpoint
http://localhost/api/users                  → Backend /api/users endpoint
```

**NGINX Config:**
```nginx
# Login endpoint - NO AUTH REQUIRED (must come before /api/)
location = /api/login {
    # Allow anyone to attempt login
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Cookie $http_cookie;
}

# Backend API - Require API key OR session cookie OR user cookie
location /api/ {
    # Allow if: has valid API key OR has session_token OR has user cookie
    set $auth_ok 0;
    
    # Check API key
    if ($api_key_valid = 1) {
        set $auth_ok 1;
    }
    
    # Check session_token cookie (backend auth)
    if ($cookie_session_token != "") {
        set $auth_ok 1;
    }
    
    # Check user cookie (frontend auth)
    if ($cookie_user != "") {
        set $auth_ok 1;
    }
    
    # Reject if none
    if ($auth_ok = 0) {
        return 401 '{"error": "Authentication required"}';
    }
    
    # Forward WITH /api prefix (NO trailing slash!)
    proxy_pass http://backend;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Cookie $http_cookie;
}
```

**CRITICAL:** The `proxy_pass http://backend;` (without trailing slash) **PRESERVES** the `/api` prefix!

**Authentication Flow:**
```
Request:  /api/strategies
    ↓
NGINX:    Checks authentication (3 methods):
          1. X-API-Key header (for workers)
          2. session_token cookie (backend sets this)
          3. user cookie (frontend sets this)
    ↓
NGINX:    If ANY valid → Forward WITH /api → http://saga-apis:8000/api/strategies
    ↓
Backend:  Receives /api/strategies
    ↓
Backend:  @app.get("/api/strategies") matches ✅
```

**Login Flow (Special Case):**
```
Request:  /api/login
    ↓
NGINX:    NO AUTH CHECK (location = /api/login bypasses auth)
    ↓
NGINX:    Forwards WITH /api → http://saga-apis:8000/api/login
    ↓
Backend:  Validates credentials
    ↓
Backend:  Sets session_token cookie (HttpOnly, 24h)
    ↓
Frontend: Also sets user cookie (stores username, topics)
    ↓
Browser:  Now has TWO cookies for subsequent requests
```

**Implementation Note:**
- All backend routes in `main.py` must have `/api/` prefix
- Router in `articles.py` must have `prefix="/api/articles"`
- `/api/login` must be defined BEFORE `/api/` in NGINX (exact match takes precedence)
- Backend sets `session_token` cookie with `path="/"` for all routes
- Frontend sets `user` cookie for client-side state management
- This ensures consistency across all deployment scenarios

---

### **3. Neo4j Browser (No API Key Required)**

**Pattern:** `/neo4j/*`

**Example:**
```
http://localhost/neo4j               → Neo4j Browser UI
```

**NGINX Config:**
```nginx
location /neo4j/ {
    proxy_pass http://neo4j_browser/;
}
```

---

## **API Key Authentication**

### **Valid API Keys**

Three API keys are configured in NGINX:

1. `785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12` (Key 1 - You)
2. `a017a1af6fe167bdfcc554debb1c9a39e2ec75b93adde5a06d11e9a1361344f5` (Key 2 - Coworker)
3. `646b3c9454024ac1f4a2abad35cf1b8d02678b7c98d84059bde4109956adeeec` (Key 3 - Extra)

### **How It Works**

1. Client includes API key in request header: `X-API-Key: <key>`
2. NGINX checks if key matches one of the three valid keys
3. If valid → Request forwarded to backend
4. If invalid → 401 Unauthorized response

### **NGINX Configuration**

```nginx
map $http_x_api_key $api_key_valid {
    default 0;
    "785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12" 1;
    "a017a1af6fe167bdfcc554debb1c9a39e2ec75b93adde5a06d11e9a1361344f5" 1;
    "646b3c9454024ac1f4a2abad35cf1b8d02678b7c98d84059bde4109956adeeec" 1;
}
```

---

## **Cookie-Based Authentication**

### **Overview**

The system uses TWO cookies, but NGINX accepts EITHER for authentication:

1. **`session_token`** - Set by backend, secure hash-based session token
2. **`user`** - Set by frontend, stores user data (username, topics)

**Why this works:**
- Backend sets `session_token` cookie (secure, hash-based)
- Frontend ALSO sets `user` cookie (stores user data for client-side use)
- NGINX accepts EITHER cookie for authentication
- Redundant authentication provides flexibility and robustness

### **Cookie Details**

| Cookie | Set By | Purpose | Attributes | Expiry |
|--------|--------|---------|------------|--------|
| `session_token` | Backend (`/api/login`) | NGINX auth (secure hash) | `HttpOnly`, `Path=/`, `SameSite=lax` | 24 hours |
| `user` | Frontend (`+page.server.ts`) | NGINX auth + Store user data | `HttpOnly`, `Path=/` | 24 hours |

**Note:** Both cookies are set during login. NGINX accepts EITHER for authentication, providing redundancy.

### **Login Flow**

```
1. User submits login form
   ↓
2. Frontend calls POST /api/login (via SvelteKit server action)
   ↓
3. NGINX allows /api/login (no auth required)
   ↓
4. Backend validates credentials
   ↓
5. Backend sets session_token cookie:
   Set-Cookie: session_token=<hash>; HttpOnly; Path=/; Max-Age=86400; SameSite=lax
   ↓
6. Backend returns JSON: {"username":"Victor","accessible_topics":[...]}
   ↓
7. Frontend receives response
   ↓
8. Frontend sets user cookie:
   Set-Cookie: user={"username":"Victor",...}; HttpOnly; Path=/; Max-Age=86400
   ↓
9. Browser now has TWO cookies
   ↓
10. Subsequent requests include both cookies
    ↓
11. NGINX checks: API key OR session_token OR user → Auth OK ✅
```

### **Backend Login Code**

**File:** `saga-be/main.py`

```python
@app.post("/api/login")
def login(request: LoginRequest, response: Response):
    # Validate credentials
    user = user_manager.authenticate(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate session token
    import hashlib, time
    session_token = hashlib.sha256(f"{user['username']}{time.time()}".encode()).hexdigest()
    
    # Set session_token cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        path="/",
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )
    
    # Return user data
    return {
        "username": user["username"], 
        "accessible_topics": user["accessible_topics"]
    }
```

**Note:** Backend DOES set `session_token` cookie, but NGINX also accepts `user` cookie from frontend.

### **Frontend Cookie Code**

**File:** `saga-fe/src/routes/login/+page.server.ts`

```typescript
export const actions: Actions = {
    default: async ({ request, cookies }) => {
        const authResult = await authenticate(username, password);
        
        // Frontend sets user cookie for auth + storing user data
        cookies.set('user', JSON.stringify(authResult), {
            path: '/',
            httpOnly: true,
            secure: false,
            maxAge: 60 * 60 * 24 // 24 hours
        });
        
        throw redirect(302, '/dashboard');
    }
};
```

**Note:** Frontend sets the ONLY cookie used for authentication.

### **Dashboard Cookie Check**

**File:** `saga-fe/src/routes/dashboard/+page.server.ts`

```typescript
export const load: PageServerLoad = async ({ cookies }) => {
    const userCookie = cookies.get('user');
    
    if (!userCookie) {
        throw redirect(302, '/login');
    }
    
    try {
        const user = JSON.parse(userCookie);
        return { user };
    } catch {
        throw redirect(302, '/login');
    }
};
```

**Note:** Dashboard checks for `user` cookie (frontend state), while NGINX checks for EITHER `session_token` OR `user` (authentication).

---

## **Backend Routes**

**CRITICAL:** All API routes include the `/api/` prefix in the backend code. This ensures consistency across all deployment scenarios (local dev, internal workers, external workers).

### **Health & Status (No `/api/` prefix)**
- `GET /` - Root endpoint (status check)
- `GET /health` - Health check with Graph API status

### **Authentication & Users (With `/api/` prefix)**
- `POST /api/login` - User authentication (returns session cookie)
- `GET /api/users` - List all users (for workers to iterate)

### **Topics & Interests (With `/api/` prefix)**
- `GET /api/topics/all` - Get all topics from Neo4j (debugging)
- `GET /api/interests?username=X` - Get user's accessible topics with names

### **Articles (With `/api/` prefix - via router)**
Router: `APIRouter(prefix="/api/articles")`
- `POST /api/articles/ingest` - Ingest article with automatic deduplication
- `GET /api/articles/{id}` - Get article by ID
- `POST /api/articles/search` - Search articles by keywords
- `POST /api/articles/bulk` - Bulk import articles (restore operations)

### **Strategies (With `/api/` prefix)**
- `GET /api/strategies?username=X` - List user's strategies
- `GET /api/strategies/{id}?username=X` - Get strategy details
- `POST /api/strategies` - Create new strategy
- `PUT /api/strategies/{id}` - Update strategy
- `DELETE /api/strategies/{id}?username=X` - Archive strategy

### **Reports & Chat (With `/api/` prefix)**
- `GET /api/reports/{topic_id}` - Get report for topic (proxies to Graph API)
- `POST /api/chat` - Chat with AI assistant (uses LangChain + OpenAI)

---

## **Implementation Checklist**

To implement this architecture correctly:

### **Backend (`saga-be/main.py`)**
```python
# ✅ Routes with /api/ prefix
@app.post("/api/login")
@app.get("/api/users")
@app.get("/api/topics/all")
@app.get("/api/interests")
@app.get("/api/strategies")
@app.post("/api/strategies")
@app.put("/api/strategies/{strategy_id}")
@app.delete("/api/strategies/{strategy_id}")
@app.get("/api/reports/{topic_id}")
@app.post("/api/chat")

# ✅ Routes WITHOUT /api/ prefix
@app.get("/")
@app.get("/health")

# ✅ Include router with /api prefix
from src.api.routes import articles
app.include_router(articles.router)
```

### **Articles Router (`saga-be/src/api/routes/articles.py`)**
```python
# ✅ Router prefix includes /api
router = APIRouter(prefix="/api/articles", tags=["articles"])

# ✅ Routes are relative to prefix
@router.post("/ingest")        # Full path: /api/articles/ingest
@router.get("/{article_id}")    # Full path: /api/articles/{article_id}
@router.post("/search")         # Full path: /api/articles/search
@router.post("/bulk")           # Full path: /api/articles/bulk
```

### **NGINX (`victor_deployment/nginx/nginx.conf`)**
```nginx
# ✅ Preserve /api prefix (no trailing slash!)
location /api/ {
    if ($api_key_valid = 0) {
        return 401 '{"error": "Invalid or missing API key"}';
    }
    proxy_pass http://backend;  # ← No trailing slash!
}
```

### **Workers (`graph-functions/src/api/backend_client.py`)**
```python
# ✅ All calls include /api prefix
BACKEND_URL = os.getenv("BACKEND_API_URL")

def ingest_article(article_data):
    response = requests.post(
        f"{BACKEND_URL}/api/articles/ingest",  # ← /api prefix
        json=article_data,
        headers={"X-API-Key": API_KEY} if API_KEY else {}
    )
```

---

## **Access Patterns**

### **1. User Login (Browser → Frontend → Backend)**

```
User opens browser: http://localhost/login
    ↓
NGINX: "No /api prefix → Send to frontend"
    ↓
Frontend: Serves login page
    ↓
User submits form
    ↓
Frontend: fetch('/api/login', { headers: { 'X-API-Key': 'xxx' } })
    ↓
NGINX: "Has /api prefix → Check API key → Forward to backend"
    ↓
Backend: Receives /api/login
    ↓
Backend: @app.post("/login") authenticates user ✅
    ↓
Response: {"username": "Victor", "accessible_topics": [...]}
    ↓
Frontend: Redirects to /dashboard
```

---

### **2. Internal Worker (Docker Container → Backend)**

```
Worker (saga-worker-main):
    ↓
requests.post(
    "http://saga-apis:8000/api/articles/ingest",  # ← /api prefix!
    headers={"X-API-Key": "785fc6c1..."},  # Optional (not checked)
    json=article
)
    ↓
Backend: Receives /api/articles/ingest directly (bypasses NGINX)
    ↓
Backend: @router.post("/ingest") processes article ✅
```

**Key Points:**
- Internal workers bypass NGINX and call backend directly via Docker network DNS (`saga-apis:8000`)
- API key is included in headers for consistency but NOT checked by backend (trusted environment)
- Uses same `/api/*` paths as external workers for code consistency

### **3. External Worker (Mac → Server via NGINX)**

```
Worker on Mac:
    ↓
requests.post(
    "http://130.241.129.211/api/articles/ingest",  # ← Same path!
    headers={"X-API-Key": "785fc6c1..."},  # Required (NGINX checks)
    json=article
)
    ↓
NGINX (Port 80): Checks X-API-Key header
    ↓
NGINX: Valid key → Forward WITH /api to backend
    ↓
Backend: Receives /api/articles/ingest
    ↓
Backend: @router.post("/ingest") processes article ✅
```

**Key Points:**
- External workers go through NGINX on port 80
- NGINX validates API key before forwarding
- Uses same `/api/*` paths as internal workers
- **Same worker code works in both environments** - only `BACKEND_API_URL` differs!

---

### **4. External Neo4j Connection (Your Mac → Neo4j)**

```
Your Mac:
    ↓
from neo4j import GraphDatabase
driver = GraphDatabase.driver(
    "bolt://SERVER-IP:7687",
    auth=("neo4j", "SagaGraph2025!Demo")
)
    ↓
Docker exposes port 7687
    ↓
Neo4j: Authenticates with username/password ✅
    ↓
Connected!
```

---

## **Authentication Methods**

SAGA Graph uses two authentication methods depending on the client type:

| Client Type | Auth Method | Route Pattern | Checked By | Expiry | Notes |
|-------------|-------------|---------------|------------|--------|-------|
| **Frontend (Browser)** | Session cookie | `/api/*` | Backend (session dict) | 24 hours | Cookie auto-deleted by browser |
| **Internal Worker** | API key (optional) | Direct: `saga-apis:8000/api/*` | None (trusted) | Never | Included for consistency |
| **External Worker** | API key (required) | Via NGINX: `server/api/*` | NGINX | Never | Must match one of 3 valid keys |
| **Health Checks** | None | `/health` | None | N/A | Public endpoint |

### **Frontend Session Flow**

**Login:**
```python
@app.post("/api/login")
def login(request: LoginRequest, response: Response):
    # 1. Authenticate user
    user = user_manager.authenticate(username, password)
    
    # 2. Generate session token
    session_token = hashlib.sha256(f"{user['username']}{time.time()}".encode()).hexdigest()
    
    # 3. Store in backend memory with timestamp
    app.state.sessions[session_token] = {
        "username": user['username'],
        "created_at": time.time()
    }
    
    # 4. Set HTTP-only cookie (browser auto-expires after 24h)
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        max_age=86400,  # 24 hours
        samesite="lax"
    )
```

**Protected Routes:**
```python
from fastapi import Cookie, Depends

def verify_session(session_token: str = Cookie(None)):
    """Verify session is valid and not expired"""
    if not session_token:
        raise HTTPException(401, "Not authenticated")
    
    session = app.state.sessions.get(session_token)
    if not session:
        raise HTTPException(401, "Session expired")
    
    # Check if older than 24h
    if time.time() - session["created_at"] > 86400:
        del app.state.sessions[session_token]
        raise HTTPException(401, "Session expired")
    
    return session["username"]

# Use in routes:
@app.get("/api/strategies")
def list_strategies(username: str = Depends(verify_session)):
    # username comes from verified session
    strategies = strategy_manager.list_strategies(username)
    return {"strategies": strategies}
```

**Expiration Handling:**
1. Browser sends request with cookie
2. Backend checks: "Token exists? Token < 24h old?"
3. If expired → 401 Unauthorized
4. Frontend receives 401 → Redirects to `/login`
5. User logs in again → New token issued

### **Worker API Key Flow**

**Internal Workers (Trusted):**
- Include API key in headers for consistency
- Backend does NOT check it (trusted Docker network)
- Direct connection bypasses NGINX

**External Workers (Untrusted):**
- MUST include valid API key in headers
- NGINX validates before forwarding
- Invalid/missing key → 401 Unauthorized

---

## **Environment Variables by Deployment**

**IMPORTANT:** Use setup scripts to configure these automatically! Do NOT edit `.env` files manually.

### **Local Development (Mac)**

```bash
# graph-functions/.env
# Set by: ./setup-local-dev.sh (or similar)
BACKEND_API_URL="http://localhost:8000"
BACKEND_API_KEY="785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12"
NEO4J_URI="neo4j://127.0.0.1:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="SagaGraph2025!Demo"
```

**Usage:** Local testing with Docker containers running on same machine.

### **Server Internal Worker**

```bash
# deployment/.env
# Set by: ./setup-server-deployment.sh (or similar)
BACKEND_API_URL="http://saga-apis:8000"  # Docker network DNS
BACKEND_API_KEY="785fc6c1..."  # Optional (not checked by backend)
NEO4J_URI="neo4j://saga-neo4j:7687"  # Docker network DNS
NEO4J_USER="neo4j"
NEO4J_PASSWORD="SagaGraph2025!Demo"
```

**Usage:** Workers running inside Docker on server (saga-worker-main, saga-worker-sources).

### **Server External Worker (Mac → Server)**

```bash
# graph-functions/.env
# Set by: ./setup-external-worker.sh SERVER_IP (or similar)
BACKEND_API_URL="http://130.241.129.211"  # Server public IP
BACKEND_API_KEY="785fc6c1..."  # Required (NGINX checks)
NEO4J_URI="neo4j://130.241.129.211:7687"  # Server public IP
NEO4J_USER="neo4j"
NEO4J_PASSWORD="SagaGraph2025!Demo"
```

**Usage:** Running workers on your Mac that connect to remote server.

**Key Insight:** The ONLY difference is the `BACKEND_API_URL` value:
- Local dev: `http://localhost:8000`
- Internal worker: `http://saga-apis:8000` (Docker DNS)
- External worker: `http://SERVER-IP` (public IP)

All worker code remains identical - just load from environment!

---

## **Frontend Configuration**

### **Environment Variables**

Set in `docker-compose.yml`:

```yaml
environment:
  - VITE_API_BASE_URL=/api
  - VITE_API_KEY=785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12
```

### **API Calls**

All frontend API calls use:

```typescript
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const API_KEY = import.meta.env.VITE_API_KEY || '';

fetch(`${API_BASE}/login`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
  body: JSON.stringify({ username, password })
});
```

**Why `/api` prefix?**
- Tells NGINX "this is a backend API call, not a frontend asset"
- NGINX preserves `/api` and forwards to backend
- Backend routes include `/api/` in their definitions

---

## **Worker Configuration**

### **Internal Workers (Docker Containers)**

```python
# saga-graph/src/config.py or similar
import os

BACKEND_URL = "http://saga-apis:8000"  # Direct Docker network access
API_KEY = os.getenv("SAGA_API_KEY", "785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12")

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Store article
requests.post(f"{BACKEND_URL}/articles", headers=headers, json=article)
```

### **External Workers (Your Mac)**

```python
# On your Mac
BACKEND_URL = "http://SERVER-IP/api"  # Through NGINX
API_KEY = "785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Store article
requests.post(f"{BACKEND_URL}/articles", headers=headers, json=article)
```

**Note:** External workers use `/api` prefix and go through NGINX!

---

## **Security Model**

### **What's Protected**

✅ **All backend API endpoints** - Require API key via NGINX  
✅ **Neo4j database** - Requires username/password authentication  

### **What's Public**

✅ **Frontend assets** - No authentication (HTML, CSS, JS)  
✅ **Neo4j Browser** - Accessible at `/neo4j` (has its own auth)  

### **Defense in Depth**

1. **NGINX Layer:** API key check for all `/api/*` requests
2. **Backend Layer:** User authentication for user-specific operations
3. **Neo4j Layer:** Username/password authentication for database access

---

## **Testing**

### **Test 1: User Login**

```bash
curl -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12" \
  -d '{"username":"Victor","password":"v123"}'

# Expected: {"username":"Victor","accessible_topics":[...]}
```

### **Test 2: Store Article (Internal Worker)**

```bash
# From inside saga-worker-main container
curl -X POST http://saga-apis:8000/articles \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12" \
  -d '{"title":"Test","content":"Test article"}'

# Expected: {"argos_id":"...","status":"stored"}
```

### **Test 3: Store Article (External Worker)**

```bash
# From your Mac
curl -X POST http://SERVER-IP/api/articles \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 785fc6c1647ff650b6b611509cc0a8f47009e6b743340503519d433f111fcf12" \
  -d '{"title":"Test","content":"Test article"}'

# Expected: {"argos_id":"...","status":"stored"}
```

### **Test 4: No API Key (Should Fail)**

```bash
curl -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Victor","password":"v123"}'

# Expected: 401 {"error": "Invalid or missing API key"}
```

### **Test 5: Neo4j Connection**

```bash
# From your Mac
docker run --rm neo4j/neo4j-admin:5 \
  cypher-shell -a bolt://SERVER-IP:7687 \
  -u neo4j -p SagaGraph2025!Demo \
  "RETURN 'Connected!' AS message"

# Expected: Connected!
```

---

## **Docker Network DNS**

### **How Service Names Work**

Docker Compose creates a network where **service names become hostnames**:

```yaml
# docker-compose.yml
services:
  nginx:
    container_name: saga-nginx
    networks:
      - saga-network
  
  saga-apis:
    container_name: saga-apis
    networks:
      - saga-network
  
  frontend:
    container_name: saga-frontend
    networks:
      - saga-network
```

**Inside the Docker network:**
- `http://nginx` → NGINX container
- `http://saga-apis:8000` → Backend API container
- `http://frontend:5173` → Frontend container
- `http://neo4j:7687` → Neo4j container

**No IP addresses needed!** Docker handles DNS resolution automatically.

---

### **Server-Side vs Client-Side Fetch**

**IMPORTANT:** SvelteKit runs code in two places:

1. **Client-side (Browser):**
   - Can use relative URLs: `/api/login`
   - Goes through NGINX on port 80
   - Uses `import.meta.env.VITE_*` for environment variables

2. **Server-side (SvelteKit server actions):**
   - **MUST use absolute URLs**: `http://nginx/api/login`
   - Runs inside frontend container
   - Uses `process.env.*` for environment variables
   - Cannot use relative URLs (Node.js fetch requirement)

**Example from `auth.ts`:**

```typescript
// Detect if running server-side or client-side
const isServer = typeof window === 'undefined';

// Use absolute URL for server, relative for client
const API_BASE = isServer 
  ? 'http://nginx/api'  // Server: through NGINX (Docker DNS)
  : '/api';              // Client: relative path (browser)

// Use correct env var access method
const API_KEY = isServer
  ? process.env.VITE_API_KEY || ''  // Server: process.env
  : import.meta.env.VITE_API_KEY || '';  // Client: import.meta.env
```

**Why this works:**
- ✅ Server-side: `http://nginx/api/login` → NGINX → Backend
- ✅ Client-side: `/api/login` → Browser → NGINX → Backend
- ✅ Both paths go through NGINX for API key validation
- ✅ Works locally AND on remote server

---

## **Troubleshooting**

### **Problem: 401 Unauthorized on Login**

**Symptoms:**
- Can't login to frontend
- curl login fails with 401
- Error: `{"error": "Authentication required"}`

**Cause:** NGINX is checking auth on `/api/login` endpoint

**Solution:**
1. Verify `/api/login` exception exists in NGINX config BEFORE `/api/` block:
```nginx
# This MUST come first (exact match takes precedence)
location = /api/login {
    # No auth check
    proxy_pass http://backend;
}

# This comes second
location /api/ {
    # Auth checks here
}
```

2. Restart NGINX: `docker compose restart nginx`

---

### **Problem: 401 Unauthorized After Login**

**Symptoms:**
- Login works, but subsequent requests fail with 401
- Can see strategies list, but can't click on individual strategy

**Cause:** Cookie not being sent or NGINX not recognizing it

**Solution:**
1. Check browser cookies (DevTools → Application → Cookies):
   - Should have `user` cookie with JSON data
   - Should have `session_token` cookie (if backend sets it)

2. Verify NGINX checks for BOTH cookies:
```nginx
# Check session_token cookie (backend auth)
if ($cookie_session_token != "") {
    set $auth_ok 1;
}

# Check user cookie (frontend auth)
if ($cookie_user != "") {
    set $auth_ok 1;
}
```

3. Check cookie `path` attribute:
   - Backend: `response.set_cookie(..., path="/")`
   - Frontend: `cookies.set('user', ..., { path: '/' })`

4. Clear cookies and login again

---

### **Problem: Login Works but Dashboard Redirects Back**

**Symptoms:**
- Login succeeds (200 OK)
- Immediately redirects back to login page
- Infinite redirect loop

**Cause:** Frontend expects `user` cookie but it's not set

**Solution:**
1. Check `saga-fe/src/routes/login/+page.server.ts` sets cookie:
```typescript
cookies.set('user', JSON.stringify(authResult), {
    path: '/',
    httpOnly: true,
    maxAge: 60 * 60 * 24
});
```

2. Check `saga-fe/src/routes/dashboard/+page.server.ts` reads cookie:
```typescript
const userCookie = cookies.get('user');
if (!userCookie) {
    throw redirect(302, '/login');
}
```

3. Rebuild frontend: `docker compose build frontend --no-cache`

---

### **Problem: Cookie Set but Not Sent**

**Symptoms:**
- Backend logs show `Cookies: {}`
- Browser has cookie in DevTools
- Requests still fail with 401

**Cause:** Cookie `path` or `domain` mismatch

**Solution:**
1. Verify cookie attributes:
   - `path="/"` (not `/api` or `/login`)
   - `domain` should be empty or match `localhost`
   - `SameSite=lax` (allows cross-site navigation)

2. Check NGINX forwards cookies:
```nginx
proxy_set_header Cookie $http_cookie;
```

3. Test with curl:
```bash
# Login and save cookie
curl -v -X POST http://localhost/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"Victor","password":"v123"}' \
  -c cookies.txt

# Use cookie for subsequent request
curl -v http://localhost/api/strategies?username=Victor \
  -b cookies.txt
```

---

### **Problem: 404 Not Found**

**Cause:** Route mismatch

**Solution:**
- Frontend calls should use `/api/` prefix
- Backend routes should NOT have `/api/` prefix
- Check NGINX `proxy_pass` has trailing slash: `http://backend/`

---

### **Problem: CORS Errors**

**Cause:** Should not happen with this setup!

**Solution:**
- All requests go through same origin (port 80)
- If you see CORS errors, check if frontend is calling backend directly instead of through NGINX

---

### **Problem: Can't Connect to Neo4j from Mac**

**Cause:** Port 7687 not exposed or firewall blocking

**Solution:**
- Check `docker-compose.yml` has `- "7687:7687"` under neo4j ports
- Check firewall allows incoming connections on port 7687
- Test with: `nc -zv SERVER-IP 7687`

---

### **Problem: Login Returns 400 Bad Request**

**Cause:** Server-side fetch using relative URL

**Symptoms:**
- NGINX logs show: `POST /login HTTP/1.1" 400`
- No requests reaching backend
- Browser console shows no errors

**Solution:**
The issue is that SvelteKit server actions run **inside the frontend container** and need **absolute URLs** for fetch:

```typescript
// ❌ WRONG - Relative URL fails server-side
const API_BASE = '/api';

// ✅ CORRECT - Detect server vs client
const isServer = typeof window === 'undefined';
const API_BASE = isServer ? 'http://nginx/api' : '/api';
```

**Why this happens:**
- Browser can use relative URLs (e.g., `/api/login`)
- Node.js fetch **requires absolute URLs** (e.g., `http://nginx/api/login`)
- SvelteKit server actions run in Node.js, not the browser
- Must use Docker network DNS (`http://nginx`) to reach NGINX from frontend container

**Verify the fix:**
```bash
# Check if auth.ts has server-side detection
docker exec saga-frontend cat /app/src/lib/auth.ts | grep "isServer"

# Should see: const isServer = typeof window === 'undefined';
```

---

## **Summary**

### **The `/api` Pattern**

- **Frontend adds `/api`** → Tells NGINX "this is a backend call"
- **NGINX checks API key** → Security at entry point
- **NGINX preserves `/api`** → Backend receives full path
- **Backend routes include `/api/`** → Consistent paths everywhere

### **Key Benefits**

✅ **Single entry point** - All traffic through port 80  
✅ **Clean separation** - Frontend vs Backend routing  
✅ **Security at edge** - API key check at NGINX  
✅ **Simple backend** - No routing prefixes  
✅ **Works everywhere** - Local Mac and remote server  
✅ **No CORS issues** - Same origin for all requests  

### **Access Summary**

| Client | Target | URL Pattern | API Key? | Auth Check |
|--------|--------|-------------|----------|------------|
| Browser | Frontend | `http://localhost/` | No | None |
| Browser | Backend | `http://localhost/api/*` | Session cookie | Backend |
| Internal Worker | Backend | `http://saga-apis:8000/api/*` | Optional | None (trusted) |
| External Worker | Backend | `http://SERVER-IP/api/*` | Required | NGINX |
| Any | Neo4j | `bolt://SERVER-IP:7687` | Username/Password | Neo4j |

---

## **Summary: Key Architectural Decisions**

### **1. `/api` Prefix is Preserved**
- ✅ NGINX does NOT strip `/api` - it forwards the full path
- ✅ Backend routes include `/api/` in their definitions
- ✅ All clients (frontend, internal workers, external workers) use `/api/*` paths
- ✅ Consistent URLs across all environments

### **2. Same Worker Code Everywhere**
- ✅ Workers use `BACKEND_API_URL` environment variable
- ✅ Local dev: `http://localhost:8000`
- ✅ Internal: `http://saga-apis:8000` (Docker DNS)
- ✅ External: `http://SERVER-IP` (public IP)
- ✅ All use same `/api/*` paths - only base URL changes

### **3. Two Authentication Methods**
- ✅ **Frontend:** Session cookies (24h expiry, managed by backend)
- ✅ **Workers:** Permanent API keys (checked by NGINX for external, trusted for internal)
- ✅ Clear separation of concerns

### **4. Security Layers**
- ✅ NGINX validates API keys for external requests
- ✅ Backend validates session cookies for frontend
- ✅ Internal workers trusted (Docker network isolation)
- ✅ Health endpoints public (no auth needed)

### **5. Setup Scripts Manage Configuration**
- ✅ Never edit `.env` files manually
- ✅ Use `./setup-local-dev.sh` for local development
- ✅ Use `./setup-server-deployment.sh` for server workers
- ✅ Use `./setup-external-worker.sh SERVER_IP` for Mac → Server
- ✅ Scripts ensure correct URLs and keys

**Everything is designed for simplicity, consistency, and security!** 🚀
