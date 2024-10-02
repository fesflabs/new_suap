import copy
import json

from comum.models import Ano
from rh.models import UnidadeOrganizacional

dados_ead_etapa_1_dict = {
    'etapa_atual': 1,
    'total_etapas': 5,
    'nome': 'Etapa 1',
    'formulario': [
        {
            'type': 'choices',
            'label': 'Edital',
            'name': 'candidato_vaga',
            'value': '702181',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2NhbmRpZGF0b3NfdmFnYSI:1jq1Mg:z-GWNxiQIzCnodTUhNYKLOwN7fM',
            'filters': {
                'cpf': '682.564.070-42'
            },
            'avaliacao_status': 'OK',
            'avaliacao_status_msg': None,
            'choices': {
                '702181': 'EDITAL Nº 11/2020-DG/ZL/RE/IFRN - Cursos de formação inicial e continuada (FIC) na modalidade EaD - Programa Novos Caminhos de 2020/1'
            },
            'display_value': 'EDITAL Nº 11/2020-DG/ZL/RE/IFRN - Cursos de formação inicial e continuada (FIC) na modalidade EaD - Programa Novos Caminhos de 2020/1'
        }
    ],
    'fieldsets': [
        {
            'name': 'Dados do Edital', 'fields': [
                'candidato_vaga']}
    ]
}

