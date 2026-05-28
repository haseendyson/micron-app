# Deployment

## Streamlit Community Cloud

[Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) is recommended for quick prototypes of the app.
The resources on which the app will be hosted are determined by Streamlit and are not configurable, so switching to AWS or another cloud provider is preferred when additional resources or extra control over the setup is needed.
However, it is a very convenient starting point for early-stage deployments.

The repository is already compatible with Streamlit Community Cloud in that it has the correct structure and contains a file listing the dependencies of the project.
You can therefore skip directly to the ["Deploy!"](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) instructions in Streamlit's documentation.
Streamlit Cloud's deployments are triggered on every push to a selected branch of a GitHub repository, so your app will update automatically when you do so.

Once you have set up the deployment, you will need to follow through the ["Optional: Configure secrets and Python version"](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy#optional-configure-secrets-and-python-version) section further down the page.
The Python version should be set to 3.12.
The required secrets are those described in the main setup guide; see details in the [README.md](../README.md#create-a-streamlit-secrets-file) file.
At minimum, this means `OPENAI_API_KEY`.
The `LANGCHAIN_*` secrets are only needed if you explicitly enable LangSmith in `app.py`.

## AWS

The app can be deployed on AWS using their Elastic Beanstalk service, and can save data to a DynamoDB database if required.

Before you start, log into the AWS Management Console and switch the region to your preferred option at the very top right corner where the location is displayed.
(For our team's deployments, we have used `London - eu-west-2`, but you can pick as you like.)
This should be next to your username/account ID.

### Prepare DynamoDB database

The use of a DynamoDB database is optional.
If you would like to use the database, follow the steps below to prepare a database table to store data from your app:

* From the "Services" menu in the AWS Management Console, or the search bar next to it in the top left of your screen, open up the "DynamoDB" service.
* Click on "Tables" from the panel on the left hand side.
* Click the orange "Create table" button on the right hand side.
* Provide a name for the table.
* Set the partition key to "session_id", and leave the type set to "String" in the drop-down menu.
* No sort key is required.
* The remaining settings relate to the capacity and provisioning of the database.
You can leave these as they are, or if you know that a smaller capacity will suffice, change the settings appropriately.
  * For example, we have set the maximum read/write request units to 1 for databases which are solely used for testing purposes.

#### Configure the app to use the database

To link your app to the database, you will need to edit the Streamlit secrets file.
This will usually be stored in `.streamlit/secrets.toml`.

To store collected data in the database, add `DYNAMODB_TABLE_NAME_WRITE = "your-database-name"`.
If the variable is removed or commented out from the file, connection to the database will not be attempted.

If the app requires scenarios generated earlier as an input, provide the relevant database with `DYNAMODB_TABLE_NAME_READ = "your-database-name"`

> [!TIP]
> You can connect to the database when running the app locally, as long as the table name is specified in `.streamlit/secrets.toml` and a set of credentials with appropriate permissions is available to `boto3` when the app is run.
> `boto3`'s [documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) provides guidance on the various methods of configuring credentials; any of them apart from passing credentials to the `boto3.client()` method or `Session` object are suitable.
> (These two methods require changes to the code, so others are preferable.)
> The set of credentials used must provide write access to the DynamoDB table.

When you are ready to deploy the app (after following the steps in the next section), make sure that the database name is present in the `.streamlit/secrets.toml` file when preparing the zipped folder to upload to AWS.

### Deploy the app using Elastic Beanstalk

The Elastic Beanstalk ["Getting started"](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/GettingStarted.CreateApp.html) guide describes the steps needed to create the infrastructure and deploy an example application.
Our use-case here is very similar - take the following steps to deploy an instance of the `micro-narratives` app:

* From the "Services" menu, or the search bar next to it in the top left of your screen, open up the "Elastic Beanstalk" service.
* Click on "Create environment" at the top right corner.

#### Step 1 - Configure environment

* Choose appropriate names for both your app and the associated environment.
* Click on "Platform" which opens a dropdown menu and choose Python.
Choose Python 3.12 for "Platform branch".
* Under "Application code", choose "Upload your code", provide an appropriate version label, and choose "local file" which enables a "choose file" button.
Click on it and upload your code as a zip file.
  * Only the files needed for deployment (Python files, dependencies, configuration files, API keys and the Procfile) are required; others can be skipped.
    (The Procfile contains the command that the AWS resources need to trigger in order to run the app.)
  * The zip file can quickly be generated by running the command `zip -r app.zip *.py configs Procfile Pipfile.lock LICENSE .streamlit` from the `micro-narratives-app` folder.
* Leave other configurations as they are.

#### Step 2 - Configure service access

* For "Existing service roles", see [step 9 of the Elastic Beanstalk Getting Started Guide](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/GettingStarted.CreateApp.html#GettingStarted.CreateApp.Create).
* If you want to connect to a DynamoDB database, you will need to make the following changes:
  * Instead of using the `aws-elasticbeanstalk-ec2-role` (as recommended, if available), you will need to create a new role that includes the same default permissions **plus** the permission to write to DynamoDB databases.
    * _King's core development team only: this role has already been created and is named `micro-narratives-elasticbeanstalk-ec2-role`._
  * Follow the instructions as specified in the guide to create a new role.
  * When prompted to select the permissions policies that apply to the role, add `AmazonDynamoDBFullAccess` in addition to the three recommended policies.
* Leave the other configurations as they are.

#### Step 3 and 4 - Set up networking, database, tags, and instance traffic and scaling

* Leave configurations as they are.

#### Step 5 - Configure updates, monitoring, and logging

* Scroll down and click on "Add environment property".
  * Add "PORT" for "Name", and "8501" for "Value".
  * If using a DynamoDB database, also add the name "AWS_DEFAULT_REGION" and value "eu-west-2" (or the region appropriate for your own setup).
* Review all configurations and submit.

### Recommended changes for production deployments

#### Set up a load balancer

* Navigate to the relevant Elastic Beanstalk environment for your app.
* Open the "Configuration" tab on the left hand side.
* Click on "Edit" in the "Instance traffic and scaling" section.
* In the "Capacity" section, switch the "Environment type" to "Load balanced".
* This will set up an application load balancer.
  * You can alter other settings as you like, for example, the maximum number of instances (for low user numbers, 1 should be fine).

If creating an environment from scratch (for instance, if following the [guide above](#deploy-the-app-using-elastic-beanstalk)), you can instead create the load balancer at that stage.

##### Healthcheck endpoint

If enhanced health reporting is enabled, you should also amend the healthcheck endpoint used by your load balancer.

* In the search bar of the console, search for "Load balancers (EC2 feature)".
* Click on "Target Groups" under "Load Balancing" on the left hand side.
* Select your load balancer, then open up the "Health check" tab and click "Edit".
* Replace the default health check path with `/healthz`, as used by Streamlit.
* Save changes and wait for the app to update.

#### Use a custom domain name

A custom domain name is recommended for production use of the micro-narratives app.
In addition to giving a clearer URL than the random ones allocated by Elastic Beanstalk, using a custom domain name will also allow us to set up HTTPS.

The AWS guide, [Routing traffic to an AWS Elastic Beanstalk environment](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/routing-to-beanstalk-environment.html), provides detailed instructions on how to this.
If your domain name was not provided by AWS, you will need to follow the [additional instructions](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/MigratingDNS.html) in the note on that page to use AWS's Route 53 as the DNS service for your domain.

If you want to host your app at a subdomain, you may also find the [Routing traffic for subdomains](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-routing-traffic-for-subdomains.html) documentation useful.

#### Configure HTTPS

Follow the AWS documentation to configure [HTTPS termination at the load balancer](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/configuring-https-elb.html).

If you do not already have a certificate set up for your custom domain name, see the note on that page which provides information on how to create one.

#### Alter headers

For some use-cases, you may need to alter the configuration of the reverse proxy used by your deployment.
For example, you may want to embed your micro-narratives site into a Qualtrics survey, but the default configuration of the reverse proxy used by Elastic Beanstalk does not allow this.

For general documentation on adapting the configuration, see the AWS documentation, [Reverse proxy configuration](https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/platforms-linux-extend.proxy.html).

To embed the app into a Qualtrics survey, you will need to do the following:

* Create a new folder in your app's repository, `<micro-narratives-app-repo>/.platform/nginx/conf.d`
* Create a new `.conf` file within that folder.
The exact name does not matter; here we will use `amend_headers.conf`
* Within that file, add an additional header to adapt the content security policy by using the following:

```conf
add_header Content-Security-Policy "frame-ancestors 'self' https://qualtrics.kcl.ac.uk;";
```

* This will permit the site to be embedded by the other listed sites.
Further information about the `frame-ancestors` directive can be found on [MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/frame-ancestors).
* The list of sites can be amended as needed (not that the example here uses KCL's own Qualtrics instance).
* Save the file, and then prepare a zip file containing all the files needed to deploy the app (see [description above](#step-1---configure-environment), remembering to also include the `.platform` folder in the zip file).
* Redeploy the app.
