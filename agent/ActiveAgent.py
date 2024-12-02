'''
This file gives a overall framework and pipeline for the active agent implementation.
All components desigend is done in `agentmodule.py`, refer to the file for details of designing.
'''
import json
from typing import List,Dict,Tuple, Any


from codelinker import CodeLinkerConfig
cfg_file = "../private.toml"

codelinker_config = CodeLinkerConfig.from_toml(cfg_file)
model_name = codelinker_config.request.default_completions_model
config = codelinker_config.get_apiconfig_by_model(model_name)


from agentmodule import (EventListener, ContextManager, Trigger, Core, LLMClient)

VERBOSE = True

class ActiveAgent(object):
    """
    This is the simple implementation for the active agent.
    Attributes:
    ---
    - `eventListner`(EventListener): the event listener for the agent. used to get events from outside.
    - `contextManager`(ContextManager): to store necessary informations for the agent.
    - `trigger`(Trigger): to make interactions with the user.
    - `core`(Core): the core of the agent, and the module to make proposals.
    - `intensity`(int): control the frequency of the propose (1 - 3: most - least).
    - `task_num`(int): determine the number of the task number.
    Methods:
    ---
    - `initEventListener`(events)->None: initialize the event listener by some events.
    - `runSingleStep`(addition_infos = None, need_user = True)->dict,str: run the agent for one step. i.e. give an event to the agent, and get a propose.
    - `run`(events)->None: run the agent for a whole conversation.
    """
    def __init__(self,client: LLMClient) -> None:
        """
        Args:
            client (OpenAI): the API for gpt.
            model_name (str): the model name of the gpt.
            prompt_settings (str, optional): the initial prompt for the agent. Defaults to "".
            intensity (int, optional): control the frequency of the propose (0 - 3: most - least). Defaults to 3.
            task_num (int, optional): determine the number of the task number. Defaults to 3.
            recall_db (FAISS, optional): The database to make a RAG in householding scenes. Defaults to None.
        """
        self.eventListner  :EventListener  = EventListener()
        self.contextManager:ContextManager = ContextManager()
        # self.trigger       :Trigger        = Trigger()
        self.core          : Core = Core(client = client)


    def load_and_run(self, events:List[Dict]):
        """
        Only used to validate our test data.
        We will use all but the last one as history and the last one turn to get a response.

        Args:
            events (_type_): The (part or complete) event trace from out test data.

        Returns:
            _type_: _description_
        """
        if len(events) == 0:
            raise ValueError("Do not pass an empty list here.")

        self.contextManager.load_trace(events[:-1])

        result, __ = self.run_single_step(new_event = events[-1]["observation"])

        return result


    def run_single_step(self, need_user = False, new_event:Any = None) -> Tuple[Dict,str]:
        """
        A simple call to run one step.
        At each step, it'll
        1. load new event if exists.
        2. manage the context
        3. reflect if to offer help.
        4. let the user give feedback.

        Tip: In json format scene, the role of the event_listner is weak, check ragent to learn how many automic actions form an event.

        Args:
            need_user (bool, optional): If to let the user to give feedback or use User Agent for automation. Defaults to False(let the User Agent for automation).
            new_event (Dict, optional): the new event (used for dynamic data generation, where the agent get new information at each round rather than get all at first). Defaults to None(i.e. all events were loaded at first).

        Returns:
            Dict: The response from the agent, in a json format.
            str:  The feedback from the user.

            If return (None, None), it shows no more event is available.
        """

        if new_event != None:
            self.eventListner.add_event(new_event)

        try:
            event = self.eventListner.get_event()
        except:
            return None,None

        self.contextManager.add_event(event)

        response = self.core.reflect(event_turns = self.contextManager.get_all_turns())

        user_input = None
        # if VERBOSE and self.trigger.front_end_open:
        #     print(response)

        # self.trigger.send(response)

        # if need_user:
        #     user_input = self.trigger.get_response_from_user()
        # else:
        #     user_input = None
        return response, user_input


def main():
    # A single case for loading test data and running.
    model = model_name
    api_key = config.api_key
    try:
        base_url = config.base_url
    except:
        base_url = None

    client = LLMClient(api_key = api_key,
                    base_url = base_url,
                    model_name=model_name)

    ag = ActiveAgent(client = client)



    with open('../dataset/test_data/code_11.json', 'r', encoding='utf-8') as f:
        event_trace = json.load(f)

    for idx in range(len(event_trace)):
        result = ag.load_and_run(events = event_trace[:idx + 1])

    print(result)

if __name__ == '__main__':
    main()
