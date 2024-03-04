import autogen
import diablo_api
from IPython import get_ipython
from typing_extensions import Annotated


def send_status_cmd(motion_list):
    for command in motion_list:
        for action, params in command.items():
            print(f"Action: {action}")
            for key in params:
                print(f"  {key}: {params[key]}")
                if key not in ["time", "angle"]:
                    print(f"Warning: Unexpected key '{key}' found. Expected 'time' or 'angle'.")
    return "ALL IS WELL"


config_list_gpt4 = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-3.5-turbo-1106"],
    },
)

gpt4_config = {
    "cache_seed": 66,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list_gpt4,
    "timeout": 120,
}

coder_config = {
    "cache_seed": 43,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list_gpt4,
    "timeout": 120,
    "functions": [
        {
            "name": "send_status_cmd",
            "description": "send the message to robot",
            "parameters": {
                "type": "object",
                "properties": {
                    "motion_list": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "motion": {
                                    "type": "object",

                                }
                            },
                        }
                    },

                },
                "required": ["motion_list"]
            },
        }
    ]
}


def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False


user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    human_input_mode="TERMINATE",
    is_termination_msg=is_termination_msg,
    max_consecutive_auto_reply=0,
    code_execution_config=False
)


corrector = autogen.AssistantAgent(
    name="Corrector",
    llm_config=gpt4_config,
    system_message='''
###Instruction###
Analyze user inputs focused on home-based tasks involving a robot assistant. Correct any mistakes and determine the intended action from the given context. Do not make assumptions; base your response solely on the provided information.

###Step-by-Step Guide###
1. Understand the Context:
   Context: The user is at home and needs assistance from a robot. The task may involve gathering or moving to some place.

2. Interpret the Command:
   Analyze the user's input to determine if they want the robot to "Get" something or "Go" somewhere. Be aware that abbreviations might be used. 
   Example: Interpret "GO" as "go to", and "MV" as "move to".

3. Correct and Clarify:
   Look for any spelling errors in the user's command that might indicate a specific location or item. Clarify the command without adding extra information.
   Note: Focus solely on the user's input for this step.
   Action: Correct any spelling mistakes and clarify the meaning of places or items mentioned.

4. Respond with the Corrected Action:
   Provide a clear response based on the corrected interpretation of the command. Conclude your response with the word "TERMINATE" to indicate the end of the task.

###Example###
User Input: "Robt, plese GO to the kithcn and gt me a sppon."
Corrected Command: "Robot, please go to the kitchen and get me a spoon."
Response: "Moving to the kitchen to retrieve a spoon. TERMINATE."
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)


corrector.initiate_chat(
    user_proxy,
    message="""Robot,GETPHOHNE
"""
)

#
# @user_proxy.register_for_execution()
# @Coder.register_for_llm(description="send message to robot")
# def send_status_cmd(cmd: Annotateddict):
#     print(cmd)
#     print("done!!!!")
#     return "done!!!!"


# trans = diablo_api.diablo(local_add="127.0.0.1", port=8801, robot_add='127.0.0.1', rport=8848)
