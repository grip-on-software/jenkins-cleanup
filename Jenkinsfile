pipeline {
    agent { label 'docker' }

    environment {
        IMAGE_TAG = env.BRANCH_NAME.replaceFirst('^master$', 'latest')
        GITLAB_TOKEN = credentials('jenkins-cleanup-gitlab-token')
    }

    options {
        gitLabConnection('gitlab')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers {
        gitlab(triggerOnPush: true, triggerOnMergeRequest: true, branchFilterType: 'All', secretToken: env.GITLAB_TOKEN)
        cron('H H(1-8) * * H')
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
        stage('Start') {
            when {
                expression {
                    currentBuild.rawBuild.getCause(hudson.triggers.TimerTrigger$TimerTriggerCause) == null
                }
            }
            steps {
                updateGitlabCommitStatus name: env.JOB_NAME, state: 'running'
            }
        }
        stage('Build') {
            steps {
                checkout scm
                withCredentials([string(credentialsId: 'pypi-repository', variable: 'PIP_REGISTRY'), file(credentialsId: 'pypi-certificate', variable: 'PIP_CERTIFICATE')]) {
                    sh 'cp $PIP_CERTIFICATE pypi.crt'
                    sh 'docker build -t $DOCKER_REGISTRY/gros-jenkins-cleanup:$IMAGE_TAG . --build-arg PIP_REGISTRY=$PIP_REGISTRY --build-arg PIP_CERTIFICATE=pypi.crt'
                }
            }
        }
        stage('Push') {
            when { branch 'master' }
            steps {
                sh 'docker push $DOCKER_REGISTRY/gros-jenkins-cleanup:latest'
            }
        }
        stage('Cleanup docker') {
            steps {
                sh './docker.sh'
            }
        }
        stage('Cleanup jenkins') {
            agent {
                docker {
                    image "${env.DOCKER_REGISTRY}/gros-jenkins-cleanup:${env.IMAGE_TAG}"
                    args '-v /etc/ssl/certs:/etc/ssl/certs -v /usr/local/share/ca-certificates:/usr/local/share/ca-certificates'
                    reuseNode true
                }
            }
            steps {
                withCredentials([file(credentialsId: 'data-gathering-settings', variable: 'GATHERER_SETTINGS_FILE'), file(credentialsId: 'data-gathering-credentials', variable: 'GATHERER_CREDENTIALS_FILE')]) {
                    sh 'python jenkins.py'
                    sh 'python sonar.py'
                    sh 'python docker.py images.txt tags.txt'
                }
            }
        }
        stage('Cleanup docker tags') {
            steps {
                sh './docker.sh tags.txt'
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
