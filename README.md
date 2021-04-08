# Visualization of Patient flow data for A2CPS
Docker container of Dash App to display A2CPS trial consort information.

This dashboard is intended for use by study personnel and others interested in the reasons why patients either complete or leave the trial.

## Version History
| Version   | Date | Description |
| ------ | ------ | ------ |
| 0.0.3 | 04/07/2021 | Add functionality for historical data. |
| 0.0.2 | 03/30/2021 | Modify data to force live load of API data and display report date. |
| 0.0.1 | 03/23/2021 | Initial simple dashboard with plotly Sankey Diagram and Data Table. |


# Development Previews

Development previews are built upon commits to the master branch. If you wish to preview the latest
build, you may use the `docker-compose.yml` file. On your local machine with Docker, run:

```
docker-compose up --force-recreate
```

Then browse to `localhost:8050` in your web browser.

# Automatic Container Build information from parent repository.
This repository was forked from the TACC dash-container[https://github.com/TACC/dash-container] repo.  

## Configuring your repository for automatic container builds (text from original repo)

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