dados_ead_etapa_2_dict = {
    'etapa_atual': 2,
    'total_etapas': 5,
    'nome': 'Etapa 2',
    'formulario': [
        {
            'type': 'string',
            'label': 'Edital',
            'name': 'edital_nome',
            'value': 'EDITAL Nº 11/2020-DG/ZL/RE/IFRN - Cursos de formação inicial e continuada (FIC) na modalidade EaD - Programa Novos Caminhos',
            'required': True,
            'read_only': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Vaga',
            'name': 'edital_vaga',
            'value': 'Formação Inicial e Continuada em Agente de Alimentação escolar',
            'required': True,
            'read_only': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Lista',
            'name': 'edital_lista',
            'value': 'Geral',
            'required': True,
            'read_only': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'CPF',
            'name': 'cpf',
            'value': '097.642.304-90',
            'required': True,
            'read_only': True,
            'mask': '000.000.000-00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Nacionalidade',
            'name': 'nacionalidade',
            'value': 'Brasileira',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX25hY2lvbmFsaWRhZGUi:1jq1Mk:AR4_vp2W_d_kAwLHEKrBQ8z4gEo',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Brasileira': 'Brasileira',
                'Brasileira - Nascido no exterior ou naturalizado': 'Brasileira - Nascido no exterior ou naturalizado',
                'Estrangeira': 'Estrangeira'
            },
            'display_value': 'Brasileira'
        },
        {
            'type': 'string',
            'label': 'Nº do Passaporte',
            'name': 'passaporte',
            'value': '',
            'required': False,
            'max_length': 50,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Nome',
            'name': 'nome',
            'value': 'Marcos Paulo',
            'required': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Sexo',
            'name': 'sexo',
            'value': 'F',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3NleG8i:1jq1Mk:BNj0oQyYr6xWAyYsJtMCVVF7vD0',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'F': 'Feminino', 'M': 'Masculino'
            },
            'display_value': 'Feminino'
        },
        {
            'type': 'date',
            'label': 'Data de Nascimento',
            'name': 'data_nascimento',
            'value': '1995-04-04',
            'required': True,
            'mask': '00/00/0000',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Estado Civil',
            'name': 'estado_civil',
            'value': 'Solteiro',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkb19jaXZpbCI:1jq1Mk:hjNq4VKblt_DBG6yuSu5Lyl-wZM',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Solteiro': 'Solteiro',
                'Casado': 'Casado',
                'União Estável': 'União Estável',
                'Divorciado': 'Divorciado',
                'Viúvo': 'Viúvo'
            },
            'display_value': 'Solteiro'
        },
        {
            'type': 'file',
            'label': 'Foto 3x4 recente',
            'name': 'foto_3x4',
            'value': None,
            'required': True,
            'label_to_file': 'Foto 3x4',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': [
                'jpg', 'jpeg', 'png'],
            'value_hash_sha512_link_id': 'dd0bf2f484480cc2829633a39574212b2a3108f5f4ec8a313216a4603da8b694776b1ce3501825426abbab95c904e560cb9189db799f74ad3d45d5610318fe46',
            'value_hash_sha512': None,
            'value_content_type': 'image/jpeg',
            'value_original_name': 'foto.jpg',
            'value_size_in_bytes': 66408,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Cep',
            'name': 'cep',
            'value': '59255-000',
            'required': False,
            'mask': '00000-000',
            'max_length': 9,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Logradouro',
            'name': 'logradouro',
            'value': 'Rua Doutor Hélio Barbosa de oliveira',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Número',
            'name': 'numero',
            'value': '185',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Complemento',
            'name': 'complemento',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Bairro',
            'name': 'bairro',
            'value': 'Centro',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Estado',
            'name': 'estado',
            'value': '24',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkbyI:1jq1Mk:O63L84ni0TnlXM-S05zVLZrVayg',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '24': 'Rio Grande do Norte'
            },
            'display_value': 'Rio Grande do Norte'
        },
        {
            'type': 'choices',
            'label': 'Cidade',
            'name': 'cidade',
            'value': '2401403',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2NpZGFkZSI:1jq1Mk:6HOo9X5aR38pF_piBSfy0Eg_0mk',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '2401403': 'Natal EAD-RN'
            },
            'display_value': 'Natal EAD-RN'
        },
        {
            'type': 'choices',
            'label': 'Zona Residencial',
            'name': 'tipo_zona_residencial',
            'value': '1',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3pvbmFfcmVzaWRlbmNpYWwi:1jq1Mk:gwUhnP9_wbGutFYWT6KKS_VhOE4',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Urbana', '2': 'Rural'
            },
            'display_value': 'Urbana'
        },
        {
            'type': 'string',
            'label': 'Nome',
            'name': 'nome_pai',
            'value': 'Wilson Paulo de Araújo',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Estado Civil',
            'name': 'estado_civil_pai',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkb19jaXZpbCI:1jq1Mk:hjNq4VKblt_DBG6yuSu5Lyl-wZM',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Solteiro': 'Solteiro',
                'Casado': 'Casado',
                'União Estável': 'União Estável',
                'Divorciado': 'Divorciado',
                'Viúvo': 'Viúvo'
            },
            'display_value': ''
        },
        {
            'type': 'boolean',
            'label': 'Falecido?',
            'name': 'pai_falecido',
            'value': False,
            'required': False,
            'html': '',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Nome',
            'name': 'nome_mae',
            'value': 'Alice Leonel da Silva',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Estado Civil',
            'name': 'estado_civil_mae',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkb19jaXZpbCI:1jq1Mk:hjNq4VKblt_DBG6yuSu5Lyl-wZM',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Solteiro': 'Solteiro',
                'Casado': 'Casado',
                'União Estável': 'União Estável',
                'Divorciado': 'Divorciado',
                'Viúvo': 'Viúvo'
            },
            'display_value': ''
        },
        {
            'type': 'boolean',
            'label': 'Falecida?',
            'name': 'mae_falecida',
            'value': False,
            'required': False,
            'html': '',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Responsável',
            'name': 'responsavel',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'E-mail',
            'name': 'email_responsavel',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Parentesco',
            'name': 'parentesco_responsavel',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3BhcmVudGVzY28i:1jq1Mk:Kf15zoIeoho__4Saadfidni_PnU',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Pai/Mãe': 'Pai/Mãe',
                'Avô/Avó': 'Avô/Avó',
                'Tio/Tia': 'Tio/Tia',
                'Sobrinho/Sobrinha': 'Sobrinho/Sobrinha',
                'Outro': 'Outro'
            },
            'display_value': ''
        },
        {
            'type': 'string',
            'label': 'CPF',
            'name': 'cpf_responsavel',
            'value': '',
            'required': False,
            'mask': '000.000.000-00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        }
    ],
    'fieldsets': [
        {
            'name': 'Dados do Edital',
            'fields': [
                'edital_nome', 'edital_vaga', 'edital_lista']
        },
        {
            'name': 'Identificação', 'fields': [
                'cpf', 'nacionalidade', 'passaporte']
        },
        {
            'name': 'Dados Pessoais',
            'fields': [
                'nome', 'sexo', 'data_nascimento', 'estado_civil', 'foto_3x4']
        },
        {
            'name': 'Endereço',
            'fields': [
                'cep',
                'logradouro',
                'numero',
                'complemento',
                'estado',
                'cidade',
                'bairro',
                'tipo_zona_residencial'
            ]
        },
        {
            'name': 'Dados Familiares - Pai',
            'fields': [
                'nome_pai', 'estado_civil_pai', 'pai_falecido']
        },
        {
            'name': 'Dados Familiares - Mãe',
            'fields': [
                'nome_mae', 'estado_civil_mae', 'mae_falecida']
        },
        {
            'name': 'Dados Familiares - Responsável',
            'fields': [
                'responsavel',
                'email_responsavel',
                'parentesco_responsavel',
                'cpf_responsavel'
            ]
        }
    ]
}

