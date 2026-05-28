# Setup

In this file, we will collect notes on the options in the config files and other things that will be relevant to users owning an an instance of the app.

## Config loading

The app resolves its config in this order:

1. A file path passed on the command line, for example `streamlit run app.py my-config.toml`
2. `CONFIG_FILE` in Streamlit secrets

If none of those are provided, the app shows the config page.
On that page, you can either paste a config manually or use the button that inserts `configs/example_social.toml`.

## Running locally with pipenv

If you want to run the app locally without the dev container, use `pipenv`.

1. Install `pipenv` if needed:

```sh
pip install --user pipenv
```

2. From the repository root, install the locked dependencies:

```sh
pipenv sync
```

3. Create `.streamlit/secrets.toml` and add at least:

```toml
OPENAI_API_KEY = "<your-openai-api-key>"
```

4. If you want the app to load a fixed config immediately, also add:

```toml
CONFIG_FILE = "path-to-file/config-file-name.toml"
```

5. Start the app:

```sh
pipenv run streamlit run app.py
```

6. Or, if you prefer, activate the environment first:

```sh
pipenv shell
streamlit run app.py
```

If you have already used the dev container setup and `pipenv` behaves strangely, remove the local `.venv` directory first and then run `pipenv sync` again.

## Participant settings

### Participant ID tracking

In the `Participant settings` section of the config file, you can set whether a user of your app is required to provide a participant ID.
If a user must provide a participant ID, set `require_participant_id = true`; otherwise this setting can be left out entirely or set to `false`.

If a participant ID is required, the user will be prompted to provide one after giving consent.
They can either fill the input widget on their own, or, if a participant ID is embedded in the URL (e.g., as in `http://my-micro-narratives-app/?pid=TESTID1234`), confirm the suggestion in the prefilled input widget (in this example, `TESTID1234`).

If the participant ID is not required, a placeholder will be used when the data is sent to the database.
This will be the same as the Streamlit session ID.

If you choose to embed a participant ID in the URL of your app, use `pid`.
The app also accepts the older `participant_id` parameter for compatibility, but `pid` is now the primary option.

## Interaction flow

The app currently uses the following high-level flow:

1. Consent
2. Participant identification if required
3. Guided data collection chat
4. Scenario generation
5. Scenario selection
6. Rating the selected scenario on a `0-10` scale
7. Optional direct editing or AI-assisted adaptation
8. Final save and completion

### Connecting the app to a database

To connect the app to a DynamoDB database, see the [deployment guide](./deployment.md#prepare-dynamodb-database).
You will need to create a database and then configure your local version of the app to connect to the database (see the "Tip" note in the linked section).

To write the collected data to the database, you will need to provide `DYNAMODB_TABLE_NAME_WRITE = "your-table-name"`

### Fetching a participant's previous final scenario

If the chatbot should utilise a participant's previous data (for example, from an earlier part of a related study), this can be retrieved by doing the following:

- Set `require_participant_id = true` in the `Participant settings` section of the config file
- Use the participant's previous scenario in the bot's introductory text, by including the placeholder `{previous_scenario}` in the `intro` text in the `collection` section of the config file.
- Specify the name of the database to read the previous scenario from in the Streamlit secrets file, `DYNAMODB_TABLE_NAME_READ = "your-table-name"`

If the app is able to connect to the database, the participant's unique ID will be used to identify their selected scenario from the database.
Note the following:

- If multiple entries exist in the database for a given participant ID, the most recent one is chosen.
- If `require_participant_id` is unset or `false`, a unique one-time ID will be assigned to the participant.
It will therefore not be possible to identify a matching previous scenario.
If data from a previous scenario is required, ensure that the settings are as noted in the list above.

## LangSmith tracing

LangSmith tracing is optional.

By default, the app runs with LangSmith disabled via the `ENABLE_LANGSMITH` flag in [`app.py`](../app.py).
If you enable that flag, you should also provide the relevant `LANGCHAIN_*` secrets in your `.streamlit/secrets.toml` file.
