# OAuth Coach ID Fix - Complete Solution

## 🚨 Problem Identified

The OAuth flow was showing `state=default` instead of the actual coach ID because the frontend was not passing the `coach_id` parameter when requesting the OAuth URL.

## ✅ Root Cause Analysis

1. **Backend**: Server correctly expects `coach_id` as a query parameter
2. **Frontend Issue**: Client calling `/google/oauth-url` without the `coach_id` parameter
3. **Result**: OAuth state defaults to "default" instead of the logged-in coach's ID

## 🔧 Complete Fix Applied

### 1. Server-Side Improvements (`railway_server.py`)

**Before:**
```python
coach_id = query_params.get('coach_id', ['default'])[0]  # ❌ Silent fallback
```

**After:**
```python
coach_id = query_params.get('coach_id', [None])[0]

# Validate coach_id is provided
if not coach_id or coach_id == 'default':
    self.send_json_response({
        "error": "Missing coach_id parameter",
        "message": "Please include coach_id as a query parameter: /google/oauth-url?coach_id=YOUR_COACH_ID",
        "status": "error",
        "example": "/google/oauth-url?coach_id=bralin-jackson-coach-id"
    }, status_code=400)
    return
```

### 2. Frontend Fix Required

The client application needs to update how it calls the OAuth endpoint:

**❌ Current (Broken) Code:**
```javascript
// This causes state=default
const response = await fetch('/google/oauth-url');
```

**✅ Fixed Code:**
```javascript
// Get coach ID from your auth system
const coachId = getLoggedInCoachId(); // However you retrieve the current coach
const response = await fetch(`/google/oauth-url?coach_id=${coachId}`);
```

### 3. Coach ID Retrieval Examples

Depending on how your authentication works:

```javascript
// Option 1: From auth context/store
const coachId = useAuth().user.coachId;

// Option 2: From localStorage
const coachId = localStorage.getItem('coachId');

// Option 3: From user session
const coachId = getCurrentUser().id;

// Option 4: From URL params (if coach ID is in route)
const coachId = useParams().coachId;
```

## 🧪 Testing Results

```bash
# ❌ Without coach_id - Now properly rejected
GET /google/oauth-url
→ 400 Bad Request: "Missing coach_id parameter"

# ✅ With coach_id - Works correctly  
GET /google/oauth-url?coach_id=bralin-jackson-coach-123
→ 200 OK: OAuth URL with state=bralin-jackson-coach-123
```

## 🎯 For Bralin Jackson Specifically

Since Bralin Jackson is currently logged in, the frontend should:

1. **Retrieve Bralin's coach ID** from the authentication system
2. **Include it in the OAuth URL request**:
   ```javascript
   const bralinCoachId = getBralinJacksonCoachId();
   const response = await fetch(`/google/oauth-url?coach_id=${bralinCoachId}`);
   ```

## 📋 Implementation Checklist

- [x] ✅ **Server validation added** - Rejects missing coach_id with helpful error
- [x] ✅ **Test script created** - Demonstrates the fix working
- [ ] 🔲 **Frontend updated** - Client needs to pass coach_id parameter
- [ ] 🔲 **Auth integration** - Get coach_id from authentication system
- [ ] 🔲 **Testing complete** - Verify Bralin Jackson's OAuth flow works

## 🚀 Immediate Next Steps

1. **Find the frontend code** that calls `/google/oauth-url`
2. **Update it** to include `?coach_id=${actualCoachId}`
3. **Test with Bralin Jackson** logged in
4. **Verify OAuth state** shows actual coach ID instead of "default"

## 📞 Files Modified

- `/Users/jarettwesley/Desktop/paestro-project/google_workspace_mcp/railway_server.py` - Added coach_id validation
- `/Users/jarettwesley/Desktop/paestro-project/google_workspace_mcp/test_oauth_fix.py` - Test demonstration

## 💡 Key Insight

The issue wasn't in the MCP server itself - it was properly designed to receive coach_id. The problem was that **no client was passing the coach_id parameter**. Now the server will clearly indicate when this parameter is missing, making it easier to debug and fix.