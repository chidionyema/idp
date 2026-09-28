# Backstage Prevention System - Incident Response Runbooks

> Reference: 6-Layer Prevention System (2026-09-16)
> Each layer has specific incident types and their remediation steps.

## Layer 1: Catalog Data Validation Errors

**Alert:** `CatalogValidationErrorsDetected`  
**Trigger:** Any catalog validation error (invalid URL, missing field, etc.)  
**Response Time SLA:** < 5 minutes to page on-call

### Symptoms
- Catalog validation errors appear in CI/CD logs
- Pre-commit hook rejects commits with invalid catalog data
- Error message references specific field (e.g., "links[1].url is not valid")

### Remediation Steps

1. **Identify the corrupt entity**
   ```bash
   bin/idp-catalog-validator --strict backstage/platform/catalog-info.yaml 2>&1 | grep ERROR
   ```

2. **Locate the source** (find in clusters/oke/*.yaml or platform/*/catalog-info.yaml)
   ```bash
   grep -r "layer-XXXX\|/invalid-url" clusters/oke/
   ```

3. **Fix the YAML**
   - For invalid URLs: ensure format is `https://...` not `/relative/path`
   - For missing fields: add required metadata (name, apiVersion, kind)
   - For broken references: verify referenced entity exists

4. **Validate the fix**
   ```bash
   bin/idp-catalog-validator backstage/platform/catalog-info.yaml
   ```

5. **Commit and deploy**
   ```bash
   git add backstage/platform/catalog-info.yaml
   git commit -m "fix(catalog): resolve validation error in layer-XXXX"
   ```

**Resolution Metric:** Validation errors should drop to 0 within 2 minutes after fix.

---

## Layer 2: API Response Schema Violations

**Alert:** `APISchemaViolationDetected`  
**Trigger:** Invalid data detected in API response before sending to client  
**Response Time SLA:** < 2 minutes to page on-call + alert external systems

### Symptoms
- `SCHEMA_VIOLATION` logs appear in backstage pod logs
- Client receives 503 Service Unavailable from `/api/catalog/entities`
- Telemetry ID in response for tracking

### Remediation Steps

1. **Locate the error in pod logs**
   ```bash
   kubectl logs -n backstage -l app.kubernetes.io/name=catalogue --tail=100 | grep SCHEMA_VIOLATION
   ```

2. **Extract telemetry ID from the violation** (format: `sv-TIMESTAMP-RANDOM`)
   - Used to trace this specific incident across systems

3. **Check what data caused the violation**
   - Review the entity that failed validation
   - Look for: invalid URLs, missing required fields, malformed references

4. **Root cause analysis**
   - Did invalid data slip through Layer 1 (pre-merge validation)?
   - Check git log to see when corrupt data was merged
   - Review the commit that introduced it

5. **Fix and re-deploy**
   ```bash
   # Fix the invalid data in the source
   # Then regenerate catalogs
   bin/catalog-platform
   # Create PR and merge
   ```

6. **Verify resolution**
   ```bash
   kubectl logs -n backstage -l app.kubernetes.io/name=catalogue | grep -c SCHEMA_VIOLATION
   # Should be 0
   ```

**Note:** Circuit breaker returns 503 (not 200) to prevent frontend from crashing on bad data.

---

## Layer 3: Frontend Component Crashes

**Alert:** `BackstageComponentCrashes`  
**Trigger:** 5+ component crashes in 5 minutes  
**Response Time SLA:** < 10 minutes

### Symptoms
- Users see "Feature unavailable" instead of blank page
- Datadog shows spike in `component_crash` events
- Specific component name in logs (e.g., "catalog-graph")

### Remediation Steps

1. **Identify which component is crashing**
   ```bash
   # Check Datadog traces or pod logs
   kubectl logs -n backstage -l app.kubernetes.io/name=catalogue | grep "component_crash" | head -10
   ```

2. **Check recent deployments**
   ```bash
   kubectl rollout history deployment/catalogue -n backstage
   ```

3. **Revert the last change to that component**
   ```bash
   git log --oneline -20 -- backstage/packages/app/src/components/CatalogGraph.tsx
   git revert <commit-sha>
   ```

4. **Deploy hotfix**
   ```bash
   git push origin your-branch
   # Create PR, get approval, merge
   ```

5. **Verify resolution**
   - Crash rate should drop to < 1/min within 2 minutes of deployment
   - Check Datadog for no new `component_crash` events

