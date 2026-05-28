import streamlit as st

import identify
import scenario

logger = st.logger.get_logger("micronarratives")


def conduct_q_and_a(
    llm_prompts,
    chat_model,
    extraction_chain,
    conversation_chain,
    message_history,
    table_read,
):
    """Collects answers to main questions from the user.

    The conversation flow is stored in the msgs variable (which acts as the persistent
    langchain-streamlit memory for the bot). The prompt for LLM must be set up to
    return "FINISHED" when all data is collected.

    Args:
        llm_prompts (LLMConfig): class containing text and templates for the app
        chat_model (ChatOpenAI): OpenAI chat model
        extraction_chain: chain for extraction
        conversation_chain (ConversationChain): chain for questions and answers
        message_history (StreamlitChatMessageHistory): chat history
        table_read (DynamoDB.Table | None): table where the previous
            scenario may be read
    """

    st.markdown("#### Collecting your story")

    messages_container = st.container(border=True)
    chat_input = st.chat_input(disabled=st.session_state.get("is_processing", False))

    # If this is the first run, set up the intro
    if len(message_history.messages) == 0:
        intro_text = _get_intro_message(llm_prompts, table_read)
        message_history.add_ai_message(intro_text)

    # Show the whole conversation history
    with messages_container:
        for msg in message_history.messages:
            if "FINISHED" in msg.content:
                st.divider()
                st.chat_message("ai").write(llm_prompts.questions_outro)
            else:
                st.chat_message(msg.type).write(msg.content)

    # If user inputs a new answer, generate new response and add into msgs
    if chat_input:
        # Note: new messages are saved to history automatically by Langchain during run
        with messages_container:
            # show that the message was accepted
            st.chat_message("human").write(chat_input)

            # generate the reply using langchain
            response = conversation_chain.invoke(input=chat_input)

            # the prompt must be set up to return "FINISHED" once all questions have
            # been answered
            # If finished, move the flow to summarisation, otherwise continue.
            if "FINISHED" in response["response"]:
                st.session_state["is_processing"] = True
                logger.info(
                    f"User {st.session_state['participant_id']}: Conversation complete"
                )
                st.rerun()
            else:
                st.chat_message("ai").write(response["response"])

    if st.session_state.get("is_processing"):
        _process_completed_conversation(
            llm_prompts,
            chat_model,
            message_history,
            extraction_chain,
        )


def _process_completed_conversation(
    llm_prompts,
    chat_model,
    message_history,
    extraction_chain,
):
    """Generate summary data and scenarios once collection is finished."""
    summary_answers = scenario.generate_summary(
        llm_prompts,
        message_history,
        extraction_chain,
        testing=False,
    )
    generated_scenarios = scenario.generate_scenarios_with_progress(
        llm_prompts,
        chat_model,
        summary_answers,
        langsmith_enabled=st.session_state.get("langsmith_client") is not None,
    )

    if len(generated_scenarios) == 1:
        st.session_state["selected_scenario_index"] = 0
        st.session_state["agentState"] = "rate"
    else:
        st.session_state["agentState"] = "review"

    st.session_state["is_processing"] = False
    st.button("I'm ready -- show me!", key="progressButton")


def _get_intro_message(llm_prompts, table_read):
    """Build the intro message, injecting a previous scenario when required."""
    if not llm_prompts.require_previous_final_scenario:
        st.session_state["previous_scenario"] = None
        return llm_prompts.questions_intro_prompt_template.format(previous_scenario="")

    previous_scenario = identify.get_previous_scenario_from_db(
        table_read,
        st.session_state.get("participant_id"),
    )

    if not previous_scenario:
        st.error(
            "This study requires your previous scenario, but we couldn't find one "
            "associated with your participant ID. Please contact the researcher."
        )
        st.stop()

    st.session_state["previous_scenario"] = previous_scenario
    return llm_prompts.questions_intro_prompt_template.format(
        previous_scenario=previous_scenario
    )
