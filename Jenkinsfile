pipeline {
  agent {
    node {
      label 'suapdev'
    }

  }
  stages{
    stage('pull code'){
        steps{
            sh 'git clone https://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@github.com/fesflabs/suap_fesf'
        }
    }
    stage('merge repo'){
      steps{
        sh '''mv /home/jenkins/suap_fesf /var/opt/
        cd /var/opt && mv suap_fesf suap'''
    }
  }
    stage('cria migration'){
        steps{
            sh 'cd /var/opt/suap && python3 manage.py makemigrations'
        }
    }
    stage('atualiza migration'){
        steps{
            sh 'cd /var/opt/suap && python3 manage.py migrate'
        }
    }
    stage('reinicia serviços'){
        steps{
            sh '''supervisorctl reload
            supervisorctl status
             '''
        }
    }
    stage('Reinicia Nginx'){
        steps{
        sh 'sudo systemctl restart nginx.service'
      }
    }
  }

}
