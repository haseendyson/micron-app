import datetime
import json

import streamlit as st

from utils import score_mappings

logger = st.logger.get_logger("micronarratives")


def summarise_session_data(message_history):
    """
    Collates a summary of all the data from this interaction with a user. If LangSmith
    is enabled, the contents of the summarised package will be stored in LangSmith.
    Args:
        message_history (StreamlitChatMessageHistory): chat history
    Returns:
        dict: data package to be placed in the database
    """

    # Combine scenario text and all user feedback (converted to numerical where
    # appropriate) into single dataset
    scenarios_with_feedback = []
    scenario_feedback = st.session_state.get("scenario_feedback", [])
    scenario_judgement = st.session_state.get("scenario_judgement", [])
    generated_scenarios = st.session_state.get("generated_scenarios", [])

    for index, scenario_text in enumerate(generated_scenarios):
        feedback = scenario_feedback[index] if index < len(scenario_feedback) else None
        judgement = (
            scenario_judgement[index] if index < len(scenario_judgement) else None
        )
        scenarios_with_feedback.append(
            {
                "text": scenario_text,
                "feedback": score_mappings.get(feedback),
                "judgement": judgement,
            }
        )

    # If a scenario hasn't been selected yet, use sensible default for scenario text
    initial_scenario = (
        generated_scenarios[st.session_state["selected_scenario_index"]]
        if st.session_state["selected_scenario_index"] is not None
        else ""
    )

    # Note: two different formats of the message history are saved, to better suit
    # different analysis methods after data collection
    scenario_package = {
        "session_id": str(st.session_state["session_id"]),
        "participant_id": str(st.session_state["participant_id"]),
        "langsmith_session_id": (
            str(st.session_state["langsmith_run_id"])
            if st.session_state.get("langsmith_run_id") is not None
            else ""
        ),
        "completion_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "language_level": st.session_state.get("language_level", ""),
        "initial_scenario": initial_scenario,
        "initial_scenario_review_score": st.session_state.get(
            "selected_scenario_review"
        ),
        "final_scenario": st.session_state["final_scenario"],
        "summary_answers": st.session_state["summary_answers"],
        "scenarios": scenarios_with_feedback,
        "chat_history": [
            {"role": m.type, "message": m.content}
            for m in message_history.messages
        ],
        "chat_history_single_string": str(message_history),
    }

    logger.debug(
        f"User {st.session_state['participant_id']}: "
        f"Prepared scenario package: {json.dumps(scenario_package, indent=4)}"
    )

    return scenario_package


def save_session_data(package, table):
    """
    Saves the session data to a connected database.
    Args:
        package (dict): a dict of data to be stored in the database
        table (DynamoDB.Table): a DynamoDB table where the data should be stored
    """

    try:
        table.put_item(Item=package)
        logger.info(
            f"User {st.session_state['participant_id']}: Data saved to database"
        )
    except Exception as e:
        logger.error(
            f"User {st.session_state['participant_id']}: "
            f"Unable to write to {table.table_name}:\n\t{e}"
        )
