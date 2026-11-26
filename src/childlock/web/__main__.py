"""!
@brief Web 시뮬레이터 실행 진입점 (QM, SWD 11장). 실행: python -m childlock.web
"""

import uvicorn

from childlock.clock import MonotonicClock
from childlock.controller import ChildLockController
from childlock.event_store import EventStore
from childlock.override import OverrideTracker
from childlock.web import create_app


def main() -> None:
    """!@brief 실제 시계와 50 ms 주기 루프로 시뮬레이터를 127.0.0.1:8000에서 실행한다."""
    clock = MonotonicClock()
    store = EventStore()
    controller = ChildLockController(clock, OverrideTracker(), store)
    uvicorn.run(create_app(controller, store, clock, run_loop=True), host="127.0.0.1", port=8000)


if __name__ == "__main__":  # pragma: no cover - 명령줄 진입점
    main()
