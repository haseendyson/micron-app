import tomllib

from langchain_core.prompts import PromptTemplate


class LLMConfig:
    """
    Configuration for the micro-narratives app.

    This class contains text and prompt templates that are used throughout the
    micro-narratives app. Some of the text is common between all instances of the app
    and is hardcoded in this class; the rest is specified by the app's owner using a
    toml file which is read in during instantiation of this class.

    Attributes:
        model_name (str): name of the LLM to be used by the app (defaults to gpt-4o).
        intro_and_consent (str): text to be shown on the first page of the app, where
            user consent is requested.
        questions_intro (str): text to be shown at the start of the conversation between
            the user and bot.
        questions_prompt_template (LangChain.PromptTemplate): instructions for the bot
            regarding the collection of data, including questions provided by the owner
            of the app.
        questions_outro (str): text to be shown at the end of the conversation between
            the bot and user.
        extraction_prompt_template (LangChain.PromptTemplate): instructions for the bot
            to create a JSON object containing summaries of aspects of the conversation
            had with the user.
        summary_keys ([str]): list of keys containing identifiers for the aspects of the
            conversation which are to be summarised.
        personas ([str]): list of personas that are to be used when creating summaries
            of the user's experience.
        one_shot (str): a complete one-shot example, containing a conversation and
            resulting scenario.
        one_shot_conversation (str): example conversation, as used in one_shot (above).
        scenario_prompt_template (LangChain.PromptTemplate): instructions for the bot to
            create a summary of the conversation in the style of a particular persona.
        adaptation_prompt_template (LangChain.PromptTemplate): instructions for the bot
            to adapt the proposed scenario according to suggestions by the user.
    """

    @classmethod
    def from_file(cls, filename):
        with open(filename, "rb") as f:
            config = tomllib.load(f)
        return cls(config)

    def __init__(self, config):
        """
        Initialises the configuration class based on text provided by the owner of the
        app in a toml-formatted file.
        Args:
            filename (str): path to the toml file that contains the text needed to
            configure the app. Examples can be found in the `configs` directory.
        """

        # Get participant settings, default to {} if section doesn't exist
        participant_config = config.get("participant", {})
        self.require_participant_id = participant_config.get(
            "require_participant_id", False
        )
        self.editable_participant_id = participant_config.get(
            "editable_participant_id", True
        )
        self.participant_collection_text = participant_config.get("text", "")
        self.require_previous_final_scenario = self.check_if_previous_scenario_required(
            config["collection"]["intro"]
        )

        # General settings
        self.model_name = config.get("model", "gpt-4o")

        # Consent page
        self.intro_and_consent = config["consent"]["intro_and_consent"].strip()

        # Conversation page
        self.questions_intro_prompt_template = PromptTemplate(
            template=config["collection"]["intro"].strip()
            + "\n\nLet me know when you're ready!",
            input_variables=[]
        )
        self.questions_prompt_template = self.generate_questions_prompt_template(
            config["collection"]
        )
        self.questions_outro = (
            "Great, I think I got all I need -- but let me double check!"
        )

        # Extraction process
        self.extraction_prompt_template = self.generate_extraction_prompt_template(
            config["summaries"]["questions"]
        )
        self.summary_keys = list(config["summaries"]["questions"].keys())

        # Scenario generation and adaptation
        self.personas = [
            persona.strip()
            for persona in list(config["summaries"]["personas"].values())
        ]
        if len(self.personas) > 3:
            self.personas = self.personas[:3]
        self.one_shot = self.generate_one_shot(config["example"])
        self.one_shot_conversation = config["example"]["conversation"].strip()
        self.scenario_prompt_template = self.generate_scenario_prompt_template(
            config["summaries"]["questions"]
        )
        self.adaptation_prompt_template = self.generate_adaptation_prompt_template()

    def check_if_previous_scenario_required(self, intro_text):
        """
        Determines whether the text of a previous scenario is required by checking for a
        placeholder in the introductory text of the questions section. If so, ensures
        that participant ID is requested.
        """

        require_previous_scenario = "{previous_scenario}" in intro_text

        if require_previous_scenario and not self.require_participant_id:
            raise ValueError(
                "Text of a previous scenario is required, "
                "but participant ID is not tracked. "
                "Set 'require_participant_id' = true in configuration file"
            )

        return require_previous_scenario

    def generate_questions_prompt_template(self, data_collection):
        """
        Creates a prompt template to ask a list of questions to the user in a particular
        style. This prompt contains instructions to the bot to remain on-topic, and
        includes a marker for the end of the conversation ("FINISHED").
        Args:
            data_collection {}: dict containing the following items:
                persona (str): the style in which the questions are to be asked
                questions ([str]): list of questions to be answered by the user
                language_type (str): the style of language to be used by the bot
                topic_restriction (str): instructions to keep the bot on-topic
        Returns:
            LangChain.PromptTemplate: a prompt template with instructions on which
                questions to ask the user, and how to do so.
        """

        questions_prompt_text = (
            "{persona}\n\n"
            "Your goal is to gather structured answers to the following questions:\n\n"
            "{questions}\n"
            "Ask each question one at a time. Do not include question numbers or list formatting when you ask the next question.\n"
            "Ask each question as a natural conversational sentence.\n"            "Do not ask more than one question in a single response.\n"
            "If the human's answer is incomplete or unclear, ask a follow-up clarification question instead of moving on to the next main question.\n"
            "If the human has already answered the current question, then ask only the next question.\n"            "{language_type}\n"
            "Ensure you get at least a basic answer to each question before moving to "
            "the next.\n"
            "Never answer for the human. "
            "If you unsure what the human meant, ask again. "
            "{topic_restriction}\n"
            "{collection_complete}, stop the conversation and write a single word "
            '"FINISHED".\n\n'
            "Current conversation:\n"
            "{history}\n"
            "Human: {input}\n"
            "AI: "
        )

        questions_prompt = PromptTemplate(
            template=questions_prompt_text,
            input_variables=["history", "input"],
            partial_variables={
                "persona": data_collection["persona"],
                "questions": self._generate_question_list(data_collection["questions"]),
                "language_type": data_collection["language_type"],
                "topic_restriction": data_collection["topic_restriction"],
                "collection_complete": self._generate_collection_complete_text(
                    data_collection["questions"]
                ),
            },
        )

        return questions_prompt

    def _generate_question_list(self, questions):
        """
        Creates a list of questions to be shown to the LLM, based on a list of
        questions.
        Args:
            questions (list[str]): a list of questions that the LLM should ask
        Returns:
            str: bullet-formatted questions, one per line
        """

        question_list = ""
        for question in questions:
            question_list += f"- {question}\n"

        return question_list

    def _generate_collection_complete_text(self, questions):
        """
        Creates instructions for what the LLM should do when singular/plural questions
        have been asked.
        Args:
            questions (list[str]): a list of questions that the LLM should ask
        Returns:
            str: concluding text, phrased appropriately for singular/plural questions
        """

        n_questions = len(questions)
        if n_questions == 1:
            return "Once you have collected an answer to the question"
        else:
            return f"Once you have collected answers to all {n_questions} questions"

    def generate_extraction_prompt_template(self, questions):
        """
        Creates instructions for the LLM to extract a JSON-formatted summary from the
        conversation between the bot and the user.
        Args:
            questions ([{key: question}]): list of questions, where the key is a short
                identifier for the content of each question.
        Returns:
            LangChain.PromptTemplate: prompt containing instructions on how to generate
                the JSON summary from the conversation.
        """

        extraction_prompt_text = (
            "You are an expert extraction algorithm. "
            "Only extract relevant information from the Human answers in the text. "
            "Use only the words and phrases that the text contains. "
            "If you do not know the value of an attribute asked to extract, return "
            "null for the attribute's value.\n\n"
            "You will output a JSON with {keys_string} keys.\n\n"
            "{questions}\n"
            "Message to date: {conversation_history}\n\n"
            "Remember, only extract text that is in the messages above and do not "
            "change it. "
        )

        extraction_prompt_template = PromptTemplate(
            template=extraction_prompt_text,
            input_variables=["conversation_history"],
            partial_variables={
                "keys_string": self._generate_summary_keys(questions),
                "questions": self._generate_summary_questions(questions),
            },
        )

        return extraction_prompt_template

    def _generate_summary_keys(self, questions):
        """
        Produces a comma-separated string that contains the list of keys that should be
        used when the app creates a summary of the conversation in JSON format.
        Args:
            questions ([{key: question}]): list of questions, where the key is a short
                identifier for the content of each question.
        Returns:
            str: comma/"and"-separated list of keys, for use in the summary template.
        """
        keys = list(questions.keys())
        keys_string = f"`{keys[0]}`"
        for key in keys[1:-1]:
            keys_string += f", `{key}`"
        if len(keys_string):
            keys_string += f", and `{keys[-1]}`"

        return keys_string

    def _generate_summary_questions(self, questions):
        """
        Provides an enumerated list of the questions which are to be used when creating
        the JSON-formatted summary of the conversation.
        Args:
            questions ([{key: question}]): list of questions, where the key is a short
                identifier for the content of each question.
        Returns:
            str: enumerated list of questions, for use in the summary template.
        """

        questions_text = (
            "These correspond to the following question"
            f"{'s' if len(questions) else ''}:\n"
        )

        for count, question in enumerate(questions.values()):
            questions_text += f"{count + 1}: {question}\n"

        return questions_text

    def generate_adaptation_prompt_template(self):
        """
        Creates a prompt which will allow users to adapt the scenario if they feel that
        the proposed scenarios do not accurately represent their experience. This
        template is consistent across all instances of the app; it is not configured by
        the app creator.
        Returns:
            LangChain.PromptTemplate: prompt containing instructions on how to adapt the
                scenario following feedback from the user
        """

        prompt_adaptation_template = PromptTemplate.from_template(
            "You're a helpful assistant, helping students adapt a scenario to their "
            "liking. Use the participant's language level: {language_level}. "
            "If the level is basic, keep the adaptation short and easy to understand. "
            "If it is intermediate, use clear everyday language. "
            "If it is advanced, use richer vocabulary and slightly more complex sentence structure.\n\n"
            "The original scenario this student came with:\n\n"
            "Scenario: {scenario}.\n\n"
            "Their current request is {input}.\n\n"
            "Suggest an alternative version of the scenario. "
            "Keep the language and content as similar as possible, while fulfilling "
            "the student's request.\n\n"
            "Return your answer as a JSON file with a single entry called "
            "'new_scenario'."
        )

        return prompt_adaptation_template

    def generate_one_shot(self, example):
        """
        Creates a complete one-shot example based on the conversation and scenario
        provided by the app creator.
        Args:
            example {conversation: str, scenario: str}: dictionary containing the
                example conversation and scenario.
        Returns:
            str: Complete one-shot text containing the example conversation and
                resulting scenario.
        """
        one_shot = (
            "Example:\n"
            f"{example['conversation'].strip()}\n\n"
            "The scenario based on these responses:\n"
            f'"{example["scenario"].strip()}"'
        )

        return one_shot

    def generate_scenario_prompt_template(self, questions):
        """
        Creates a prompt template with instructions on how a scenario should be
        generated, given the summary of the conversation between the bot and the user
        and a persona provided by the app creator which describes the tone of the
        scenario.
        Args:
            questions ([{key: question}]): list of questions, where the key is a short
                identifier for the content of each question.
        Returns:
            LangChain.PromptTemplate: instructions on how to generate a scenario.
        """

        scenario_prompt_template_text = (
            (
                "{persona}\n\n"
                "{one_shot}\n\n"
                "Your task:\nCreate one complete scenario based on the following answers:\n\n"
                "Use the participant's language level: {language_level}. "
                "If the level is basic, keep the scenario short and easy to understand. "
                "If it is intermediate, use clear everyday language. "
                "If it is advanced, use richer vocabulary and slightly more complex sentence structure.\n\n"
                "Write a full scenario with the following structure:\n"
                "1. A bolded title that is clearly different from the other scenarios and avoids repeating the same wording.\n"
                "2. One or two paragraphs describing the future healthcare vision from this persona's perspective.\n"
                "3. A list of themes at the end, prefixed with 'Themes:'.\n\n"
                "Use a natural, informal South Asian voice. Mention family, neighbours, community support, simple care rituals, or local trust. "
                "Do not be formal — write as if you were sharing a real story from the neighbourhood.\n\n"
                "Give each title a distinct and specific heading that does not repeat the same short phrase used by the other scenarios.\n"
                "Keep the title separate from the narrative and avoid repeating it as the first sentence.\n\n"
            )
            + self._generate_q_and_a(questions)
            + (
                "\n"
                "Create a scenario based on these responses.\n\n"
                "Your output should be a JSON file with a single entry called \"output_scenario\" "
                "and that entry should itself be a JSON object with keys \"Scenario Title\", \"Narrative\", and \"Themes\".\n"
                "Do not return only a title or themes; always provide a title, narrative paragraph(s), and themes.\n"
            )
        )

        scenario_prompt_template = PromptTemplate(
            template=scenario_prompt_template_text,
            input_variables=["persona", "language_level"] + list(questions.keys()),
            partial_variables={
                "one_shot": self.one_shot,
            },
        )

        return scenario_prompt_template

    def _generate_q_and_a(self, questions):
        """
        Creates a string marking questions and answers from the summary questions
        provided by the user (which will be used as the basis for the JSON summary of
        the conversation).
        Args:
            questions ({name: question}): dict containing summary questions
        Returns:
            str: formatted questions and answers, with answers as templates to be filled
                in with data from the conversation
        """

        q_and_a = ""
        for key, question in questions.items():
            q_and_a += f"Question: {question}\n"
            q_and_a += f"Answer: {{{key}}}\n"

        return q_and_a