dados_ead_etapa_2_dict_corrigido = copy.copy(dados_ead_etapa_2_dict)
dados_ead_etapa_2_dict_corrigido[
    'formulario'][6][
    'value'] = 'Marcos Paulo de Araújo'

dados_ead_etapa_3_dict = {
    'etapa_atual': 3,
    'total_etapas': 5,
    'nome': 'Etapa 3',
    'formulario': [
        {
            'type': 'string',
            'label': 'Telefone Principal',
            'name': 'telefone_principal',
            'value': '(84) 99999-3185',
            'required': False,
            'mask': '00telefone00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Telefone Secundário',
            'name': 'telefone_secundario',
            'value': '(84) 99479-4276',
            'required': False,
            'mask': '00telefone00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Telefone do Responsável',
            'name': 'telefone_adicional_1',
            'value': '',
            'required': False,
            'mask': '00telefone00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Telefone do Responsável',
            'name': 'telefone_adicional_2',
            'value': '',
            'required': False,
            'mask': '00telefone00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'E-mail Pessoal',
            'name': 'email_pessoal',
            'value': 'joao@joao.com',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Portador de Necessidades Especiais',
            'name': 'aluno_pne',
            'value': 'Não',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3NpbV9uYW8i:1jq1NG:udOy3c1w9eEdFNE6W7aOthfiBmw',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Sim': 'Sim', 'Não': 'Não'
            },
            'display_value': 'Não'
        },
        {
            'type': 'choices',
            'label': 'Deficiência',
            'name': 'tipo_necessidade_especial',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3RpcG9fbmVzc2VjaWRhZGVfZXNwZWNpYWwi:1jq1NG:5o98jHropbjsVYqPTBenz3xRls4',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Baixa Visão',
                '11': 'Cegueira',
                '2': 'Deficiência Auditiva',
                '3': 'Deficiência Física',
                '4': 'Deficiência Intelectual',
                '5': 'Deficiência Múltipla',
                '22': 'Surdez',
                '222': 'Surdocegueira'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Transtorno',
            'name': 'tipo_transtorno',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3RpcG9fdHJhbnN0b3JubyI:1jq1NG:he6hwthRta4GyoXYM23uhHZIUp8',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Autismo',
                '2': 'Síndrome de Asperger',
                '3': 'Síndrome de Rett',
                '4': 'Transtorno Desintegrativo da Infância'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Superdotação',
            'name': 'superdotacao',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3N1cGVyZG90YWNhbyI:1jq1NG:HcPLcHH-Z14MhdDwUvqpRE8-La0',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Altas habilidades/Superdotação'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Utiliza Transporte Escolar Público',
            'name': 'utiliza_transporte_escolar_publico',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3NpbV9uYW8i:1jq1NG:udOy3c1w9eEdFNE6W7aOthfiBmw',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Sim': 'Sim', 'Não': 'Não'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Poder Público Responsável pelo Transporte Escolar',
            'name': 'poder_publico_responsavel_transporte',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3BvZGVyX3B1YmxpY29fcmVzcG9uc2F2ZWxfdHJhbnNwb3J0ZSI:1jq1NG:CxvEGXgiPmyq3mTuX7LlWgVqEb4',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Municipal', '2': 'Estadual'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Tipo de Veículo Utilizado no Transporte Escolar',
            'name': 'tipo_veiculo',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3RpcG9fdmVpY3VsbyI:1jq1NG:MLdR53yiXnTm2hHAoTNeLigrFos',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Vans/WV',
                '2': 'Kombi Micro-Ônibus',
                '3': 'Ônibus',
                '4': 'Bicicleta',
                '5': 'Tração Animal',
                '6': 'Outro tipo de veículo rodoviário',
                '7': 'Capacidade de até 5 alunos',
                '8': 'Capacidade entre 5 a 15 alunos',
                '9': 'Capacidade entre 15 e 35 alunos',
                '10': 'Capacidade acima de 35 alunos',
                '11': 'Trem/Metrô'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Tipo Sanguíneo',
            'name': 'tipo_sanguineo',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3RpcG9fc2FuZ3VpbmVvIg:1jq1NG:bQEzLdI7PbWVkOQKhfClqJuCYc0',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'O-': 'O-',
                'O+': 'O+',
                'A-': 'A-',
                'A+': 'A+',
                'B-': 'B-',
                'B+': 'B+',
                'AB-': 'AB-',
                'AB+': 'AB+'
            },
            'display_value': ''
        },
        {
            'type': 'choices',
            'label': 'Estado de Origem',
            'name': 'estado_naturalidade',
            'value': '24',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkbyI:1jq1NG:TVp3QAJOhNCwcB_XYtp6bvYN7Og',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '24': 'Rio Grande do Norte'
            },
            'display_value': 'Rio Grande do Norte'
        },
        {
            'type': 'choices',
            'label': 'Naturalidade',
            'name': 'naturalidade',
            'value': '2401403',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2NpZGFkZSI:1jq1NG:quFpRi4Nsv6jVxawbqENdR5pH2s',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '2401403': 'Natal EAD-RN'
            },
            'display_value': 'Natal EAD-RN'
        },
        {
            'type': 'choices',
            'label': 'Raça',
            'name': 'raca',
            'value': '101',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3JhY2Ei:1jq1NG:SwoyotX53Sht3aLKORJnbMrI9F8',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '101': 'Parda EAD'
            },
            'display_value': 'Parda EAD'
        },
        {
            'type': 'choices',
            'label': 'Nível de Ensino',
            'name': 'nivel_ensino_anterior',
            'value': '1',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX25pdmVsX2Vuc2lubyI:1jq1NG:1E7LSWiQQIYVn6kjXtcBqQJiX9Q',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Fundamental'
            },
            'display_value': 'Fundamental'
        },
        {
            'type': 'choices',
            'label': 'Tipo da Instituição',
            'name': 'tipo_instituicao_origem',
            'value': 'Pública',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3RpcG9faW5zdGl0dWljYW9fb3JpZ2VtIg:1jq1NG:YrwWEyTNYDCdmVRVfX7-YJXxk-I',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                'Pública': 'Pública', 'Privada': 'Privada'
            },
            'display_value': 'Pública'
        },
        {
            'type': 'choices',
            'label': 'Ano de Conclusão',
            'name': 'ano_conclusao_estudo_anterior',
            'value': str(Ano.objects.get(ano='2020').pk),
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2FubyI:1jq1NG:BOAzR06UxzAh-1QGr9mHRH4P_Kc',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                str(Ano.objects.get(ano='2020').pk): '2020'
            },
            'display_value': '2020'
        },
        {
            'type': 'file',
            'label': 'Declaração/certidão/certificado/diploma ou histórico de conclusão da formação mínima',
            'name': 'copia_doc_conclusao_ensino',
            'value': None,
            'required': True,
            'label_to_file': 'Comprovação de Formação Mínima',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': [
                'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png'],
            'value_hash_sha512_link_id': 'dd0bf2f484480cc2829633a39574212b2a3108f5f4ec8a313216a4603da8b694776b1ce3501825426abbab95c904e560cb9189db799f74ad3d45d5610318fe46',
            'value_hash_sha512': None,
            'value_content_type': 'image/jpeg',
            'value_original_name': 'foto.jpg',
            'value_size_in_bytes': 66408,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        }
    ],
    'fieldsets': [
        {
            'name': 'Informações para Contato',
            'fields': [
                'telefone_principal',
                'telefone_secundario',
                'telefone_adicional_1',
                'telefone_adicional_2',
                'email_pessoal'
            ]
        },
        {
            'name': 'Deficiências, Transtornos e Superdotação',
            'fields': [
                'aluno_pne',
                'tipo_necessidade_especial',
                'tipo_transtorno',
                'superdotacao'
            ]
        },
        {
            'name': 'Transporte Escolar Utilizado',
            'fields': [
                'utiliza_transporte_escolar_publico',
                'poder_publico_responsavel_transporte',
                'tipo_veiculo'
            ]
        },
        {
            'name': 'Outras Informações',
            'fields': [
                'estado_naturalidade',
                'naturalidade',
                'raca',
                'tipo_sanguineo'
            ]
        },
        {
            'name': 'Dados Escolares Anteriores',
            'fields': [
                'nivel_ensino_anterior',
                'tipo_instituicao_origem',
                'ano_conclusao_estudo_anterior',
                'copia_doc_conclusao_ensino'
            ]
        }
    ]
}

