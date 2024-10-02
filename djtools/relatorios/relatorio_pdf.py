# -*- coding: utf-8 -*-

from io import BytesIO
from django.conf import settings
from os.path import join
from djtools.relatorios.utils import data_assinatura, montar_paragrafo, montar_tabela_pdf
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak
from reportlab.platypus import SimpleDocTemplate, Spacer, Frame


class RelatorioPDF(object):
    """
    Gera um relatório reportlab em formato de tabela a partir
    de um dicionário de dados
    Converte o dict 'dados' em atributos da instância.

    A chave 'elementos' contém uma lista de itens que serão adicionados ao
    documento. Caso o item seja do tipo basestring, ele será convertido num
    parágrafo, caso seja dict, será uma tabela.

    Args:
        dados (dict or string) : dados da tabela ou parágrafo
        paisagem (bool) : formato do relatório
        """
    valores_padrao = dict(
        cidade='Natal',
        altura_pagina=210 * mm,
        largura_pagina=297 * mm,
        margem_esquerda=15 * mm,
        margem_direita=15 * mm,
        margem_superior=20 * mm,
        margem_inferior=20 * mm,
        elementos=[],
    )

    def __init__(self, dados, paisagem=False):
        self.paisagem = paisagem
        for chave, valor in list(RelatorioPDF.valores_padrao.items()):
            dados.setdefault(chave, valor)
        for chave, valor in list(dados.items()):
            self.__setattr__(chave, valor)
        self.data_assinatura = data_assinatura % (dict(cidade=self.cidade))

    def desenhar_brasao(self, canvas):
        """
        Desenha a imagem do brasão no canto superior esquerdo.

        Args:
            canvas (reportlab.pdfgen.canvas) : Documento PDF parcial
        """
        imagem = join(settings.STATIC_ROOT, 'comum/img/brasao_cinza.jpg')
        if self.paisagem:
            canvas.drawImage(imagem, self.largura_pagina - 250 * mm, self.altura_pagina - 38 * mm, 15.96 * mm, 17.4 * mm)
        else:
            canvas.drawImage(imagem, self.largura_pagina - 185 * mm, self.altura_pagina - 170 * mm, 15.96 * mm, 17.4 * mm)

    def montar_cabecalho(self, canvas):
        """
        Desenha o cabeçalho do relatório

        Args:
            canvas (reportlab.pdfgen.canvas) : Documento PDF parcial
        """
        self.desenhar_brasao(canvas)
        story = []
        for item in ['orgao', 'uo', 'setor']:
            item = montar_paragrafo(self.cabecalho.get(item, ''), alinhamento='center', tamanho=12)
            story.append(item)
        f = Frame(20 * mm, self.altura_pagina - 45 * mm, 230 * mm, 25 * mm, leftPadding=1 * mm, bottomPadding=1 * mm, rightPadding=1 * mm, topPadding=1 * mm, showBoundary=0)
        f.addFromList(story, canvas)
        canvas.setFont('Times-Roman', 9)
        canvas.drawRightString(self.largura_pagina - 21 * mm, self.altura_pagina - 43 * mm, self.data)

    def montar_rodape(self, canvas):
        """
        As subclasses podem implementar este método.

        Args:
            canvas (reportlab.pdfgen.canvas) : Documento PDF parcial
        """
        pass

    def montar_primeira_pagina(self, canvas, doc):
        """
        Monta a primeira página do relatório que pode ser diferente das demais

        Args:
            canvas (pdf_document) : Documento PDF parcial
        """
        canvas.saveState()
        self.montar_cabecalho(canvas)
        self.montar_rodape(canvas)
        canvas.setFont('Times-Roman', 16)
        canvas.drawCentredString(self.largura_pagina / 2, self.altura_pagina - 60 * mm, self.titulo)
        canvas.restoreState()

    def montar_paginas_seguintes(self, canvas, doc):
        """
        Monta as demais páginas do relatório

        Args:
            canvas (reportlab.pdfgen.canvas) : Documento PDF parcial
        """
        canvas.saveState()
        self.montar_rodape(canvas)
        canvas.restoreState()

    def montar(self):
        """
        Monta o pdf do relatório

        Returns:
            Documento PDF
        """
        arquivoPDF = BytesIO()
        if self.paisagem:
            doc = SimpleDocTemplate(
                arquivoPDF,
                showBoundary=0,
                leftMargin=self.margem_esquerda,
                rightMargin=self.margem_direita,
                topMargin=self.margem_superior,
                bottomMargin=self.margem_inferior,
                pagesize=landscape(A4),
            )
        else:
            doc = SimpleDocTemplate(
                arquivoPDF,
                showBoundary=0,
                leftMargin=self.margem_esquerda,
                rightMargin=self.margem_direita,
                topMargin=self.margem_superior,
                bottomMargin=self.margem_inferior
            )

        story = [Spacer(1, 48 * mm)]  # Espaçamento para o título

        for e in self.elementos[::-1]:
            if isinstance(e, dict):
                ultimo_dict = e
                break
        # Varrendo os elementos do relatório
        for e in self.elementos:

            # O elemento é um parágrafo
            if isinstance(e, str):
                story.append(montar_paragrafo(e))
            # O elemento é uma tabela
            elif isinstance(e, dict):
                story.append(Spacer(1, 5 * mm))
                story += montar_tabela_pdf(e)
                if not e == ultimo_dict:
                    story.append(PageBreak())
                story.append(Spacer(1, 5 * mm))
        doc.build(story, onFirstPage=self.montar_primeira_pagina, onLaterPages=self.montar_paginas_seguintes)
        return arquivoPDF.getvalue()
