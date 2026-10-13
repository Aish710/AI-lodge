"""One JSON error format everywhere: {"error": {"code", "message", "details"?, "request_id"?}}."""
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None, headers: dict | None = None):
        super().__init__(message)
        self.status, self.code, self.message, self.details, self.headers = status, code, message, details, headers or {}


def error_body(code: str, message: str, details=None, request_id: str | None = None) -> dict:
    err: dict = {"code": code, "message": message}
    if details:
        err["details"] = details
    if request_id:
        err["request_id"] = request_id
    return {"error": err}


def error_response(status: int, code: str, message: str, details=None, request_id: str | None = None, headers: dict | None = None):
    return JSONResponse(status_code=status, content=error_body(code, message, details, request_id), headers=headers)
