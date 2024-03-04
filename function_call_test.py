import autogen


def send_status_cmd(cmd):
    return cmd


config_list_gpt4 = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-3.5-turbo-1106"],
    },
)

gpt4_config = {
    "cache_seed": 78,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list_gpt4,
    "timeout": 120,
}

coder_config = {
    "cache_seed": 78,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list_gpt4,
    "timeout": 120,
    "functions": [
        {
            "name": "send_status_cmd",
            "description": "send the message to robot",
            "parameters":
                {
                    "name": "send_status_cmd",
                    "description": "send status cmd to robot,where cmd is a list of dict",
                    "parameters":
                        {
                            "type": "object",
                            "properties":
                                {
                                    "cmd":
                                        {
                                            "type": "string",
                                            "description": "for each dictionary of cmd,send it to robot",
                                        },
                                },
                            "required": ["cmd"],
                        },
                },
        }
    ],

}


def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False


user_proxy = autogen.UserProxyAgent(
    name="User_proxy",
    system_message='''Admin.Check the output of executor, if it execute susscefully,task complete and output 
    TERMINATE.''',
    code_execution_config={"work_dir": '.'},
    is_termination_msg=is_termination_msg)

AgentA = autogen.UserProxyAgent(
    name="Description_selector",
    system_message='''You should generate code in a python block.Generate servarl key value pairs like{"motion":"descrpition"}according user's description,and put them
    into a list called motion_list.
    ''',
    human_input_mode="NEVER",
    llm_config=gpt4_config,
    is_termination_msg=is_termination_msg
)

Coder = autogen.AssistantAgent(
    name="executor",
    system_message='''Executor.You should receice the message from Description_selector ,and send motion_descripiton to robot,.
                   ''',
    llm_config=coder_config,
    is_termination_msg=is_termination_msg,
    code_execution_config={"work_dir": '.'}
)

groupchat = autogen.GroupChat(agents=[AgentA, user_proxy, Coder],
                              messages=[],
                              max_round=30)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
user_proxy.initiate_chat(
    manager,
    message="""go """
)
