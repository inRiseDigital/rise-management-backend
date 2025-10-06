# PDF Frontend Display - Troubleshooting Guide

## Current Issue
When you ask "generate report including kitchen expenses details", the backend generates the PDF successfully but the frontend doesn't display it. Instead, you see a text response with a sandbox link.

## What I Fixed

### 1. System Prompt Updates (`test-kitche-client.py`)

**Added instruction to NOT create fake download links:**
```
IMPORTANT FOR PDF REPORTS:
When generate_document_with_data() returns PDF data, DO NOT create download links or sandbox paths.
Simply confirm: "Report generated successfully. PDF will be displayed in the interface."
The frontend will automatically detect and display the PDF from the tool result.
```

**Added debug logging:**
```python
print("API RESPONSE DEBUG:")
print(f"Output text: {resp.output_text[:200]}...")
print(f"Response keys: {resp_dict.keys()}")
print(f"Output: {str(resp_dict['output'])[:500]}...")
```

### 2. Why This Happens

OpenAI's Responses API:
1. Calls your MCP tool `generate_document_with_data()`
2. Tool returns: `{success: true, pdf_data: "base64...", filename: "report.pdf"}`
3. OpenAI agent formats a human-readable response
4. Frontend needs to extract the **raw tool result**, not the text response

## Next Steps - RESTART & TEST

### Step 1: Restart Test Client
```bash
# Stop current client (Ctrl+C)
cd E:\ABSOLX\Rise-management-app\rise_app_backend\mcp-client
uvicorn test-kitche-client:app --reload --port 8001
```

### Step 2: Test & Check Logs
Ask: "Generate report including kitchen expenses details"

**Watch the terminal output:**
```
================================================================================
API RESPONSE DEBUG:
Output text: Report generated successfully...
Response keys: dict_keys(['id', 'output', 'output_text', ...])
Output type: <class 'list'>
Output: [tool_result_content_here]
================================================================================
```

### Step 3: Check Browser Console
Open DevTools (F12) → Console tab

Look for these logs:
```javascript
Full raw data structure: {...}
Full raw data structure: {...}
Searching at depth 0: [...]
Found PDF data at depth X: {pdf_data: "...", filename: "..."}
PDF processing details:
- Filename: kitchen_expense_report_2025-01-01_to_2025-10-04.pdf
- Has PDF Data: true
- PDF Data length: 123456
```

## Debugging Checklist

### ❌ If PDF Still Not Showing:

**Check 1: Is pdf_data in the response?**
```javascript
// In browser console
console.log('Raw data:', data.raw);
console.log('Output:', data.raw.output);
```

**Check 2: Is frontend finding it?**
```javascript
// Should see in console:
"Found PDF data at depth X: {pdf_data: '...', filename: '...'}"
```

**Check 3: Is OpenAI returning tool results?**
```bash
# Check terminal logs
# Should see: Output type: <class 'list'>
# Should see tool result in output
```

### ✅ If You See This:
```
Found PDF data at depth X: {
  pdf_data: "JVBERi0xLjQK...",
  filename: "kitchen_expense_report_2025-01-01_to_2025-10-04.pdf"
}
```
**→ PDF should display! 🎉**

## Alternative: Force Tool Result Display

If OpenAI is hiding the tool results, update the endpoint to extract them explicitly:

```python
@app.post("/api/chat")
async def chat_endpoint(body: ChatRequest):
    resp = client.responses.create(...)
    resp_dict = resp.to_dict()

    # Extract tool results explicitly
    tool_results = []
    if 'output' in resp_dict and isinstance(resp_dict['output'], list):
        for item in resp_dict['output']:
            if item.get('type') == 'tool_result':
                tool_results.append(item.get('content'))

    return {
        "ok": True,
        "output_text": resp.output_text,
        "raw": resp_dict,
        "tool_results": tool_results  # Add this explicitly
    }
```

Then update frontend to check `data.tool_results` first.

## Summary

1. ✅ Updated system prompt to not create fake links
2. ✅ Added debug logging to backend
3. ✅ Frontend already has PDF detection logic
4. 🔄 **YOU NEED TO: Restart test client and check logs**

**Next: Restart and share the terminal + console logs if it's still not working!**
