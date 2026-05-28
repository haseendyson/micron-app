import os
import sys
import tomllib
from pathlib import Path

import boto3
import streamlit as st
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.output_parsers.json import SimpleJsonOutputParser
from langchain_community.chat_message_histories import StreamlitChatMessageHistory
from langchain_openai import ChatOpenAI

try:
    from langsmith import Client
except ImportError:
    Client = None

import adapt
import conversation
import finalise
import identify
import review
import scenario
from llm_config import LLMConfig

ENABLE_LANGSMITH = False
logger = st.logger.get_logger("micronarratives")


def stateAgent(
    llm_prompts,
    chat_model,
    extraction_chain,
    message_history,
    memory,
    table_write,
    table_read,
):
    """
    Main flow function of the whole interaction -- keeps track of the system state and
    calls the appropriate procedure on each streamlit refresh.
    Args:
        llm_prompts (LLMConfig): class containing text and templates for the app
        chat_model (ChatOpenAI): OpenAI chat model
        smith_client (langsmith.Client): LangSmith client
        message_history (StreamlitChatMessageHistory): chat history, stored in Streamlit
            session state
        memory (ConversationBufferMemory): chat history
        table (DynamoDB.Table | None): table where the data will be stored
        table (DynamoDB.Table | None): table from where previous data will be read
    """

    logger.debug(
        f"Running stateAgent loop\tsession state: {st.session_state['agentState']}"
    )

    conversation_chain = ConversationChain(
        prompt=llm_prompts.questions_prompt_template,
        llm=chat_model,
        verbose=logger.getEffectiveLevel() < 20,
        memory=memory,
    )

    # Select the appropriate agent depending on session state
    # (conversation/check/scenario/review/adapt/finalise)
    match st.session_state["agentState"]:
        case "identify":
            identify.get_participant_data(llm_prompts)
        case "collect":
            conversation.conduct_q_and_a(
                llm_prompts,
                chat_model,
                extraction_chain,
                conversation_chain,
                message_history,
                table_read,
            )
        case "review":
            review.review_scenarios(
                ENABLE_LANGSMITH,
                st.session_state.get("langsmith_client"),
                llm_prompts.one_shot,
            )
        case "rate":
            scenario.rate_selected_scenario()
        case "adapt":
            adapt.adapt_scenario(chat_model, llm_prompts.adaptation_prompt_template)
        case "save":
            finalise.confirm_final_scenario(message_history, table_write)


def markConsent():
    """
    Updates the session's consent marker; used when button is pressed on consent page.
    """

    logger.info("Consent given")
    st.session_state["consent"] = True


def requestConsent(consent_text):
    """
    Generates a page with the provided consent text and a button to accept.
    """

    logger.info("Consent not provided")
    consent_message = st.container()
    with consent_message:
        st.markdown(consent_text)
        st.button("I accept", key="consent_button", on_click=markConsent)


@st.cache_resource
def createLLMPromptsFromFile(config_file):
    """
    Generates a set of prompts and other strings required by the app from a config file.
    Cached to share across all users, sessions and re-runs.

    Args:
        config_file (str): path to configuration file
    """

    logger.info(f"Configuring app using {config_file}\n")
    llm_prompts = LLMConfig.from_file(config_file)

    return llm_prompts


@st.cache_data
def createLLMPromptsFromUserInput(config_toml):
    """
    Generates a set of prompts and other strings required by the app from a custom
    configuration uploaded by a user. Cached to share across re-runs.

    Args:
        config_toml (str): TOML-formatted string containing app configuration
    """

    logger.info("Configuring app with custom configuration from user\n")
    llm_prompts = LLMConfig(config_toml)

    return llm_prompts


