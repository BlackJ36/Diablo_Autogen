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


# user_proxy = autogen.UserProxyAgent(
#     name="Patient",
#     system_message="A human admin which as a patient who can only send command through BCI speller,there may be mistakes in the spelling. Interact with the robot to give it an order.",
#     code_execution_config=False,
# )

# robot


def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False


user_proxy = autogen.UserProxyAgent(
    name="User",
    system_message='''Admin.For each query,I need the agents to communicate and generate code from executor.TERMINATE the task if executor has no error.''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    code_execution_config=False

)

# correction
# corrector = autogen.AssistantAgent(
#     name="corrector",
#     llm_config=gpt4_config,
#     system_message='''Corrector. You dont need to execute the command but correct spelling mistakes from user.
#     You receive the first command provided by user.If there are mistakes in spelling,try to correct it.When you correct words, pay attenion itis a command which
#     robot may execute,including action/time/angles,ask Motion_selector for assistance.
#     TAKE Example into consideration.
#     Example:
#     - Abbreviation motion like 'mv' can be move.
#     - Abbreviation direction like 'for' can be forward
#     - Abbreviation angles like 'dg' can be degree
#     - There are also human like command such as 'danc' can be dance.
#     - If user give a question, you should think over it first and give the answer.Tell Motion_selector to simulate motion to answer the question.
# ''',
#     human_input_mode="NEVER",
#     is_termination_msg=is_termination_msg
# )
corrector = autogen.AssistantAgent(
    name="corrector",
    llm_config=gpt4_config,
    system_message='''Corrector. You can communicate with Motion_selector.
    You should analyse the command or question of user.
    Think step by step then analyse and answer the user's question or command using your knowledge,NO USER INPUT.
    Step1:If there are mistakes in spelling,try to correct it.
    Step2:If there is question,give your answer and ask Motion_selector to show your attitude with motion.
    Step3:Explain the user command,generate proposal motion list communicate with Motion_selector.
    
    TAKE <RULES> into consideration.
    """<RULES>:
    - Abbreviation motion like 'mv' can be move.
    - Abbreviation direction like 'for' can be forward
    - Abbreviation angles like 'dg' can be degree
    - There are also human like command such as 'danc' can be dance.
    - If user give a question, you should think over it first and give your answer."""
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)

robot = autogen.AssistantAgent(
    name="wheel-legs-bot",
    system_message='''Wheel-legs-bot. You can communicate with Motion_selector and Description_selector.
    You receive the todo motion list from Motion_selector.You must check the todo motion list follow the <Rules>.Let Motion_selector to translate it human-like motion like "shake" in todo motion list.
If there are no mistakes in todo motion list,you should generate the final_motion from Step of Motion_selector.Finally ask Description_selector to generate structure output.

"""<Rules>
Predefined-motion:A wheel-legs-bot including move forwards and backwards,turn left and right,pitch up and down,roll left and right,body rising, standing up, and squatting down. 
1.The final_motion list should consist of predefined-motion,can be attached with description.

2.Robot should has stood up if the motion containing "pitch","roll“,”squat“ or ”body rising“.Assuming the robot is squatting.
# Example:"move forward and pitch up and turn right"
Thinking:Step1:check each motion in the list,if any "pitch" or "roll" or "squat" or "body rising" motion?
         Step2:If there is "pitch" or "roll" or "squat" or "rise" motion,and no "stand up"before, it should add "stand up" at first of the motion sequence.
        Step3:the list should be "move forward","stand up","pitch up","turn right"
          
3.Let Motion_selector to translate it human-like motion like "shake" in todo motion list.
# Example:"move forward and shake"
 Thinking:Step1:check every motion in the list.
          Step2:"move forward" is valid.But "shake" is invalid.
          Step3:tell Motion_selector to translate "shake" motion.        
"""
''',
    llm_config=gpt4_config,
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)

Motion_selector = autogen.AssistantAgent(
    name="Motion_selector",
    llm_config=gpt4_config,
    system_message='''Motion_selector. You receive the message from Corrector and communicate with wheel-legs-bot to determined todo motion list.
    Separate the complex motion into pieces first.If there is motion expressed in human-like-action,take a deep breathe,simulate the motion in the sequence of predefined motion,
    no user input so you decide the combination.
    Ask wheel-legs-bot to make sure the it can execute todo motion list.

Predefined-motion:A wheel-legs-bot including move forwards and backwards,turn left and right,pitch up and down,roll left and right,body rising, standing up, and squatting down. 
Human-like-description:Wheel-legs-bot's head can pitching up and down, Wheel-legs-bot's body can turning and tilting left or right,go forward and back.
Make sure you follow the <Rules> below.
"""<Rules>
1.For movement motion,wheel-legs-bot can only move forward or backward.If the movement description in a shape or other direction you should determine the angle first.
# Example: "run a square shape"
Thinking:Step1:<interior angle sum> of square shape is 360 degrees,<number of edge> is 4.
         Step2:change angle can be calculated as {180-<interior angle sum>/<number of edge>},means 180 minus 360/4 equals to 120.
         Step3:I should repeat turn <direction> 90 degrees and move forward.
         Step4:Repeat step3 for 4 times.

# Example: "move towards 8 oclock direction"
Thinking:Step1:I face towards 12 oclock direction now.
         Step2:Think what direction I should turn from 12 oclock to 8 oclock.
         Step3:Determined the <direction> and <angles> Step2,think over it and give the result.
         Step4:Turn <direction> <angles>.
         Step5:concat result of Step 4 and "move forward"
         

2.You should translate motion expressed in human-like-description should be translated into a sequence of predefined-motion like "pitch up" and "turn right".
# Example: "move forward and show unwilling"
Thinking:Step1:"unwilling" is human-like motion
         Step2:Human act unwillingness in "shake head"or"shake body"
         Step3:Check the predefined-motion list first.
         Step4:Robot may simulate "shake body" by "rolling.
         Step5:"shake body" should be translated into several predefined-motion.
         Step6:concat"move forward" and result of Step 5.

3.command like "move forward then backward",which is expressed a sequence of motion.You should translate it into a several predefined-motion like"move forward","move backward"
4.when you output the todo motion list , make sure the motion should all be predefined-motion.
5.Element of list should be one predefined motion with corresponding description like angle/time.
"""
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)

# Confirm your output and send it to Description_selector.
Description_selector = autogen.UserProxyAgent(
    name="Description_selector",
    system_message='''Description_selector.You can get the final_motion list.
    You should be sensitive to predefined motion(move,turn and etc) and 
    description(execution direction or time or angle changed assigned ) in every motion in final motion list. Then you 
    should translate the description into accurate numeric following the <RULES>.
    Answer in the form of <TEMPLATE>.
"""<TEMPLATE> 
- You should answer in a JSON array like [{<Predefined motion1>:<Description1>},{<Predefined motion2>:<Description2>}]
"""<Description>:should be one of the following JSON object:{"angle":<pitch angle to be change>} or {"angle":<yaw angle to be change>} or {"angle":<roll angle to be change>} or {"time":<motion execution time>}"""
"""<Predefined motion>:should be one of move forward or backward,turn left or right,pitch up or down,roll left or right,body rising,stand up,squat down. """
"""<RULES>:
- Translate "pitch up and down" into "pitch up","pitch down"
- Angles to be change should be positive.
- For "move forward and backwards", default velocity is 0.5m/s,translate distance into time.
- If "move" motion" has no time specified,set motion execution time to 1 seconds.
- If "pitch","roll" motion has no angel mentioned, the corresponding angle set to 15 degree.
- If "turn" motion has no angel mentioned, the corresponding angle set to 90 degree."""
"""

    ''',
    human_input_mode="NEVER",
    llm_config=gpt4_config,
    is_termination_msg=is_termination_msg,
    code_execution_config=False
)

# Coder = autogen.AssistantAgent(
#     name="executor",
#     system_message='''Executor.You can communicate with Description_selector.
#     Check the Description_selector's output,send output as cmd_list to robot.
#     Check the response of your code,if there are mistakes,try to work it out with Description_selector''',
#     llm_config=coder_config,
#     is_termination_msg=is_termination_msg,
#     function_map={"send_status_cmd": send_status_cmd}
# )

groupchat = autogen.GroupChat(agents=[robot, corrector, Motion_selector, user_proxy, Description_selector],
                              messages=[],
                              max_round=12)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
user_proxy.initiate_chat(
    manager,
    message="""robot:show your acknowledgement"""
)

#
# @user_proxy.register_for_execution()
# @Coder.register_for_llm(description="send message to robot")
# def send_status_cmd(cmd: Annotateddict):
#     print(cmd)
#     print("done!!!!")
#     return "done!!!!"


# trans = diablo_api.diablo(local_add="127.0.0.1", port=8801, robot_add='127.0.0.1', rport=8848)
