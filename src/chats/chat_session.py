from __future__ import annotations

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types import ChatModel

from src.utils import Logger

class ChatSession:
    __client: OpenAI
    __model_name: ChatModel | str
    __instructions: str | None = None
    __user_name: str | None = None
    __init_histories: list[ChatCompletionMessageParam]
    __histories: list[ChatCompletionMessageParam]
    
    def __init__(self, client: OpenAI, model_name: ChatModel | str, 
                 instructions: str | None = None, 
                 user_name: str | None = None,
                 histories: list[ChatCompletionMessageParam] = []):
        self.__client = client
        self.__model_name = model_name
        self.__instructions = instructions
        self.__user_name = user_name
        
        self.__init_histories = []
        if self.__instructions:
            self.__init_histories.append(
                {"role": "system", "content": self.__instructions}
            )
        if self.__user_name:
            self.__init_histories.append(
                {"role": "system", "content": f"The name of the user is '{self.__user_name}'. You can call the user by his or her name."}
            )
        
        self.__histories = histories
        if not self.__histories:
            Logger.info(f"Initializing chat session history for user '{user_name}'")
            self.__histories.extend(self.__init_histories)

    def set_model_name(self, model_name: ChatModel | str):
        self.__model_name = model_name
    
    @property
    def histories(self) -> list[ChatCompletionMessageParam]:
        return self.__histories.copy()
    
    def send_chat(self, prompt: str) -> str | None:
        """Engage chat with the AI in a continuous chat session

        Args:
            prompt (str): The prompt

        Returns:
            str | None: The chat response text if success, else None
        """
        # Make a copy of the histories when prompting
        histories = self.__histories[:]
        histories.append({"role": "user", "content": prompt})
        
        Logger.info("The AI is thinking...")
        
        try:
            response = self.__client.chat.completions.create(
                model=self.__model_name,
                messages=histories,
                temperature=0,
                max_tokens=512,
                stream=False,
            )
            
            response_message = response.choices[0].message
            choice = response.choices[0]
            
            Logger.info("The AI responded!")
            Logger.info(f"Finish Reason: {choice.finish_reason}")
            Logger.info(f"Completion Tokens: {response.usage.completion_tokens}")
                
            if choice.finish_reason == "length":
                Logger.warning("AI response was truncated due to token limit.")
        except Exception as err:
            Logger.warning("Chat API Error")
            Logger.warning(f"{err.__class__.__name__}: {err}")
            return None
        
        # Add the AI's respones to the histories
        histories.append(response_message.model_dump(exclude_none=True))
        
        # Copy back the histories if succeeded
        self.__histories = histories[:]
        del histories
        
        return response_message.content
    
    def clear(self) -> bool:
        """Clears and re-initiates the chat history of the chat session"""
        if self.__histories:
            self.__histories.clear()
            self.__histories.extend(self.__init_histories)
            return True
        
        return False
