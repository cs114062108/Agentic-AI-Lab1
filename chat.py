from __future__ import annotations

from src.core.agent_service import AgentService
from src.utils import Logger

from dotenv import load_dotenv
import os
import json

# ANSI color codes
_COLORS = {
    "CYAN": "\033[36m",  # cyan
    "GREEN": "\033[32m",  # green
    "YELLOW": "\033[33m",  # yellow
    "RED": "\033[31m",  # red
    "BLUE": "\033[34m", # blue
    "RESET": "\033[0m",
}
RESET = _COLORS["RESET"]
CYAN = _COLORS["CYAN"]
GREEN = _COLORS["GREEN"]
YELLOW = _COLORS["YELLOW"]
RED = _COLORS["RED"]
BLUE = _COLORS["BLUE"]

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
                    print(f"{CYAN}Histories Retrieved:{RESET}")
                    histories_text = json.dumps(histories, indent=2, ensure_ascii=False)
                    print(histories_text)
                elif message == "!save":
                    file_name = input(f"{YELLOW}Enter File Name: {RESET}").strip()
                    AgentService.save_chat_histories(user_name, file_name)
                elif message == "!clear":
                    cleared = AgentService.clear_chat_histories(user_name)
                    if cleared:
                        print(f"{GREEN}Histories Cleared and Reseted!{RESET}")
                    else:
                        print(f"{RED}History is already empty!{RESET}")
            else:
                response = AgentService.chat_engage(user_name, message)
                print(response)
        Logger.info("---Test End---")
    except (KeyboardInterrupt, EOFError):
        Logger.info("---Test Interrupted---")
    

if __name__ == "__main__":
    raise SystemExit(main())
