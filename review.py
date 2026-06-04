import streamlit as st

try:
    from streamlit_feedback import streamlit_feedback
except ImportError:
    streamlit_feedback = None

import scenario
from utils import score_mappings

logger = st.logger.get_logger("micronarratives")


def _scenario_to_text(scenario_data) -> str:
    """
    Convert a scenario (dict or str) into clean human-readable text.

    The LLM returns a dict with keys like "Scenario Title",
    "Participant's Vision for Healthcare", and "AI-Generated Scenario".
    We render only the parts the participant needs to read — the title,
    the narrative, and the themes — as plain prose with no JSON or braces.
    If the value is already a plain string, it is returned as-is.
    """
    if scenario_data is None:
        return ""

    if isinstance(scenario_data, str):
        return scenario_data.strip()

    if not isinstance(scenario_data, dict):
        return str(scenario_data).strip()

    parts = []

    # Title (top-level or nested inside AI-Generated Scenario)
    title = scenario_data.get("Scenario Title") or scenario_data.get("scenario_title")
    if not title:
        ai_block = scenario_data.get("AI-Generated Scenario", {})
        if isinstance(ai_block, dict):
            title = ai_block.get("Scenario Title") or ai_block.get("scenario_title")
    if title:
        parts.append(f"**{title}**")

    # Narrative from AI-Generated Scenario block
    ai_block = scenario_data.get("AI-Generated Scenario", {})
    if isinstance(ai_block, dict):
        narrative = ai_block.get("Narrative") or ai_block.get("narrative")
        if narrative:
            parts.append(narrative)
        themes = ai_block.get("Themes") or ai_block.get("themes")
        if themes:
            parts.append(f"*Themes: {themes}*")

    # Fallback: if there was no AI-Generated Scenario block, try common keys
    if len(parts) <= 1:
        for key in ("narrative", "Narrative", "output_scenario", "scenario"):
            value = scenario_data.get(key)
            if value and isinstance(value, str):
                parts.append(value)
                break

    return "\n\n".join(parts) if parts else str(scenario_data)


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

    for index, scenario_data in enumerate(scenarios):
        _display_scenario_card(
            index,
            scenario_data,
            langsmith_enabled=langsmith_enabled,
            smith_client=smith_client,
            one_shot=one_shot,
        )


def _display_scenario_card(
    index,
    scenario_data,
    langsmith_enabled=False,
    smith_client=None,
    one_shot="",
):
    """Render a scenario card with clean readable text."""
    scenario_text = _scenario_to_text(scenario_data)

    with st.container(border=True):
        col_content, col_button = st.columns([3, 1])
        with col_content:
            st.header(f"Scenario {index + 1}")
            # FIX: use st.markdown instead of st.write so bold/italic
            # formatting in scenario_text renders correctly, and the value
            # is always a plain string — never a raw dict.
            st.markdown(scenario_text)

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


def collectFeedback(answer, column_index, scenario_data, smith_client, one_shot):
    """Submit optional scenario feedback when LangSmith is enabled."""
    st.session_state["scenario_feedback"][column_index] = answer["score"]
    num_score = score_mappings.get(answer["score"])
    # Convert to plain text for logging/LangSmith payload
    scenario_text = _scenario_to_text(scenario_data)
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