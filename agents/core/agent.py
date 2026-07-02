import os
import time
import anthropic

_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


class Agent:
    def __init__(self, name: str, instructions: str, model: str = "claude-sonnet-4-6"):
        self.name = name
        self.system = instructions
        self.model = model
        self.messages = []
        self.conversation_log = []

    def chat(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        response = get_client().messages.create(
            model=self.model,
            max_tokens=2000,
            system=self.system,
            messages=self.messages
        )
        reply = response.content[0].text
        self.messages.append({"role": "assistant", "content": reply})
        self.conversation_log.append({"from": "user", "to": self.name, "text": message})
        self.conversation_log.append({"from": self.name, "to": "user", "text": reply})
        return reply

    def reset(self):
        self.messages = []
        self.conversation_log = []


class TmuxAgent(Agent):
    """파일 기반 IPC로 tmux 창의 agent-worker.sh와 통신.

    각 tmux 창에서 agent-worker.sh가 실행 중이어야 합니다.
    작업 파일: /tmp/dgm/tasks/<name>.task
    결과 파일: /tmp/dgm/tasks/<name>.result
    타임아웃 시 Python SDK로 자동 폴백합니다.
    """

    TASK_DIR = "/tmp/dgm/tasks"

    def __init__(self, name: str, instructions: str, model: str = "claude-sonnet-4-6",
                 timeout: int = 300):
        super().__init__(name, instructions, model)
        self.task_file = f"{self.TASK_DIR}/{name}.task"
        self.result_file = f"{self.TASK_DIR}/{name}.result"
        self.timeout = timeout
        os.makedirs(self.TASK_DIR, exist_ok=True)

    def chat(self, message: str) -> str:
        # 이전 결과 파일 제거
        if os.path.exists(self.result_file):
            os.remove(self.result_file)

        # 작업 파일 작성 → agent-worker.sh가 감지하여 claude 실행
        with open(self.task_file, "w", encoding="utf-8") as f:
            f.write(message)

        print(f"    [{self.name}] → tmux 창 전달 완료, 응답 대기...")

        # 결과 파일 폴링
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if os.path.exists(self.result_file):
                raw = open(self.result_file, encoding="utf-8").read()
                if "__DONE__" in raw:
                    reply = raw.split("__DONE__")[0].strip()
                    self.messages.append({"role": "user", "content": message})
                    self.messages.append({"role": "assistant", "content": reply})
                    self.conversation_log.append({"from": "user", "to": self.name, "text": message})
                    self.conversation_log.append({"from": self.name, "to": "user", "text": reply})
                    return reply
            time.sleep(1)

        # 타임아웃 → Python SDK 직접 호출
        print(f"    [{self.name}] tmux 타임아웃({self.timeout}s) — Python SDK 폴백")
        if os.path.exists(self.task_file):
            os.remove(self.task_file)
        return super().chat(message)


def agent_dialogue(agent_a: "Agent", agent_b: "Agent",
                   initial_message: str, max_rounds: int = 3,
                   meeting_log: list = None) -> str:
    """
    Two agents discuss until consensus or max_rounds exhausted.
    agent_a = Director (approves/rejects)
    agent_b = Specialist (proposes)
    Returns the approved content string.
    """
    current_msg = initial_message
    last_proposal = ""

    for round_num in range(1, max_rounds + 1):
        print(f"    [{agent_b.name}] 라운드 {round_num}...")
        proposal = agent_b.chat(current_msg)
        last_proposal = proposal
        if meeting_log is not None:
            meeting_log.append({
                "round": round_num, "speaker": agent_b.name,
                "role": "specialist", "content": proposal
            })

        review_prompt = (
            f"전문가의 제안 (라운드 {round_num}):\n\n{proposal}\n\n"
            "이 제안을 검토하세요.\n"
            "동의하면 첫 줄에 '승인:' 을 쓰고 최종 내용을 정리하세요.\n"
            "수정이 필요하면 구체적인 피드백만 작성하세요 (승인 없이)."
        )
        print(f"    [{agent_a.name}] 검토 중...")
        review = agent_a.chat(review_prompt)
        if meeting_log is not None:
            meeting_log.append({
                "round": round_num, "speaker": agent_a.name,
                "role": "director", "content": review
            })

        if review.strip().startswith("승인:"):
            approved = review.split("승인:", 1)[1].strip()
            return approved if approved else proposal

        # Feed feedback back to specialist
        current_msg = (
            f"디렉터 피드백:\n{review}\n\n"
            "피드백을 반영해서 다시 제안해주세요."
        )

    return last_proposal
