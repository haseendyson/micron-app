import streamlit as st
from langchain.output_parsers.json import SimpleJsonOutputParser

logger = st.logger.get_logger("micronarratives")


def _coerce_to_str(value) -> str:
    """
    Safely convert any scenario value to a plain string.
    Guards against None or dict values reaching st.text_area, which requires str.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    # Fallback: should not happen after scenario.py's _scenario_to_text fix,
    # but belt-and-braces for any pre-existing session state.
    import json
    try:
        return json.dumps(value, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def adapt_scenario(chat_model, adaptation_prompt_template):
    """
    Prepare the final version of the selected scenario.

    The active UX now mirrors the demo flow:
    - direct manual editing
    - optional AI-assisted adaptation
    - explicit accept/reject/reset controls
    """
    # FIX: coerce both session state values to str before any widget reads
    # them. Without this, if final_scenario or final_scenario_editor were
    # set to a dict (from the old code path), st.text_area raises:
    #   TypeError: text_area_proto.value = widget_state.value  (StringValue)
    if not st.session_state["final_scenario"]:
        raw = st.session_state["generated_scenarios"][
            st.session_state["selected_scenario_index"]
        ]
        st.session_state["final_scenario"] = _coerce_to_str(raw)

    if not st.session_state["final_scenario_editor"]:
        st.session_state["final_scenario_editor"] = _coerce_to_str(
            st.session_state["final_scenario"]
        )

    # Belt-and-braces: even if the values were already set, ensure they are str.
    # This catches any legacy session state from before the scenario.py fix.
    if not isinstance(st.session_state["final_scenario"], str):
        st.session_state["final_scenario"] = _coerce_to_str(
            st.session_state["final_scenario"]
        )
    if not isinstance(st.session_state["final_scenario_editor"], str):
        st.session_state["final_scenario_editor"] = _coerce_to_str(
            st.session_state["final_scenario_editor"]
        )

    st.markdown(
        "It seems that you selected a story that you liked. "
        "You can either edit this below, or ask the AI to adapt it for you."
    )
    st.divider()

    st.markdown("### Adapt yourself")
    st.text_area(
        "Edit your story directly",
        height=230,
        label_visibility="hidden",
        key="final_scenario_editor",
    )

    _, col_reset, col_done, _ = st.columns([1, 2, 2, 1])
    with col_reset:
        st.button(
            "Reset to original",
            icon="↩️",
            on_click=resetFinalScenario,
            use_container_width=True,
            type="secondary",
        )
    with col_done:
        st.button(
            "I'm happy with this!",
            on_click=confirmCurrentScenario,
            use_container_width=True,
            type="primary",
        )

    st.markdown("")
    adapt_container = st.container(border=True)
    with adapt_container:
        st.markdown("### Adapt with AI")
        display_adaptation_page(chat_model, adaptation_prompt_template)


def display_adaptation_page(chat_model, adaptation_prompt_template):
    """Render the adaptation chat flow."""
    messages = st.session_state["adapt_messages"]

    if not messages:
        messages.append(
            {
                "role": "ai",
                "content": "Okay, what's missing or could change to make this better?",
            }
        )

    for message in messages:
        st.chat_message(message["role"]).write(message["content"])

    if st.session_state.get("adapted_scenario"):
        get_feedback(st.container(), st.session_state["adapted_scenario"])
        return

    if st.session_state.get("adapt_is_processing"):
        pending_input = st.session_state.get("pending_adapt_input", "")
        if pending_input:
            with st.spinner("Working on your updated scenario..."):
                updated_scenario = update_scenario(
                    chat_model,
                    adaptation_prompt_template,
                    pending_input,
                )
            st.session_state["adapted_scenario"] = updated_scenario
        st.session_state["pending_adapt_input"] = ""
        st.session_state["adapt_is_processing"] = False
        st.rerun()

    chat_input = st.chat_input("Describe what you'd like to change...")
    if chat_input:
        messages.append({"role": "human", "content": chat_input})
        st.session_state["pending_adapt_input"] = chat_input
        st.session_state["adapt_is_processing"] = True
        st.rerun()


def get_feedback(container, updated_scenario):
    """Display feedback controls for an AI-generated adaptation."""
    del container

    # FIX: coerce to str before rendering — adapted_scenario should already
    # be a str from update_scenario(), but guard against edge cases.
    updated_scenario = _coerce_to_str(updated_scenario)

    st.chat_message("ai").markdown(
        f"Here is the adaptation:\n\n"
        f":orange[{updated_scenario}]\n\n"
        f"**What do you think?**"
    )

    col_reject, col_accept = st.columns(2)
    with col_reject:
        st.button(
            "Nope, let's try again",
            icon="↩️",
            use_container_width=True,
            on_click=rejectAdaptation,
        )
    with col_accept:
        st.button(
            "Yes, use this version",
            icon="✅",
            use_container_width=True,
            on_click=confirmFinalScenario,
            args=(updated_scenario,),
        )


def update_scenario(chat_model, adaptation_prompt_template, chat_input):
    """Use the chat model to apply an update to the current scenario."""
    chain = adaptation_prompt_template | chat_model | SimpleJsonOutputParser()

    try:
        new_response = chain.invoke(
            {
                "scenario": st.session_state["final_scenario_editor"],
                "input": chat_input,
                "language_level": st.session_state.get("language_level", "intermediate"),
            }
        )
    except Exception as exc:
        logger.error(f"Error generating adaptation: {exc}")
        return (
            "Sorry, something went wrong while adapting the scenario. "
            "Please try again."
        )

    if not isinstance(new_response, dict) or "new_scenario" not in new_response:
        logger.error(f"Unexpected adaptation response format: {new_response}")
        return (
            "Sorry, I couldn't generate an adaptation. "
            "Please try again with different wording."
        )

    # FIX: coerce the returned value to str — new_scenario could itself be a
    # nested dict if the LLM wraps its output unexpectedly.
    return _coerce_to_str(new_response["new_scenario"])


def resetFinalScenario():
    """Reset the draft back to the original selected scenario."""
    original = _coerce_to_str(
        st.session_state["generated_scenarios"][
            st.session_state["selected_scenario_index"]
        ]
    )
    st.session_state["final_scenario"] = original
    st.session_state["final_scenario_editor"] = original
    st.session_state["adapt_messages"] = []
    st.session_state["adapted_scenario"] = ""
    st.session_state["pending_adapt_input"] = ""
    st.session_state["adapt_is_processing"] = False


def iterateFinalScenario(new_scenario):
    """Compatibility wrapper for the older adapt flow."""
    new_scenario = _coerce_to_str(new_scenario)
    st.session_state["final_scenario"] = new_scenario
    st.session_state["final_scenario_editor"] = new_scenario
    st.session_state["adapted_scenario"] = ""
    st.session_state["adapt_messages"] = []
    st.session_state["pending_adapt_input"] = ""
    st.session_state["adapt_is_processing"] = False


def confirmCurrentScenario():
    """Accept the manually edited scenario as final."""
    st.session_state["final_scenario"] = st.session_state["final_scenario_editor"]
    st.session_state["agentState"] = "save"


def confirmFinalScenario(new_scenario):
    """Accept an AI-generated adaptation as final."""
    new_scenario = _coerce_to_str(new_scenario)
    st.session_state["final_scenario"] = new_scenario
    st.session_state["final_scenario_editor"] = new_scenario
    st.session_state["adapted_scenario"] = ""
    st.session_state["adapt_messages"] = []
    st.session_state["pending_adapt_input"] = ""
    st.session_state["adapt_is_processing"] = False


def rejectAdaptation():
    """Discard the current AI-generated adaptation and reopen the chat."""
    st.session_state["adapted_scenario"] = ""
    st.session_state["adapt_messages"] = []
    st.session_state["pending_adapt_input"] = ""
    st.session_state["adapt_is_processing"] = False