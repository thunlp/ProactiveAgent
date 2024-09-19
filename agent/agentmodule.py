'''
This file mainly focus on the implementation of the components of ActiveAgent(a.k.a. proactive agent in paper)
The components are as:
1. LLMClient: This component create a unified interface to generate response from different llm like openai/together/qwen
2. EventListener: This component is originally designed for receiving actions from users, in experiments it is used to load in an event trace only.
3. contextManager: This component is used to manage the context in an event trace, it contains the overall event trace and the proposal history to guide the generation.
4. Core: This component is used to let LLM finally generate content for given senario, with some additional functions to control the format of generation.
5. Trigger: This component is a design for interaction with the user. Though in experiment it is not used, we give a simple implementation by using tkinter. A more complete trigger is used in Restricted Agent.
'''

import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Literal, Union, Optional

Dialogue = List[Dict[str, str]]
API_MODE = Literal["openai","together","dashscope"]

from tenacity import retry, stop_after_attempt

from prompt import SYSTEM_PROMPT, USER_TEMPLATE



class LLMClient(object):
    """
    Give a unified interface to call any LLM.
    Now to support: openai, dashscope, together.
    """
    def __init__(self, 
                api_key   : str, 
                model_name: str, 
                base_url  : Optional[str] = None, 
                type      : API_MODE = "openai",
                **kwargs) -> None: 
        """
        initialization of the LLM Client.

        Args:
            api_key (str): The API key for the LLM.
            model_name (str): the model name of the LLM.
            base_url (str): The base url of the LLM (if any).
            type (str, optional): The interface used to call the LLM, now support openai/together/dashscope. Defaults to "openai".
            **kwargs: the other parameters used to control the LLM interface.
        """
        self.type      : str = type
        self.client    : Any = None
        self.model_name: str = model_name
        self.base_url  : str = base_url
        self.api_key   : str = api_key
        
        self.temperature:float = 0.0
        
        if type == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key = api_key, base_url = base_url, **kwargs)

        elif type == "together":
            from together import Together
            self.client = Together(api_key = api_key, base_url = base_url, **kwargs)
        
        elif type == "dashscope":
            # Dashscope does not require a client.
            pass
        
        else:
            raise NotImplementedError(f"LLM type {type} is not supported yet.")

    def get_name(self) -> str:
        return self.model_name
        
    def chatCompletion(self, messages:Union[Dialogue,str], **kwargs) -> str:
        """
        Given a prompt | dialogue, the function returns the direct response in string.
        If messages is a direct string, it will be transfer as [{role:user, content: message}]

        Args:
            messages (Dialogue|str): the prompt or the dialogue.
            **kwargs: the other parameters used to control the LLM interface.

        Returns:
            str: the direct response.
        """
        
        # Format the dialogue.
        if type(messages) == str:
            dialogue = [{"role": "user", "content": messages}]
        else:
            dialogue = messages

        if self.type == "openai":
            response = self.client.chat.completions.create(
            model = self.model_name,
            messages = dialogue,
            temperature=self.temperature,
            **kwargs)
            response = response.choices[0].message.content
            return response

        elif self.type == "together":
            response = self.client.chat.completions.create(
                model = self.model_name,
                messages = dialogue,
                temperature=self.temperature,
                **kwargs
            )
            return response.choices[0].message.content

        elif self.type == "dashscope":
            from dashscope import Generation
            responses = Generation.call(
                model = self.model_name,
                messages = dialogue,
                api_key = self.api_key,
                temperature = self.temperature,
                stream = False,
                **kwargs
            )
            return responses["output"]["text"]

