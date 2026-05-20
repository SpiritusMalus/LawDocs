# GitHub Issues to Create (from review.md)

## Priority: HIGH (P1) - Security

### Issue 1: XSS vulnerability - Admin secret in sessionStorage
**File:** `frontend/app/admin/reviews/page.tsx:32-56`
**Severity:** CRITICAL
**Description:**
ADMIN_SECRET is stored in sessionStorage and sent via X-Admin-Secret header. Any XSS on this domain leaks the master moderation key.
**Fix:**
- Use server action to authenticate (POST /api/auth/admin/login)
- Backend validates ADMIN_SECRET and sets httpOnly admin-cookie with 15min TTL
- Frontend uses only the cookie for subsequent requests
- Never expose secret in JS context

### Issue 2: CSRF protection bypass for /api/admin/*
**File:** `frontend/middleware.ts:17-24`
**Severity:** HIGH
**Description:**
CSRF protection skips requests without Origin header. Vulnerable to XSS + CSRF on old browsers or legacy fetch calls.
**Fix:**
- For /api/admin/*, require Origin header strictly
- Only allow requests from known admin IPs if applicable

---

## Priority: MEDIUM (P2) - Data Integrity

### Issue 3: Race condition in toggle_review_visibility
**File:** `backend/app/api/v1/reviews.py:166-169`
**Severity:** MEDIUM
**Description:**
Read-modify-write without locking. If 2 moderators click simultaneously, race condition possible.
**Fix:**
- Use `.with_for_update()` on review query
- Test with concurrent requests

---

## Priority: LOW (P3) - Refactoring & Quality

### Issue 4: Duplicate validator - strip_and_escape
**File:** `backend/app/api/v1/reviews.py:32` and `backend/app/api/v1/users.py:25`
**Description:**
Identical field_validator in 2 files (now strip_whitespace after html.escape removal).
**Fix:**
- Extract to `app/core/validators.py`
- Import and reuse in both schemas

### Issue 5: Dead code - verify_magic_token
**File:** `backend/app/core/security.py:52-53`
**Severity:** LOW
**Description:**
Function is never called (only direct hash comparison used).
**Fix:**
- Delete `verify_magic_token` function

### Issue 6: Side effect in loadReviews function
**File:** `frontend/app/admin/reviews/page.tsx:39-57`
**Severity:** LOW
**Description:**
loadReviews directly calls `sessionStorage.setItem()`, making it hard to reuse.
**Fix:**
- Move setItem to handleLogin
- Keep loadReviews pure (only load + return data)

### Issue 7: Accessibility - missing aria-label
**File:** `frontend/app/admin/reviews/page.tsx:147`
**Severity:** LOW
**Description:**
Toggle button missing aria-label and aria-pressed.
**Fix:**
- Add `aria-label="Toggle review visibility"`
- Add `aria-pressed={!review.is_hidden}`

### Issue 8: Magic numbers in docgen.py
**File:** `backend/app/services/docgen.py:139` and `_render_sig_block`
**Severity:** LOW
**Description:**
Hardcoded 105.0 (RIGHT_COL_X) and 85.0 (RIGHT_COL_W) used in multiple places.
**Fix:**
- Define constants at module level:
  ```python
  RIGHT_COL_X = 105.0
  RIGHT_COL_W = 85.0
  ```

### Issue 9: Inefficient user lookup in create_review
**File:** `backend/app/api/v1/reviews.py:66-103`
**Severity:** LOW
**Description:**
Uses duplicate query on existing check (`existing.scalar_one_or_none()`) instead of relying on IntegrityError.
**Fix (Optional):**
- Keep current approach for clarity (simpler error messages)
- Or: remove duplicate query, catch IntegrityError and respond with 409

---

## Fixed (Already in commits)
✅ Timing attack - timing-safe ADMIN_SECRET comparison
✅ Double html.escape - removed from validators
✅ _render_sig_block page break - proper BLOCK_H calculation
✅ Pagination - added to /reviews/admin
✅ Email normalization - .lower() in auth/orders flows
✅ ADMIN_SECRET validation - required in production
✅ Page validation - max(page, 1) to prevent negative offsets
