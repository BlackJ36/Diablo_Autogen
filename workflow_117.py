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


def is_termination_gg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "GG" in content["content"]:
        return True
    return False


user_proxy = autogen.UserProxyAgent(
    name="user_proxy",
    system_message='''A human admin.''',
    human_input_mode="NEVER",
    max_consecutive_auto_reply=3,
    code_execution_config={"work_dir": "."}

)

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config=gpt4_config,
    system_message='''assistant,you receive command from user, help Guide and Robot to satisfied user.You must ask Guide for get the location about all the relevant objects.
###Instruction###
Must not make assumptions.
###Job for Correction###
1. Understand the Context:
   Context:The task may involve gathering or moving to some place.

2. Interpret the Command:
   Analyze the user's input to determine if they want the robot to "Get" something or "Go" somewhere. Be aware that abbreviations might be used. 
   Example: Interpret "GO" as "go to", and "MV" as "move to".

3. Correct and Clarify:
   Look for any spelling errors in the user's command that might indicate a specific location or item. Clarify the command without adding extra information.
   Note: Focus solely on the user's input for this step.
   Action: Correct any spelling mistakes and clarify the meaning of places or items mentioned.
Example:
    User Input: "Robt, plese GO to the kithcn and gt me a sppon."
    Corrected Command: "Robot, please go to the kitchen and get me a spoon."
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    description="the first agents to process user information."
)

guide = autogen.AssistantAgent(
    name="Guide",
    llm_config=gpt4_config,
    system_message='''Only you know the location of object.You should follow the <RULES> to share <object locations>.
<RULES to share information>:
1.You MUST NOT tell spoon location is [6,2] to other UNTIL Robot report it has reach kitchen,you can tell the kitchen location if robot need.
2.You MUST NOT tell table location is [2,6.5] to other UNTIL Robot report it has reach door,you can tell the door location if robot need.
3.You can share other location if not forbidden.
</RULES to share information>:

<object locations>
    The toy locations: [1,3].
    The bed locations: [-1,5]. 
    The door locations: [7,3].
    The water locations: [2,23].
    The user locations:[0,0].
    The windows location:[6,6].
    The phone location:[4,9].
    The cup location:[3,7].
    The kitchen location:[-1,2].
    The spoon location: share according to  RULES.
    The table locations:share according RULES.
</object locations>


''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    description="response when other agent need object location"
)

robot = autogen.AssistantAgent(
    name="robot",

    llm_config=gpt4_config,
    system_message='''
you are a robot.You dont know the object location until Guide tell you.
You should generate a plan then coding to execute your plan in python to satisfy user.

At any given point of time, you have the following abilities. You are also required to output code for satisfied the user.
You have access to the following functions, please use only these functions as much as possible:
###Your key Variable###
<current_pos> a 2D position coordinate </current_pos>
<current_face>:the angle to  you face to.</current_face>

###You have access to the following functions, please use only these functions as much as possible:
Action:
        catch_or_put(object): catch up or put down [object] 
        forward(distance): Move forward by <distance> meters at <current_pos>
        turn(angle): turn left get a positive angle,turn right get a negative angle,<current_face> will change as current_face = current_face + angle
Notice:You cannot move left or right directly,you must face to the angle you want to reach first.<current_face> will be changed after turn action.

    
Your skill conclude observe,planning,calculate,coding.

<Observe> 
   After a action has taken,update and save your [current_pos] and the [current_face],use variable to store your message.
</Observe>

<Planning> 
For the task,generate a plan and explain why you did something the way you did it.You must collect all the object location to generate your plan.If you cant finish at once.Separate it into two stage.

You should use <Calculate> skill to get numeric description,flow the template below:
     Step1:Im in [0,0],face 12 oclock,I should take action to reach [des_position1],changed angle can be calculate as [face_angle]-[angles between the face_angle and dest]
     Step2:[observe],save your <current_pos> and the <current_face>
     Step3:Base the [observe],i am in [des_position1],[face direction1],I should take action to reach [des_position2],changed angle can be calcultate as [face_angle]-[angles between face_angle and dest]
     Step4:[observe].save your <current_pos> and the <current_face>
     Step5:...
</Planning>
 
<Calculate>
   You write code from Python libraries such as math, numpy etc to help you calculate the planning step,including [position] and [direction]
   # You can take a deep breathe and calculate angle and distance,target position as the parameter of the code from your knowledge.
</Calculate>

<Report>
    After generate a code to finish a task,report that you has done to other agents in string.
</Report>

<Code>
# Code from your plan and calculation and action to finish your task,must not assume.You must use functions from Python libraries such as math, numpy etc to help you calculate.
</Code>

RULES:
1.You are not to use any other hypothetical functions. You must use functions from Python libraries such as math, numpy etc to help you calculate.

Your coding template:
"""python code
# Initialization:
current_pos=[0,0]
current_face=90 

# Code from your plan and calculation and action to finish your task,must not assume,ask for other agents to get help.
"""


''',
    human_input_mode="NEVER",
    code_execution_config=False,
    description="response when the robot is assigned a task from assistant"
)

# critic = autogen.AssistantAgent(
#     name="critic",
#     llm_config=gpt4_config,
#     system_message='''Critic. You are specify in math and space geometry.Check the <Code> of robot to make sure its action will get correct effect.
#     You can use functions from Python libraries such as math, numpy etc to help you calculate.
#     ###Several things should be contained###
#         <current_pos> a 2D position coordinate </current_pos>
#         <current_face>:the angle to  you face to.</current_face>
#         forward(distance): Move forward by <distance> meters.
#         turn(angle): turn left get a positive angle,turn right get a negative angle.
#     ''',
#     human_input_mode="NEVER",
#
# )

groupchat = autogen.GroupChat(agents=[robot, assistant, guide, user_proxy],
                              messages=[],
                              max_round=15)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

user_proxy.initiate_chat(manager,
                         message="rOBOT,GETbottle the bottle is 3m behind you")
