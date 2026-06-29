# -*- coding: utf-8 -*-
# [Jolly-Carson 분석 패키지 - 이니셜라이저]
# - 설계 의도:
#   외부 모듈(server.py 등)에서 analytics 패키지를 편리하게 사용할 수 있도록
#   핵심 함수와 정보를 외부에 개방(export)합니다.

from .analyzer import analyze_student_history
from .prerequisites import PREREQUISITE_MAP

__all__ = [
    "analyze_student_history",
    "PREREQUISITE_MAP"
]
