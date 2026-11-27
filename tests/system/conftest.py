"""!
@brief 시스템 시험 공통 설정: 시험 하네스 모듈(vector_runner)을 import 경로에 추가한다.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
