pipeline {
    agent any

    environment {
        APP_NAME = 'llm3' // 应用名称
        DEFAULT_VERSION = 'dev-1.3.0' // 默认版本号
         ALIYUN_REGISTRY = 'crpi-ps9xboxyksvf1vax-vpc.cn-shanghai.personal.cr.aliyuncs.com' // 阿里云镜像仓库地址
        ALIYUN_CREDENTIALS_ID = 'aliyun-registry-credentials' // 阿里云镜像仓库凭证 ID
    }

    stages {

        stage('Fetch Tags and Pull Code') {
            steps {
                script {
                    // 动态获取当前分支名称
                    def branchName = env.BRANCH_NAME ?: sh(script: 'git rev-parse --abbrev-ref HEAD', returnStdout: true).trim()

                    // 更新远程分支和 Tag
                    sh """
                        git fetch --tags
                        git pull origin ${branchName}
                    """
                }
            }
        }

        stage('Get Git Tag') {
            steps {
                script {
                    try {
                        // 获取最新的 Git Tag
                        env.GIT_TAG = sh(script: 'git describe --tags --abbrev=0', returnStdout: true).trim()
                        echo "Git Tag: ${env.GIT_TAG}"
                    } catch (Exception e) {
                        // 如果没有找到 Tag，则设置为空
                        echo "No Git Tag found. Using default version."
                        env.GIT_TAG = ""
                    }

                    // 判断是否找到 Tag，并去掉前缀 v
                    if (env.GIT_TAG?.trim()) {
                        env.VERSION = env.GIT_TAG.startsWith("v") ? env.GIT_TAG.substring(1) : env.GIT_TAG
                    } else {
                        env.VERSION = env.DEFAULT_VERSION
                    }

                    echo "Using version: ${env.VERSION}"

                    // 动态生成镜像名称
                    env.IMAGE_NAME = "${ALIYUN_REGISTRY}/allab-test/${APP_NAME}:${VERSION}"
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    // 构建 Docker 镜像
                    sh """
                        docker build -t ${IMAGE_NAME} .
                    """
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    // 推送镜像到阿里云镜像仓库
                    withDockerRegistry([credentialsId: ALIYUN_CREDENTIALS_ID, url: "https://${ALIYUN_REGISTRY}"]) {
                        sh "docker push ${IMAGE_NAME}"
                    }
                }
            }
        }
    }

    post {
        always {
            ClearIfBuildByTag()
        }
    }
}


def ClearIfBuildByTag() {
    def v = getTagName()
    if (v == env.version) {
        return
    }
    cleanWs()
}

def getTagName() {
    def branchName = env.BRANCH_NAME
    if (branchName.startsWith('develop') || branchName.startsWith('release') || branchName.startsWith('master') || branchName.startsWith('main')) {
        return env.version
    }else {
        return branchName
    }
}