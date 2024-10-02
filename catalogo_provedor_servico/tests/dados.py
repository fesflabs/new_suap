servicos_ativos_01 = {
    'resposta': [
        {
            'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 6024,
            'titulo': 'Emissão de 2a Via de Diploma',
            'descricao': 'Este serviço permite que um aluno formado possa solicitar a emissão de segunda via de diploma'
        },
        {
            'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 6176,
            'titulo': 'Matrícula EAD',
            'descricao': 'Este serviço permite que um candidato possa fazer uma matrícula de ensino a distancia'
        },
        {
            'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 10056,
            'titulo': 'Protocolar Documentos',
            'descricao': 'Este serviço permite que um cidadão possa protocolar documentos junto a instituição'
        }
    ],
    'mensagem': None, 'has_error': False
}

servicos_ativos_02 = {
    'resposta': [
        {
            'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 6024,
            'titulo': 'Emissão de 2a Via de Diploma',
            'descricao': 'Este serviço permite que um aluno formado possa solicitar a emissão de segunda via de diploma'
        }
    ],
    'mensagem': None, 'has_error': False
}

servicos_disponiveis_01 = {
    'resposta': [
        {
            'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 10056,
            'titulo': 'Protocolar Documentos',
            'descricao': 'Este serviço permite que um cidadão possa protocolar documentos junto a instituição'
        }
    ],
    'mensagem': None, 'has_error': False
}

servicos_avaliacao_disponibilidade_01 = {
    'resposta': [
        {
            'servico': {
                'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 6024,
                'titulo': 'Emissão de 2a Via de Diploma',
                'descricao': 'Este serviço permite que um aluno formado possa solicitar a emissão de segunda via de diploma'
            },
            'cpf': '861.474.078-64',
            'criterios_sucesso': "['Serviço ativo.', 'Não há solicitações em aberto.']",
            'criterios_erro': '[\'O aluno com o CPF "861.474.078-64" nunca emitiu um diploma.\']',
            'is_ok': False
        }, {
            'servico': {
                'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 6176,
                'titulo': 'Matrícula EAD',
                'descricao': 'Este serviço permite que um candidato possa fazer uma matrícula de ensino a distancia'
            },
            'cpf': '861.474.078-64',
            'criterios_sucesso': "['Serviço ativo.', 'Não há solicitações em aberto.']",
            'criterios_erro': "['Não há editais em que o cidadão foi aprovado, ou não estão em período de matrícula nem em período de avaliação.']",
            'is_ok': False
        }, {
            'servico': {
                'icone': 'fa fa-question-circle', 'id_servico_portal_govbr': 10056,
                'titulo': 'Protocolar Documentos',
                'descricao': 'Este serviço permite que um cidadão possa protocolar documentos junto a instituição'
            },
            'cpf': '861.474.078-64',
            'criterios_sucesso': "['Serviço ativo.', 'Não há solicitações em aberto.']", 'criterios_erro': '[]',
            'is_ok': True
        }
    ], 'mensagem': None, 'has_error': False
}

receber_solicitacao_protocolar_documento_01_response_fieldsets = [
    {
        'name': 'Declaração de Ciência',
        'fields': ['declaracao_ciencia']
    },
    {
        'name': 'Dados Pessoais',
        'fields': ['nome', 'cpf', 'email', 'telefone']
    },
    {
        'name': 'Endereço',
        'fields': ['cep', 'logradouro', 'numero', 'complemento', 'cidade', 'bairro']
    }
]

