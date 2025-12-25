# Security Audit

**Version**: 2025-12-25
**Estimated Time**: 5-10 minutes
**Output**: Security vulnerabilities and risks

---

## Task

Scan codebase for common security vulnerabilities and security-relevant issues.

This is NOT a penetration test - it's a code review for obvious security problems.

---

## Scope

**All Code:**
- `graph-functions/`
- `saga-be/`
- `saga-fe/`
- `victor_deployment/`

---

## Checks to Perform

### 1. Hardcoded Secrets
**What**: Credentials, API keys, passwords in code

**Check For:**
- API keys in source files
- Database passwords in code
- JWT secrets not from environment
- Hardcoded encryption keys

**Exclude:**
- `.env` files (intentionally have secrets)
- Example/template files clearly marked as such

**Good:**
```python
API_KEY = os.getenv("BACKEND_API_KEY")
if not API_KEY:
    raise ValueError("BACKEND_API_KEY not set")
```

**Bad:**
```python
API_KEY = "sk-abc123..."  # ❌ Hardcoded secret
```

**Output**: Files with hardcoded secrets

---

### 2. SQL/Cypher Injection
**What**: User input concatenated into queries

**Check For:**
- String formatting in Cypher queries
- User input not parameterized
- Dynamic query construction

**Good:**
```python
query = "MATCH (t:Topic {id: $topic_id}) RETURN t"
result = client.run(query, topic_id=user_input)
```

**Bad:**
```python
query = f"MATCH (t:Topic {{id: '{user_input}'}}) RETURN t"  # ❌ Injection risk
result = client.run(query)
```

**Output**: Potential injection vulnerabilities

---

### 3. Authentication/Authorization Bypass
**What**: Missing auth checks, weak auth, privilege escalation

**Check For:**
- API endpoints without auth checks
- User isolation not enforced (can access other users' data)
- Admin endpoints without admin check
- Session handling issues

**Example Issues:**
```python
@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str):
    return strategy_manager.get(strategy_id)  # ❌ No user check
```

**Output**: Auth/authz issues

---

### 4. Unsafe File Operations
**What**: Path traversal, arbitrary file access

**Check For:**
- User-provided paths not validated
- File operations without path sanitization
- Directory traversal vulnerabilities

**Good:**
```python
from pathlib import Path
safe_path = Path("/allowed/dir") / user_filename
if not safe_path.resolve().is_relative_to("/allowed/dir"):
    raise ValueError("Invalid path")
```

**Bad:**
```python
file_path = f"/data/{user_filename}"  # ❌ Path traversal risk
with open(file_path) as f:
    ...
```

**Output**: Unsafe file operations

---

### 5. Command Injection
**What**: User input in shell commands

**Check For:**
- `os.system()`, `subprocess` with user input
- Shell=True with user data
- Unescaped command arguments

**Good:**
```python
subprocess.run(["ls", user_dir], shell=False, check=True)
```

**Bad:**
```python
os.system(f"ls {user_dir}")  # ❌ Command injection
```

**Output**: Command injection risks

---

### 6. Insecure Dependencies
**What**: Known vulnerabilities in dependencies

**Check:**
```bash
cd graph-functions && pip-audit
cd saga-be && pip-audit
```

**Output**: Vulnerable packages

---

### 7. Sensitive Data Exposure
**What**: Logging or returning sensitive data

**Check For:**
- Passwords/tokens in logs
- Full user objects returned in API (including hashed passwords)
- Error messages exposing system details
- Debug mode enabled in production

**Output**: Data exposure issues

---

### 8. CORS/CSRF Issues
**What**: Insecure cross-origin or CSRF protection

**Check For:**
- CORS allowing all origins (`Access-Control-Allow-Origin: *`)
- State-changing endpoints without CSRF protection
- Cookie settings missing SameSite

**Output**: CORS/CSRF issues

---

## Output Format

```markdown
# Security Audit Report
**Date**: YYYY-MM-DD
**Scope**: All repositories
**Severity Levels**: 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## Summary
- 🔴 **Critical**: [N] - Immediate action required
- 🟠 **High**: [N] - Fix this week
- 🟡 **Medium**: [N] - Fix this month
- 🟢 **Low**: [N] - Fix when convenient
- ✅ **Passed**: [N] checks

**Risk Level**: [Critical | High | Medium | Low]

---

## 🔴 Critical Issues (Fix Immediately)

### 1. Hardcoded API Key
**File**: `graph-functions/src/api/client.py:15`
**Severity**: 🔴 Critical

```python
API_KEY = "sk-abc123def456..."  # ❌ Hardcoded secret in source
```

**Risk**: Key exposed in git history, anyone with code access has API access

**Fix**:
```python
API_KEY = os.getenv("BACKEND_API_KEY")
if not API_KEY:
    raise ValueError("BACKEND_API_KEY must be set")
```

**Steps**:
1. Remove hardcoded key from source
2. Add key to `.env` file
3. Rotate the exposed key immediately
4. Update `.gitignore` to prevent future leaks

---

### 2. SQL Injection in User Strategy Query
**File**: `saga-be/src/routes/strategies.py:67`
**Severity**: 🔴 Critical

```python
query = f"MATCH (s:Strategy {{owner: '{username}'}}) RETURN s"
```

**Risk**: Attacker can inject Cypher to read/modify any data

**Attack Example**: `username = "'; MATCH (u:User) DETACH DELETE u; //"`

**Fix**:
```python
query = "MATCH (s:Strategy {owner: $username}) RETURN s"
result = client.run(query, username=username)
```

---

## 🟠 High Priority Issues

### 1. Missing Authorization Check
**File**: `saga-be/src/routes/strategies.py:89`
**Severity**: 🟠 High

```python
@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str):
    return strategy_manager.get(strategy_id)  # No user check
