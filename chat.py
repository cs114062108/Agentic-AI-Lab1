from __future__ import annotations

from typing import Callable

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
    
    Logger.info(f"Current user: {user_name}")

    check_command: Callable[[str, str], bool] = lambda msg, cmd: (msg == cmd) or msg.startswith(f"{cmd} ")
    
    try:
        while True:
            message = input(">> ")
            if message.startswith("!"):
                message = message[1:]
                if check_command(message, "exit"):
                    break
                elif check_command(message, "history"):
                    histories = AgentService.get_chat_histories(user_name)
                    print(f"{CYAN}Histories Retrieved:{RESET}")
                    histories_text = json.dumps(histories, indent=2, ensure_ascii=False)
                    print(histories_text)
                elif check_command(message, "profile"):
                    profile = AgentService.get_user_profile(user_name)
                    print(f"{CYAN}Profile Retrieved:{RESET}")
                    profile_text = json.dumps(profile, indent=2, ensure_ascii=False)
                    print(profile_text)
                elif check_command(message, "save"):
                    file_name = input(f"{YELLOW}Enter File Name: {RESET}").strip()
                    AgentService.save_chat_histories(user_name, file_name)
                elif check_command(message, "clear"):
                    cleared = AgentService.clear_chat_histories(user_name)
                    if cleared:
                        print(f"{GREEN}Histories Cleared and Reseted!{RESET}")
                    else:
                        print(f"{RED}History is already empty!{RESET}")
                elif check_command(message, "reset"):
                    AgentService.reset_user(user_name)
                    print(f"{GREEN}Histories and Profile Reseted!{RESET}")
                else:
                    splited = message.split()
                    print(
                        f"{RED}The {BLUE}command {YELLOW}'{splited[0] if splited else message}' {RED}is not defined!{RESET}"
                    )
            else:
                response = AgentService.chat_engage(user_name, message)
                print(response)
        Logger.info("---Test End---")
    except (KeyboardInterrupt, EOFError):
        Logger.info("---Test Interrupted---")
    

if __name__ == "__main__":
    raise SystemExit(main())