class EventListener(object):
    '''
    This module is a basic component to receive events from outer environment.
    This class is the basic class, which only takes event in string format.

    Attributes:
    ---
    - events (list[dict]): the event series read from one file.

    Methods:
    ---
    addEvent: For a outer interface to add events.
    getEvent: get one event from the event series sequentially.
    '''
    
    def __init__(self, event_series:List[Any]|None = None) -> None:
        """
        Initialization of EventListener, listen from a complete list.

        Args:
            event_series (list[dict]) the origin event list.
        """
        
        self.events = []
        if event_series is not None:
            self.set_events(event_series)

    def set_events(self,event_series:List[Dict]):
        """
        set the event trace as input, and reset previous traces.
        
        Args:
            event_series (List[Any]): The event trace.
        """
        if type(event_series) != list:
            try:
                event_series = list(event_series)
            except:
                raise TypeError("The event series should be iterable.")

        self.events = event_series

    @classmethod
    def from_file(cls, file_path:str):
        """
        Initialization of EventListener, loading from a json file. Only support .json file.

        Args:
            file_path (str): the path of the file.
        """

        with open(file_path, 'r') as f:
            events = json.load(f)
        return cls(events)
    
    def add_event(self,event:Any):
        """
        add an event in the event series manually.

        Args:
            event (Any): the new event
        """
        self.events.append(event)

    def get_event(self) -> Any:
        """
        Get the event sequentially. the event will be removed from the event series.
            
        Returns:
            Any: the object to describe one single event.

        Raises:
            IndexError: when the event series is empty.
            Note that the agent use the raise to stop from an empty loop.
        """
        try:
            event = self.events.pop(0)
            return event
        except:
            raise IndexError("The event series is now empty.")

class ContextManager(object):
    '''
    ContextManager is used to store the conversation history now.
    The context manager is aim to restore the dialogue history between events input and the candidates out from the agent.
    
    Attributes
    ----------
    - event_sequence : list[dict]: all the turns for eventlistener and core response.
    A turn is a dict with two keys: "event" and "response".
    "event" if from user, and "response" is from the agent.

    Methods:
    ---
    - add_event(): add a event from the listener.
    - update_response(): update the response from the Core.
    - load_trace(): load the trace from the test data.
    - get_all_turns(): get all the turns.
    '''
    def __init__(self):
        self.event_turns = []

    def add_event(self,event:Any):
        """
        Add a single event from the listener.
        """
        
        new_turn = {
            "event": event,
            "response": None
        }
        
        self.event_turns.append(new_turn)
        
    def update_response(self,response:Any):
        """
        For each event, the response from the core will be updated.

        _extended_summary_

        Args:
            response (Any): The object to describe the agent's response.
        """
        if len(self.event_turns) == 0:
            raise IndexError("The event turns is empty, please add an event first.")
        
        if self.event_turns[-1].get("response", None) is not None:
            raise KeyError("The last event already has a response.")
        else:
            self.event_turns[-1]["response"] = response

    def load_trace(self, trace:List[Dict]):
        """
        This function is only used to load the trace from our test data.

        Args:
            trace (List[Dict]): the list load from out test data.
        """
        
        if self.event_turns != []:
            self.event_turns = []

        for turn in trace:
            self.add_event(json.dumps(turn["observation"]))
            self.update_response(f'I offered my assistance as:\n{turn["agent_response"]}')
        
    def get_all_turns(self) -> List[Dict]:
        """
        Return all the events observed and contained in context manager.

        Returns:
            List[Dict]: the current event trace
        """
        return self.event_turns
    
