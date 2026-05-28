import streamlit as st

import save

logger = st.logger.get_logger("micronarratives")


def confirm_final_scenario(message_history, table):
    """
    Manages the process of saving the data related to the user's interaction with the
    app, and presenting the final scenario to the user.
    Args:
        message_history (StreamlitChatMessageHistory): chat history
        table (DynamoDB.Table | None): a DynamoDB table where the data should be stored
    """

    package = save.summarise_session_data(message_history)

    if table:
        save.save_session_data(package, table)

    st.session_state["final_scenario_editor"] = st.session_state["final_scenario"]
    display_completion_page()


def display_completion_page():
    """
    Displays the final scenario to the user.
    """

    st.markdown(":tada: Yay! :tada:")
    st.markdown(
        "You've now completed the interaction and hopefully found a scenario that "
        "you liked! "
    )
    st.markdown(f":green[{st.session_state['final_scenario']}]")
