from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat import ChatCompletionMessage
from openai.types.chat import ChatCompletionToolUnionParam
from openai.types import ChatModel

from src.utils import Logger
from src.core.agent_toolbox import AgentToolbox

class ChatSession:
    __client: OpenAI
    __model_name: ChatModel | str
    __instructions: str | None = None
    __user_name: str | None = None
    __init_histories: list[ChatCompletionMessageParam]
    __histories: list[ChatCompletionMessageParam]
    
    __tool_schemas: list[ChatCompletionToolUnionParam]
    
    def __init__(
        self, client: OpenAI, model_name: ChatModel | str, 
        instructions: str | None = None, 
        user_name: str | None = None,
        histories: list[ChatCompletionMessageParam] | None = None,
        tool_schemas: list[ChatCompletionToolUnionParam] | None = None
    ):
        self.__client = client
        self.__model_name = model_name
        self.__instructions = instructions
        self.__user_name = user_name
        
        self.__tool_schemas = list(tool_schemas) if tool_schemas is not None else []
        
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
    def histories(self) -> list[ChatCompletionMessageParam]:
        return self.__histories.copy()
    
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
                succeeded, result = AgentToolbox.process_tool(name, args_text)
                histories.append({"role": "tool", "tool_call_id": call.id, "content": result})
            
            tool_executed = True
        
        return tool_executed
    
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
        
        Logger.info("The AI is thinking...")
        
        try:
            # Limit the tool calling rounds
            max_tool_rounds = 5
            
            for _ in range(max_tool_rounds + 1):
                response = self.__client.chat.completions.create(
                    model=self.__model_name,
                    messages=histories,
                    temperature=0,
                    max_tokens=512,
                    stream=False,
                    tools=self.__tool_schemas, tool_choice="auto"
                )
                
                choice = response.choices[0]
                response_message = choice.message
                
                if response_message.tool_calls:
                    self.handle_tool_call(response_message, histories)
                    continue
                
                Logger.info("The AI responded!")
                Logger.info(f"Finish Reason: {choice.finish_reason}")
                Logger.info(f"Completion Tokens: {response.usage.completion_tokens}")
                    
                if choice.finish_reason == "length":
                    Logger.warning("AI response was truncated due to token limit.")
            
                # Add the AI's respones to the histories
                histories.append(response_message.model_dump(exclude_none=True))
                
                # Copy back the histories if succeeded
                self.__histories = histories[:]
                del histories
                
                return response_message.content or ""
            
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