dados_ead_etapa_4_dict = {
    'etapa_atual': 4,
    'total_etapas': 5,
    'nome': 'Etapa 4',
    'formulario': [
        {
            'type': 'string',
            'label': 'Número do RG',
            'name': 'numero_rg',
            'value': '2810506',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Estado Emissor',
            'name': 'uf_emissao_rg',
            'value': '24',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkbyI:1jq1Nm:-RIF7SafknMsNsRZGAVXDD77XIc',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '24': 'Rio Grande do Norte'
            },
            'display_value': 'Rio Grande do Norte'
        },
        {
            'type': 'choices',
            'label': 'Orgão Emissor',
            'name': 'orgao_emissao_rg',
            'value': '40',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX29yZ2FvX2VtaXNzYW9fcmci:1jq1Nm:j2u6tWUlBT2DGWaX_DFS3kpqty0',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '40': 'Ministérios Militares'
            },
            'display_value': 'Ministérios Militares'
        },
        {
            'type': 'date',
            'label': 'Data de Emissão',
            'name': 'data_emissao_rg',
            'value': '2006-03-30',
            'required': True,
            'mask': '00/00/0000',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Cópia do RG legível',
            'name': 'copia_rg',
            'value': None,
            'required': True,
            'label_to_file': 'RG',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': [
                'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png'],
            'value_hash_sha512_link_id': 'dd0bf2f484480cc2829633a39574212b2a3108f5f4ec8a313216a4603da8b694776b1ce3501825426abbab95c904e560cb9189db799f74ad3d45d5610318fe46',
            'value_hash_sha512': None,
            'value_content_type': 'image/jpeg',
            'value_original_name': 'foto.jpg',
            'value_size_in_bytes': 66408,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Título de Eleitor',
            'name': 'numero_titulo_eleitor',
            'value': '12',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Zona',
            'name': 'zona_titulo_eleitor',
            'value': '12',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Seção',
            'name': 'secao',
            'value': '12',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'date',
            'label': 'Data de Emissão',
            'name': 'data_emissao_titulo_eleitor',
            'value': '1212-12-12',
            'required': True,
            'mask': '00/00/0000',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Estado Emissor',
            'name': 'uf_emissao_titulo_eleitor',
            'value': '24',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2VzdGFkbyI:1jq1Nm:-RIF7SafknMsNsRZGAVXDD77XIc',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '12': 'Acre'
            },
            'display_value': 'Acre'
        },
        {
            'type': 'file',
            'label': 'Cópia do Título de Eleitor',
            'name': 'copia_titulo',
            'value': None,
            'required': True,
            'label_to_file': 'Título de Eleitor',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': [
                'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png'],
            'value_hash_sha512_link_id': 'dd0bf2f484480cc2829633a39574212b2a3108f5f4ec8a313216a4603da8b694776b1ce3501825426abbab95c904e560cb9189db799f74ad3d45d5610318fe46',
            'value_hash_sha512': None,
            'value_content_type': 'image/jpeg',
            'value_original_name': 'foto.jpg',
            'value_size_in_bytes': 66408,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Cópia de Quitação Eleitoral',
            'name': 'copia_quitacao_eleitoral',
            'value': None,
            'required': True,
            'label_to_file': 'Comprovante de Quitação Eleitoral',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': [
                'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png'],
            'value_hash_sha512_link_id': 'dd0bf2f484480cc2829633a39574212b2a3108f5f4ec8a313216a4603da8b694776b1ce3501825426abbab95c904e560cb9189db799f74ad3d45d5610318fe46',
            'value_hash_sha512': None,
            'value_content_type': 'image/jpeg',
            'value_original_name': 'foto.jpg',
            'value_size_in_bytes': 66408,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Tipo de Certidão',
            'name': 'tipo_certidao',
            'value': '1',
            'required': True,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX3RpcG9fY2VydGlkYW8i:1jq1Nm:WlYnaEAApVvQCzPyWEIr7Y5QIzQ',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'Nascimento', '2': 'Casamento'
            },
            'display_value': 'Nascimento'
        },
        {
            'type': 'choices',
            'label': 'Cartório',
            'name': 'cartorio',
            'value': '',
            'required': False,
            'choices_resource_id': 'Ik1hdHJpY3VsYUVhZFNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2NhcnRvcmlvIg:1jq1Nn:uR0sjyxCrrx5lweomwRfstIJjIc',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'display_value': ''
        },
        {
            'type': 'string',
            'label': 'Número de Termo',
            'name': 'numero_certidao',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Folha',
            'name': 'folha_certidao',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Livro',
            'name': 'livro_certidao',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'date',
            'label': 'Data de Emissão',
            'name': 'data_emissao_certidao',
            'value': None,
            'required': False,
            'mask': '00/00/0000',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Matrícula',
            'name': 'matricula_certidao',
            'value': '',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Cópia da Certidão',
            'name': 'copia_certidao',
            'value': None,
            'required': True,
            'label_to_file': 'Certidão',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': [
                'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png'],
            'value_hash_sha512_link_id': 'dd0bf2f484480cc2829633a39574212b2a3108f5f4ec8a313216a4603da8b694776b1ce3501825426abbab95c904e560cb9189db799f74ad3d45d5610318fe46',
            'value_hash_sha512': None,
            'value_content_type': 'image/jpeg',
            'value_original_name': 'foto.jpg',
            'value_size_in_bytes': 66408,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        }
    ],
    'fieldsets': [
        {
            'name': 'RG',
            'fields': [
                'numero_rg',
                'uf_emissao_rg',
                'orgao_emissao_rg',
                'data_emissao_rg',
                'copia_rg'
            ]
        },
        {
            'name': 'Título de Eleitor',
            'fields': [
                'numero_titulo_eleitor',
                'zona_titulo_eleitor',
                'secao',
                'data_emissao_titulo_eleitor',
                'uf_emissao_titulo_eleitor',
                'copia_titulo',
                'copia_quitacao_eleitoral'
            ]
        },
        {
            'name': 'Certidão Civil',
            'fields': [
                'tipo_certidao',
                'cartorio',
                'numero_certidao',
                'folha_certidao',
                'livro_certidao',
                'data_emissao_certidao',
                'matricula_certidao',
                'copia_certidao'
            ]
        }
    ]
}

