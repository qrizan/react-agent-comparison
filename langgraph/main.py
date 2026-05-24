import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from assistant import build_assistant
from config import QUESTION
from langchain_core.messages import HumanMessage
from utils import print_message

if __name__ == "__main__":
    restaurant_assistant = build_assistant("gpt-4o")
    user_message = HumanMessage(QUESTION)
    print_message(user_message)

    for chunk in restaurant_assistant.stream({"messages": [user_message]}):
        for _, values in chunk.items():
            for message in values.get("messages", []):
                print_message(message)
