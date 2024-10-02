# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Acesso ao Prontuário e Registro de Atendimentos
  Acesso ao prontuário médico

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E  os seguintes usuários
      | Nome        | Matrícula      | Setor | Lotação | Email              | CPF            | Senha | Grupo |
      | Aluno Saude | 20191101011111 | CZN   | CZN     | aluno1@ifrn.edu.br | 559.454.350-31 | abcd  | Aluno |
    E as seguintes orientacoes nutricionais
      | Titulo       | Descrição              |
      | Orientação A | Descrição orientação A |
      | Orientação B | Descrição orientação B |
      | Orientação C | Descrição orientação C |
      | Orientação D | Descrição orientação D |
      | Orientação E | Descrição orientação E |
    E as seguintes receitas nutricionais
      | Titulo    | Descrição           |
      | Receita A | Descrição receita A |
      | Receita B | Descrição receita B |
      | Receita C | Desfrição receita C |
      | Receita D | Descrição receita D |
      | Receita E | Descrição receita E |
    E as seguintes avaliações gastrointestinais
      | Descrição                                                 |
      | Pirose                                                    |
      | Náuseas                                                   |
      | Vômitos                                                   |
      | Dores abdominais                                          |
      | Distensão abdominal                                       |
      | Meteorismo/Flatulência                                    |
      | Obstipação intestina                                      |
      | Diarreia aguda                                            |
      | Intolerância à lactose                                    |
      | Patologia (DRGE/Gastrite/Doença Inflamatória Instestinal) |
      | Outros                                                    |
    E as seguintes restrições alimentares
      | Descrição         |
      | Leite e derivados |
      | Ovos              |
      | Oleaginosas       |
      | Soja              |
      | Peixe             |
      | Crustáceos        |
      | Amendoim e nozes  |
      | Glúten            |
      | Chocolates        |
      | Corantes          |
      | Aditivos químicos |
      | Frutas            |
      | Outros            |
    E os seguintes motivos do atendimento nutricional
      | Descrição                         |
      | Perda de peso                     |
      | Ganho de peso                     |
      | Ganho de massa muscular           |
      | Manutenção do peso                |
      | Prática de atividade física       |
      | Dislipidemias                     |
      | Doenças do Trato Gastrointestinal |
      | Intolerância Alimentar            |
      | Alergia Alimentar                 |
      | Transtorno Alimentar              |
      | Patologias                        |
      | Alimentação saudável              |
      | Outros                            |
    E os seguintes diagnósticos nutricionais
      | Descrição                                                                                                                       |
      | Hipermetabolismo (necessidades energéticas aumentadas)                                                                          |
      | Gasto energético aumentado                                                                                                      |
      | Hipometabolismo (necessidades energéticas diminuídas)                                                                           |
      | Ingestão insuficiente de energia                                                                                                |
      | Ingestão excessiva de energia                                                                                                   |
      | Ingestão oral insuficiente de alimento/bebida                                                                                   |
      | Ingestão oral excessiva de alimento/bebida                                                                                      |
      | Ingestão excessiva de nutrição enteral/parenteral                                                                               |
      | Ingestão inadequada de nutrição enteral/parenteral                                                                              |
      | Ingestão insuficiente de líquidos                                                                                               |
      | Ingestão excessiva de líquidos                                                                                                  |
      | Ingestão insuficiente de substâncias bioativas                                                                                  |
      | Ingestão excessiva de líquidos                                                                                                  |
      | ingestão insuficiente de líquidos                                                                                               |
      | Ingestão excessiva de substâncias bioativas                                                                                     |
      | Ingestão excessiva de álcool                                                                                                    |
      | Necessidades aumentadas de nutriente (especificar)                                                                              |
      | Desnutrição calórico-proteica evidente                                                                                          |
      | Ingestão insuficiente de energia e proteína                                                                                     |
      | Necessidades diminuídas de nutriente (especificar)                                                                              |
      | Desequilíbrio de nutrientes                                                                                                     |
      | Ingestão insuficiente de lipídios                                                                                               |
      | Ingestão excessiva de lipídios                                                                                                  |
      | Ingestão inapropriada de alimentos ricos em gordura (especificar)                                                               |
      | Ingestão insuficiente de proteínas                                                                                              |
      | Ingestão excessiva de proteínas                                                                                                 |
      | Ingestão inapropriada de aminoácidos (especificar)                                                                              |
      | Ingestão insuficiente de carboidratos                                                                                           |
      | Ingestão excessiva de carboidratos                                                                                              |
      | Ingestão inapropriada de tipos de carboidratos (especificar)                                                                    |
      | Ingestão irregular de carboidratos                                                                                              |
      | Ingestão insuficiente em fibras                                                                                                 |
      | Ingestão excessiva de fibras                                                                                                    |
      | Ingestão insuficiente de vitaminas (especificar)                                                                                |
      | Ingestão excessiva de vitaminas (especificar)                                                                                   |
      | Ingestão insuficiente de minerais (especificar)                                                                                 |
      | Ingestão excessiva de minerais (especificar)                                                                                    |
      | Dificuldade na deglutição                                                                                                       |
      | Dificuldade na mastigação                                                                                                       |
      | Dificuldade na amamentação                                                                                                      |
      | Alteração na função GI                                                                                                          |
      | Alteração na utilização de nutrientes                                                                                           |
      | Alteração nos valores laborais relacionados com a nutrição                                                                      |
      | Interação fármaco-nutriente                                                                                                     |
      | Baixo peso                                                                                                                      |
      | Perda de peso involuntária                                                                                                      |
      | Sobrepeso/obesidade                                                                                                             |
      | Ganho de peso involuntário                                                                                                      |
      | Deficiência de conhecimento relacionado com os alimentos e a nutrição                                                           |
      | Atitudes/crenças perigosas quanto aos alimentos ou tópicos relacionados com a nutrição                                          |
      | Despreparo para mudança na dieta/estilo de vida	Despreparo para mudança na dieta/estilo de vida                                 |
      | Deficiência no automonitoramento                                                                                                |
      | Distúrbio no padrão alimentar                                                                                                   |
      | Aderência limitada às recomendações relacionadas com a nutrição	Aderência limitada às recomendações relacionadas com a nutrição |
      | Escolhas alimentares indesejáveis                                                                                               |
      | Inatividade física                                                                                                              |
      | Excesso de exercício                                                                                                            |
      | Incapacidade ou falta de desejo para conduzir o autocuidado                                                                     |
      | Alteração da capacidade de preparar alimentos/refeições	Alteração da capacidade de preparar alimentos/refeições                 |
      | Qualidade de vida e nutrição deficientes                                                                                        |
      | Dificuldade na autoalimentação                                                                                                  |
      | Ingestão de alimento não seguro                                                                                                 |
      | Acesso limitado aos alimentos                                                                                                   |
    E os seguintes motivos de chegada psicológo
      | Descrição                                        |
      | Demanda Espontânea                               |
      | Encaminhado pelo Plantão psicológico/COASS/DIGPE |
      | Encaminhado pelo Serviço de Saúde                |
      | Encaminhado por Docente                          |
      | Encaminhado por ETEP                             |
      | Encaminhado por Familiares                       |
      | Encaminhado por Outro Aluno                      |
      | Encaminhado por outros servidores                |
      | Encaminhado por Terceirizados                    |
      | Encaminhamento Externo                           |
    E as seguintes queixas psicológicas
      | Descrição                                                        |
      | Ansiedade                                                        |
      | Autoestima/autoimagem                                            |
      | Automutilação                                                    |
      | Conflito Interpessoal - família                                  |
      | Conflito Interpessoal - professores/servidores                   |
      | Conflito Interpessoal - relacionamentos afetivos                 |
      | Conflito Interpessoal - turma                                    |
      | Conflitos religiosos                                             |
      | Desmotivação                                                     |
      | Dificuldade de aprendizagem/concentração                         |
      | Ideação suicida                                                  |
      | Ideias obsessivas                                                |
      | Impulsividade                                                    |
      | Organização de horário de estudo                                 |
      | Orientação Profissional                                          |
      | Outros                                                           |
      | Perdas/luto                                                      |
      | Problemas com a homoafetividade                                  |
      | Problemas com pais ou parentes                                   |
      | Problemas no relacionamento/ comunicação com os pais/ familiares |
      | Queixas escolares (dificuldades com o conteúdo)                  |
      | Queixas Escolares - Dificuldades com o conteúdo                  |
      | Queixas Escolares - Dificuldades de Aprendizagem                 |
      | Queixas Escolares - Dificuldades de Concentração                 |
      | Queixas psicossomáticas                                          |
      | Questões ligadas a sexualidade                                   |
      | Questões sobre a adaptação à escola                              |
      | Sintomas depressivos                                             |
      | Tensão pré-menstrual (TPM)                                       |
      | Transtorno mental diagnosticado                                  |
      | Uso de álcool ou outras drogas                                   |
      | Vítima de violência / abuso                                      |
    E os seguintes procedimentos de enfermagem
    E os seguintes procedimentos odontológicos
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Buscar Prontuários do Aluno
  Localiza o prontuário do aluno através de busca por nome, matrícula ou CPF.
    Dado acesso a página "/"
    Quando realizo o login com o usuário "111001" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E acesso o menu "Sair"

  @do_document
  Cenário: Buscar Prontuários do Servidor
  Localiza o prontuário do servidor através de busca por nome, matrícula ou CPF.
    Dado acesso a página "/"
    Quando realizo o login com o usuário "111001" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor    |
      | Buscar por Nome, Matrícula ou CPF | Texto | 111001   |
      | Vínculo                           | Lista | Servidor |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E acesso o menu "Sair"


  # Criando prontuários de atendimento.
  # Perfil: Auxiliar de Enfermagem.
  @do_document
  Cenário: Abertura de Atendimento Médico/Enfermagem
  Buscar prontuários de alunos buscando por campos como nome, matrícula ou CPF.
    Dado acesso a página "/"
    Quando realizo o login com o usuário "111006" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico no link "Adicionar Atendimento Médico/Enfermagem"
    E clico no botão "Adicionar"
    E preencho o formulário com os dados
      | Campo                 | Tipo     | Valor                 |
      | Motivo do Atendimento | Textarea | Motivo do atendimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Motivo do Atendimento registrado com sucesso."

  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Registro de Intervenção no Atendimento Médico/Enfermagem
    Quando acesso a página "/"
    E realizo o login com o usuário "111005" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico na aba "Atendimentos Médico/Enfermagem"
    E clico no ícone de exibição
    Quando clico na aba "Motivo do Atendimento"
    E clico no botão "Adicionar Motivo"
    E preencho o formulário com os dados
      | Campo                 | Tipo     | Valor                 |
      | Motivo do Atendimento | Textarea | Motivo de Atendimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento registrado com sucesso."
    E vejo a página "Atendimento Médico/Enfermagem"
    Quando clico na aba "Intervenção de Enfermagem"
    Então vejo o botão "Adicionar Intervenção"
    Quando clico no botão "Adicionar Intervenção"
    E preencho o formulário com os dados
      | Campo        | Tipo            | Valor                     |
      | Procedimento | Autocomplete multiplo   | Outros                    |
      | Descrição       | Textarea     | Descrição da Intervenção  |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Intervenção de enfermagem registrada com sucesso."



  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Registro do Médico no Atendimento Médico/Enfermagem
    Quando acesso a página "/"
    E realizo o login com o usuário "111002" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico na aba "Atendimentos Médico/Enfermagem"
    E clico no ícone de exibição
    E clico na aba "Anamnese"
    Então vejo o botão "Adicionar Anamnese"
    Quando clico no botão "Adicionar Anamnese"
    E preencho o formulário com os dados
      | Campo | Tipo     | Valor               |
      | HDA   | Textarea | Descrição Anamnese. |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Anamnese registrada com sucesso."
    E vejo a página "Atendimento Médico/Enfermagem"
    Quando clico na aba "Hipótese Diagnóstica"
    E olho para o quadro "Conduta Médica"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo   | Tipo     | Valor          |
      | Conduta | Textarea | Conduta médica |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Conduta Médica registrada com sucesso."
    Quando clico no link "Fechar"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor      |
      | Observação de Fechamento | Textarea | Observação |
    Então vejo o botão "Salvar"
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento fechado com sucesso."


  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"


  # Criando atendimento fisioterapêutico.
  # Perfil: Fisioterapeuta.
  @do_document
  Cenário: Registro de Atendimento de Fisioterapia
  Criando atendimento fisioterapêutico.
    Quando acesso a página "/"
    E realizo o login com o usuário "111007" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico no link "Adicionar Atendimento de Fisioterapia"
    Então vejo mensagem de sucesso "Atendimento de Fisioterapia gerado com sucesso."
    Quando clico na aba "Anamnese"
    Então vejo o botão "Adicionar"
    Quando clico no botão "Adicionar"
    E preencho o formulário com os dados
      | Campo    | Tipo     | Valor               |
      | Anamnese | Textarea | Descrição Anamnese. |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Anamnese registrada com sucesso."
    E vejo o botão "Fechar"
    Quando clico no link "Fechar"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor               |
      | Observação de Fechamento | Textarea | Nenhuma observação. |
    E clico no botão "Salvar"
    Então vejo a página "Prontuário"
    E vejo mensagem de sucesso "Atendimento fechado com sucesso."


  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"



  # Criando atendimento nutricional.
  # Perfil: Nutricionista.
  @do_document
  Cenário: Registro de Atendimento de Nutrição
  Criando atendimento nutricional.
    Quando acesso a página "/"
    E realizo o login com o usuário "111009" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico no link "Adicionar Atendimento Nutricional"
    Então vejo mensagem de sucesso "Atendimento Nutricional gerado com sucesso."
    Quando clico na aba "Anamnese"
    Então vejo a página "Atendimento Nutricional"
    Quando olho para o quadro "Hábitos de Vida"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo                | Tipo     | Valor               |
      | Faz uso da internet? | Checkbox | marcar              |
      | Qual o tempo de uso  | Lista    | 4 ou mais horas/dia |
    E clico no botão "Salvar"
    Quando olho para o quadro "Antropometria"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo    | Tipo  | Valor |
      | Estatura | Texto | 180   |
      | Peso     | Texto | 100   |
    E clico no botão "Salvar"
    Quando olho para o quadro "Avaliação Gastrointestinal"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo                      | Tipo                   | Valor                  |
      | Avaliação Gastrointestinal | FilteredSelectMultiple | Diarreia aguda, Outros |
    E clico no botão "Salvar"
    Quando olho para o quadro "Dados Gerais da Alimentação"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor                    |
      | Apetite                  | Textarea | Apetite                  |
      | Aversões                 | Textarea | Aversões                 |
      | Preferências             | Textarea | Preferências             |
      | Consumo de Água/Líquidos | Textarea | Consumo de Água/Líquidos |
    E clico no botão "Salvar"
    Quando olho para o quadro "Restrições Alimentares"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo               | Tipo                   | Valor              |
      | Restrição Alimentar | FilteredSelectMultiple | Chocolates, Outros |
    E clico no botão "Salvar"
    Quando olho para o quadro "Recordatório Alimentar"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo                                   | Tipo     | Valor                        |
      | Refeição                                | Texto    | Café da manhã                |
      | Horário de Consumo                      | Hora     | 06:30                        |
      | Local de Consumo                        | Texto    | Casa                         |
      | Alimentos Consumidos / Medidas Caseiras | Textarea | Pão, Café, Suco, Papa, Frios |
    E clico no botão "Salvar"
    Quando clico na aba "Motivo do Atendimento"
    E clico no botão "Adicionar"
    E preencho o formulário com os dados
      | Campo                 | Tipo                   | Valor                 |
      | Motivo do Atendimento | FilteredSelectMultiple | Perda de peso, Outros |
      | Observações           | Textarea               | Nenhuma observação    |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento registrado com sucesso."
    Quando clico na aba "Conduta Nutricional"
    E olho para o quadro "Cálculo das Necessidades Energéticas"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo                 | Tipo  | Valor    |
      | Categoria de Trabalho | Lista | Moderada |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento registrado com sucesso."
    Quando clico na aba "Conduta Nutricional"
    E olho para o quadro "Conduta"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo   | Tipo       | Valor                             |
      | Conduta | Texto Rico | Descrição da conduta a realizada. |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento registrado com sucesso."
    Quando clico na aba "Conduta Nutricional"
    E olho para o quadro "Plano Alimentar"
    E clico no link "Adicionar Plano Alimentar"
    E preencho o formulário com os dados
      | Campo                    | Tipo                   | Valor                      |
      | Orientação Nutricional   | FilteredSelectMultiple | Orientação A, Orientação C |
      | Cardápio                 | Texto Rico             | Descrição do cardápio.     |
      | Receitas                 | FilteredSelectMultiple | Receita A, Receita C       |
      | Plano Alimentar Liberado | Checkbox               | marcar                     |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento registrado com sucesso."
    Quando clico no link "Fechar"
    Quando preencho o formulário com os dados
      | Campo                    | Tipo     | Valor      |
      | Observação de Fechamento | Textarea | Observação |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento fechado com sucesso."


  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"


  # Criando atendimento psicológico.
  # Perfil: Psicológico.
  @do_document
  Cenário: Registro de Atendimento Psicológico
  Criando atendimento psicológico.
    Quando acesso a página "/"
    E realizo o login com o usuário "111008" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico no link "Adicionar Atendimento Psicológico"
    Então vejo mensagem de sucesso "Atendimento Psicológico gerado com sucesso."
    Quando clico na aba "Informações sobre o Atendimento"
    E clico no link "Registrar Data/Hora do Atendimento"
    E preencho o formulário com os dados
      | Campo                    | Tipo  | Valor      |
      | Data/Hora do Atendimento | Data  | 29/01/2020 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Data/hora do atendimento registrada com sucesso."
    Quando clico na aba "Informações sobre o Atendimento"
    Então vejo o botão "Adicionar"
    Quando clico no botão "Adicionar"
    Então vejo os seguintes campos no formulário
      | Campo                        | Tipo              |
      | Motivo da Chegada            | Autocomplete      |
      | Queixa Principal             | checkbox multiplo |
      | Queixa Identificada          | checkbox multiplo |
      | Intervenção / Encaminhamento | Textarea          |
    Quando preencho o formulário com os dados
      | Campo                        | Tipo              | Valor                            |
      | Motivo da Chegada            | Autocomplete      | Demanda Espontânea               |
      | Queixa Principal             | checkbox multiplo | Autoestima/autoimagem, Ansiedade |
      | Queixa Identificada          | checkbox multiplo | Autoestima/autoimagem, Ansiedade |
      | Intervenção / Encaminhamento | Textarea          | Descrição da intervenção.        |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento registrado com sucesso."
    Quando clico no botão "Fechar"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor      |
      | Observação de Fechamento | Textarea | Observação |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atendimento fechado com sucesso."


  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

  # Criando atendimento odontólogico.
  # Perfil: Odontólogico.
  @do_document
  Cenário: Registro de Atendimento de Odontológico
  Criando atendimento odontólogico.
    Quando acesso a página "/"
    E realizo o login com o usuário "111003" e senha "abcd"
    E acesso o menu "Saúde::Prontuários"
    E preencho o formulário com os dados
      | Campo                             | Tipo  | Valor          |
      | Buscar por Nome, Matrícula ou CPF | Texto | 20191101011111 |
      | Vínculo                           | Lista | Aluno          |
    E clico no botão "Buscar"
    Então vejo o botão "Visualizar Prontuário"
    Quando clico no link "Visualizar Prontuário"
    E clico no link "Adicionar Atendimento Odontológico"
    Então vejo mensagem de sucesso "Atendimento Odontológico gerado com sucesso."
    Quando clico na aba "Situação Clínica"