**Prevention:** Always wrap new components in `<ErrorBoundary>`:
```tsx
<ErrorBoundary componentName="MyComponent">
  <MyComponent />
</ErrorBoundary>
```

---

## Layer 4: Pod Instability (Restarts/Memory Pressure)

**Alert:** `BackstagePodRestartSpike` or `BackstageMemoryPressure`  
**Trigger:** Pod restarts > 5/hour OR memory > 85% of limit  
**Response Time SLA:** < 15 minutes

### Symptoms
- Pods cycling through crashes
- Backstage becomes slow or unresponsive
- Manifest shows high memory usage

### Memory Pressure Remediation

1. **Check pod memory limits**
   ```bash
   kubectl get pod -n backstage -o=jsonpath='{.items[*].spec.containers[*].resources.limits.memory}'
   ```

2. **Identify the memory leak**
   - Check pod logs for messages before crash
   - Look for unbounded cache growth or event listener leaks

3. **Temporary mitigation: Increase memory limit**
   ```bash
   # Edit platform/backstage/base/catalogue.yaml
   # limits: { memory: 2Gi }  # Increased from 1Gi
   kubectl apply -f platform/backstage/base/catalogue.yaml
   ```

4. **Permanent fix: Find and patch the leak**
   - Debug the code causing unbounded memory growth
   - Add cache eviction policy or listener cleanup
   - Deploy patched version

### Pod Restart Spike Remediation

1. **Check why pods are restarting**
   ```bash
   kubectl describe pod -n backstage <pod-name> | grep -A 10 "Last State"
   ```

2. **Immediate action: Scale up**
   ```bash
   # Temporarily scale to handle traffic while restarting
   kubectl scale deployment/catalogue --replicas=5 -n backstage
   ```

3. **Root cause investigation**
   - Check for deadlocks in database connections
   - Review recent code changes
   - Check pod logs for panic messages

4. **Deploy fix and scale back**
   ```bash
   # Fix the issue and deploy
   kubectl scale deployment/catalogue --replicas=3 -n backstage
   ```

---

## Layer 5: Service Degradation (< 2/3 pods ready)

**Alert:** `BackstageServiceDegraded`  
**Trigger:** Less than 2 of 3 pods ready for > 2 minutes  
**Response Time SLA:** < 5 minutes (manual intervention needed)

### Symptoms
- Catalog page becomes slow or times out
- Some requests get 503 errors
- Kubernetes shows pods in CrashLoopBackOff or Pending

### Immediate Actions

1. **Assess impact**
   ```bash
   kubectl get pods -n backstage -o wide | grep catalogue
   kubectl top pod -n backstage | grep catalogue
   ```

2. **Check node status**
   ```bash
   kubectl get nodes -o wide
   kubectl top nodes
   ```

3. **If pods are Pending:**
   - Check if node has capacity
   - Check for pod scheduling conflicts
   - Manually evict non-essential pods if needed

4. **If pods are CrashLoopBackOff:**
   - Revert last deployment
   - Scale down to 1 replica temporarily
   - Investigate crash logs

5. **Manual pod recovery**
   ```bash
   # Force delete stuck pods
   kubectl delete pod <pod-name> -n backstage --grace-period=0 --force
   # Deployment controller will recreate them
   ```

6. **Restore to 3 replicas**
   ```bash
   # Once healthy
   kubectl scale deployment/catalogue --replicas=3 -n backstage
   ```

---

## Universal Incident Response Checklist

1. **Acknowledge the alert** (page on-call, post to #critical-alerts)
2. **Assess severity** (is prod down? can users access? how many affected?)
3. **Take initial action** (scale up, revert, restart)
4. **Root cause analysis** (what broke? when? why did it slip through?)
5. **Implement permanent fix** (code change, deployment, documentation)
6. **Post-incident review** (what failed? how do we prevent this again?)
7. **Update runbook** (add section for this incident type)

---

## Prevention System Guarantees

✅ **Layer 1:** Invalid data blocked BEFORE merge (pre-commit hook + CI gate)  
✅ **Layer 2:** Invalid API responses return 503 (circuit breaker) - never crash frontend  
✅ **Layer 3:** Component crashes show "Feature unavailable" (error boundary) - never blank page  
✅ **Layer 4:** Pod failure = 2+ pods still serving (replicas: 3, minAvailable: 2)  
✅ **Layer 5:** Critical errors page on-call in < 2 minutes (Prometheus alerts)  
✅ **Layer 6:** Every incident type has a tested runbook  

**The system CANNOT fail silently.** Every failure is detected, alerted, and has a known remediation path.
