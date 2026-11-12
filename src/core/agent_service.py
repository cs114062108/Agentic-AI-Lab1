from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat import ChatCompletionToolUnionParam
from openai.types import ChatModel

import os
import json

from src.utils import Logger, RESULTS_DIR, load_instructions, load_courses, courses_as_text
from src.chats import ChatSession
from src.utils.definition import StudentProfile, ProfileData
from src.core.agent_toolbox import AgentToolbox

class AIService:
    __client: OpenAI | None
    __model_name: ChatModel | str
    __instructions: str
    __chat_sessions: dict[str, ChatSession]
    
    __student_profiles: dict[str, StudentProfile]
    __session_histories: dict[str, list[ChatCompletionMessageParam]]
    
    __tool_schemas: list[ChatCompletionToolUnionParam]
    
    def __init__(self):
        self.__chat_sessions = {}
        self.__model_name = os.getenv("LLM_MODEL", "qwen2.5:3b")
        
        # Instructions & Course Catalog
        instructions = load_instructions()
        instructions += "\n\n"
        
        courses = load_courses()
        catalog = courses_as_text(courses)
        
        instructions += "## Course Catalog\n\n"
        instructions += catalog
        
        self.__instructions = instructions
        
        # Profiles
        self.__student_profiles = {}
        
        # Histories
        self.__session_histories = {}
        self.load_all_histories()
        
        # Tools
        self.__tool_schemas = AgentToolbox.tool_schemas
        
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
            
            # Pass profile to session
            profile = self.__student_profiles.setdefault(user_name, StudentProfile())
            
            self.__chat_sessions[user_name] = ChatSession(
                self.__client, self.__model_name, 
                instructions=self.__instructions, 
                user_name=user_name,
                histories=prev_histories,
                tool_schemas=self.__tool_schemas,
                student_profile=profile
            )
            Logger.info(f"Created new chat session for user '{user_name}' with model [{self.__model_name}].")
        
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
    
    def reset_user(self, user_name: str, auto_save = True):
        self.clear_chat_histories(user_name, auto_save=False)
        
        if user_name in self.__student_profiles:
            self.__student_profiles[user_name].reset()
            Logger.info(f"Profile reseted for user '{user_name}'")
        
        if auto_save:
            self.save_all_histories()
    
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
    
    def get_user_profile(self, user_name: str) -> ProfileData:
        if user_name in self.__student_profiles:
            return self.__student_profiles[user_name].to_dict()
        
        Logger.info(f"No profile found for user '{user_name}'")
        return {}
    
    # --- Save to json file and load ---
    def save_chat_histories(self, user_name: str, file_name: str):
        if not file_name:
            Logger.warning("File name is empty")
            return
        
        if not file_name.endswith(".json"):
            file_name += ".json"
        
        histories = self.get_chat_histories(user_name)
        if not histories:
            Logger.info(f"Chat history for user '{user_name}' is empty or not found, don't save")
            return
        
        dat: dict[str, object] = {}
        dat["model_name"] = self.__model_name
        dat["instructions"] = self.__instructions
        dat["user_name"] = user_name
        dat["histories"] = histories
        
        profile = self.__student_profiles.get(user_name)
        profile_dat: ProfileData = {}
        if profile:
            profile_dat = profile.to_dict()
        else:
            Logger.info(f"No profile for user '{user_name}'")
        dat["profile"] = profile_dat
        
        json_path = RESULTS_DIR / file_name
        with json_path.open("w", encoding="utf-8") as file:
            json.dump(dat, file, indent=2, ensure_ascii=False)
            
        Logger.info(f"Chat history for user '{user_name}' with model [{self.__model_name}] saved to file '{file_name}'")
    
    def save_all_histories(self):
        dat: dict[str, object] = {}
        dat["model_name"] = self.__model_name
        dat["instructions"] = self.__instructions
        
        session_histories: dict[str, list[ChatCompletionMessageParam]] = {}
        for user_name, chat_session in self.__chat_sessions.items():
            session_histories[user_name] = chat_session.histories
        dat["histories"] = session_histories
        
        self.__session_histories = session_histories
        
        profile_dats: dict[str, ProfileData] = {}
        for user_name, profile in self.__student_profiles.items():
            profile_dats[user_name] = profile.to_dict()
        dat["profiles"] = profile_dats
        
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
        
        profile_dats: dict[str, ProfileData] = dat.get("profiles", {})
        self.__student_profiles = {
            user_name: StudentProfile.from_dict(profile_dat)
            for user_name, profile_dat in profile_dats.items()
        }


AgentService = AIService()
