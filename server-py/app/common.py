"""
统一响应模型、错误码、业务异常
对应 Java 的 Result / ErrorCode / BusinessException / GlobalExceptionHandler
"""
from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    """统一响应格式（与 Java 版兼容，前端无需改动）"""
    code: int = 0
    message: str = "success"
    data: Optional[Any] = None

    @classmethod
    def success(cls, data: Any = None) -> "Result":
        return cls(code=0, message="success", data=data)

    @classmethod
    def error(cls, code: int, message: str) -> "Result":
        return cls(code=code, message=message, data=None)


class ErrorCode:
    """错误码常量（与 Java 版对齐）"""
    SUCCESS = 0
    PARAM_ERROR = 400
    UNAUTHORIZED = 401
    NOT_FOUND = 404
    SYSTEM_ERROR = 500

    # 业务错误码
    CONTENT_EMPTY = 1001
    CONTENT_ILLEGAL = 1002
    AI_PROVIDER_NOT_FOUND = 2001
    AI_CALL_FAILED = 2002
    AI_RESPONSE_INVALID = 2003
    AI_ALL_PROVIDERS_FAILED = 2004
    CARD_ROAST_NOT_FOUND = 3001
    CARD_GENERATE_FAILED = 3002


class BusinessException(Exception):
    """业务异常，controller 层可直接 raise"""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


async def business_exception_handler(
    request: Request, exc: BusinessException
) -> JSONResponse:
    """全局业务异常处理"""
    return JSONResponse(
        status_code=200,  # 与 Java 版保持一致：HTTP 200 + code 区分成功失败
        content=Result.error(exc.code, exc.message).model_dump(),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """兜底异常处理"""
    import logging
    logging.getLogger(__name__).exception("[GlobalException] %s", exc)
    return JSONResponse(
        status_code=200,
        content=Result.error(ErrorCode.SYSTEM_ERROR, f"服务器繁忙：{exc}").model_dump(),
    )
