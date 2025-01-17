import logging
import random
import re
import typing as t

from toolbox.core.models import Episode, Turn, TurnKind
from toolbox.core.task import BaseTask
from toolbox.datasets.ai_dungeon import AiDungeonDataset
from toolbox.utils.prompts import generate_prompts

LOG = logging.getLogger(__name__)


class AiDungeonTextAdventureTask(BaseTask):
    '''Text adventure task based on AI Dungeon data.'''

    def __iter__(self) -> t.Generator[Episode, None, None]:
        idx = 0
        current_story = ""

        for line in AiDungeonDataset():
            if line.startswith("<|startoftext|>"):
                # Started a new story, handle the previous one.
                turns = _convert_story_to_turns(current_story)
                sp = random.choice(_SYSTEM_PROMPTS)
                turns.insert(0, Turn(utterance=sp, kind=TurnKind.SYSTEM))

                yield Episode(turns=turns, identifier=f"ai-dungeon-{idx}")

                current_story = line
                idx += 1
            else:
                # Continuation.
                current_story += line


def _convert_story_to_turns(story: str) -> list[Turn]:
    turns: list[Turn] = []
    current_turn = ""
    current_word_count = 0

    for line in story.splitlines():
        # Handle the easy stuff first: if the line starts with `> `, it's user
        # input.
        if line.startswith("> "):
            utterance = line.replace("> ", "").strip()

            if len(utterance) == 0:
                # We don't care about empty user inputs.
                continue

            turns.append(Turn(utterance=utterance, kind=TurnKind.USER))
            continue

        # Otherwise, let's keep accumulating text and breaking it up into
        # manageable chunks so we can do a sliding window over the story text.

        # Remove useless tokens.
        line = line.replace("<|startoftext|>", "")
        line = line.replace("<|endoftext|>", "")

        current_turn += line.strip() + "\n"
        current_word_count += len(line.split())
        if current_word_count >= _MIN_WORD_COUNT_PER_MODEL_TURN:
            # Simple regex substitution to clean up excessive spacing before
            # creating the Turn object.
            utterance = re.sub(r"\n{3,}", "\n\n", current_turn)

            turns.append(Turn(utterance=utterance, kind=TurnKind.MODEL))

            current_turn = ""
            current_word_count = 0
            continue

    return turns


_MIN_WORD_COUNT_PER_MODEL_TURN = 300

_SYSTEM_PROMPTS = generate_prompts([
    '''%{This is|You are|Start|Simulate|You are to simulate|Begin} a text %{adventure|adventure game}. %{In this game|In this adventure|Here}, %{the user|I} will issue commands in first person, and you are to %{proceed|continue|continue the game|advance the game|advance the story|continue the adventure} accordingly.''',
])