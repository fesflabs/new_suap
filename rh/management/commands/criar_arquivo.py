import datetime

from catalogo_provedor_servico.models import SolicitacaoEtapa, SolicitacaoEtapaArquivo
from djtools.management.commands import BaseCommandPlus


# Ref:
# https://www.revsys.com/tidbits/loading-django-files-from-code/
class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        # Arquivo A1.pdf
        # original_name = 'A1.pdf'
        # content_strb64 = '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aWRzWyAxIDAgUiBdCi9Db3VudCAxPj4KZW5kb2JqCgoxMiAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgNCAwIFIKL09wZW5BY3Rpb25bMSAwIFIgL1hZWiBudWxsIG51bGwgMF0KL0xhbmcocHQtQlIpCj4+CmVuZG9iagoKMTMgMCBvYmoKPDwvQ3JlYXRvcjxGRUZGMDA1NzAwNzIwMDY5MDA3NDAwNjUwMDcyPgovUHJvZHVjZXI8RkVGRjAwNEMwMDY5MDA2MjAwNzIwMDY1MDA0RjAwNjYwMDY2MDA2OTAwNjMwMDY1MDAyMDAwMzYwMDJFMDAzMD4KL0NyZWF0aW9uRGF0ZShEOjIwMTkwMzA4MTc1ODE4LTAzJzAwJyk+PgplbmRvYmoKCnhyZWYKMCAxNAowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDUxNjQgMDAwMDAgbiAKMDAwMDAwMDAxOSAwMDAwMCBuIAowMDAwMDAwMTc2IDAwMDAwIG4gCjAwMDAwMDUzMzMgMDAwMDAgbiAKMDAwMDAwMDE5NSAwMDAwMCBuIAowMDAwMDA0Mzg0IDAwMDAwIG4gCjAwMDAwMDQ0MDUgMDAwMDAgbiAKMDAwMDAwNDYwNyAwMDAwMCBuIAowMDAwMDA0OTA1IDAwMDAwIG4gCjAwMDAwMDUwNzcgMDAwMDAgbiAKMDAwMDAwNTEwOSAwMDAwMCBuIAowMDAwMDA1NDMyIDAwMDAwIG4gCjAwMDAwMDU1MjkgMDAwMDAgbiAKdHJhaWxlcgo8PC9TaXplIDE0L1Jvb3QgMTIgMCBSCi9JbmZvIDEzIDAgUgovSUQgWyA8OUM2NjUwMDk1NDk5MDA1MDgxRjQ4RENFNEI4N0ZGMTE+Cjw5QzY2NTAwOTU0OTkwMDUwODFGNDhEQ0U0Qjg3RkYxMT4gXQovRG9jQ2hlY2tzdW0gLzhGNDZGNTRCNkU0NDg0NEJFNEVDQkY3NTg0NEU5MkNFCj4+CnN0YXJ0eHJlZgo1NzA0CiUlRU9GCg=='
        # content_type = 'application/pdf'
        # size = 6187
        # charset = None

        original_name = 'B1.pdf'
        content_strb64 = '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R0IvSSB0cnVlPj4vQ29udGVudHMgMiAwIFI+PgplbmRvYmoKCjQgMCBvYmoKPDwvVHlwZS9QYWdlcwovUmVzb3VyY2VzIDExIDAgUgovTWVkaWFCb3hbIDAgMCA1OTUgODQxIF0KL0tpZHNbIDEgMCBSIF0KL0NvdW50IDE+PgplbmRvYmoKCjEyIDAgb2JqCjw8L1R5cGUvQ2F0YWxvZy9QYWdlcyA0IDAgUgovT3BlbkFjdGlvblsxIDAgUiAvWFlaIG51bGwgbnVsbCAwXQovTGFuZyhwdC1CUikKPj4KZW5kb2JqCgoxMyAwIG9iago8PC9DcmVhdG9yPEZFRkYwMDU3MDA3MjAwNjkwMDc0MDA2NTAwNzI+Ci9Qcm9kdWNlcjxGRUZGMDA0QzAwNjkwMDYyMDA3MjAwNjUwMDRGMDA2NjAwNjYwMDY5MDA2MzAwNjUwMDIwMDAzNjAwMkUwMDMwPgovQ3JlYXRpb25EYXRlKEQ6MjAxOTAzMDgxNzU5NDQtMDMnMDAnKT4+CmVuZG9iagoKeHJlZgowIDE0CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwNTI2OCAwMDAwMCBuIAowMDAwMDAwMDE5IDAwMDAwIG4gCjAwMDAwMDAxODUgMDAwMDAgbiAKMDAwMDAwNTQzNyAwMDAwMCBuIAowMDAwMDAwMjA0IDAwMDAwIG4gCjAwMDAwMDQ0ODggMDAwMDAgbiAKMDAwMDAwNDUwOSAwMDAwMCBuIAowMDAwMDA0NzExIDAwMDAwIG4gCjAwMDAwMDUwMDkgMDAwMDAgbiAKMDAwMDAwNTE4MSAwMDAwMCBuIAowMDAwMDA1MjEzIDAwMDAwIG4gCjAwMDAwMDU1MzYgMDAwMDAgbiAKMDAwMDAwNTYzMyAwMDAwMCBuIAp0cmFpbGVyCjw8L1NpemUgMTQvUm9vdCAxMiAwIFIKL0luZm8gMTMgMCBSCi9JRCBbIDxBREIzNDZGMTYxMDlDQTc2QkM0MkYwRUIzNjgxMEVGMD4KPEFEQjM0NkYxNjEwOUNBNzZCQzQyRjBFQjM2ODEwRUYwPiBdCi9Eb2NDaGVja3N1bSAvQUZDQkFFMUZGRUE2QUY5NDA2OTVFNTQzNUVFQkNFOEQKPj4Kc3RhcnR4cmVmCjU4MDgKJSVFT0YK'
        content_type = 'application/pdf'
        size = 6291

        # content_bytes_b64 = content_strb64.encode('utf-8')
        # sha256_hash_strb64 = hashlib.sha512(content_bytes_b64).hexdigest()
        # content_bytes = base64.b64decode(content_bytes_b64)
        # sha256_hash = hashlib.sha512(content_bytes).hexdigest()
        #
        # django_file = File(content_bytes)
        #
        # arquivo = ArquivoUnico()
        # content = ContentFile(content_bytes)
        # arquivo.content_type = content_type
        # arquivo.size_in_bytes = size
        # arquivo.sha256_hash = sha256_hash
        # arquivo.content.save(original_name, content, save=False)
        # arquivo.save()
        #
        # print(arquivo)

        # arquivo_unico, created = ArquivoUnico.get_or_create_from_file_strb64(strb64=content_strb64,
        #                                                               tipo_conteudo=content_type,
        #                                                               tamanho_em_bytes=size,
        #                                                               data_hora_primeiro_upload=datetime.date(2020, 5, 1))
        # print(arquivo_unico, created)

        solicitacao_etapa = SolicitacaoEtapa.objects.get(id=18)
        solicitacao_etapa_arquivo, solicitacao_etapa_arquivo_created, arquivo_unico, arquivo_unico_created = SolicitacaoEtapaArquivo.update_or_create_from_file_strb64(
            strb64=content_strb64,
            tipo_conteudo=content_type,
            data_hora_upload=datetime.datetime.now(),
            nome_original=original_name,
            nome_exibicao='CertidaoNascimento.pdf',
            solicitacao_etapa=solicitacao_etapa,
            nome_atributo_json='certidao_nascimento',
            tamanho_em_bytes_para_validar=size,
            hash_sha512_para_validar=None,
            # solicitacao_etapa_arquivo_id=3
        )

        print(solicitacao_etapa_arquivo, solicitacao_etapa_arquivo_created, arquivo_unico, arquivo_unico_created)