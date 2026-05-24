import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from datetime import date
from typing import Annotated

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from tools import (
    make_reservation,
    calculate_bill_estimate,
    get_weather,
    query_restaurants,
    web_search,
)
from typing_extensions import TypedDict

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

all_tools = [
    query_restaurants,
    calculate_bill_estimate,
    get_weather,
    make_reservation,
    web_search,
]

with open(os.path.join(os.path.dirname(__file__), "../shared/prompt.md")) as f:
    system_prompt = f.read().format(today=date.today().isoformat())


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_assistant(model: str = "gpt-4o"):
    """Bangun restaurant assistant dengan model yang dipilih."""
    llm = init_chat_model(model=model, model_provider="openai")
    llm_with_tools = llm.bind_tools(all_tools)
    system_message = SystemMessage(content=system_prompt)

    def reason(state: State) -> dict:
        messages = [system_message] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    act = ToolNode(all_tools)

    builder = StateGraph(State)
    builder.add_node("reason", reason)
    builder.add_node("act", act)
    builder.add_edge(START, "reason")
    builder.add_conditional_edges("reason", tools_condition, {"tools": "act", END: END})
    builder.add_edge("act", "reason")

    return builder.compile()


if __name__ == "__main__":
    restaurant_assistant = build_assistant("gpt-4o")
