# dash-container
Template project for a containerized plot.ly dash visualization

## Configuring your repository for automatic container builds

### Github Actions workflows

This repository comes with two Github Action workflows that automatically build Docker containers:

- [build-pr](./github/workflows/build-pr) builds commit sha tagged
images upon pull requests
- [build-main](./github/workflows/build-main) builds a commit sha tagged and `:latest` tagged image upon
pushes to main (such as when merging a pull request)

Both require specific Github repo configuration.

### Setting up a Dockerhub token

You will need to create a token for the account that will be used to push your repo.

- On [Dockerhub](https://hub.docker.com) go to your account's [security settings](https://hub.docker.com/settings/security).
- Click the **New Access Token** button and type in a description
- You will see a UUID value - this is your access token. Copy it immediately, as these can only
be read upon creation. You will not see this token again.

### Setting up a Github Actions environment

You will need to create a build environment with secrets to contain Dockerhub settings.

- In your Github repo, click on **Settings**. Then click on **Environments**
- Click on the **New Environment** button and name this environment `docker`. (You can change the
`environment` value in the workflows if you wish to call it something else or keep multiple environments)
- At the bottom of the screen you will see **Environment Secrets**. Click the **Add Secret** button to create secrets.
- Create a secret called `DOCKERHUB_TOKEN` and paste your Dockerhub token here
- Create a secret called `DOCKERHUB_USERNAME` and put the name of the corresponding user here
- Create a secret called `DOCKERHUB_REPO` and put your Docker repository name here. For example, this Github repo
autobuilds images at `jchuahtacc/dash-container`, so that is the value that is used for `DOCKERHUB_REPO`.

### Test it out

Upon pull requests, pushes to main and pushes to main, you will see the workflows perform autobuilds. You can
view the Action results by going to the **Actions** tag of your repo. You can also go to your [Dockerhub](https://hub.docker.com) page and make sure images are properly getting tagged and pushed