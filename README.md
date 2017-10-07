# Pawar APIs

Based off [zouzias](https://github.com/zouzias)/[docker-compose-flask-example](https://github.com/zouzias/docker-compose-flask-example).

## Local Development

To develop locally you have a few options.  You can use a Docker image to keep an isolated
environment, use a virtualenv in Python or just use Python directly.  All of these options
should work correctly.

### Environment Variables

To work in a local environment you'll need to configure two environment variables:

| Variable              | Description                                                                         |
|:----------------------|:------------------------------------------------------------------------------------|
| ENV                   | The environment that you're working in which should be "dev"                        |
| cert                  | The firebase certificate used to connect to the firebase facts database (see below) |
| AWS_ACCESS_KEY_ID     | AWS API Key                                                                         |
| AWS_SECRET_ACCESS_KEY | AWS Secret Key                                                                      |

Be sure that when you set up your local environment that the JSON for the firebase
certificate is properly escaped.

### Firebase key

We're using the firebase admin interface so to generate a new key, go to the IAM and admin portion of the Google cloud
console (there's a link on the gear menu on the left column of the firebase console) and go to Service Accounts.
You can generate a new user on there and make sure it has access to databases.

Once you have the key copy it into the "cert" environment variable in your local development setup.

### AWS Configuration

The AWS credentials are required because of the cache mechanism built into the API.  It would
probably make sense to add a way to toggle this off when working locally, but that has not
been added yet.  By default you'll use the dev DynamoDB which is the same one that's used
by dev-expenditures.pawarapis.com.

### Running the Code

Once you've got the environment setup, the script can be run from the command line as follows:

    `python expenditures/app.py`

Once running the app should auto-restart if you make any changes to the code base.  The

## Environments

There are two environments for the system.  When developing locally you are effectively
using the dev version of the environment.  Ideally this would be segmented, but that hasn't
been done at this time.

![Expenditures Environments](expenditures/docs/Expenditures%20Environments.png)

## Deploy

This code base has been set up with automation through Jenkins so no explicit deploy process
is required.  When the dev or master branch is checked in, the build will kick off and
deploy to the appropriate environment.

### Branching Strategy

The dev branch is the default branch and should be used for building code as testing is done.
Once the code is ready to go to production, the code should be added to the master branch via
a pull request.

![Expenditures Build](expenditures/docs/Expenditures%20Build.png)

Note that the calculator front end portion of the code base is in the calculator Github repo
but it auto-builds in a similar fashion.

## Architecture

For context, the fully deployed system looks as follows:

![Expenditures API](expenditures/docs/Expenditures%20API.png)

The twitter bot and the website both pull from the expenditures API.  The HTML and CSS
for the calculator all comes out of an S3 bucket fronted by AWS Cloudfront.
