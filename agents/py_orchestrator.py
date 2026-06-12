#!/usr/bin/env python3
"""
DGM 멀티에이전트 파이프라인 오케스트레이터
사용법:
  python py_orchestrator.py [채널명]
  python py_orchestrator.py DGM
"""
import os
import sys

# ── 환경 설정 ──────────────────────────────────────────────────────────────
# .env 파일 로드 (Windows 쪽 suno-api 프로젝트)
_env_paths = [
    "/mnt/c/suno-api/.env",
    os.path.expanduser("~/.env"),
    os.path.join(os.path.dirname(__file__), "..", ".env"),
]
for _p in _env_paths:
    if os.path.exists(_p):
        with open(_p, encoding="utf-8", errors="ignore") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    os.environ.setdefault(_k.strip(), _v.strip())
        break

# Suno API 서버 (WSL→Windows host)
os.environ.setdefault("SUNO_API_BASE", "http://172.28.32.1:3000")

# ── 실행 ───────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from core.pipeline import run_pipeline

if __name__ == "__main__":
    channel = sys.argv[1] if len(sys.argv) > 1 else "DGM"
    try:
        state = run_pipeline(channel)
        sys.exit(0 if state.get("status") == "completed" else 1)
    except KeyboardInterrupt:
        print("\n사용자 중단")
        sys.exit(130)
    except Exception as e:
        print(f"\n파이프라인 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