receber_solicitacao_protocolar_documento_02_request = {
    'etapa_atual': 1, 'total_etapas': 2, 'nome': 'Etapa 1',
    'formulario': [
        {
            'type': 'boolean', 'label': 'Confirmo', 'name': 'declaracao_ciencia', 'value': None, 'required': True
        },
        {
            'type': 'string', 'label': 'Nome', 'name': 'nome', 'value': 'Joao Pereira', 'required': True,
            'read_only': True, 'max_length': 200, 'min_length': 0, 'balcaodigital_user_info': 'GOVBR_NOME',
            'widget': 'textinput', 'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'CPF', 'name': 'cpf', 'value': '157.329.477-28', 'required': True,
            'read_only': True, 'mask': '000.000.000-00', 'max_length': 255, 'min_length': 0,
            'balcaodigital_user_info': 'GOVBR_CPF', 'widget': 'textinput', 'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'E-mail', 'name': 'email', 'value': 'hugotacito1@gmail.com', 'required': True,
            'max_length': 200, 'min_length': 0, 'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Telefone', 'name': 'telefone', 'value': '123123123', 'required': True,
            'max_length': 200, 'min_length': 0, 'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Cep', 'name': 'cep', 'value': '59370-000', 'required': False,
            'mask': '00000-000',
            'max_length': 9, 'min_length': 0, 'balcaodigital_user_info': 'TSE_CEP', 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Logradouro', 'name': 'logradouro', 'value': 'RUA DA MATRIZ', 'required': True,
            'max_length': 255, 'min_length': 0, 'balcaodigital_user_info': 'TSE_ENDERECO', 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Número', 'name': 'numero', 'value': '10', 'required': True, 'max_length': 255,
            'min_length': 0, 'balcaodigital_user_info': 'TSE_NUMERO', 'widget': 'textinput', 'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Complemento', 'name': 'complemento', 'value': 'IGREJA', 'required': False,
            'max_length': 255, 'min_length': 0, 'balcaodigital_user_info': 'TSE_COMPLEMENTO', 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Bairro', 'name': 'bairro', 'value': 'CENTRO', 'required': True,
            'max_length': 255,
            'min_length': 0, 'balcaodigital_user_info': 'TSE_BAIRRO', 'widget': 'textinput', 'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices', 'label': 'Cidade', 'name': 'cidade', 'value': '5200050', 'required': True,
            'choices_resource_id': 'IlByb3RvY29sYXJEb2N1bWVudG9TZXJ2aWNlUHJvdmlkZXIuY2hvaWNlc19jaWRhZGUi:1kb6Wm:dqS6y_cBQwWkNdf274cTT3kSoVA',
            'filters': 'null', 'lazy': True, 'avaliacao_status': None, 'avaliacao_status_msg': None,
            'choices': {'5200050': 'Abadia de Goias-GO'}, 'display_value': 'Abadia de Goias-GO'
        }
    ],
    'fieldsets': [
        {'name': 'Declaração de Ciência', 'fields': ['declaracao_ciencia']},
        {'name': 'Dados Pessoais', 'fields': ['nome', 'cpf', 'email', 'telefone']},
        {'name': 'Endereço', 'fields': ['cep', 'logradouro', 'numero', 'complemento', 'cidade', 'bairro']}
    ]
}

receber_solicitacao_protocolar_documento_02_response_fieldsets = [
    {'name': 'Dados do Requerimento', 'fields': ['assunto', 'descricao', 'campus']},
    {'name': 'Anexo 1', 'fields': ['anexo_1_descricao', 'anexo_1_file']},
    {'name': 'Anexo 2', 'fields': ['anexo_2_descricao', 'anexo_2_file']},
    {'name': 'Anexo 3', 'fields': ['anexo_3_descricao', 'anexo_3_file']},
    {'name': 'Anexo 4', 'fields': ['anexo_4_descricao', 'anexo_4_file']},
    {'name': 'Anexo 5', 'fields': ['anexo_5_descricao', 'anexo_5_file']}
]

