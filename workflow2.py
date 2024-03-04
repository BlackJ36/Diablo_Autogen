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
        "model": ["gpt-3.5-turbo"],
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
    name="User_proxy",
    system_message='''Admin.Ask agents to get a clear final motion list.Output TERMINATE when the task finished''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    max_consecutive_auto_reply=1

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
    name="Corrector",
    llm_config=gpt4_config,
    system_message='''corrector.
    Your Role: Analyze and respond to user inputs using your knowledge base. Tell the Motion_Selector to add a motion-based response.
    Note: No user input is directly fed into the system.

Step-by-Step Procedure:

1.Spelling Corrections:
Check: Look for any spelling errors in the command or question.
Action: Correct spelling mistakes to understand the user's intent accurately.

2.Responding to Questions:
Identify: Determine if the input is a question.
Respond: Provide an answer based on your knowledge.
Motion Expression: Request Motion_Selector to express your response's attitude through a motion.



<RULES> 
for Interpretation:
1.Abbreviations to Full Forms:
'mv' ➡️ 'move'
'for' ➡️ 'forward'
'dg' ➡️ 'degree'

2.No suggest motion but ask Motion_selector to show answer in motion.
</RULES>

🌐 Your Task:
Step 1: 📝 Receive and analyze the input, correcting any spelling errors.
Step 2: 💡 If it’s a question, provide an answer and express it through Motion_Selector. 
Step 3: 🤖 For commands,ask Motion_Selector for providing the appropriate actions.


"""
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_gg
)

robot = autogen.AssistantAgent(
    name="wheel-legs-bot",
    system_message='''
As wheel-Legs-Bot, Make sure the todo motion list adhere strictly to the following rules to ensure correct execution of motions.

Rules for Final Motion List Creation:
1.Inclusion of Predefined Motions: The final motion list must only include predefined motions such as moving forwards,turning left and right, pitching up and down, 
rolling left and right, body rising, standing up, and squatting down.Descriptions may accompany each motion.

2.Mandatory Standing Up Requirement:
    Initial Condition: Assume the robot starts in a squatting position.
    Action: If the motion list includes any of the following actions - "pitch," "roll," "squat," or "body rising," the robot must first perform a "stand up" motion.
3.Translation of Non-standard Motions.
    Verification: Examine each motion in the list. If a motion, like "shake," doesn't correspond to a predefined motion, flag it for translation.
    Action: Request Motion_Selector to convert non-standard motions into equivalent predefined motions.
    Example: For a sequence like "move forward and shake," retain "move forward" and replace "shake" with an equivalent predefined motion as per Motion_Selector's translation.

<Step-by-step procedure>:
    Step 1: Review each motion in the 'to-do motion list' for compliance with predefined motions.
    Step 2: Apply the 'standing up' rule where necessary.
    Step 3: Identify and let Motion_selector translate any non-standard motions.
    Step 4: Generate the 'final_motion' list from the result of Helper, ensuring it follows the correct sequence and format,give it to user.

     
"""
''',
    llm_config=gpt4_config,
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)

Motion_selector = autogen.AssistantAgent(
    name="Motion_selector",
    llm_config=gpt4_config,
    system_message='''🌟 Your task: Generate todo motion list from the predefined-motion.Obey the <RULES>
    
🔍 Your responsibility:
1.Decompose and translate Complex Motions:
Action: Break down complex motions into simpler components,If a motion resembles human-like action, simulate it using predefined motions.

2.Output Todo Motion List:
Ensure: All motions in the list are predefined and accompanied with vague descriptions like angle or duration.

3.Ask Helper for help
Action:You can not design accurate numeric description for the angle or distance,ask Helper for help.

<predefined motions>:
wheel-Legs-Bot can move forwards, turn left/right, pitch up/down, roll left/right, body rise, stand up, squat down.
</predefined motions>

Human-like Descriptions(Must no be contained in your todo motion list):
    wheel-Legs-Bot's head can pitch, body can turn/tilt, move forward/backward.

