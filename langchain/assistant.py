import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from datetime import date

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from tools import (
    make_reservation,
    calculate_bill_estimate,
    get_weather,
    query_restaurants,
    web_search,
)

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


def build_assistant(model: str = "gpt-4o"):
    """Bangun restaurant assistant dengan model yang dipilih."""
    llm = init_chat_model(model=model, model_provider="openai")

    return create_react_agent(
        model=llm,
        tools=all_tools,
        prompt=SystemMessage(content=system_prompt),
    )


if __name__ == "__main__":
    restaurant_assistant = build_assistant("gpt-4o")
