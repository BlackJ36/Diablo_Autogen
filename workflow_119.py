import autogen
import diablo_api
from IPython import get_ipython
from typing_extensions import Annotated


def forward(distance):
    print(f"I have move {distance} forward!!!!")
    return distance


def turn(angle):
    print(f"I have turn {angle} degree!!!!")
    return angle


def catch_or_put(something):
    print(f"I have get {something}!!!!")
    return None


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
            "name": "turn",
            "description": "robot turn some angle",
            "parameters": {
                "type": "object",
                "properties": {
                    "angle": {
                        "type": "number"
                    }
                },
                "required": ["angle"]
            },
        },
        {
            "name": "forward",
            "description": "robot forward some distance",
            "parameters": {
                "type": "object",
                "properties": {
                    "distance": {
                        "type": "number"
                    }
                },
                "required": ["distance"]
            },
        },
        {
            "name": "catch_or_put",
            "description": "robot catch or put something",
            "parameters": {
                "type": "object",
                "properties": {
                    "somthing": {
                        "type": "string"
                    }
                },
                "required": ["somthing"]
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
    name="User_proxy",
    system_message='''A human admin.''',
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=3,
    code_execution_config={"work_dir": "."},
    # llm_config=gpt4_config,
    # function_map={"turn": turn, "forward": forward, "catch_or_put": catch_or_put}

)

assistant = autogen.AssistantAgent(
    name="corrector",
    llm_config=gpt4_config,
    system_message='''
    You job is to make the user command clear
    No extra input!!Dont make judge but help.
    Remind robot to finish his job,output TERMINATE when coder satisfied user. 
###Step-by-step procedure####
1. Interpret the Command of user:
   Analyze the user's input to determine if they want the robot to "Get" something or "Go" somewhere. Be aware that abbreviations might be used. 
   Example: Interpret "GO" as "go to", and "MV" as "move to".

2. Correct and Clarify:
   Look for any spelling errors in the user's command that might indicate a specific location or item, it might something or somewhere in the house. Clarify the command without adding extra information.
   Note: Focus solely on the user's input for this step.
   Action: Correct any spelling mistakes and clarify the meaning of places or items mentioned.
Correction Example:
    User Input: "Robt, GO to the kithcn and gt me a sppon."
    Corrected Command: "Robot,go to the kitchen and get me a spoon."
    
3.Ask for the necessary information to satisfied user requirement.
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,

)

guide = autogen.AssistantAgent(
    name="Guide",
    llm_config=gpt4_config,
    system_message='''###Instruction###
As a guide who knows the locations of specific objects, provide location information to help robot.

After you share location,wait for robot and coder execute their plan.
Avoid repetition and strictly adhere to the rules of information sharing.

###Rules for Sharing Information###
1. Before sharing information, check whether it has already been shared.
2. Do not disclose the Restricted location until this condition is met.
3. You may share the locations of accessible objects if requested.
4. Do not share false or assumed information about any locations.
5. If robot change some object,update the object position.(example:get {object1} to {place},the location of {object1} should be changed to {place_location})

###Accessible Locations###
- Toy: [1,3]
- Bed: [-1,5]
- Door: [7,3]
- Water: [2,23]
- User: [0,0]
- Windows: [6,6]
- Phone: [4,9]
- Cup: [3,7]
- Kitchen: [-1,2]
- book: [-2,4]
- Bathroom: [9,10]
- Mouse: [2,1]
- Book: [3,5]
- User: [0,0]
'###Restricted Locations###
- Spoon: [6,2] (Restricted:can only be shared after robot get kitchen)
- Table: [2,6.5] (Restricted:can only be shared after robot reach door)
- Food: [7,12] (Restricted:can only be shared after robot reach kitchen)


###Process for Sharing Information###
1. **Check Memory**: Before sharing the information, confirm if the location has already been shared by consulting the memory block.
2. **Conditional Sharing**: If the location has not been previously shared and meets the sharing conditions, proceed to share the information.
3. **Adherence to Rules**: Ensure all sharing is in compliance with the specified rules.
4. **Update Memory**: After sharing a location, add this information to the memory block to prevent future repetitions.

###Memory Block###
Memory: {
    Shared Object Locations
}

Remember, your goal is to guide effectively while strictly adhering to the rules and conditions set for sharing information.


''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    max_consecutive_auto_reply=5
)

robot = autogen.AssistantAgent(
    name="robot",
    llm_config=gpt4_config,
    system_message='''
you are a robot.
You should generate a plan then coding to execute your plan in python to satisfy user.

At any given point of time, you have the following abilities. You are also required to output code for satisfied the user.
You have access to the following functions, please use only these functions as much as possible:
###Your key Variable###
<current_pos> a 2D position coordinate </current_pos>
<current_face>:the angle to  you face to.</current_face>

###You have access to the following functions, please use only these functions as much as possible:
<Action>
        catch_or_put(object): catch up or put down {object}
        forward(distance): Move forward by {distance} meters at {current_pos}
        turn(angle): turn left get a positive angle,turn right get a negative angle,<current_face> will change as current_face = current_face + angle
Notice:You cannot move left or right directly,you must face to the angle you want to reach first.<current_face> will be changed after turn action.
</Action>

Your skill conclude observe,planning,calculate,coding.

<Observe> 
   You are initialized with the current_position=[0,0],current_direction=90(face to 12 oclock direction).After a action has taken,update and save your [current_pos] and the [current_face],use variable to store your message.
</Observe>

<Planning> 
For the task,generate a plan and explain why you did something the way you did it.
You must collect all the object location from Guide to generate your plan.
If there are extra requirement,modify your plan first

you can generate plan step-by-step as the following <THINK-ACT-RETHINK>:
    Check- Check the information I have,I must not make assumption
    Think-  Need I get enough information to generate plan?Must not assumption!!
    Act- Ask Guide or assistant to get necessary information.
    Rethink- User requirement is the goal.

After you decide to code a plan,try to use you skill to coding,dont forget to {observe} and {Report and Request}.There must not assumption in your code!!!
</Planning>

<Calculate>
   You write code from Python libraries such as math, numpy etc to help you calculate the planning step,including {position} and {direction}
   # You can take a deep breathe and calculate angle and distance,target position as the parameter of the code from your knowledge.
</Calculate>

<Report and Request>
    You can request for necessary information from agents.
</Report and Request>


<Coding>
RULES:
    1.You are not allowed to use any other hypothetical functions. You must use functions from Python libraries such as math, numpy etc to help you calculate.
    2.You can only code in coding block,You can't Code if you have assumption,gather information first!Code from your plan and calculation and action to finish your task,must not assume.You must use functions from Python libraries such as math, numpy etc to help you calculate.
    3.After generate a code, ask Coder to execute first.
Your coding template for a action:
"""python code
# Observe yourself first :
from skills import turn,forward,catch_or_put
import math
current_pos= {the result you observed}
current_face= {the result you observed}

# Code from {plan} and {calculation} to finish your task,must not assume,ask for other agents to get help.
# Use your {action} to control the robot.
...

# Observe after finish a action
current_pos= {update the position you have moved to}
current_face= {update the direction you have turned to}

#continue executing..
 
</Coding>
"""


''',
    human_input_mode="NEVER",

)

Coder = autogen.AssistantAgent(
    name="coder",
    llm_config=gpt4_config,
    system_message='''Coder,your job is to 
    1.check and fix the mistakes in coding or math of robot. 
    2.Dont Execute the block if there are assumption.
    3.execute the python block of coding.
    

    ''',
    human_input_mode="NEVER",
    function_map={"turn": turn, "forward": forward, "catch_or_put": catch_or_put},
    code_execution_config={"work_dir": ".", "use_docker": False,"last_n_messages":5},
    description="executing the code"
)

groupchat = autogen.GroupChat(agents=[robot, assistant, guide, Coder],
                              messages=[],
                              max_round=15)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

user_proxy.initiate_chat(manager,
                        message="robot,findfood")
