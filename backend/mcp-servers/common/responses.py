UNKNOWN_EMPLOYEE_MESSAGE="""No active employee record matches the signed-in user."""

def tool_error(error_type:str,message:str,retryable:bool=False)->dict:
    """Build the standard failure payload every MCP tool returns; retryable tells the caller whether trying again can help."""
    return {"ok": False, "error": {"type": error_type, "message": message, "retryable": retryable}}