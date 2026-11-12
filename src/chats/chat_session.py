from __future__ import annotations

import json
from copy import deepcopy

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat import ChatCompletionMessage
from openai.types.chat import ChatCompletionToolUnionParam
from openai.types import ChatModel

from src.utils.definition import StudentProfile, ConversationMode, ToolType
from src.utils.tool_utils import generate_schema

from src.utils import Logger
from src.core.agent_toolbox import AgentToolbox

class ChatSession:
    __client: OpenAI
    __model_name: ChatModel | str
    __instructions: str | None = None
    __user_name: str | None = None
    __init_histories: list[ChatCompletionMessageParam]
    __histories: list[ChatCompletionMessageParam]
    
    __student_profile: StudentProfile
    
    __tool_schemas: list[ChatCompletionToolUnionParam]
    
    def __init__(
        self, client: OpenAI, model_name: ChatModel | str, 
        instructions: str | None = None, 
        user_name: str | None = None,
        histories: list[ChatCompletionMessageParam] | None = None,
        tool_schemas: list[ChatCompletionToolUnionParam] | None = None,
        student_profile: StudentProfile | None = None
    ):
        self.__client = client
        self.__model_name = model_name
        self.__instructions = instructions
        self.__user_name = user_name
        
        # Tool Schemas
        self.__tool_schemas = list(tool_schemas) if tool_schemas is not None else []
        
        # Student Profile
        self.__student_profile = student_profile if student_profile is not None else StudentProfile()
        
        # Histories
        self.__init_histories = []
        if self.__instructions:
            self.__init_histories.append(
                {"role": "system", "content": self.__instructions}
            )
        if self.__user_name:
            self.__init_histories.append(
                {"role": "system", "content": f"The name of the user is '{self.__user_name}'. You can call the user by his or her name."}
            )
        
        self.__histories = list(histories) if histories is not None else []
        if not self.__histories:
            Logger.info(f"Initializing chat session history for user '{user_name}'")
            self.__histories.extend(self.__init_histories)

    def set_model_name(self, model_name: ChatModel | str):
        self.__model_name = model_name
    
    @property
    def student_profile(self) -> StudentProfile:
        return self.__student_profile
    
    def get_conversation_mode(self) -> ConversationMode:
        if self.__student_profile.is_ready:
            return "planning"
        
        return "gathering"
    
    @property
    def histories(self) -> list[ChatCompletionMessageParam]:
        return self.__histories.copy()

    def update_student_profile(
        self, 
        department: str | None = None, 
        year: int | None = None, 
        completed_courses: list[str] | None = None,
        interests: list[str] | None = None,
        min_credits: int | None = None, 
        max_credits: int | None = None
    ) -> str:
        """
        Update the student's profile using information explicitly 
        provided by the student. Only include fields that are known. 
        Do not guess missing information.
        """
        try:
            prev = self.__student_profile.to_dict()
            
            if department is not None:
                self.__student_profile.department = department
            if year is not None:
                self.__student_profile.year = year
            if completed_courses is not None:
                self.__student_profile.completed_courses = completed_courses.copy()
            if interests is not None:
                self.__student_profile.interests = interests.copy()
                
            if min_credits is not None:
                self.__student_profile.min_credits = min_credits
            if max_credits is not None:
                self.__student_profile.max_credits = max_credits
                
            now = self.__student_profile.to_dict()
            updated = prev != now
            
            if updated:
                result = f"Successfully updated the profile of '{self.__user_name}'"
            else:
                result = f"Nothing is updated for '{self.__user_name}'"
            
            Logger.info("[Profile] " + result)
            return result
        except Exception as err:
            result = f"Failed editing the profile of '{self.__user_name}'"
            Logger.warning("[Profile]" + result)
            Logger.warning(f"[Profile] {err.__class__.__name__}: {err}")
            return result
    
    def get_additional_tools(self) -> dict[str, ToolType]:
        tools = {self.update_student_profile.__name__: self.update_student_profile}
        return tools
    
    def get_additional_tools_schemas(self) -> list[ChatCompletionToolUnionParam]:
        tools = [self.update_student_profile]
        tools_schemas = [generate_schema(tool) for tool in tools]
        return tools_schemas
    
    def print_additional_tools_schemas(self):
        tools_schemas = self.get_additional_tools_schemas()
        tools_schemas_text = json.dumps(tools_schemas, indent=2, ensure_ascii=False)
        print(tools_schemas_text)
    
    def handle_tool_call(
        self, message: ChatCompletionMessage,
        histories: list[ChatCompletionMessageParam]
    ) -> bool:
        
        tool_executed = False
        if message.tool_calls:
            histories.append(message.model_dump(exclude_none=True))
            
            for call in message.tool_calls:
                name = call.function.name
                args_text = call.function.arguments
                tools = self.get_additional_tools()
                succeeded, result = AgentToolbox.process_tool(name, args_text, additional_tools=tools)
                histories.append({"role": "tool", "tool_call_id": call.id, "content": result})
            
            tool_executed = True
        
        return tool_executed
    
    def _build_messages(
        self,
        histories: list[ChatCompletionMessageParam]
    ) -> list[ChatCompletionMessageParam]:

        messages = histories.copy()

        mode = self.get_conversation_mode()
        profile_data = json.dumps(
            self.__student_profile.to_dict(),
            ensure_ascii=False
        )

        if mode == "gathering":
            state_instruction = (
                f"CONVERSATION MODE: {mode}\n"
                "Collect the missing student information through conversation. "
                "Use update_student_profile when the student provides information. "
                "Do not recommend courses yet. "
                f"Missing fields: {self.__student_profile.missing_fields()}"
            )
        else:
            state_instruction = (
                f"CONVERSATION MODE: {mode}\n"
                "The student profile is complete. You may now search and "
                "recommend courses using the available tools."
            )

        state_message: ChatCompletionMessageParam = {
            "role": "system",
            "content": (
                f"{state_instruction}\n"
                f"Current student profile: {profile_data}"
            )
        }

        state_str = json.dumps(state_message, indent=2, ensure_ascii=False)
        print(state_str)
        
        # Place dynamic state before the conversation content to avoid the cumulative repetition of system messages in each turn.
        insert_at = next(
            (
                i for i, message in enumerate(messages)
                if message.get("role") != "system"
            ),
            len(messages)
        )

        messages.insert(insert_at, state_message)
        """
        msg_str = json.dumps(messages, indent=2, ensure_ascii=False)
        print(msg_str)
        """

        return messages
    
    def _restore_profile(self, snapshot: StudentProfile):
        # Preserve the identity of the original StudentProfile object,
        # since AIService also holds a reference to the same object.
        for field in snapshot.__dataclass_fields__:
            setattr(
                self.__student_profile,
                field,
                deepcopy(getattr(snapshot, field))
            )
    
    def send_chat(self, prompt: str) -> str | None:
        """Engage chat with the AI in a continuous chat session

        Args:
            prompt (str): The prompt

        Returns:
            str | None: The chat response text if success, else None
        """
        # Make a copy of the histories when prompting
        histories = self.__histories.copy()
        histories.append({"role": "user", "content": prompt})
        
        # Back up the profile to ensure it can be restored in the event of a failure or truncation during this run
        profile_snapshot = deepcopy(self.__student_profile)
        
        Logger.info("The AI is thinking...")
        
        try:
            # Limit the tool calling rounds
            max_tool_rounds = 5
            
            # Entended Profile Tool
            extended_schemas = self.get_additional_tools_schemas()
            tool_schemas = []
            tool_schemas.extend(self.__tool_schemas)
            tool_schemas.extend(extended_schemas)
            
            # Accumulate content from all assistant responses
            response_contents: list[str] = []
            
            for _ in range(max_tool_rounds + 1):
                
                response = self.__client.chat.completions.create(
                    model=self.__model_name,
                    messages=self._build_messages(histories),
                    temperature=0.3,
                    max_tokens=2048,
                    stream=False,
                    tools=tool_schemas, tool_choice="auto"
                )
                
                choice = response.choices[0]
                response_message = choice.message
                
                Logger.info("The AI responded!")
                Logger.info(f"Finish Reason: {choice.finish_reason}")
                Logger.info(f"Completion Tokens: {response.usage.completion_tokens}")
                    
                # When truncated, no tools are executed, and the results of the current round are not saved.
                if choice.finish_reason == "length":
                    Logger.warning("AI response was truncated due to token limit.")
                    self._restore_profile(profile_snapshot)
                    return None
                
                # Collect content even when tool_calls exist
                if response_message.content:
                    response_contents.append(response_message.content)
                
                # Handle tool calls
                if response_message.tool_calls:
                    self.handle_tool_call(response_message, histories)
                    continue
            
                # Add the AI's respones to the histories
                histories.append(response_message.model_dump(exclude_none=True))
                
                # Copy back the histories if succeeded
                self.__histories = histories.copy()
                del histories
                
                return "\n".join(response_contents) or ""
            
            raise RuntimeError("Maximum tool calling rounds exceeded")
            
        except Exception as err:
            Logger.warning("Chat API Error")
            Logger.warning(f"{err.__class__.__name__}: {err}")
            return None
    
    def clear(self) -> bool:
        """Clears and re-initiates the chat history of the chat session"""
        if self.__histories:
            self.__histories.clear()
            self.__histories.extend(self.__init_histories)
            return True
        
        return False


if __name__ == "__main__":
    chat = ChatSession(client=None, model_name="classroom-llm", user_name="Test")
    chat.print_additional_tools_schemas()