dados_ead_etapa_5_dict = {
    'etapa_atual': 5,
    'total_etapas': 5,
    'nome': 'Etapa 5',
    'formulario': [
        {
            'type': 'boolean',
            'label': 'Confirmo',
            'name': 'declaracao_didatica',
            'value': True,
            'required': True,
            'html': '<p>Declaro que estou ciente das normas previstas na Organização Didática* do IFRN e que:</p><ol><li>Terei que frequentar as aulas presenciais, independente do turno, se assim a Instituição determinar;</li><li>Terei de renovar minha matrícula, periodicamente, durante o período de renovação de matrícula, previsto no Calendário Acadêmico, sob pena de ter a matrícula cancelada pela instituição;</li><li>Caso deixe de frequentar as aulas (acessar o ambiente virtual), nos 10 (dez) primeiros dias úteis do início do curso, sem que seja apresentada uma justificativa, serei desligado do IFRN, sendo minha vaga preenchida por outro candidato, de acordo com a ordem classificatória do processo seletivo.</li><li>O estudante não poderá ocupar matrículas simultâneas no mesmo campus ou em diferentes campi do IFRN, nas seguintes situações, independente da modalidade de ensino: em mais de um curso de pós-graduação stricto sensu, em mais de um curso de pós-graduação lato sensu; em mais de um curso de graduação; em mais de um curso técnico de nível médio. Não será permitida a matrícula simultânea em mais de dois cursos.</li><li>Para os alunos de graduação, estou ciente da Lei Federal nº 12.089 de 11 de novembro de 2009, que proíbe que uma mesma pessoa ocupe 2 (duas) vagas simultaneamente em instituições públicas de ensino superior.</li></ol><p>Diante do exposto, assumo o compromisso de seguir as normas institucionais, e peço deferimento.\u200b</p>',
            'avaliacao_status': 'OK',
            'avaliacao_status_msg': None
        },
        {
            'type': 'boolean',
            'label': 'Confirmo',
            'name': 'declaracao_legais',
            'value': True,
            'required': True,
            'html': 'Declaro, também, estar ciente de que, a comprovação da falsidade desta declaração, em procedimento que me assegure o contraditório e a ampla defesa, implicará no cancelamento da minha matrícula nesta Instituição Federal de Ensino, sem prejuízo das sanções penais cabíveis.',
            'avaliacao_status': 'OK',
            'avaliacao_status_msg': None
        },
        {
            'type': 'boolean',
            'label': 'Confirmo',
            'name': 'declaracao_veracidade',
            'value': True,
            'required': True,
            'html': 'Reconheço que as informações prestadas são verdadeiras.',
            'avaliacao_status': 'OK',
            'avaliacao_status_msg': None
        },
        {
            'type': 'boolean',
            'label': 'Confirmo',
            'name': 'declaracao_conclusao',
            'value': True,
            'required': True,
            'html': 'Confirmo que após concluir o meu cadastro não poderei mais alterar os dados e arquivos enviados.',
            'avaliacao_status': 'OK',
            'avaliacao_status_msg': None
        }
    ],
    'fieldsets': [
        {
            'name': 'Declarações de Organização didática',
            'fields': [
                'declaracao_didatica']
        },
        {
            'name': 'Declarações legais', 'fields': [
                'declaracao_legais']
        },
        {
            'name': 'Declaração de veracidade', 'fields': [
                'declaracao_veracidade']
        },
        {
            'name': 'Declaração de conclusão', 'fields': [
                'declaracao_conclusao']
        }
    ]
}

