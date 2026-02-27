from typing import Annotated, TypedDict

from config.config import OPENAI_MODEL, TEMPERATURE
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from src.prompts import AGENT_SYSTEM_PROMPT
from tools.rag import rag_retrieval


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class Chatbot:

    def __init__(self):
        self.message_history: list[BaseMessage] = []
        self.graph = self.build_graph()
        tools = [rag_retrieval]
        self.llm = ChatOpenAI(
            max_completion_tokens=2000,
            base_url="https://openrouter.ai/api/v1",
            model=OPENAI_MODEL,
            temperature=TEMPERATURE,
        )
        self.model_with_tools = self.llm.bind_tools(tools)

    # GRAPH NODES
    ## LOGIC NODE
    def LogicNode(self, state: State) -> State:
        messages = state["messages"]

        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + messages

        response = self.model_with_tools.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            state["messages"].append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("args", {})

                if tool_name == "rag_retrieval":
                    tool_result = rag_retrieval.invoke(tool_input)

                    tool_message = ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call.get("id", ""),
                        name=tool_name,
                    )
                    state["messages"].append(tool_message)

            final_response = self.model_with_tools.invoke(state["messages"])
            state["messages"].append(final_response)
        else:
            state["messages"].append(response)

        return state

    # INPUT NODE
    def InputNode(self, state: State) -> State:
        question = state["messages"][-1].content
        print(f"\n📝 INPUT: {question}")
        return state

    # GRAPH BUILDING
    def build_graph(self) -> StateGraph:
        graph = StateGraph(State)
        # Add nodes
        graph.add_node("input_node", self.InputNode)
        graph.add_node("process", self.LogicNode)
        # Add edges
        graph.add_edge(START, "input_node")
        graph.add_edge("input_node", "process")
        graph.add_edge("process", END)
        return graph.compile()

    # CHAT
    def chat(self, user_input: str, options: dict) -> dict:
        human_message = HumanMessage(content=user_input)
        self.message_history.append(human_message)

        state = State(messages=self.message_history)

        output_state = self.graph.invoke(state)

        self.message_history = output_state["messages"]

        answer = "No response generated"
        retrieved_documents = ""

        # Find the final answer from AI
        for message in reversed(self.message_history):
            if isinstance(message, AIMessage) and message.content:
                answer = message.content
                break

        # Find retrieved documents from recent Tool messages
        for message in reversed(self.message_history):
            if isinstance(message, HumanMessage) and message.content == user_input:
                break  # Stop search when reaching the current user question
            if isinstance(message, ToolMessage) and message.name == "rag_retrieval":
                retrieved_documents = message.content
                break

        return {"answer": answer, "retrieved_documents": retrieved_documents}


if __name__ == "__main__":
    chatbot = Chatbot()
    print(chatbot.chat("đánh bài phạt bao nhiêu tiền?", {})["answer"])
