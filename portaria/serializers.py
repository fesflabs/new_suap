from datetime import timedelta
from rest_framework import serializers
from .models import Acesso, ConfiguracaoSistemaPortaria


class AcessoSerializer(serializers.ModelSerializer):
    expiration = serializers.SerializerMethodField('get_expiration')

    class Meta:
        model = Acesso
        fields = ('chave_wifi', 'expiration')

    def get_expiration(self, obj):
        expiration_date = obj.data_geracao_chave_wifi + timedelta(obj.quantidade_dias_chave_wifi)
        return expiration_date.strftime("%B %d %Y %H:%M:%S")

    def get_simultaneous_use(self, obj):
        conf = ConfiguracaoSistemaPortaria.objects.get(campus=obj.local_acesso)
        return conf.limite_compartilhamento_chave

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['Simultaneous-Use'] = self.get_simultaneous_use(instance)
        return ret
