from autogen.agentchat.groupchat import GroupChat
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import AssistantAgent
import autogen

config_list_gpt4 = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={
        "model": ["gpt-3.5-turbo-1106"],
    },
)

llm_config = {
    "cache_seed": 44,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": config_list_gpt4,
    "timeout": 120,
}

import random
from typing import List, Dict


class CustomGroupChat(GroupChat):
    def __init__(self, agents, messages, max_round=10):
        super().__init__(agents, messages, max_round)
        self.previous_speaker = None  # Keep track of the previous speaker

    def select_speaker(self, last_speaker: Agent, selector: AssistantAgent):
        # Check if last message suggests a next speaker or termination
        last_message = self.messages[-1] if self.messages else None
        if last_message:
            if 'NEXT:' in last_message['content']:
                suggested_next = last_message['content'].split('NEXT: ')[-1].strip()
                print(f'Extracted suggested_next = {suggested_next}')
                try:
                    return self.agent_by_name(suggested_next)
                except ValueError:
                    pass  # If agent name is not valid, continue with normal selection
            elif 'TERMINATE' in last_message['content']:
                try:
                    return self.agent_by_name('User_proxy')
                except ValueError:
                    pass  # If 'User_proxy' is not a valid name, continue with normal selection

        team_leader_names = [agent.name for agent in self.agents if agent.name.endswith('1')]

        if last_speaker.name in team_leader_names:
            team_letter = last_speaker.name[0]
            possible_next_speakers = [
                agent for agent in self.agents if
                (agent.name.startswith(team_letter) or agent.name in team_leader_names)
                and agent != last_speaker and agent != self.previous_speaker
            ]
        else:
            team_letter = last_speaker.name[0]
            possible_next_speakers = [
                agent for agent in self.agents if agent.name.startswith(team_letter)
                                                  and agent != last_speaker and agent != self.previous_speaker
            ]

        self.previous_speaker = last_speaker

        if possible_next_speakers:
            next_speaker = random.choice(possible_next_speakers)
            return next_speaker
        else:
            return None


# Termination message detection
def is_termination_msg(content) -> bool:
    have_content = content.get("content", None) is not None
    if have_content and "TERMINATE" in content["content"]:
        return True
    return False


# Initialization
agents_A = [
    AssistantAgent(name='A1',
                   system_message="You are a team leader A1, your team consists of A2, A3. You can talk to the other team leader B1, whose team member is B2.",
                   llm_config=llm_config),
    AssistantAgent(name='A2',
                   system_message="You are team member A2, you know the secret value of x but not y, x = 9. Tell others x to cooperate.",
                   llm_config=llm_config),
    AssistantAgent(name='A3',
                   system_message="You are team member A3, You know the secret value of y but not x, y = 5. Tell others y to cooperate.",
                   llm_config=llm_config)
]

agents_B = [
    AssistantAgent(name='B1',
                   system_message="You are a team leader B1, your team consists of B2. You can talk to the other team leader A1, whose team member is A2, A3. Use NEXT: A1 to suggest talking to A1.",
                   llm_config=llm_config),
    AssistantAgent(name='B2',
                   system_message="You are team member B2. Your task is to find out the value of x and y and compute the product. Once you have the answer, say out the answer and append a new line with TERMINATE.",
                   llm_config=llm_config)
]

# Terminates the conversation when TERMINATE is detected.
user_proxy = autogen.UserProxyAgent(
    name="User_proxy",
    system_message="Terminator admin.",
    code_execution_config=False,
    is_termination_msg=is_termination_msg,
    human_input_mode="NEVER")

list_of_agents = agents_A + agents_B
list_of_agents.append(user_proxy)

# Create CustomGroupChat
group_chat = CustomGroupChat(
    agents=list_of_agents,  # Include all agents
    messages=[
        'Everyone cooperate and help agent B2 in his task. Team A has A1, A2, A3. Team B has B1, B2. Only members of the same team can talk to one another. Only team leaders (names ending with 1) can talk amongst themselves. You must use "NEXT: B1" to suggest talking to B1 for example; You can suggest only one person, you cannot suggest yourself or the previous speaker; You can also dont suggest anyone.'],
    max_round=30
)

# Create the manager
llm_config = {"config_list": config_list_gpt4,
              "cache_seed": None}  # cache_seed is None because we want to observe if there is any communication pattern difference if we reran the group chat.
manager = autogen.GroupChatManager(groupchat=group_chat, llm_config=llm_config)

# Initiates the chat with B2
agents_B[1].initiate_chat(manager, message="Find the product of x and y, the other agents know x and y.")
