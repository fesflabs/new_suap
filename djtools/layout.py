from django.dispatch import Signal

from djtools.utils import silenciar

index_alertas_data = Signal()  # providing_args=["request"]
index_infos_data = Signal()  # providing_args=["request"]
index_quick_access_data = Signal()  # providing_args=["request"]
index_inscricoes_data = Signal()  # providing_args=["request"]
index_atualizacoes_data = Signal()  # providing_args=["request"]
index_quadros_data = Signal()  # providing_args=["request"]
servicos_anonimos_data = Signal()  # providing_args=["request"]
quadros_cadastrados = []


class Layout:
    pass


class Quadro(Layout):
    def __init__(self, titulo, icone, classes=''):
        self.items = dict()
        self.titulo = titulo
        self.icone = icone
        self.classes = classes

    def add_item(self, item):
        klass_name = type(item).__name__

        if not klass_name in self.items:
            self.items[klass_name] = list()

        self.items[klass_name].append(item)

    def add_itens(self, itens):
        for item in itens:
            self.add_item(item)

    def has_items(self):
        return len(self.items) > 0

    def get_items(self, klass_name):
        return self.items.get(klass_name)

    def get_acessos_rapidos(self):
        return self.get_items('ItemAcessoRapido')

    def get_buscas_rapidas(self):
        return self.get_items('BuscaRapida')

    def get_calendarios(self):
        return self.get_items('ItemCalendario')

    def get_contadores(self):
        return self.get_items('ItemContador')

    def get_indicadores(self):
        return self.get_items('ItemIndicador')

    def get_grupos(self):
        return self.get_items('ItemGrupo')

    def get_imagens(self):
        return self.get_items('ItemImagem')

    def get_listas(self):
        return self.get_items('ItemLista')

    def get_noticias(self):
        return self.get_items('ItemNoticia')

    def get_titulos(self):
        return self.get_items('ItemTitulo')


class ItemBase(Layout):
    def __init__(self, titulo, url):
        self.titulo = titulo
        self.url = url


class ItemCalendario(Layout):
    def __init__(self, calendario, legenda=''):
        self.calendario = calendario
        self.legenda = legenda


class ItemLista(Layout):
    def __init__(self, titulo, valor, grupo='', url=''):
        self.titulo = titulo
        self.valor = valor
        self.grupo = grupo
        self.url = url


class ItemAcessoRapido(ItemBase):
    def __init__(self, icone='link', classe='default', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.icone = icone
        self.classe = classe


class BuscaRapida(ItemBase):
    def __init__(self, extra_valor='', extra_nome='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_valor = extra_valor
        self.extra_nome = extra_nome


class ItemNoticia(ItemBase):
    def __init__(self, chapeu='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chapeu = chapeu


class ItemContador(ItemBase):
    def __init__(self, qtd, subtitulo='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qtd = qtd
        self.subtitulo = subtitulo


class ItemIndicador(ItemBase):
    def __init__(self, qtd, grupo='', icone='', classname='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qtd = qtd
        self.grupo = grupo
        self.icone = icone
        self.classname = classname


class ItemGrupo(ItemBase):
    def __init__(self, grupo, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.grupo = grupo


class ItemImagem(ItemBase):
    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.path = path


class ItemTitulo(Layout):
    def __init__(self, titulo):
        self.titulo = titulo


def quadro(titulo, icone, classes='', pode_esconder=False):
    nome_quadro = titulo.upper()
    quadros_cadastrados.append(nome_quadro)

    def receive_function(func):
        @silenciar()
        def index_quadro(sender, request, **kwargs):
            from comum.models import IndexLayout

            layouts_salvos = request.session.get('index_layout')
            if not layouts_salvos:
                layouts_salvos = request.session['index_layout'] = {}

            if nome_quadro in list(layouts_salvos.keys()):
                quadro_visivel = not request.session['index_layout'][nome_quadro]['escondido']
            else:
                qs = IndexLayout.objects.filter(quadro_nome=nome_quadro, usuario=request.user)
                if not qs.exists():
                    i = IndexLayout(quadro_nome=nome_quadro, quadro_coluna=1, quadro_ordem=1, usuario=request.user)
                    i.save()
                    IndexLayout.recarregar_layouts(request)
                quadro_visivel = True

            obj = Quadro(titulo, icone, classes)
            obj.pode_esconder = pode_esconder
            if quadro_visivel or not pode_esconder:
                return func(obj, request)
            else:
                return None

        index_quadros_data.connect(index_quadro)
        return index_quadro

    return receive_function


def connect_signal(signal):
    def receive_function(func):
        @silenciar(return_on_error=[])
        def index_signal(sender, request, **kwargs):
            return func(request)

        signal.connect(index_signal)
        return index_signal

    return receive_function


def quick_access():
    return connect_signal(index_quick_access_data)


def alerta():
    return connect_signal(index_alertas_data)


def info():
    return connect_signal(index_infos_data)


def inscricao():
    return connect_signal(index_inscricoes_data)


def atualizacao():
    return connect_signal(index_atualizacoes_data)


def servicos_anonimos():
    return connect_signal(servicos_anonimos_data)


def gerar_servicos_anonimos(request):
    servicos_anonimos = []
    for _, data in servicos_anonimos_data.send(sender=gerar_servicos_anonimos, request=request):
        servicos_anonimos.extend(data)
    servicos_anonimos = sorted(servicos_anonimos, key=lambda data: data["categoria"])
    return servicos_anonimos
