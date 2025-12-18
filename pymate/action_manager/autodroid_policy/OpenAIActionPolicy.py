from openai import OpenAI
from os import getenv

from pymate.action_manager.graph.Action import ActionBag
from pymate.action_manager.graph.GraphManager import GraphManager
from pymate.action_manager.ActionPolicy import ActionPolicy
from pymate.action_manager.autodroid_policy.AutoDroidPrompt import AutoDroidPrompt
from pymate.action_manager.ActionMemory import MemoryManager

OPENAI_API_KEY = getenv('OPENAI_API_KEY')

AVAILABLE_MODELS = [
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-0301",
    "text-davinci-003",
    "code-davinci-002",
]


def validate_model(model):
    if model not in AVAILABLE_MODELS:
        raise ValueError(
            f"Invalid model '{model}', available models: {', '.join(AVAILABLE_MODELS)}"
        )


def query_gpt(prompt, model="gpt-3.5-turbo"):
    client = OpenAI(
        api_key=OPENAI_API_KEY
    )
    retry = 0
    completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model=model,
        timeout=15
    )
    res = completion.choices[0].message.content
    return res


class OpenAIActionPolicy(ActionPolicy):
    def __init__(self):
        self.prompt = None
        self.prompt_str = None
        self.prompt_resp = None
        self.succeeded = False

    def choose_actions(self, task: str, memory_manager: MemoryManager, graph_manager: GraphManager) -> ActionBag:
        self.succeeded = False
        self.prompt = AutoDroidPrompt(self.task, graph_manager)
        self.prompt_str = self.prompt.get_prompt_str()
        response = query_gpt(self.prompt_str)
        self.prompt.parse_question_response(response)
        self.succeeded = True
        return self.prompt.action_bag

    def to_dict(self):
        return {
            "prompt_question": self.prompt_str,
            "prompt_response": self.prompt_resp
        }

    def has_succeeded(self):
        return self.succeeded


def main():
    query_gpt("Say something good.")


if __name__ == "__main__":
    main()