dados_diploma_etapa_1_dict = {
    'etapa_atual': 1,
    'total_etapas': 1,
    'nome': 'Etapa 1',
    'formulario': [
        {
            'type': 'string',
            'label': 'Nome',
            'name': 'nome',
            'value': 'Maria Eduarda',
            'required': True,
            'read_only': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': 'NOME',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'CPF',
            'name': 'cpf',
            'value': '947.767.240-81',
            'required': True,
            'read_only': True,
            'mask': '000.000.000-00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': 'CPF',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'E-mail',
            'name': 'email',
            'value': 'maria@eduarda.com',
            'required': True,
            'read_only': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': 'EMAIL',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Telefone',
            'name': 'telefone',
            'value': '31996455971',
            'required': True,
            'read_only': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': 'FONE',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Matrícula',
            'name': 'alunos',
            'value': '96439',
            'display_value': '20121014040334 - Tecnologia em Análise e Desenvolvimento de Sistemas (2012) - Campus Natal-Central',
            'required': True,
            'choices_resource_id': 'IkVtaXNzYW9TZWd1bmRhVmlhRGlwbG9tYVNlcnZpY2VQcm92aWRlci5jaG9pY2VzX2FsdW5vcyI:1jqLXj:U9QcBpP3bQKyWEzdqLHPVn-LLwg',
            'filters': {
                'pessoa_fisica__cpf': '947.767.240-81'
            },
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '96439': '20121014040334 - Tecnologia em Análise e Desenvolvimento de Sistemas (2012) - Campus Natal-Central'
            }
        }
    ],
    'fieldsets': [
        {
            'name': 'Dados Pessoais',
            'fields': [
                'nome', 'cpf', 'email', 'telefone']
        },
        {
            'name': 'Matrícula', 'fields': [
                'alunos']
        }
    ]
}

