pipeline {
    agent { label 'docker' }

    environment {
        GITLAB_TOKEN = credentials('jenkins-cleanup-gitlab-token')
        PIP_HOSTNAME = env.PIP_REGISTRY.split(':').getAt(0)
    }

    options {
        gitLabConnection('gitlab')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers {
        gitlab(triggerOnPush: true, triggerOnMergeRequest: true, branchFilterType: 'All', secretToken: env.GITLAB_TOKEN)
        cron('H H * * 6')
    }

    post {
        failure {
            updateGitlabCommitStatus name: env.JOB_NAME, state: 'failed'
        }
        aborted {
            updateGitlabCommitStatus name: env.JOB_NAME, state: 'canceled'
        }
    }

    stages {
        stage('Run') {
            agent {
                docker {
                    image 'python:3.6-alpine'
                    reuseNode true
                }
            }
            steps {
                checkout scm
                updateGitlabCommitStatus name: env.JOB_NAME, state: 'running'
                withCredentials([file(credentialsId: 'data-gathering-settings', variable: 'GATHERER_SETTINGS_FILE')]) {
                    sh 'pip install --extra-index-url http://$PIP_REGISTRY/ --trusted-host $PIP_HOSTNAME -r requirements.txt'
                    sh './docker.sh'
                    sh 'python jenkins.py'
                }
            }
        }
        stage('Status') {
            when {
                expression {
                    currentBuild.rawBuild.getCause(hudson.triggers.TimerTrigger$TimerTriggerCause) == null
                }
            }
            steps {
                updateGitlabCommitStatus name: env.JOB_NAME, state: 'success'
            }
        }
    }
}
