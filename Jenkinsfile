pipeline {
    agent { label 'docker' }

    environment {
        GITLAB_TOKEN = credentials('jenkins-cleanup-gitlab-token')
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
        stage('Build') {
            steps {
                checkout scm
                updateGitlabCommitStatus name: env.JOB_NAME, state: 'running'
                sh 'docker build -t $DOCKER_REGISTRY/gros-jenkins-cleanup . --build-arg PIP_REGISTRY=$PIP_REGISTRY'
            }
        }
        stage('Push') {
            when { branch 'master' }
            steps {
                sh 'docker push $DOCKER_REGISTRY/gros-jenkins-cleanup:latest'
            }
        }
        stage('Run') {
            agent {
                docker {
                    image '$DOCKER_REGISTRY/gros-jenkins-cleanup'
                    reuseNode true
                }
            }
            steps {
                withCredentials([file(credentialsId: 'data-gathering-settings', variable: 'GATHERER_SETTINGS_FILE')]) {
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
