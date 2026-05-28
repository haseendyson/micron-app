A Streamlit app to collect rich yet narrowly-scoped qualitative data from study participants.

## :wave: Welcome

Welcome to the micro-narratives project!

This repository contains the code for the main micro-narratives application.
It is currently under active development, so expect to see frequent changes here.

We welcome your feedback and input - as a small community, we are keen to hear about your experiences when using, testing and deploying the application.
Please [open an issue](https://github.com/micro-narratives/micro-narratives-app/issues) if you experience a problem, or have suggestions for new features.

Write access to this repository is restricted to the main project developers, so if you would like to make direct changes to the code yourself, make a fork of this repository before beginning.
Note that GitHub's forking policy means that all forks of this repo will remain private, but will inherit permissions from this repository.
The fork will therefore be visible by others within this GitHub organisation (for more details, see [GitHub's documentation](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/about-permissions-and-visibility-of-forks)).

The documentation within this file should be sufficient for you to get a local instance of the app up and running.
For more in-depth documentation and deployment guidance, see the [`docs` folder](./docs).

## :arrow_down_small: Get the code

If you have write access to this repository, or have no need to push your changes back, clone the repository from GitHub:

```shell
git clone git@github.com:micro-narratives/micro-narratives-app.git
```

Otherwise, you can [make a fork](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo) and then obtain a clone of the fork:

```shell
git clone git@github.com:<your-account-or-organisation>/micro-narratives-app.git
```

If you have not already done so, you may need to [generate an SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) and [add it to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).

## :technologist: Running the app

There are two main options to run the app locally:

- [Run the app inside a dev container](#running-the-app-via-a-dev-container)
- [Run the app using your own Python installation](#running-via-your-own-python-installation)

The first option is recommended for most users.

### Create a Streamlit secrets file

Regardless of how you choose to run the app, you will need to create a `.streamlit` directory inside the repository and add a new file, `secrets.toml`, which contains various API keys and settings for the app.
This file should not be committed to version control.

The file should have the following structure, which you should fill in with your own API keys and project details:

```toml
OPENAI_API_KEY = "<your-openai-api-key>"
```

If you want to enable LangSmith tracing, also add:

```toml
LANGCHAIN_API_KEY = "<your-langchain-api-key>"
LANGCHAIN_PROJECT = "<your-langchain-project-name>"
LANGCHAIN_TRACING_V2 = true
```

LangSmith is currently disabled by default in [`app.py`](./app.py) via the `ENABLE_LANGSMITH` flag, so these extra variables are optional unless you switch that flag on.

### Running the app via a dev container

You will need to have [VSCode](https://code.visualstudio.com/download) and [Docker](https://www.docker.com/products/docker-desktop/) installed.
Make sure that Docker is running before you proceed with the remaining steps. 

Open VSCode, and then install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers). To do so, open the Extensions menu (through one of the icons on the left of your screen) and you can search for the Dev Containers extension there.

From the Command Palette in VSCode (at the top of the screen, or press `F1` or `Ctrl+Shift+p`), run the "Dev Containers: Open Folder in Container" command. 
Select the project's folder, and the dev container will start up.

When running the container, your project directory is automatically mounted at `/workspaces/micro-narratives-app`. 
Any files you create or modify in this directory will persist between container rebuilds and are synchronized between your local machine and the container.

For further details about dev containers, see [VSCode's documentation](https://code.visualstudio.com/docs/devcontainers/containers).

### Running via your own Python installation

It is recommended that you use Python 3.12 to run this app.

This project uses [`pipenv`](https://pipenv.pypa.io/en/latest/installation.html) for both creating a virtual environment and managing dependencies.
If you don't have `pipenv` installed already, do so with

```sh
pip install --user pipenv
```

or see the [guide in `pipenv`'s documentation](https://pipenv.pypa.io/en/latest/installation.html) for alternative installation methods.

_Note: We have had reports of issues with `pipenv` if it is used after the devcontainer setup method has already been used. If this affects you, remove the `.venv` directory that was created by the devcontainer before using `pipenv`._

Create a virtual environment and install the required packages with

```sh
pipenv sync
```

> [!TIP]
> If you do not have Python 3.12, you can try
>
>```shell
> pipenv --python <your-python-version> install 
> ```
>
> first.
If there are no incompatibilities with other package requirements, `pipenv sync` will be able to install the dependencies.

You can then run the app directly with

```sh
pipenv run streamlit run app.py
```

or alternatively, enable the virtual environment first and run all subsequent commands without `pipenv`:

```sh
pipenv shell
streamlit run app.py
```

More details on the [`shell`](https://pipenv.pypa.io/en/latest/cli.html#shell), [`sync`](https://pipenv.pypa.io/en/latest/cli.html#sync) and [`run`](https://pipenv.pypa.io/en/latest/cli.html#run) commands can be found in `pipenv`'s [CLI documentation](https://pipenv.pypa.io/en/latest/cli.html).

## :rocket: Deploying the app

See [`docs/deployment.md`](docs/deployment.md) for a guide to deploying the app on Streamlit Community Cloud or AWS.

## :pen: Customising app content

By default, the app will start with a page where a user can specify the config to be used for that session.
This is mainly suitable for demos; generally, we will want to specify a single config file to be used whenever the app is loaded.

To tell the app to use content from a specific config file, you can either:

add another line to your Streamlit secrets file (or the secrets configuration in Streamlit Community Cloud):

```toml
CONFIG_FILE = 'path-to-file/config-file-name.toml'
```

or run the app with an additional argument to specify the file:

```sh
streamlit run app.py path-to-file/config-file-name.toml
```

Config precedence is:

1. The path passed to `streamlit run app.py ...`
2. `CONFIG_FILE` in Streamlit secrets

If neither option is used, the app shows the config input page.
From there, you can either paste a config manually or use the button that inserts the default [`configs/example_social.toml`](./configs/example_social.toml) content for quick testing.
If you want that button to insert a different example file, set `EXAMPLE_CONFIG_FILE` in Streamlit secrets.
More details about each of the sections are available inside the example configuration files.

## :speech_balloon: Current interaction flow

The default app flow is now:

1. The user gives consent.
2. They provide a participant ID if the config requires one, or the app uses the Streamlit session ID.
3. The app collects a short guided conversation.
4. It generates candidate scenarios.
5. The user selects one scenario to continue with.
6. The user rates how close that scenario is to what they want to say on a `0-10` scale.
7. If the rating is not `10`, the user can either edit the text directly or ask the AI to adapt it.
8. The final scenario is saved and shown on the completion page.

## :gear: Other options

By default, the logging level of the app is set to `info`.
This will provide regular reports of user interactions with the app.
If other [levels](https://docs.python.org/3/library/logging.html#logging-levels) are required (e.g. `warning`, `debug`), they can be specified when the app is run:

```sh
streamlit run app.py --logger.level=<level>
```
