# Security Analysis and Recommendations

## Overview

This document contains security findings from the Amazon Q Code Review (2026-01-05) and provides recommendations for addressing identified issues.

## Critical Findings

### 1. SSL Certificate Verification Disabled

**Location:** `starbelly/downloader.py:261`

**Issue:** SSL certificate verification is disabled for all non-SOCKS connections:
```python
session_args['connector'] = aiohttp.TCPConnector(verify_ssl=False)
```

**Risk Level:** CRITICAL

**Security Impact:**
- The application is vulnerable to Man-in-the-Middle (MITM) attacks
- Attackers could intercept and modify HTTPS traffic
- Credentials and sensitive data transmitted over HTTPS could be compromised
- No validation that the server is who it claims to be

**Business Justification:**
As a web crawler, Starbelly may need to crawl websites with:
- Self-signed certificates
- Expired certificates  
- Invalid certificate chains

**Recommendations:**
1. **Short-term:** Enable SSL verification by default with an optional policy setting to disable it per-domain or per-crawl
2. **Medium-term:** Implement certificate pinning for known domains
3. **Long-term:** Add certificate validation bypass only for explicitly whitelisted domains

**Proposed Fix:**
```python
# Add to Policy configuration
verify_ssl = self._policy.ssl_verification.get_verify_ssl(url)
session_args['connector'] = aiohttp.TCPConnector(verify_ssl=verify_ssl)
```

### 2. Pickle Deserialization of Database Data

**Location:** `starbelly/job.py:328`

**Issue:** Using `pickle.loads()` to deserialize data from the database:
```python
old_urls = pickle.loads(job_doc['old_urls'])
```

**Risk Level:** MEDIUM

**Security Impact:**
- If the database is compromised, attackers could execute arbitrary code
- Pickle can deserialize malicious objects that execute code during deserialization
- No validation of the deserialized data structure

**Mitigation Factors:**
- Data comes from RethinkDB which should be in a trusted environment
- Database access requires authentication
- Attack surface is limited to database compromise scenarios

**Recommendations:**
1. **Preferred:** Replace pickle with JSON serialization for URL sets
2. **Alternative:** Use restricted unpickler with allowlist of safe classes
3. **Minimum:** Document the security assumption that database is trusted

**Proposed Fix:**
```python
# Replace pickle with JSON for URL storage
# Convert set to list for JSON serialization
old_urls_list = list(job.old_urls)
old_urls_json = json.dumps(old_urls_list)

# On load:
old_urls_list = json.loads(job_doc['old_urls'])
old_urls = set(old_urls_list)
```

## Medium Priority Findings

### 3. No Request Timeouts on HTML Parsing

**Location:** `starbelly/extractor.py`

**Issue:** BeautifulSoup parsing has no timeout or size limits

**Risk Level:** LOW-MEDIUM

**Security Impact:**
- Large or maliciously crafted HTML could cause denial of service
- Memory exhaustion from parsing extremely large documents
- CPU exhaustion from deeply nested HTML structures

**Recommendations:**
1. Add maximum response body size check before parsing
2. Implement parsing timeout using async timeout context
3. Limit recursion depth for HTML tree traversal

**Proposed Fix:**
```python
# Add size limit
MAX_BODY_SIZE_FOR_PARSING = 10 * 1024 * 1024  # 10MB

if len(response.body) > MAX_BODY_SIZE_FOR_PARSING:
    logger.warning(f'Skipping large response: {len(response.body)} bytes')
    return

# Add parsing timeout
with trio.fail_after(30):  # 30 second timeout
    soup = BeautifulSoup(response.body, 'lxml')
```

### 4. Subprocess Usage in Development Mode

**Location:** `starbelly/__main__.py:54`

**Issue:** Environment variables passed to subprocess without sanitization

**Risk Level:** LOW

