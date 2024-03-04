import autogen
import networkx as nx
import matplotlib.pyplot as plt
from autogen.agentchat.groupchat import GroupChat
from autogen.agentchat.assistant_agent import AssistantAgent

import random


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
    "cache_seed":  66,  # change the cache_seed for different trials
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


class CustomGroupChat(GroupChat):
    def __init__(self, agents, messages, max_round=10, graph=None):
        super().__init__(agents, messages, max_round)
        self.previous_speaker = None  # Keep track of the previous speaker
        self.graph = graph  # The graph depicting who are the next speakers available

    def select_speaker(self, last_speaker, selector):
        self.previous_speaker = last_speaker

        # Check if last message suggests a next speaker or termination
        last_message = self.messages[-1] if self.messages else None
        suggested_next = None

        if last_message:
            if 'NEXT:' in last_message['content']:
                suggested_next = last_message['content'].split('NEXT: ')[-1].strip()
                # Strip full stop and comma
                suggested_next = suggested_next.replace('.', '').replace(',', '')
                print(f"Suggested next speaker from the last message: {suggested_next}")

            elif 'TERMINATE' in last_message['content']:
                try:
                    return self.agent_by_name('User_proxy')
                except ValueError:
                    print(f"agent_by_name failed suggested_next: {suggested_next}")

        # Debugging print for the current previous speaker
        if self.previous_speaker is not None:
            print('Current previous speaker:', self.previous_speaker.name)

        # Selecting first round speaker
        if self.previous_speaker is None and self.graph is not None:
            eligible_speakers = [agent for agent in agents if
                                 self.graph.nodes[agent.name].get('first_round_speaker', False)]
            print('First round eligible speakers:', [speaker.name for speaker in eligible_speakers])

        # Selecting successors of the previous speaker
        elif self.previous_speaker is not None and self.graph is not None:
            eligible_speaker_names = [target for target in self.graph.successors(self.previous_speaker.name)]
            eligible_speakers = [agent for agent in agents if agent.name in eligible_speaker_names]
            print('Eligible speakers based on previous speaker:', eligible_speaker_names)

        else:
            eligible_speakers = agents

        # Debugging print for the next potential speakers
        print(
            f"Eligible speakers based on graph and previous speaker {self.previous_speaker.name if self.previous_speaker else 'None'}: {[speaker.name for speaker in eligible_speakers]}")

        # Three attempts at getting the next_speaker
        # 1. Using suggested_next if suggested_next is in the eligible_speakers.name
        # 2. Using LLM to pick from eligible_speakers, given that there is some context in self.message
        # 3. Random (catch-all)
        next_speaker = None

        if eligible_speakers:
            print("Selecting from eligible speakers:", [speaker.name for speaker in eligible_speakers])
            # 1. Using suggested_next if suggested_next is in the eligible_speakers.name
            if suggested_next in [speaker.name for speaker in eligible_speakers]:
                print("suggested_next is in eligible_speakers")
                next_speaker = self.agent_by_name(suggested_next)

            else:
                msgs_len = len(self.messages)
                print(f"msgs_len is now {msgs_len}")
                if len(self.messages) > 1:
                    # 2. Using LLM to pick from eligible_speakers, given that there is some context in self.message
                    print(
                        f"Using LLM to pick from eligible_speakers: {[speaker.name for speaker in eligible_speakers]}")
                    selector.update_system_message(self.select_speaker_msg(eligible_speakers))
                    _, name = selector.generate_oai_reply(self.messages + [{
                        "role": "system",
                        "content": f"Read the above conversation. Then select the next role from {[agent.name for agent in eligible_speakers]} to play. Only return the role.",
                    }])

                    # If exactly one agent is mentioned, use it. Otherwise, leave the OAI response unmodified
                    mentions = self._mentioned_agents(name, eligible_speakers)
                    if len(mentions) == 1:
                        name = next(iter(mentions))
                        next_speaker = self.agent_by_name(name)

                if next_speaker is None:
                    # 3. Random (catch-all)
                    next_speaker = random.choice(eligible_speakers)

            print(f"Selected next speaker: {next_speaker.name}")

            return next_speaker
        else:
            # Cannot return next_speaker with no eligible speakers
            raise ValueError("No eligible speakers found based on the graph constraints.")


graph = nx.DiGraph()

graph.add_node("corrector")
graph.add_node("planner")
graph.add_node("motion_selector")
graph.add_node("wheel_leg_bot")
graph.add_node("coder")

graph.add_edge("corrector", "planner")
graph.add_edge("planner", "motion_selector")
graph.add_edge("motion_selector", "planner")
graph.add_edge("planner", "wheel_leg_bot")
graph.add_edge("wheel_leg_bot","planner")
graph.add_edge("wheel_leg_bot", "motion_selector")
graph.add_edge("motion_selector","wheel_leg_bot")
graph.add_edge("wheel_leg_bot", "coder")

pos = nx.spring_layout(graph)  # positions for all nodes
agents = []
plt.figure(figsize=(12, 10))


def get_node_color(node):
    if graph.nodes[node].get('first_round_speaker', False):
        return 'red'
    else:
        return 'green'


nx.draw(graph, pos, with_labels=True, font_weight='bold', node_color=["red"])

# Annotate secret values
# for node, (x, y) in pos.items():
#     secret_value = graph.nodes[node]['secret_value']
#     plt.text(x, y + 0.1, s=f"Secret: {secret_value}", horizontalalignment='center')

plt.show()