dados_ead_etapa_1 = json.dumps(dados_ead_etapa_1_dict)
dados_ead_etapa_2 = json.dumps(dados_ead_etapa_2_dict)
dados_ead_etapa_2_corrigido = json.dumps(dados_ead_etapa_2_dict_corrigido)
dados_ead_etapa_3 = json.dumps(dados_ead_etapa_3_dict)
dados_ead_etapa_4 = json.dumps(dados_ead_etapa_4_dict)
dados_ead_etapa_5 = json.dumps(dados_ead_etapa_5_dict)

dados_diploma_etapa_1 = json.dumps(dados_diploma_etapa_1_dict)

dados_processo_etapa_1_dict = {
    'etapa_atual': 1,
    'total_etapas': 2,
    'nome': 'Etapa 1',
    'formulario': [
        {
            'type': 'string',
            'label': 'Nome',
            'name': 'nome',
            'value': 'João Tomé Pinto de Souza Palhares Blá',
            'required': True,
            'read_only': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': 'NOME',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'CPF',
            'name': 'cpf',
            'value': '682.564.070-42',
            'required': True,
            'read_only': True,
            'mask': '000.000.000-00',
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': 'CPF',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'E-mail',
            'name': 'email',
            'value': 'joao@jao.com',
            'required': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Telefone',
            'name': 'telefone',
            'value': '31996455971',
            'required': True,
            'read_only': True,
            'max_length': 200,
            'min_length': 0,
            'balcaodigital_user_info': 'FONE',
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Cep',
            'name': 'cep',
            'value': '59000-000',
            'required': False,
            'mask': '00000-000',
            'max_length': 9,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Logradouro',
            'name': 'logradouro',
            'value': 'av jaguarari',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Número',
            'name': 'numero',
            'value': '8499',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Complemento',
            'name': 'complemento',
            'value': 'apto 101',
            'required': False,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Bairro',
            'name': 'bairro',
            'value': 'Candelária',
            'required': True,
            'max_length': 255,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Cidade',
            'name': 'cidade',
            'value': '2401403',
            'required': True,
            'choices_resource_id': 'IlByb3RvY29sYXJEb2N1bWVudG9TZXJ2aWNlUHJvdmlkZXIuY2hvaWNlc19jaWRhZGUi:1jqQsm:B2TCD0JZF3txIWwsyvM0HvXFIhM',
            'filters': None,
            'lazy': True,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '2401403': 'Natal EAD-RN'
            },
            'display_value': 'Natal EAD-RN'
        }
    ],
    'fieldsets': [
        {
            'name': 'Dados Pessoais',
            'fields': [
                'nome', 'cpf', 'email', 'telefone'
            ]
        },
        {
            'name': 'Endereço',
            'fields': [
                'cep',
                'logradouro',
                'numero',
                'complemento',
                'cidade',
                'bairro'
            ]
        }
    ]
}