class Core(object):
    '''
    Core is mainly used to actually interact with the LLM from the active agent.

    Attributes
    ----------
    - client : LLMClient, the client used to interact with the LLM.
    - model_name : str, the name of the model to be used.
    - prompt_setting : str, the setting of the prompt.

    Methods:
    --------
    - reflect(): Based on the information given, raise an output.
    '''
    
    def __init__(self, client: LLMClient):
        """
        The initalization of the core components.

        Args:
            client (LLMClient): The client used to interact. 
        """
        self.client:LLMClient = client
    
    def generate_response(self, prompt:Union[str,List[Dict]]) -> str:
        
        return self.client.chatCompletion(prompt)
    
    def propose_candidates(self, messages: List[Dict]) -> Dict:
        """
        Get the candidate tasks from the agent.

        Args:
            event_turns: The event trace passed from the context manager.
            functions_list: The list of functions that the agent can use (by tool recall)

        Returns:
            dict: The result assmbles in a dict.
        """
        
        def format_answer(text:str) -> Dict:
            """
            extract content from the origin string.

            Args:
                text (str): the origin text.

            Returns:
                Dict: formatted json.
            """
            
            # get code block.
            lbrace, rbrace = text.find("```"), text.rfind("```")
            # strip lines.
            lines = text[lbrace+3:rbrace].strip().split('\n')    
            
            template_result = {
                "purpose":"",
                "profile":"",
                "need_help":"",
                "raise_query":"",
                "candidate_task":[]
            }
            
            # iterate lines to get content.
            for line in lines:
                if line.startswith("rpose"):
                    line = line.replace("rpose", "purpose")
                if line.startswith("purpose:"):
                    template_result["purpose"] = line[8:].strip()
                elif line.startswith("profile:"):
                    template_result["profile"] = line[8:].strip()
                elif line.startswith("need_help:"):
                    template_result["need_help"] = line[10:].strip()
                elif line.startswith("raise_query:"):
                    template_result["raise_query"] = line[12:].strip()
                elif line.startswith("candidate_task:"):
                    template_result["candidate_task"] = [line[15:].strip()]
                    if template_result["candidate_task"] == ['']:
                        template_result["candidate_task"] = []
                elif line == '':
                    continue
                else:
                    print('Invalid line in response: \n<{}>'.format(line))
            if 'no' in template_result["need_help"] or 'No' in template_result["need_help"]:
                template_result["candidate_task"] = []

            return template_result

        response = self.client.chatCompletion(messages)
        
        response_dict = format_answer(response)
        
        return response_dict
    
    def fix_response(self, response) -> str:
        """
        Fix the response(str), and make it into a JSON format(dict).
        Since the LLM may not generate as given format, we need further control.
        we simply cut the json part out, and for those who generate content as a list, we use key word finding to determine the part.
        ! will be deprecated in the future.

        Args:
            response (str):

        Returns:
            dict: The JSON format of the response.
        """
        old = response
        # print(response)
        idx_left = response.find('{')
        idx_right = response.find('}')
        
        if idx_left != -1 and idx_right != -1:
            response = response[idx_left:idx_right + 1]

        try:
            response = json.loads(response)
        except:
            raise Exception('Response is not in JSON format.')
        
        return response
    
    @retry(stop = stop_after_attempt(3),reraise=True)
    def reflect(self, event_turns:List[Dict]) -> Dict:
        """
        reflect the event_seq and give some output.

        Args:
            event_seq (list): the event information given, including the new event(with only observation)
            addition_infos (dict): the addition information given.
            proposed_history (list): the history of proposed task.

        Raises:
            Exception: when the response is not complete, used for retrying.

        Returns:
            dict: the output.
        """
        
        # Assemble a dialogue
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        for turn in event_turns[:-1]:
            messages.append({"role": "user", "content": turn["event"]})
            messages.append({"role": "assistant", "content": turn["response"]})

        functions_list = None

        # with all information given, we use core to reason if to offer help.
        messages.append(
            {"role": "user", 
            "content": USER_TEMPLATE.format(
                observation = event_turns[-1]["event"], tools = functions_list)
            })
        response_json = self.propose_candidates(messages=messages)

        return response_json
    
class Trigger(ABC):
    """
    A Trigger will be able to receive the content from the agent and pass it to the user.
    There are two main methods:
    - receive(): receive the content from the agent and store it.
    - send(): send the content to the user in a proper way.
    """
    
    @abstractmethod
    def receive(self, *args, **kwargs) -> None:
        """
        receive the content from the agent and store it.
        Args:
            infos (Any): information needed in any possible form.
        """
        pass
    
    @abstractmethod
    def send(self):
        """
        The action to send something from the agent to the user.
        """
        pass
