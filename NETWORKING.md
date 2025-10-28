# 🌐 SAGA GRAPH NETWORKING ARCHITECTURE

## **Overview**

SAGA Graph uses NGINX as a single entry point (port 80) to route all external traffic. The `/api` prefix is used as a routing signal to distinguish between frontend assets and backend API calls.

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

| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| 80 | NGINX | External | Single entry point for all HTTP traffic |
| 7687 | Neo4j Bolt | External | Database access for external workers |
| 7474 | Neo4j Browser | External (via /neo4j) | Database browser UI |
| 5173 | Frontend | Internal only | Svelte dev server |
| 8000 | Backend API | Internal only | FastAPI backend |
| 8001 | Graph API | Internal only | Neo4j graph operations |

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

### **2. Backend API Calls (API Key Required)**

**Pattern:** `/api/*`

**Examples:**
```
http://localhost/api/login           → Backend /login endpoint
http://localhost/api/strategies      → Backend /strategies endpoint
http://localhost/api/articles        → Backend /articles endpoint
http://localhost/api/users           → Backend /users endpoint
```

**NGINX Config:**
```nginx
location /api/ {
    # Check API key
    if ($api_key_valid = 0) {
        return 401 '{"error": "Invalid or missing API key"}';
    }
    
    # Strip /api prefix and send to backend
    proxy_pass http://backend/;
}
```

**Key Point:** The trailing slash in `proxy_pass http://backend/;` strips the `/api` prefix!

**Flow:**
```
Request:  /api/login
    ↓
NGINX:    Checks X-API-Key header
    ↓
NGINX:    Strips /api prefix
    ↓
Backend:  Receives /login
    ↓
Backend:  @app.post("/login") matches ✅
```

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

## **Backend Routes**

All backend routes are **clean** - no `/api` prefix in the backend code!

### **Authentication & Users**
- `POST /login` - User authentication
- `GET /users` - List all users (for workers)

### **Topics & Interests**
- `GET /topics/all` - Get all topics (debugging)
- `GET /interests?username=X` - Get user's accessible topics

### **Articles**
- `POST /articles` - Store article (workers)
- `GET /articles/{id}` - Get article by ID
- `GET /articles?topic_id=X` - Get articles for topic

### **Strategies**
- `GET /strategies?username=X` - List user's strategies
- `GET /strategies/{id}?username=X` - Get strategy details
- `POST /strategies` - Create new strategy
- `PUT /strategies/{id}` - Update strategy
- `DELETE /strategies/{id}?username=X` - Archive strategy

### **Reports & Chat**
- `GET /reports/{topic_id}` - Get report for topic
- `POST /chat` - Chat with AI assistant

### **Health**
- `GET /` - Root endpoint
- `GET /health` - Health check

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
NGINX: "Has /api prefix → Check API key → Strip /api → Send to backend"
    ↓
Backend: Receives /login
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
    "http://saga-apis:8000/articles",
    headers={"X-API-Key": "785fc6c1..."},
    json=article
)
    ↓
Backend: Receives /articles directly (no NGINX)
    ↓
Backend: @app.post("/articles") stores article ✅
```

**Note:** Internal workers bypass NGINX and call backend directly using Docker network DNS (`saga-apis:8000`). API key is included but not checked by backend - it's for consistency.

---

### **3. External Worker (Your Mac → NGINX → Backend)**

```
Your Mac:
    ↓
requests.post(
    "http://SERVER-IP/api/articles",
    headers={"X-API-Key": "785fc6c1..."},
    json=article
)
    ↓
NGINX: "Has /api prefix → Check API key ✅ → Strip /api → Send to backend"
    ↓
Backend: Receives /articles
    ↓
Backend: @app.post("/articles") stores article ✅
```

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
- NGINX strips `/api` before sending to backend
- Backend receives clean route (e.g., `/login`)

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

### **Problem: 401 Unauthorized**

**Cause:** Missing or invalid API key

**Solution:**
- Check `X-API-Key` header is included
- Verify key matches one of the three valid keys in NGINX config
- Check NGINX logs: `docker-compose logs nginx`

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
- **NGINX strips `/api`** → Backend receives clean routes
- **Backend has no `/api`** → Simple, clean route definitions

### **Key Benefits**

✅ **Single entry point** - All traffic through port 80  
✅ **Clean separation** - Frontend vs Backend routing  
✅ **Security at edge** - API key check at NGINX  
✅ **Simple backend** - No routing prefixes  
✅ **Works everywhere** - Local Mac and remote server  
✅ **No CORS issues** - Same origin for all requests  

### **Access Summary**

| Client | Target | URL Pattern | API Key? |
|--------|--------|-------------|----------|
| Browser | Frontend | `http://localhost/` | No |
| Browser | Backend | `http://localhost/api/*` | Yes |
| Internal Worker | Backend | `http://saga-apis:8000/*` | Yes |
| External Worker | Backend | `http://SERVER-IP/api/*` | Yes |
| Any | Neo4j | `bolt://SERVER-IP:7687` | Username/Password |

**Everything is designed for simplicity and security!** 🚀
