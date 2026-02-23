from langchain_core.messages import BaseMessage


def get_history(self) -> list[BaseMessage]:
    return self.message_history

def clear_history(self):
    self.message_history = []