#    Bug neste trecho.
#    E olho para o quadro "Odontograma"
#    E preencho o formulário com os dados
#      | Campo                                | Tipo             | Valor                                    |
#      | Queixa Principal                     | Textarea         | Uma breve descrição da queixa principal. |
#      | Situação Clínica                     | Lista            | Cárie                                    |
#      | Selecione o(s) dente(s) e/ou face(s) | FaceOdontologica | A_O_48                                   |
    E olho para o quadro "Exame Periodontal"
    E clico no link "Adicionar"
    E preencho o formulário com os dados
      | Campo      | Tipo                   | Valor       |
      | Ocorrência | Lista                  | Sangramento |
      | Sextante   | FilteredSelectMultiple | S1, S2      |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Exame periodontal registrado com sucesso."
    Quando clico no link "Voltar ao Atendimento"
    E clico na aba "Situação Clínica"
    E olho para o quadro "Exame Estomatológico"
    Então vejo o botão "Adicionar"
    Quando clico no botão "Adicionar"
    Então vejo os seguintes campos no formulário
      | Campo                            | Tipo  |
      | Alteração nos lábios             | Texto |
      | Alteração na língua              | Texto |
      | Alteração na gengiva             | Texto |
      | Alteração no assoalho            | Texto |
      | Alteração na mucosa jugal        | Texto |
      | Alteração no palato duro         | Texto |
      | Alteração no palato mole         | Texto |
      | Alteração no rebordo             | Texto |
      | Alteração na cadeia ganglionar   | Texto |
      | Alteração nas tonsilas palatinas | Texto |
      | Alteração na ATM                 | Texto |
      | Alteração na Oclusão             | Texto |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo                            | Tipo  | Valor |
      | Alteração nos lábios             | Texto | Não   |
      | Alteração na língua              | Texto | Não   |
      | Alteração na gengiva             | Texto | Não   |
      | Alteração no assoalho            | Texto | Não   |
      | Alteração na mucosa jugal        | Texto | Não   |
      | Alteração no palato duro         | Texto | Não   |
      | Alteração no palato mole         | Texto | Não   |
      | Alteração no rebordo             | Texto | Não   |
      | Alteração na cadeia ganglionar   | Texto | Não   |
      | Alteração nas tonsilas palatinas | Texto | Não   |

#   Bug neste trecho.
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Exame Estomatológico registrado com sucesso."
    Quando clico na aba "Plano de Tratamento"
    E clico no link "Gerar Plano de Tratamento Automático"
    Então vejo mensagem de sucesso "Plano de Tratamento criado com sucesso."
    Quando clico no link "Fechar"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor               |
      | Observação de Fechamento | Textarea | Nenhuma observação. |
    E clico no botão "Salvar"
    Então vejo a página "Prontuário"
    E vejo mensagem de sucesso "Atendimento fechado com sucesso."

  Cenário: Sai do sistema
    Dado acesso a página "/"
    Quando acesso o menu "Sair"
