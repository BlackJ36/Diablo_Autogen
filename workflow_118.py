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
    system_message='''A human admin.Output TERMINATE if robot finish your job.''',
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=3,
    code_execution_config={"work_dir": "."}

)

assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config=gpt4_config,
    system_message='''
###Instruction###
Analyze user inputs focused on home-based tasks involving a robot assistant. Correct any mistakes and determine the intended action from the given context. 
Do not make assumptions.Ask Guide for the location of object.
###Job for Correction###
1. Understand the Context:
   Context: The user is at home and needs assistance from a robot. The task may involve gathering or moving to some place.

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


You should think and take action step-by-step,after you finish a step,turn to the next one.
###Step-by-step procedure###:
Step 1: Correct user input if there are mistakes,if not,go to step2.
Step 2: ask Guide to generate a path
Step 3: share the information with Robot and let it generate code.

''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)

guide = autogen.AssistantAgent(
    name="Guide",
    llm_config=gpt4_config,
    system_message='''
    Guide.You can share the <object locations> with other agents.Do not suggest plan.
<object locations>
    the toy locations: [1,3].
    The bed locations: [-1,5]. 
    The door locations: [7,3].
    The water locations: [2,23].
    The table locations:5m 45 degree ccw of the toy.
</object locations>

Example:
# the toy position
the toy in in [1,3]

# the table position:
I dont know the table position,but I know the toy position is [1,3],the table is 5m 45 degree ccw of the toy.
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
)

robot = autogen.AssistantAgent(
    name="Robot",

    llm_config=gpt4_config,
    system_message='''
Robot. 

After the position of waypoints of the task is clear,you can start to plan.
You are required to output code for your <Planning>.
Take Critic suggestion to refine your plan or code.

###Your key properties###
[current_pos]:a 2D position coordinate
[current_face]:the angle to show where you face to.

###You have access to the following functions, please use only these functions as much as possible:
Action:
        catch_or_put(object): catch up or put down[object]
        forward(distance): Move forward by <distance> meters at [current_face] 
        turn(angle): turn left get a positive angle,turn right get a negative angle,it will change current_face = current_face+angle
Example for action and coordinate:
# assume you are in the origin [0,0],face to 12 oclock,[current_face=90]
    1.After forward(1) action,your position is [0,1],[current_face=90]
    2.After turn(-90),forward(1) action,your position is [1,0],[current_face=0]
Notice:You cannot move left or right directly,you must face to the angle you want to reach first.[face direction]will be changed after turn

Variable:to store the message we need.
    [current_pos] and [current_face] should be calculate in observation.###


At any given point of time, you have the following abilities.
Your skill include observe,planning,coding,calculate.

<Observe> 
   After a action has taken,update and report your [current_pos] and the [current_face] in python code.
</Observe>

<Planning> 
For the task,generate a plan and explain why you did something the way you did it.You can use <calculate> skill and <Code> skill to help you.
     Step1:Im in [0,0],face 12 oclock,I should reach [des_position1],changed angle can be calcultate as [current_face]-[angles between the current_face and dest]
        Action:take action from the Step 1 analyse
     Step2:[observe],update the [current_position] and [current_face] after action.
     Step3:Base the [observe],i am in [current_position],[current_face],I should reach [des_position2],changed angle can be calcultate as [current_face]-[angles between the current_face and dest]
        Action:take action from the Step 2 analyse
     Step4:[observe],update the [current_position] and [current_face] after action.
     Step5:...

</Planning>

<Calculate>
You write code from Python libraries such as math, numpy etc to help you calculate the planning step,including [position] and [direction]
</Calculate>

<Code>
"""
# python code
# You can only write python code in <Code> block to finish the task,use comment to explain the action you take.!!!!
# Python code should be executed for the task,use forward(distance) and turn(angle) to move.
# Observation should be store in variable[current_position] and [current_face]!!
"""
</Code>


Notice:
You are not to use any other hypothetical functions. You can use functions from Python libraries such as math, numpy etc to help you calculate.After a step procedure,output what you get.
'''


,
    human_input_mode="NEVER",
    code_execution_config=False
)

critic = autogen.AssistantAgent(
    name="Critic",
    llm_config=gpt4_config,
    system_message='''Critic. You are specify in math and space geometry.You can use python to coding.
    Check the <Code> of robot to make sure its action will get correct effect,let Robot to renew his <Code>,make sure it obey ###Robot RULES###
    output TERMINATE if the code is OK.

    
    ###Robot RULSS###
    ###ROBOT key properties###
1.[current_pos]:a 2D position coordinate
2.[current_face]:the angle to show where you face to, can be express in angle(degree). 

###ROBOT have access to the following functions, please use only these functions as much as possible:
Action:
        catch_or_put(object): catch up or put down[object]
        forward(distance): Move forward by <distance> meters at [current_face] 
        turn(angle): turn left get a positive angle,turn right get a negative angle,it will change current_face = current_face+angle
    ''',
    human_input_mode="NEVER",

)

groupchat = autogen.GroupChat(agents=[robot, guide, assistant,critic,user_proxy],
                              messages=[],
                              max_round=20)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

user_proxy.initiate_chat(manager,
                         message="go to [1,3] then [4,2] and back to origin.")
