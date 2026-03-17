from typing import Annotated, TypedDict

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages import BaseMessage
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from backend.config.config import (
    HUGGINGFACE_MODEL,
    OPENAI_API_KEY,
    OPENAI_ENDPOINT,
    OPENAI_MODEL,
    TEMPERATURE,
)
from backend.src.prompts import AGENT_SYSTEM_PROMPT
from backend.tools.graphrag import format_graphrag_documents, graphrag_retrieval
from backend.tools.rag import rag_retrieval, retrieve_rag_documents


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    options_dict: dict
    retrieved_documents: list[str]


class Chatbot:

    DEFAULT_ARTIFACT_FOLDER = "artifacts"

    def __init__(self, model_option: int = 1, retrieval_mode: str = "auto"):
        """
        Initialize Chatbot with a specific model.
        :param model_option: 1 for HuggingFace, 2 for OpenAI
        :param retrieval_mode: "auto" | "rag_only" | "graphrag_only"
        """
        self.message_history: list[BaseMessage] = []
        self.graph = self.build_graph()
        if retrieval_mode == "auto":
            tools = [rag_retrieval, graphrag_retrieval]
        elif retrieval_mode == "rag_only":
            tools = [rag_retrieval]
        elif retrieval_mode == "graphrag_only":
            tools = [graphrag_retrieval]
        else:
            raise ValueError(
                "Invalid retrieval_mode. Use 'auto', 'rag_only', or 'graphrag_only'."
            )

        if model_option == 1:
            llm = HuggingFacePipeline.from_model_id(
                model_id=HUGGINGFACE_MODEL,
                task="text-generation",
                pipeline_kwargs={
                    "max_new_tokens": 2500,
                    "temperature": TEMPERATURE,
                    "do_sample": True,
                },
            )
            self.llm = ChatHuggingFace(llm=llm)
        elif model_option == 2:
            self.llm = ChatOpenAI(
                # base_url="https://openrouter.ai/api/v1",
                model=OPENAI_MODEL,
                max_completion_tokens=1000,
                temperature=float(TEMPERATURE),
            )
        else:
            raise ValueError(
                "Invalid model_option. Use 1 for HuggingFace or 2 for OpenAI."
            )
        
        self.model_with_tools = self.llm.bind_tools(tools)

    # GRAPH NODES
    ## LOGIC NODE
    def LogicNode(self, state: State) -> State:
        messages = state["messages"]
        options_dict = state.get("options_dict", {})
        state.setdefault("retrieved_documents", [])

        output_folder = options_dict.get("output_folder") or options_dict.get(
            "outputFolder"
        )
        if not output_folder:
            output_folder = self.DEFAULT_ARTIFACT_FOLDER

        if not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + messages

        response = self.model_with_tools.invoke(messages)

        if hasattr(response, "tool_calls") and response.tool_calls:
            state["messages"].append(response)

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("args", {}) or {}

                if not isinstance(tool_input, dict):
                    tool_input = {"query": str(tool_input)}

                if tool_name == "rag_retrieval":
                    retrieved_documents = retrieve_rag_documents(
                        tool_input.get("query", "")
                    )
                    state["retrieved_documents"] = retrieved_documents
                    tool_result = rag_retrieval.invoke(tool_input)

                    tool_message = ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call.get("id", ""),
                        name=tool_name,
                    )
                    state["messages"].append(tool_message)
                elif tool_name == "graphrag_retrieval":
                    tool_input["output_folder"] = output_folder
                    retrieved_documents = graphrag_retrieval.invoke(tool_input)  # returns list[str]
                    state["retrieved_documents"] = retrieved_documents
                    tool_result = format_graphrag_documents(retrieved_documents)
                    if not retrieved_documents:
                        tool_result = "Không tìm thấy thông tin phù hợp trong GraphRAG."

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
    def chat(self, user_input: str, options_dict: dict = None) -> dict:
        if options_dict is None:
            options_dict = {}

        human_message = HumanMessage(content=user_input)
        self.message_history.append(human_message)

        state = State(
            messages=self.message_history,
            options_dict=options_dict,
            retrieved_documents=[],
        )

        output_state = self.graph.invoke(state)

        self.message_history = output_state["messages"]

        answer = "No response generated"
        for message in reversed(self.message_history):
            if isinstance(message, AIMessage):
                answer = message.content
                break

        return {
            "answer": answer,
            "retrieved_documents": output_state.get("retrieved_documents", []),
        }


if __name__ == "__main__":
    # Choose 1 for HuggingFace, 2 for OpenAI
    chatbot = Chatbot(model_option=2, retrieval_mode="graphrag_only")
    response = chatbot.chat("đánh bài phạt bao nhiêu tiền?")
    print(f"response: {response}")