receber_solicitacao_protocolar_documento_03_request = {
    'etapa_atual': 2, 'total_etapas': 2, 'nome': 'Etapa 2',
    'formulario': [
        {
            'type': 'string', 'label': 'Assunto', 'name': 'assunto',
            'value': 'best', 'required': True, 'max_length': 100,
            'min_length': 0, 'balcaodigital_user_info': None,
            'widget': 'textinput', 'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Descrição', 'name': 'descricao',
            'value': 'best', 'required': True, 'max_length': 510,
            'min_length': 0, 'balcaodigital_user_info': None,
            'widget': 'textarea', 'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices', 'label': 'Campus', 'name': 'campus',
            'value': '1', 'required': True,
            'choices_resource_id': 'IlByb3RvY29sYXJEb2N1bWVudG9TZXJ2aWNlUHJvdmlkZXIuY2hvaWNlc191bmlkYWRlX29yZ2FuaXphY2lvbmFsIg:1kb6Xz:uXQ83JN5dXRG6atmgMExlN7aGLI',
            'filters': 'null', 'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {'8': 'CAMPUS APODI', '7': 'CAMPUS CAICÓ',
                        '13': 'CAMPUS NATAL - CIDADE ALTA',
                        '41': 'CAMPUS CANGUARETAMA',
                        '45': 'CAMPUS CEARÁ-MIRIM',
                        '3': 'CAMPUS CURRAIS NOVOS',
                        '1': 'CAMPUS NATAL - CENTRAL',
                        '6': 'CAMPUS IPANGUAÇU',
                        '9': 'CAMPUS JOÃO CÂMARA',
                        '55': 'CAMPUS AVANÇADO JUCURUTU',
                        '47': 'CAMPUS AVANÇADO LAJES',
                        '10': 'CAMPUS MACAU', '4': 'CAMPUS MOSSORÓ',
                        '16': 'CAMPUS NOVA CRUZ',
                        '48': 'CAMPUS AVANÇADO PARELHAS',
                        '15': 'CAMPUS PARNAMIRIM',
                        '11': 'CAMPUS PAU DOS FERROS',
                        '12': 'CAMPUS SANTA CRUZ',
                        '17': 'CAMPUS SÃO GONÇALO DO AMARANTE',
                        '43': 'CAMPUS SÃO PAULO DO POTENGI',
                        '14': 'CAMPUS AVANÇADO NATAL-ZONA LESTE',
                        '2': 'CAMPUS NATAL - ZONA NORTE',
                        '18': 'REITORIA'}
        },
        {
            'type': 'string', 'label': 'Descrição',
            'name': 'anexo_1_descricao', 'value': '', 'required': False,
            'max_length': 100, 'min_length': 0,
            'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'file', 'label': 'Anexo', 'name': 'anexo_1_file',
            'value': None, 'required': False, 'label_to_file': 'Anexo1',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None, 'value_content_type': None,
            'value_original_name': None, 'value_size_in_bytes': None,
            'value_md5_hash': None, 'value_charset': None,
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Descrição',
            'name': 'anexo_2_descricao', 'value': '', 'required': False,
            'max_length': 100, 'min_length': 0,
            'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'file', 'label': 'Anexo', 'name': 'anexo_2_file',
            'value': None, 'required': False, 'label_to_file': 'Anexo2',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None, 'value_content_type': None,
            'value_original_name': None, 'value_size_in_bytes': None,
            'value_md5_hash': None, 'value_charset': None,
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Descrição',
            'name': 'anexo_3_descricao', 'value': '', 'required': False,
            'max_length': 100, 'min_length': 0,
            'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'file', 'label': 'Anexo', 'name': 'anexo_3_file',
            'value': None, 'required': False, 'label_to_file': 'Anexo3',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None, 'value_content_type': None,
            'value_original_name': None, 'value_size_in_bytes': None,
            'value_md5_hash': None, 'value_charset': None,
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Descrição',
            'name': 'anexo_4_descricao', 'value': '', 'required': False,
            'max_length': 100, 'min_length': 0,
            'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'file', 'label': 'Anexo', 'name': 'anexo_4_file',
            'value': None, 'required': False, 'label_to_file': 'Anexo4',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None, 'value_content_type': None,
            'value_original_name': None, 'value_size_in_bytes': None,
            'value_md5_hash': None, 'value_charset': None,
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'string', 'label': 'Descrição',
            'name': 'anexo_5_descricao', 'value': '', 'required': False,
            'max_length': 100, 'min_length': 0,
            'balcaodigital_user_info': None, 'widget': 'textinput',
            'avaliacao_status': None, 'avaliacao_status_msg': None
        },
        {
            'type': 'file', 'label': 'Anexo', 'name': 'anexo_5_file',
            'value': None, 'required': False, 'label_to_file': 'Anexo5',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None, 'value_content_type': None,
            'value_original_name': None, 'value_size_in_bytes': None,
            'value_md5_hash': None, 'value_charset': None,
            'avaliacao_status': None, 'avaliacao_status_msg': None
        }
    ],
    'fieldsets': [
        {'name': 'Dados do Requerimento', 'fields': ['assunto', 'descricao', 'campus']},
        {'name': 'Anexo 1', 'fields': ['anexo_1_descricao', 'anexo_1_file']},
        {'name': 'Anexo 2', 'fields': ['anexo_2_descricao', 'anexo_2_file']},
        {'name': 'Anexo 3', 'fields': ['anexo_3_descricao', 'anexo_3_file']},
        {'name': 'Anexo 4', 'fields': ['anexo_4_descricao', 'anexo_4_file']},
        {'name': 'Anexo 5', 'fields': ['anexo_5_descricao', 'anexo_5_file']}
    ]
}

receber_solicitacao_protocolar_documento_03_response = {
    'resposta': {
        'situacao': 'EM_ANALISE',
        'mensagem': 'Dados enviados com sucesso. A sua solicitação está aguardando análise.'
    },
    'mensagem': None, 'has_error': False
}
