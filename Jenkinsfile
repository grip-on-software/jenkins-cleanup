pipeline {
    agent { label 'docker' }

    environment {
        IMAGE_TAG = env.BRANCH_NAME.replaceFirst('^master$', 'latest')
        GITLAB_TOKEN = credentials('jenkins-cleanup-gitlab-token')
        SCANNER_HOME = tool name: 'SonarQube Scanner 3', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
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
        always {
            publishHTML([allowMissing: true, alwaysLinkToLastBuild: false, keepAll: true, reportDir: 'mypy-report/', reportFiles: 'index.html', reportName: 'Typing', reportTitles: ''])
            junit allowEmptyResults: true, testResults: 'mypy-report/junit.xml'
        }
    }

    stages {
        stage('Start') {
            when {
                not {
                    triggeredBy 'TimerTrigger'
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
        stage('SonarQube Analysis') {
            steps {
                withCredentials([string(credentialsId: 'pypi-repository', variable: 'PIP_REGISTRY'), file(credentialsId: 'pypi-certificate', variable: 'PIP_CERTIFICATE')]) {
                    withPythonEnv('System-CPython-3') {
                        pysh 'python -m pip install -r analysis-requirements.txt'
                        pysh 'python -m pip install certifi'
                        pysh 'python -m pip install $(python make_pip_args.py $PIP_REGISTRY $PIP_CERTIFICATE) -r requirements.txt'
                        pysh 'mypy cleanup --html-report mypy-report --cobertura-xml-report mypy-report --junit-xml mypy-report/junit.xml --no-incremental --show-traceback || true'
                        pysh 'python -m pylint cleanup --exit-zero --reports=n --msg-template="{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}" -d duplicate-code > pylint-report.txt'
                    }
                }
                withSonarQubeEnv('SonarQube') {
                    sh '${SCANNER_HOME}/bin/sonar-scanner -Dsonar.projectKey=jenkins-cleanup:$BRANCH_NAME -Dsonar.projectName="Jenkins cleanup $BRANCH_NAME"'
                }
            }
        }
        stage('Cleanup docker') {
            steps {
                sh './cleanup/docker.sh'
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
                    sh 'python cleanup/jenkins.py'
                    sh 'python cleanup/sonar.py'
                    sh 'python cleanup/docker.py images.txt tags.txt'
                }
            }
        }
        stage('Cleanup docker tags') {
            steps {
                sh './cleanup/docker.sh tags.txt'
            }
        }
        stage('Status') {
            when {
                not {
                    triggeredBy 'TimerTrigger'
                }
            }
            steps {
                updateGitlabCommitStatus name: env.JOB_NAME, state: 'success'
            }
        }
    }
}