dados_processo_etapa_2_dict = {
    'etapa_atual': 2,
    'total_etapas': 2,
    'nome': 'Etapa 2',
    'formulario': [
        {
            'type': 'string',
            'label': 'Assunto',
            'name': 'assunto',
            'value': 'Transparência de Dados',
            'required': True,
            'max_length': 100,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Descrição',
            'name': 'descricao',
            'value': 'Solicito acesso aos dados de quantos alunos foram aprovados pela instituição no ano de 2018.',
            'required': True,
            'max_length': 510,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textarea',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'choices',
            'label': 'Campus',
            'name': 'campus',
            'value': str(UnidadeOrganizacional.objects.get(sigla='CEN').pk),
            'required': True,
            'choices_resource_id': 'IlByb3RvY29sYXJEb2N1bWVudG9TZXJ2aWNlUHJvdmlkZXIuY2hvaWNlc191bmlkYWRlX29yZ2FuaXphY2lvbmFsIg:1jqQtX:5AbqNshZeeKJCSYF1j7hegg-oAQ',
            'filters': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None,
            'choices': {
                '1': 'RAIZ',
                str(UnidadeOrganizacional.objects.get(sigla='CEN').pk): 'CEN'
            },
            'display_value': 'CEN'
        },
        {
            'type': 'string',
            'label': 'Descrição',
            'name': 'anexo_1_descricao',
            'value': 'Solicitação do MP',
            'required': False,
            'max_length': 100,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Anexo',
            'name': 'anexo_1_file',
            'value': None,
            'required': False,
            'label_to_file': 'Anexo1',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': 'fac33e5a056a9dab2b8f1f7b49a0721e6b317b800898fd3ed0e4767f15a0c3c91e183c682f064b0b5327032a02cb0e5c83f0ed9a4483a9ff54b377aa6cffb715',
            'value_hash_sha512': None,
            'value_content_type': 'application/pdf',
            'value_original_name': 'Ligacao Nova.pdf',
            'value_size_in_bytes': 39079,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Descrição',
            'name': 'anexo_2_descricao',
            'value': '',
            'required': False,
            'max_length': 100,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Anexo',
            'name': 'anexo_2_file',
            'value': None,
            'required': False,
            'label_to_file': 'Anexo2',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None,
            'value_content_type': None,
            'value_original_name': None,
            'value_size_in_bytes': None,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Descrição',
            'name': 'anexo_3_descricao',
            'value': '',
            'required': False,
            'max_length': 100,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Anexo',
            'name': 'anexo_3_file',
            'value': None,
            'required': False,
            'label_to_file': 'Anexo3',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None,
            'value_content_type': None,
            'value_original_name': None,
            'value_size_in_bytes': None,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Descrição',
            'name': 'anexo_4_descricao',
            'value': '',
            'required': False,
            'max_length': 100,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Anexo',
            'name': 'anexo_4_file',
            'value': None,
            'required': False,
            'label_to_file': 'Anexo4',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None,
            'value_content_type': None,
            'value_original_name': None,
            'value_size_in_bytes': None,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'string',
            'label': 'Descrição',
            'name': 'anexo_5_descricao',
            'value': '',
            'required': False,
            'max_length': 100,
            'min_length': 0,
            'balcaodigital_user_info': None,
            'widget': 'textinput',
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        },
        {
            'type': 'file',
            'label': 'Anexo',
            'name': 'anexo_5_file',
            'value': None,
            'required': False,
            'label_to_file': 'Anexo5',
            'limit_size_in_bytes': 2097152,
            'allowed_extensions': ['pdf'],
            'value_hash_sha512_link_id': None,
            'value_hash_sha512': None,
            'value_content_type': None,
            'value_original_name': None,
            'value_size_in_bytes': None,
            'value_md5_hash': None,
            'value_charset': None,
            'avaliacao_status': None,
            'avaliacao_status_msg': None
        }
    ],
    'fieldsets': [
        {
            'name': 'Dados do Requerimento',
            'fields': ['assunto', 'descricao', 'campus']
        },
        {
            'name': 'Anexo 1', 'fields': ['anexo_1_descricao', 'anexo_1_file']
        },
        {
            'name': 'Anexo 2', 'fields': ['anexo_2_descricao', 'anexo_2_file']
        },
        {
            'name': 'Anexo 3', 'fields': ['anexo_3_descricao', 'anexo_3_file']
        },
        {
            'name': 'Anexo 4', 'fields': ['anexo_4_descricao', 'anexo_4_file']
        },
        {
            'name': 'Anexo 5', 'fields': ['anexo_5_descricao', 'anexo_5_file']
        }
    ]
}

dados_processo_etapa_1 = json.dumps(dados_processo_etapa_1_dict)
dados_processo_etapa_2 = json.dumps(dados_processo_etapa_2_dict)