```

**Risk**: Users can access other users' strategies

**Fix**:
```python
@app.get("/api/strategies/{strategy_id}")
def get_strategy(strategy_id: str, username: str = Depends(verify_session)):
    strategy = strategy_manager.get(strategy_id)
    if strategy["owner"] != username:
        raise HTTPException(403, "Not authorized")
    return strategy
```

---

### 2. Path Traversal in File Upload
**File**: `saga-be/src/routes/admin.py:123`
**Severity**: 🟠 High

```python
file_path = f"/uploads/{user_filename}"
with open(file_path, "w") as f:
    f.write(content)
```

**Risk**: Attacker can write to arbitrary paths with `../../etc/passwd`

**Fix**: Use Path validation and stay within allowed directory

---

## 🟡 Medium Priority Issues

### 1. Weak CORS Configuration
**File**: `saga-be/main.py:20`
**Severity**: 🟡 Medium

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Too permissive
)
```

**Risk**: Any origin can make requests, CSRF easier

**Fix**: Whitelist specific origins

---

### 2. Verbose Error Messages
**File**: `saga-be/src/routes/users.py:45`
**Severity**: 🟡 Medium

```python
except Exception as e:
    return {"error": str(e)}  # Exposes stack traces
```

**Risk**: Error messages leak implementation details

**Fix**: Return generic message, log details server-side

---

## 🟢 Low Priority Issues

### 1. Debug Mode in Production Config
**File**: `victor_deployment/docker-compose.yml:34`
**Severity**: 🟢 Low

```yaml
environment:
  - DEBUG=true  # Should be false in production
```

**Fix**: Use `DEBUG=false` in production

---

## ✅ Passed Checks

- [x] No command injection vulnerabilities found
- [x] File operations use safe path handling
- [x] Session cookies have HttpOnly flag
- [x] HTTPS enforced in production
- [x] Rate limiting on API endpoints

---

## Dependency Vulnerabilities

### Critical
None found ✅

### High
- `requests==2.28.0` - CVE-2023-XXXX (example)
  - **Fix**: Upgrade to `requests>=2.31.0`

---

## Recommendations

### Immediate (This Week)
1. 🔴 Rotate exposed API key and remove from code
2. 🔴 Fix Cypher injection with parameterized queries
3. 🟠 Add authorization checks to all strategy endpoints
4. 🟠 Add path traversal protection

### Short Term (This Month)
1. 🟡 Restrict CORS to known origins
2. 🟡 Sanitize error messages
3. Run `pip-audit` regularly (add to CI)
4. Add security headers (CSP, X-Frame-Options, etc.)

### Long Term
1. Security training for team
2. Penetration testing
3. Bug bounty program
4. Security code review in PR process

---

## Security Checklist for Future Code

Before merging:
- [ ] No secrets in code (use environment variables)
- [ ] User input parameterized in queries
- [ ] Authorization checks on protected endpoints
- [ ] File paths validated/sanitized
- [ ] No shell=True with user input
- [ ] Errors don't expose system details
- [ ] Dependencies have no known CVEs

---

## Next Steps

1. Fix all 🔴 Critical issues TODAY
2. Schedule fix for 🟠 High priority issues this week
3. Create tickets for 🟡 Medium priority
4. Re-run audit after fixes
5. Add automated security scanning to CI/CD
```

---

## Deliverable

Provide the full security report in the format above.

For each issue:
- Exact file path and line number
- Code snippet showing vulnerability
- Concrete attack scenario
- Specific fix with code example
- Prioritized by actual risk

Be conservative - better to flag false positives than miss real vulnerabilities.
