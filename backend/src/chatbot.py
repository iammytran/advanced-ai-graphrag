import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from backend.src.graphrag import rag_retrieval

load_dotenv()


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class Chatbot:
    
    def __init__(self):
        self.message_history: list[BaseMessage] = []
        self.graph = self._build_graph()
        tools = [rag_retrieval]
        self.model_with_tools = self.llm.bind_tools(tools)
    
    # GRAPH NODES
    ## LOGIC NODE 
    def LogicNode(self, state: State) -> State:
        messages = state["messages"]
        response = self.model_with_tools.invoke(messages)
        
        if hasattr(response, 'tool_calls') and response.tool_calls:
            state["messages"].append(response)
            
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_input = tool_call.get("args", {})
                
                if tool_name == "rag_retrieval":
                    tool_result = rag_retrieval.invoke(tool_input)
                    
                    tool_message = ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call.get("id", ""),
                        name=tool_name
                    )
                    state["messages"].append(tool_message)
            
            final_response = self.model_with_tools.invoke(state["messages"])
            state["messages"].append(final_response)
        else:
            state["messages"].append(response)
        
        return state

    # GRAPH BUILDING
    def build_graph(self) -> StateGraph:
        graph = StateGraph(State)
        graph.add_node("process", self.LogicNode)
        graph.add_edge("process", END)
        return graph.compile()
    
    # CHAT
    def chat(self, user_input: str) -> str:
        human_message = HumanMessage(content=user_input)
        self.message_history.append(human_message)

        state = State(messages=self.message_history)

        output_state = self.graph.invoke(state)

        self.message_history = output_state["messages"]
        
        for message in reversed(self.message_history):
            if isinstance(message, AIMessage):
                return message.content
        
        return "No response generated"
