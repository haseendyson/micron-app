import streamlit as st

try:
    from streamlit_feedback import streamlit_feedback
except ImportError:
    streamlit_feedback = None

import scenario
from utils import score_mappings

logger = st.logger.get_logger("micronarratives")


def review_scenarios(langsmith_enabled=False, smith_client=None, one_shot=""):
    """
    Display the generated scenarios and allow the user to select one to continue.

    The older thumbs-feedback flow is preserved as an optional hook but the active UX
    now follows the demo app flow.
    """

    scenarios = st.session_state["generated_scenarios"]
    selected_index = st.session_state["selected_scenario_index"]

    if selected_index is not None:
        logger.info(
            f"User {st.session_state['participant_id']}: "
            f"Scenario {selected_index} selected"
        )
        st.session_state["agentState"] = "rate"
        st.rerun()
        return

    st.markdown("#### Review your scenarios")
    st.chat_message("ai").write(
        "Please have a look at the scenarios below. "
        "Then pick the one that you like the most to continue."
    )

    for index, scenario_text in enumerate(scenarios):
        _display_scenario_card(
            index,
            scenario_text,
            langsmith_enabled=langsmith_enabled,
            smith_client=smith_client,
            one_shot=one_shot,
        )


def _display_scenario_card(
    index,
    scenario_text,
    langsmith_enabled=False,
    smith_client=None,
    one_shot="",
):
    """Render a scenario card with the new demo-style selection UI."""

    with st.container(border=True):
        col_content, col_button = st.columns([3, 1])

        with col_content:
            st.header(f"Scenario {index + 1}")
            st.write(scenario_text)
            if langsmith_enabled and streamlit_feedback is not None:
                _set_up_feedback(index, smith_client, one_shot)

        with col_button:
            st.button(
                "Continue with this one",
                icon="🎉",
                key=f"select_scenario_{index}",
                on_click=scenario.select_scenario,
                args=(index,),
                use_container_width=True,
            )


def _set_up_feedback(scenario_index, smith_client, one_shot):
    """Optional thumbs feedback retained for LangSmith-enabled runs."""

    if streamlit_feedback is None:
        return

    streamlit_feedback(
        feedback_type="thumbs",
        optional_text_label="[Optional] Please provide an explanation",
        align="center",
        key=f"column_{scenario_index + 1}_fb",
        disable_with_score=st.session_state["scenario_feedback"][scenario_index],
        on_submit=collectFeedback,
        args=(
            scenario_index,
            st.session_state["generated_scenarios"][scenario_index],
            smith_client,
            one_shot,
        ),
    )


def collectFeedback(answer, column_index, scenario_text, smith_client, one_shot):
    """Submit optional scenario feedback when LangSmith is enabled."""

    st.session_state["scenario_feedback"][column_index] = answer["score"]
    num_score = score_mappings.get(answer["score"])

    if (
        num_score is not None
        and smith_client is not None
        and st.session_state.get("langsmith_run_id") is not None
    ):
        payload = (
            f"{num_score} rating scenario: \n{scenario_text} \nBased on: \n{one_shot}"
        )
        smith_client.create_feedback(
            run_id=st.session_state["langsmith_run_id"],
            value=payload,
            key=f"column_{column_index + 1}_fb",
            score=num_score,
            comment=answer["text"],
        )
    elif num_score is None:
        logger.warning(
            f"User {st.session_state['participant_id']}: "
            "Invalid feedback score was not submitted to LangSmith"
        )
