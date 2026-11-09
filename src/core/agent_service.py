from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types import ChatModel

import os
import json

from src.utils import Logger, RESULTS_DIR
from src.chats import ChatSession

class AIService:
    __client: OpenAI | None
    __model_name: ChatModel | str
    __instructions: str
    __chat_sessions: dict[str, ChatSession]
    
    __session_histories: dict[str, list[ChatCompletionMessageParam]]
    
    def __init__(self):
        self.__chat_sessions = {}
        self.__model_name = os.getenv("LLM_MODEL", "qwen2.5:3b")
        self.__instructions = "You are a helpful assistant. When detected Mandarin, please use Traditional Chinese to reply."
        
        self.__session_histories = {}
        self.load_all_histories()
        
        try:
            
            self.__client = OpenAI(
                base_url=os.getenv(
                    "LLM_BASE_URL", "http://127.0.0.1:8000/v1"
                ),
                api_key=os.getenv("LLM_API_KEY", "classroom-internal"),
                timeout=float(os.getenv("LLM_TIMEOUT", "120")),
                max_retries=0,
            )
        except Exception as err:
            Logger.warning("Failed instantiating AI client")
            Logger.warning(f"{err.__class__.__name__}: {err}")
            self.__client = None
    
    # --- Chat Engage API ---
    def get_chat_session(self, user_name: str) -> ChatSession:
        if user_name not in self.__chat_sessions:
            prev_histories = self.__session_histories.get(user_name, [])
            if prev_histories:
                Logger.info(f"Previous history for user '{user_name}' found.")
            
            self.__chat_sessions[user_name] = ChatSession(
                self.__client, self.__model_name, 
                instructions=self.__instructions, 
                user_name=user_name,
                histories=prev_histories
            )
            Logger.info(f"Created new chat session for user '{user_name}'.")
        
        return self.__chat_sessions[user_name]
    
    def chat_engage(self, user_name: str, prompt: str, auto_save = True) -> str:
        chat_session = self.get_chat_session(user_name)
        respond = chat_session.send_chat(prompt)
        if respond:
            if auto_save:
                self.save_all_histories()
            return respond
        else:
            return "❌ Some error occured when calling the AI. Please check the log message."
    
    def clear_chat_histories(self, user_name: str, auto_save = True) -> bool:
        if user_name in self.__chat_sessions:
            cleared = self.__chat_sessions[user_name].clear()
            if cleared:
                Logger.info(f"Chat session cleared for user '{user_name}'")
            else:
                Logger.info(f"Chat session for user '{user_name}' is empty")
            
            if auto_save:
                self.save_all_histories()
                
            return cleared
        
        if user_name in self.__session_histories:
            cleared = False
            if self.__session_histories[user_name]:
                self.__session_histories[user_name].clear()
                cleared = True
            
            if auto_save:
                self.save_all_histories()
            
            return cleared
            
        return False
    
    # --- Chat History ---
    def get_chat_histories(self, user_name: str) -> list[ChatCompletionMessageParam]:
        if user_name in self.__chat_sessions:
            return self.__chat_sessions[user_name].histories
        
        if user_name in self.__session_histories:
            return self.__session_histories[user_name]
        
        Logger.info(f"No recent chat histories found for user '{user_name}'")
        return []
    
    # --- Save to json file and load ---
    def save_all_histories(self):
        dat: dict[str, object] = {}
        dat["model_name"] = self.__model_name
        dat["instructions"] = self.__instructions
        
        session_histories: dict[str, list[ChatCompletionMessageParam]] = {}
        for user_name, chat_session in self.__chat_sessions.items():
            session_histories[user_name] = chat_session.histories
        dat["histories"] = session_histories
        
        self.__session_histories = session_histories
        
        json_path = RESULTS_DIR / "histories.json"
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(dat, file, indent=2, ensure_ascii=False)
    
    def load_all_histories(self):
        dat: dict[str, object] = {}
        
        json_path = RESULTS_DIR / "histories.json"
        if os.path.exists(json_path):
            Logger.info("Previous histories exists, load it")
            with json_path.open("r", encoding="utf-8") as file:
                dat = json.load(file)
        
        self.__session_histories = dat.get("histories", {})


AgentService = AIService()
