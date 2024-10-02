from catalogo_provedor_servico.providers.base import AbstractBaseServiceProviderFactory
from catalogo_provedor_servico.providers.impl.ifrn.solicitar_cerfificado_encceja import SolicitarCertificadoEnccejaServiceProvider
from .codes import (
    ID_GOVBR_12100_SOLICTAR_CERTIFICADO_ENCCEJA_IFRN,
    ID_GOVBR_6176_MATRICULA_EAD,
    ID_GOVBR_10056_PROTOCOLAR_DOCUMENTOS_IFRN,
    ID_GOVBR_6024_EMISSAO_SEGUNDA_VIA_DIPLOMA_IFRN,
    ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN,
    ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN,
    ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN
)
from .emissao_segunda_via_diploma import \
    EmissaoSegundaViaDiplomaServiceProvider
from .matricula_ead import MatriculaEadServiceProvider
from .matricula_superior import MatriculaSuperiorServiceProvider
from .matricula_tecnico import MatriculaTecnicoServiceProvider
from .protocolar_documento import ProtocolarDocumentoServiceProvider
from .matricula_pos_graduacao import MatriculaPosGraduacaoServiceProvider


class IfrnServiceProviderFactory(AbstractBaseServiceProviderFactory):
    def get_service_provider(self, id_servico_portal_govbr):
        if id_servico_portal_govbr == ID_GOVBR_6176_MATRICULA_EAD:
            return MatriculaEadServiceProvider()
        elif id_servico_portal_govbr == ID_GOVBR_12100_SOLICTAR_CERTIFICADO_ENCCEJA_IFRN:
            return SolicitarCertificadoEnccejaServiceProvider()
        elif id_servico_portal_govbr == ID_GOVBR_10056_PROTOCOLAR_DOCUMENTOS_IFRN:
            return ProtocolarDocumentoServiceProvider()
        elif id_servico_portal_govbr == ID_GOVBR_6024_EMISSAO_SEGUNDA_VIA_DIPLOMA_IFRN:
            return EmissaoSegundaViaDiplomaServiceProvider()
        elif id_servico_portal_govbr == ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN:
            return MatriculaSuperiorServiceProvider()
        elif id_servico_portal_govbr == ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN:
            return MatriculaTecnicoServiceProvider()
        elif id_servico_portal_govbr == ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN:
            return MatriculaPosGraduacaoServiceProvider()
        # else:
        #     return DefaultServiceProvider(id_servico_portal_govbr=id_servico_portal_govbr)
        # return None