**Security Impact:**
- Only affects development mode with watchdog enabled
- If environment variables are controlled by attacker, could lead to code injection
- Production deployments should not use this code path

**Recommendations:**
1. Document that development mode should not be used in production
2. Sanitize environment variables before passing to subprocess
3. Use explicit allowlist of environment variables to pass through

## Performance Findings

### 5. Resource Management

**Status:** ✅ Properly Implemented

**Location:** `starbelly/resource_monitor.py:78-87`

The resource monitor correctly handles channel cleanup with try-except blocks to prevent memory leaks from broken channels.

### 6. Memory Growth in Job Manager

**Location:** `starbelly/job.py:90-94`

**Issue:** `self._jobs` dictionary could grow unbounded with long-running processes

**Risk Level:** LOW

**Impact:**
- Memory usage increases with number of concurrent jobs
- Old job data may not be cleaned up promptly

**Recommendation:**
- Implement periodic cleanup of completed jobs from memory
- Add maximum job retention limit
- Consider using weak references for old job stats

## Input Validation Findings

### 7. Limited Validation on API Inputs

**Location:** `starbelly/server/*.py`

**Issue:** Seeds and tags are stripped but not validated against patterns

**Risk Level:** LOW

**Security Impact:**
- Malicious regex patterns could cause ReDoS (Regular Expression Denial of Service)
- Invalid URLs could cause exceptions
- No limits on seed/tag list sizes

**Recommendations:**
1. Add URL validation before accepting seeds
2. Limit maximum number of seeds/tags per request
3. Validate regex patterns for complexity before compilation
4. Add input length limits

## Dependencies

### 8. Dependency Vulnerability Scanning

**Recommendations:**
1. Enable automated dependency vulnerability scanning
2. Regular updates of dependencies, especially:
   - `aiohttp` - HTTP client library
   - `lxml` - XML parser (known for security issues)
   - `beautifulsoup4` - HTML parser
3. Consider using tools like:
   - `pip-audit` for Python dependency scanning
   - GitHub Dependabot alerts
   - Snyk or similar security scanning tools

### 9. Outdated Dependencies

Some dependencies may have known vulnerabilities:
- Check `poetry.lock` against CVE databases
- Update to latest compatible versions
- Test thoroughly after updates

## Security Best Practices Currently Implemented

✅ **Parameterized Database Queries** - No SQL injection vulnerabilities  
✅ **No Eval/Exec** - No dynamic code execution  
✅ **Async/Await** - Proper concurrency handling  
✅ **Configuration Management** - Secrets via config files, not hardcoded  
✅ **Logging** - Proper logging for security auditing  

## Recommendations Summary

### Immediate Actions (Critical)
1. Document SSL verification disabled - why and risks
2. Add security warnings to README
3. Consider adding SSL verification policy option

### Short-term Actions (High Priority)
1. Replace pickle with JSON for URL set serialization
2. Add response size limits before parsing
3. Add parsing timeouts
4. Implement input validation on API endpoints

### Long-term Actions (Medium Priority)
1. Implement configurable SSL verification per policy
2. Add certificate pinning for known domains
3. Implement comprehensive input validation framework
4. Set up automated dependency vulnerability scanning
5. Regular security audits and penetration testing

## Security Assumptions

This application assumes:
1. **Trusted Database:** RethinkDB instance is in a secure, trusted environment
2. **Internal Network:** Deployment is on trusted internal network
3. **Development Mode:** Watchdog/dev mode only used in development environments
4. **Configuration Security:** Config files are properly secured with appropriate permissions

## Disclosure Policy

If you discover a security vulnerability in Starbelly:
1. Do NOT open a public GitHub issue
2. Email security concerns to: acaceres@hyperiongray.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

## Version History

- **2026-03-03:** Initial security analysis based on Amazon Q Code Review
- **Review Scope:** 62 source files analyzed
- **Commit:** 5d01b187488c87d3de49dbeb9fa0db60c7c32d1b
