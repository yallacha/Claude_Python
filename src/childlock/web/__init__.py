"""!
@brief Web 시뮬레이터 (QM, SWD 11장, SWR-014·015·023).
@details FastAPI JSON API와 정적 화면을 제공한다.
    run_loop이면 50 ms마다 controller.step()을 호출한다.
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from childlock.model import CYCLE_MS, Event, Status

_STATIC = Path(__file__).with_name("static")


def _plain(value: object) -> object:
    """!@brief Enum은 값 문자열로, 나머지는 그대로. @return 변환 값"""
    return value.value if isinstance(value, Enum) else value


def serialize_status(status: Status) -> dict[str, object]:
    """!
    @brief 상태를 JSON 객체로 바꾼다 (SWR-014).
    @param status 상태
    @return 7개 필드 사전
    @throws TypeError status가 Status가 아닐 때
    """
    return {key: _plain(value) for key, value in asdict(status).items()}


def serialize_event(event: Event) -> dict[str, object]:
    """!@brief 이벤트를 JSON 객체로 바꾼다. @return 허용 필드 사전"""
    return {key: _plain(value) for key, value in asdict(event).items()}


async def _read_json(request: Request) -> tuple[object, JSONResponse | None]:
    """!
    @brief 요청 본문을 JSON으로 읽는다. 내용 검증은 controller가 한다.
    @return (본문, 오류 응답). 구문 오류면 422 응답
    """
    try:
        return await request.json(), None
    except json.JSONDecodeError:
        return None, JSONResponse({"error": "invalid_json"}, status_code=422)


def _lifespan(controller, run_loop: bool):
    """!
    @brief 앱 수명 주기: run_loop이면 50 ms 주기 평가 작업을 띄운다 (SWR-023).
    @return FastAPI lifespan 함수
    """

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async def cycle() -> None:
            while True:
                controller.step()
                await asyncio.sleep(CYCLE_MS / 1000)

        task = asyncio.create_task(cycle()) if run_loop else None
        yield
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    return lifespan


def _register_inputs(app: FastAPI, controller, clock, run_loop: bool) -> None:
    """!@brief 입력 제출과 수동 평가 라우트를 등록한다."""

    @app.post("/api/snapshot", status_code=202)
    async def post_snapshot(request: Request, stamp: bool = False):
        body, error = await _read_json(request)
        if error:
            return error
        if stamp:
            # 화면 입력은 브라우저가 서버 시계를 모르므로 서버 수신 시각을 입력 시각으로 쓴다
            if not isinstance(body, dict):
                return JSONResponse({"error": "object_required"}, status_code=422)
            body = {**body, "source_timestamp_s": clock.now()}
        controller.submit_snapshot(body)
        return {"accepted": True}

    @app.post("/api/command", status_code=202)
    async def post_command(request: Request):
        body, error = await _read_json(request)
        if error:
            return error
        controller.submit_command(body)
        return {"accepted": True}

    @app.post("/api/step")
    def post_step():
        if run_loop:  # 주기 루프와 경합하지 않도록 시험 모드에서만 허용
            return JSONResponse({"error": "cycle_loop_running"}, status_code=409)
        return serialize_status(controller.step())


def _register_outputs(app: FastAPI, controller, events) -> None:
    """!@brief 상태·이력 조회와 화면 라우트를 등록한다."""

    @app.get("/api/status")
    def get_status():
        try:
            return serialize_status(controller.status())
        except Exception:  # 직렬화 실패는 HTTP 500 (SWR-015)
            return JSONResponse({"error": "serialization_failed"}, status_code=500)

    @app.get("/api/events")
    def get_events():
        return [serialize_event(e) for e in events.list_events()]

    @app.get("/", response_class=HTMLResponse)
    def index():
        return (_STATIC / "index.html").read_text(encoding="utf-8")


def create_app(controller, events, clock, run_loop: bool = True) -> FastAPI:
    """!
    @brief Web 시뮬레이터 앱을 만든다.
    @param controller ChildLockController (또는 같은 메서드를 가진 객체)
    @param events 결정 이력 저장소(list_events 제공, controller에 주입한 것과 같은 객체)
    @param clock controller와 같은 시계(화면 입력 시각 채우기용)
    @param run_loop True면 50 ms 주기 평가 루프 실행, False면 POST /api/step으로 수동 평가
    @return FastAPI 앱
    """
    app = FastAPI(title="Childlock PC/SIL Simulator", lifespan=_lifespan(controller, run_loop))
    _register_inputs(app, controller, clock, run_loop)
    _register_outputs(app, controller, events)
    return app
