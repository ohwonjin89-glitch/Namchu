"""Meeting log writer — saves agent conversations as Markdown."""
import os
import sys
import json
import datetime


class _Tee:
    """stdout/stderr를 콘솔과 로그 파일에 동시에 쓴다."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self.streams:
            s.flush()


def setup_run_logging(channel: str, date_str: str) -> str:
    """파이프라인 실행 전체(print 출력 + traceback)를 agents/logs/에 파일로도 남긴다.
    tmux pane 스크롤백은 유한하고 유실되기 쉬워, 사후 디버깅용 영구 기록이 필요하다."""
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{channel}_{date_str}.log")
    log_file = open(log_path, "a", encoding="utf-8")
    sys.stdout = _Tee(sys.__stdout__, log_file)
    sys.stderr = _Tee(sys.__stderr__, log_file)
    return log_path


class MeetingLogger:
    def __init__(self, output_dir: str, channel: str, date_str: str):
        self.output_dir = output_dir
        self.channel = channel
        self.date_str = date_str
        self.entries: list = []
        self.start_time = datetime.datetime.now()

    def log(self, speaker: str, question: str, answer: str, round_num: int = 0):
        self.entries.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "speaker": speaker,
            "round": round_num,
            "question": question,
            "answer": answer
        })

    def add_section(self, title: str, content: str):
        self.entries.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "section": title,
            "content": content
        })

    def save(self, state: dict):
        log_path = os.path.join(self.output_dir, "meeting_log.md")
        elapsed = datetime.datetime.now() - self.start_time
        total_min = int(elapsed.total_seconds() / 60)

        lines = [
            f"# DGM 에이전트 회의록",
            f"",
            f"- **채널**: {self.channel}",
            f"- **일시**: {self.start_time.strftime('%Y-%m-%d %H:%M')}",
            f"- **소요시간**: {total_min}분",
            f"- **상태**: {state.get('status', 'unknown')}",
            f"",
            "---",
            "",
        ]

        # Results summary
        selected = state.get("selectedPrompt", {})
        if selected:
            lines += [
                "## 최종 결정",
                f"",
                f"| 항목 | 내용 |",
                f"|------|------|",
                f"| 제목 | {selected.get('title', '')} |",
                f"| 스타일 | {selected.get('style', '')} |",
                f"| 가이드 | {selected.get('guide', '')} |",
                f"| 업로드 제목 | {state.get('uploadTitle', '')} |",
                f"| YouTube URL | {state.get('uploadedUrl', '미업로드')} |",
                f"",
                "---",
                "",
            ]

        # Trend data
        top_titles = state.get("topTitles", [])
        if top_titles:
            lines += [
                "## 트렌드 분석",
                "",
            ]
            for t in top_titles:
                lines.append(f"- {t}")
            lines += ["", "---", ""]

        # Agent conversations
        current_section = ""
        for entry in self.entries:
            if "section" in entry:
                current_section = entry["section"]
                lines += [f"## {current_section}", "", entry.get("content", ""), "", "---", ""]
                continue

            if "round" in entry and entry.get("round", 0) > 0:
                if not current_section:
                    current_section = "에이전트 회의"
                    lines += [f"## {current_section}", ""]
                round_label = f"라운드 {entry['round']}"
                lines += [
                    f"### [{entry['time']}] {entry['speaker']} — {round_label}",
                    "",
                    "**질문/요청:**",
                    "",
                    f"> {entry.get('question', '').replace(chr(10), chr(10) + '> ')}",
                    "",
                    "**답변:**",
                    "",
                    entry.get("answer", ""),
                    "",
                ]

        lines += [
            "---",
            "",
            f"*자동 생성 by DGM 멀티에이전트 시스템 — {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}*",
        ]

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"  회의록 저장: {log_path}")
        return log_path
