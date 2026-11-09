from __future__ import annotations

from src.core.agent_service import AgentService
from src.utils import Logger

from dotenv import load_dotenv
import os
import json

load_dotenv()

def main() -> int:
    Logger.info("---Start Test---")

    test_user_name = "Test User"
    user_name = os.getenv("USER_NAME", "")
    if not user_name:
        user_name = input("Enter user name: ").strip()
    if not user_name:
        user_name = test_user_name
    
    try:
        while True:
            message = input(">> ")
            if message.startswith("!"):
                if message == "!exit":
                    break
                elif message == "!history":
                    histories = AgentService.get_chat_histories(user_name)
                    print("Histories Retrieved:")
                    histories_text = json.dumps(histories, indent=2, ensure_ascii=False)
                    print(histories_text)
                elif message == "!clear":
                    cleared = AgentService.clear_chat_histories(user_name)
                    if cleared:
                        print("Histories Cleared and Reseted!")
                    else:
                        print("History is already empty!")
            else:
                response = AgentService.chat_engage(user_name, message)
                print(response)
        Logger.info("---Test End---")
    except (KeyboardInterrupt, EOFError):
        Logger.info("---Test Interrupted---")
    

if __name__ == "__main__":
    raise SystemExit(main())
