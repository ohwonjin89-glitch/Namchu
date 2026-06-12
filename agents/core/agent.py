import os
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