📝 <Rules> for Motion Selector:
1.Movement Motion:
Example: "run a square shape."
Notice: You cannot move to left or right directly,turn before you move if necessary.
Process: Calculate angles for direction changes with the help of helper.

2.Human-like Motion Translation:
Example: "show unwillingness."
Process: Translate expressions like "unwillingness" into predefined motions (e.g., "shake body" ➡️ "roll").

3.Sequence Command Translation:
Example: "rolling"
Process: Break down sequential commands into distinct predefined motions like "roll left","roll right"


🌐 Your Procedure:
Step 1: 📝 Receive the message from Corrector and analyze it.
Step 2: 🔄 Translate complex or human-like motions into predefined motions,propose todo motion list
Step 3: 🔄 Translate description in todo motion list with the help of Helper,validate your output.




"""
''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg
)

# Confirm your output and send it to Description_selector.
Helper = autogen.UserProxyAgent(
    name="Helper",
    system_message='''
    Help Motion_Selector to generate precise numeric answer for proposed todo motion list. Focus on interpreting and quantifying predefined motions and their descriptions.

🔍 Key Responsibilities:

1.Understand Predefined Motions:
Predefined-motion:A wheel-legs-bot including move forwards and backwards,turn left and right,pitch up and down,roll left and right,body rising, standing up, and squatting down. 
Focus: Recognize standard motions such as 'move', 'turn', etc.

2.Analyze Motion Descriptions:
Notice:If there are some description along with the motion,calculate the value base on your knowledge
Details: Examine each motion for its execution direction, time, or angle.

3.Remember the direction you face to:
Notice:suggest you are face to 12 oclock direction
Action:Update the direction you face after you execute motion.

4.Determined Numeric Values:
Notice:No extra details are provided.
Guidance: Follow the specific rules to accurately translate descriptions into numbers
Action:Generate the output by analyse the task and todo motion list.

📚 <RULES> for Numeric Translation:
1.Split Motions:
Split "pitch up and down" into "pitch up" and "pitch down."
2.Positive Angles:
All angle changes must be positive.
3.The description can be one of "time" or "angle"
4.Movement Calculations:Default velocity for "move forward" and "move backward" is 0.5m/s. Convert distances into time.
5.Calculate the numeric changed angle for the motion from description for "pitch" or "roll" motions.
6.Calculate the numeric changed angle for the motion from description for "turn" motions.
</RULES>

🌐 Your Task:
Step 1: 📝 Review each motion's description carefully.
Step 2: Remember the motion sequence you proposed, you should calculate the value from the command and the motion execute before.
Step 3: 🔢 Translate descriptions into numeric values as per the rules.

''',
    human_input_mode="NEVER",
    is_termination_msg=is_termination_msg,
    llm_config=gpt4_config,
)
#     human_input_mode="NEVER",
#     llm_config=gpt4_config,
#     is_termination_msg=is_termination_msg,
#     code_execution_config=False
# )

# Coder = autogen.AssistantAgent(
#     name="executor",
#     system_message='''Executor.You can communicate with Description_selector.
#     Check the Description_selector's output,send output as cmd_list to robot.
#     Check the response of your code,if there are mistakes,try to work it out with Description_selector''',
#     llm_config=coder_config,
#     is_termination_msg=is_termination_msg,
#     function_map={"send_status_cmd": send_status_cmd}
# )

groupchat = autogen.GroupChat(agents=[robot, corrector, Motion_selector, user_proxy, Helper],
                              messages=[],
                              max_round=20)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
user_proxy.initiate_chat(
    manager,
    message="""move 8 meter at your 8 oclcok direction"""
)

#
# @user_proxy.register_for_execution()
# @Coder.register_for_llm(description="send message to robot")
# def send_status_cmd(cmd: Annotateddict):
#     print(cmd)
#     print("done!!!!")
#     return "done!!!!"


# trans = diablo_api.diablo(local_add="127.0.0.1", port=8801, robot_add='127.0.0.1', rport=8848)
