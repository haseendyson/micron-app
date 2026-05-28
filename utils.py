from enum import Enum

"""
Mapping from emoji scores to numerical values. streamlit_feedback has two options for
feedback style, "thumbs" and "faces". Only one of these will be in use throughout the
app, so don't check the option type here as there is no overlap in emojis between the
two options.
"""

score_mappings = {
    "👍": 1,  # "thumbs" style
    "👎": 0,
    "😀": 1,
    "🙂": 0.75,  # "faces" style
    "😐": 0.5,
    "🙁": 0.25,
    "😞": 0,
}


class SliderOptions(Enum):
    """
    Options for the user's opinion on the scenario that they want to take forward.
    """

    NO = "Not really"
    EDIT = "Needs some edits"
    GOOD = "Pretty good but I'd like to tweak it"
    READY = "Ready as is!"