def initialiseAppPage():
    """
    Initialise the Streamlit app's page.
    """

    st.set_page_config(page_title="MicrON", page_icon="📖")
    st.title("📖 MicrON")

    # Hide GitHub icon
    st.markdown(
        """
        <style>
        [data-testid="stToolbarActions"] {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialiseStreamlitSessionState(llm_prompts, num_scenarios):
    """
    Initialise variables that persist throughout refreshes of a Streamlit session.
    """

    if "session_id" in st.session_state:
        return

    session_id = st.runtime.scriptrunner.get_script_run_ctx().session_id
    url_participant_id = st.query_params.get("pid") or st.query_params.get(
        "participant_id"
    )
    if isinstance(url_participant_id, list):
        url_participant_id = url_participant_id[0] if url_participant_id else None
    if isinstance(url_participant_id, str):
        url_participant_id = url_participant_id.strip() or None

    if url_participant_id:
        participant_id = url_participant_id
        initial_state = "collect"
    elif not llm_prompts.require_participant_id:
        participant_id = session_id
        initial_state = "collect"
    else:
        participant_id = None
        initial_state = "identify"

    defaults = {
        "participant_id": participant_id,
        "consent": False,
        "agentState": initial_state,
        "session_id": session_id,
        "langsmith_run_id": None,
        "langsmith_client": None,
        "previous_scenario": None,
        "summary_answers": {},
        "generated_scenarios": [""] * num_scenarios,
        "scenario_feedback": [None] * num_scenarios,
        "scenario_judgement": [""] * num_scenarios,
        "selected_scenario_index": None,
        "selected_scenario_review": None,
        "final_scenario": "",
        "final_scenario_editor": "",
        "adapt_messages": [],
        "adapted_scenario": "",
        "adapt_is_processing": False,
        "pending_adapt_input": "",
        "is_processing": False,
    }

    if participant_id is None and "participant_id" in st.query_params:
        defaults["participant_id"] = st.query_params["participant_id"]

    for key, value in defaults.items():
        st.session_state[key] = value


@st.cache_resource
def loadSettings():
    """
    Obtain settings from streamlit secrets file and/or command line arguments.
    """

    if ENABLE_LANGSMITH:
        if st.secrets.get("LANGCHAIN_API_KEY"):
            os.environ["LANGCHAIN_API_KEY"] = st.secrets["LANGCHAIN_API_KEY"]
        if st.secrets.get("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = st.secrets["LANGCHAIN_PROJECT"]
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if st.secrets.get("LANGCHAIN_ENDPOINT"):
            os.environ["LANGCHAIN_ENDPOINT"] = st.secrets["LANGCHAIN_ENDPOINT"]
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    # Get an OpenAI API Key before continuing
    if "OPENAI_API_KEY" in st.secrets:
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
    else:
        os.environ["OPENAI_API_KEY"] = st.sidebar.text_input(
            "OpenAI API Key", type="password"
        )
    if not os.environ["OPENAI_API_KEY"]:
        st.info("Enter an OpenAI API Key to continue")
        st.stop()

    # Identify config file from input args or streamlit secrets.
    input_args = sys.argv[1:]
    config_file = input_args[0] if len(input_args) else st.secrets.get("CONFIG_FILE")

    return config_file


def buildExtractionChain(extraction_prompt_template, model_name):
    """
    Create a chain to generate json-formatted output based on the conversation history.
    Args:
        extraction_prompt (str): text for the extraction prompt
        model_name (str): name of the OpenAI LLM
    Returns:
        RunnableSequence: chain to extract json-formatted output from conversation
    """

    extraction_llm = ChatOpenAI(
        temperature=0.1, model=model_name, openai_api_key=os.environ["OPENAI_API_KEY"]
    )

    extraction_chain = (
        extraction_prompt_template | extraction_llm | SimpleJsonOutputParser()
    )

    return extraction_chain


@st.cache_resource
def createDatabaseLink(table_name, required=False):
    """
    Set up a boto3 session to handle connection to the DynamoDB database (if required).
    If no table name is provided, connection to the database will not be attempted.
    Relies on credentials being available in the current environment. If the table is
    required and not accessible, an exception will immediately be thrown.

    Args:
        table_name (str | None): Name of the table to connect to, if required
        required (bool): Whether connection to this table is strictly required

    Returns:
        table (DynamoDB.Table | None): the DynamoDB table where the data will be stored/
        retrieved from, or None if the database is not required
    """

    table = None

    if table_name:
        session = boto3.Session()
        dynamodb_resource = session.resource("dynamodb")
        existing_tables = [t.name for t in dynamodb_resource.tables.all()]

        if table_name in existing_tables:
            table = dynamodb_resource.Table(table_name)
            logger.info(f"Found database table {table_name}")
        else:
            logger.warning(
                f"Unable to find database table {table_name}; "
                "connection will not be attempted"
            )

    if required and not table:
        if table_name is None:
            raise Exception(
                "Stopping: No table name provided in secrets (DYNAMODB_TABLE_NAME_READ)"
            )
        else:
            raise Exception(f"Stopping: Table '{table_name}' not found in DynamoDB")

    return table


def upload_config():
    logger.info("Creating form")

    form_placeholder = st.empty()
    example_config_path = Path(
        st.secrets.get("EXAMPLE_CONFIG_FILE", "configs/example_social.toml")
    )
    example_config_text = example_config_path.read_text(encoding="utf-8")

    if "config_text" not in st.session_state:
        st.session_state["config_text"] = ""

    def insert_example_config():
        st.session_state["config_text"] = example_config_text

    with form_placeholder.form("upload_config_form"):
        st.text_area(
            "Provide your config for the micro-narratives app below:",
            height=680,
            key="config_text",
        )

        submit_col, insert_col = st.columns(2)
        submitted = submit_col.form_submit_button(
            "Submit",
            type="primary",
            use_container_width=True,
        )
        insert_col.form_submit_button(
            "Insert example config",
            on_click=insert_example_config,
            use_container_width=True,
        )

        if submitted:
            if st.session_state["config_text"] == "":
                st.error("Config is empty")
            else:
                try:
                    config_toml = tomllib.loads(st.session_state["config_text"])
                    LLMConfig(config_toml)
                except tomllib.TOMLDecodeError as e:
                    st.error("TOML is invalid:")
                    st.error(e)
                except KeyError as e:
                    st.error("Expected section/key not provided:")
                    st.error(e)
                else:
                    form_placeholder.empty()
                    return config_toml
        st.stop()


if __name__ == "__main__":
    initialiseAppPage()

    config_file = loadSettings()

    if "config_toml" not in st.session_state:
        st.session_state["config_toml"] = ""        
    if config_file:
        st.session_state["config_toml"] = ""
        llm_prompts = createLLMPromptsFromFile(config_file)
    else:
        if not st.session_state["config_toml"]:
            st.session_state["config_toml"] = upload_config()
        llm_prompts = createLLMPromptsFromUserInput(st.session_state["config_toml"])

    table_write = createDatabaseLink(st.secrets.get("DYNAMODB_TABLE_NAME_WRITE"))
    table_read = createDatabaseLink(
        st.secrets.get("DYNAMODB_TABLE_NAME_READ"),
        llm_prompts.require_previous_final_scenario,
    )

    # Initialise Streamlit session and optional LangSmith
    initialiseStreamlitSessionState(llm_prompts, len(llm_prompts.personas))
    chat_model = ChatOpenAI(
        temperature=0.3,
        model=llm_prompts.model_name,
        openai_api_key=os.environ["OPENAI_API_KEY"],
    )

    if ENABLE_LANGSMITH and Client is not None:
        st.session_state["langsmith_client"] = Client()
    else:
        st.session_state["langsmith_client"] = None

    message_history = StreamlitChatMessageHistory(key="langchain_messages")
    memory = ConversationBufferMemory(memory_key="history", chat_memory=message_history)

    extraction_chain = buildExtractionChain(
        llm_prompts.extraction_prompt_template, llm_prompts.model_name
    )

    if st.session_state["consent"]:
        stateAgent(
            llm_prompts,
            chat_model,
            extraction_chain,
            message_history,
            memory,
            table_write,
            table_read,
        )
    else:
        requestConsent(llm_prompts.intro_and_consent)
