# -*- coding: utf-8 -*-
from django.db import connection

from djtools.management.commands import BaseCommandPlus
from financeiro.models import SubElementoNaturezaDespesa, NaturezaDespesa
from djtools.db import has_column
from materiais.models import UnidadeMedida, Categoria, Material


class Command(BaseCommandPlus):
    def executar_sql(self, sql):
        cur = connection.cursor()
        cur.execute(sql)
        connection._commit()

    def evoluir_tabelas(self):
        sql = """
            ALTER TABLE "materiais_categoria" ADD COLUMN "ativa" boolean  DEFAULT True;
            ALTER TABLE "materiais_categoria" ALTER COLUMN "ativa" DROP DEFAULT;
            ALTER TABLE "materiais_categoria" ALTER COLUMN "ativa" SET NOT NULL;
        """
        if not has_column('materiais_categoria', 'ativa'):
            self.executar_sql(sql)

    def exportar_material(self, mc):

        natureza_despesa = NaturezaDespesa.objects.get(codigo='339030')

        unidade_medida = UnidadeMedida.objects.all()[0]
        if mc[3]:
            unidade_medida, nova = UnidadeMedida.objects.get_or_create(descricao=mc[3])
            if nova:
                pass
                # print 'Criada unidade de medida %s com id %s'%(mc[3], unidade_medida.pk)

        qs = SubElementoNaturezaDespesa.objects.filter(codigo_subelemento=mc[4], natureza_despesa=natureza_despesa)
        if not qs.exists():
            sub_elemento_nd = SubElementoNaturezaDespesa()
            sub_elemento_nd.natureza_despesa = natureza_despesa
            sub_elemento_nd.codigo_subelemento = mc[4]
            sub_elemento_nd.save()
            # print 'Criando subelemento de natureza de despesa %s com id %s'%(sub_elemento_nd.codigo, sub_elemento_nd.pk)

        else:
            sub_elemento_nd = qs[0]
        qs = Categoria.objects.filter(sub_elemento_nd=sub_elemento_nd, codigo='00')
        if not qs.exists():
            categoria = Categoria()
            categoria.id = sub_elemento_nd.pk
            categoria.sub_elemento_nd = sub_elemento_nd
            categoria.descricao = mc[2]
            categoria.codigo = '00'
            categoria.ativa = True
            categoria.save()
            # print 'Criada categoria de material %s %s com id %s'%(categoria.descricao, categoria.codigo_completo, categoria.pk)
        else:
            categoria = qs[0]
        material = Material.objects.create(categoria=categoria, unidade_medida=unidade_medida, descricao=mc[1], especificacao=mc[1], ativo=False)
        return material.id

    def remover_chaves_estrangeiras(self):
        sql = """
            ALTER TABLE almoxarifado_configuracaoestoque DROP CONSTRAINT "almoxarifado_configuracaoestoque_material_id_fkey";
            ALTER TABLE empenhoconsumo DROP CONSTRAINT "material_id_referencing_materialconsumo_id";
            ALTER TABLE requisicaoalmoxuomaterial DROP CONSTRAINT "material_id_referencing_materialconsumo_id_1";
            ALTER TABLE movimentoalmoxentrada DROP CONSTRAINT "movimentoalmoxentrada_material_id_fkey";
            ALTER TABLE movimentoalmoxsaida DROP CONSTRAINT "movimentoalmoxsaida_material_id_fkey";
            ALTER TABLE requisicaoalmoxusermaterial DROP CONSTRAINT "requisicaoalmoxusermaterial_material_id_fkey";
        """
        self.executar_sql(sql)

    def adicionar_chaves_estrangeiras(self):
        sql = """
            ALTER TABLE almoxarifado_configuracaoestoque ADD CONSTRAINT "almoxarifado_configuracaoestoque_material_id_fkey" FOREIGN KEY (material_id) REFERENCES materiais_material (id);
            ALTER TABLE empenhoconsumo ADD CONSTRAINT "material_id_referencing_materialconsumo_id" FOREIGN KEY (material_id) REFERENCES materiais_material (id);
            ALTER TABLE requisicaoalmoxuomaterial ADD CONSTRAINT "material_id_referencing_materialconsumo_id_1" FOREIGN KEY (material_id) REFERENCES materiais_material (id);
            ALTER TABLE movimentoalmoxentrada ADD CONSTRAINT "movimentoalmoxentrada_material_id_fkey" FOREIGN KEY (material_id) REFERENCES materiais_material (id);
            ALTER TABLE movimentoalmoxsaida ADD CONSTRAINT "movimentoalmoxsaida_material_id_fkey" FOREIGN KEY (material_id) REFERENCES materiais_material (id);
            ALTER TABLE requisicaoalmoxusermaterial ADD CONSTRAINT "requisicaoalmoxusermaterial_material_id_fkey" FOREIGN KEY (material_id) REFERENCES materiais_material (id);
        """
        self.executar_sql(sql)

    def inativar_categorias(self):
        Categoria.objects.filter(codigo='00').update(ativa=False)

    def handle(self, *args, **options):
        self.evoluir_tabelas()
        print('tabelas evoluidas')
        self.exportar_materiais()
        print('materiais exportados')
        self.remover_chaves_estrangeiras()
        print('chaves estrangeiras removidas')
        self.atualizar_referencias()
        print('referencias atualizadas')
        self.adicionar_chaves_estrangeiras()
        print('chaves estrangeiras adicionadas')
        self.inativar_categorias()
        print('categorias inativadas')
        print('MIGRACAO CONCLUIDA COM SUCESSO!')
