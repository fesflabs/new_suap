import tqdm

from clipping.models import PublicacaoDigital, Veiculo, Editorial, Fonte
from xml.dom import minidom
import urllib.request
import urllib.parse
import urllib.error
import tempfile
import os


def download(url):
    webFile = urllib.request.urlopen(url)
    localfile = tempfile.NamedTemporaryFile('w', delete=False)
    localfile.write(webFile.read().decode('utf-8'))
    webFile.close()
    return localfile.name


def read(url):
    from dateutil.parser import parse

    rss_links = []
    filename = download(url)
    dom = minidom.parse(filename).documentElement
    os.unlink(filename)
    for channel in dom.getElementsByTagName("channel"):
        if channel.getElementsByTagName("lastBuildDate"):
            pubdate = parse(channel.getElementsByTagName("lastBuildDate")[0].childNodes[0].nodeValue)
        for item in channel.getElementsByTagName("item"):
            title = item.getElementsByTagName("title")[0].childNodes[0].nodeValue
            link = item.getElementsByTagName("link")[0].childNodes[0].nodeValue
            description = ''
            if item.getElementsByTagName("pubDate"):
                pubdate = parse(item.getElementsByTagName("pubDate")[0].childNodes[0].nodeValue)
            if item.getElementsByTagName("description"):
                if item.getElementsByTagName("description")[0].childNodes:
                    description = item.getElementsByTagName("description")[0].childNodes[0].nodeValue
            if item.getElementsByTagName("content"):
                description = item.getElementsByTagName("content")[0].childNodes[0].nodeValue
            rss_links.append(dict(title=title, pubdate=pubdate, link=link, description=description))
    for item in dom.getElementsByTagName("entry"):
        title = item.getElementsByTagName("title")[0].childNodes[0].nodeValue
        link = item.getElementsByTagName("link")[0].getAttribute("href")
        description = ''
        if item.getElementsByTagName("published"):
            pubdate = parse(item.getElementsByTagName("published")[0].childNodes[0].nodeValue)
        if item.getElementsByTagName("updated"):
            pubdate = parse(item.getElementsByTagName("updated")[0].childNodes[0].nodeValue)
        if item.getElementsByTagName("summary"):
            if item.getElementsByTagName("summary")[0].childNodes:
                description = item.getElementsByTagName("summary")[0].childNodes[0].nodeValue
        if item.getElementsByTagName("description"):
            if item.getElementsByTagName("description")[0].childNodes:
                description = item.getElementsByTagName("description")[0].childNodes[0].nodeValue
        if item.getElementsByTagName("content"):
            if item.getElementsByTagName("content")[0].childNodes:
                description = item.getElementsByTagName("content")[0].childNodes[0].nodeValue
        rss_links.append(dict(title=title, pubdate=pubdate, link=link, description=description))

    return rss_links


def importar_tudo(verbosity=3):
    count = 0
    qs = Fonte.objects.filter(ativo=True)
    if verbosity:
        fontes = tqdm.tqdm(qs)
    else:
        fontes = qs
    for fonte in fontes:
        try:
            itens = read(fonte.link)
            for item in itens:
                publicacao = PublicacaoDigital()
                publicacao.data = item['pubdate']
                publicacao.titulo = item['title'].strip()
                publicacao.texto = item['description']
                publicacao.link = item['link']
                publicacao.subtitulo = ''
                publicacao.veiculo = Veiculo.objects.get_or_create(nome=fonte.nome)[0]
                publicacao.editorial = Editorial.objects.get_or_create(nome=fonte.editorial)[0]
                if not PublicacaoDigital.objects.filter(titulo=publicacao.titulo, veiculo__nome=fonte.nome).exists():
                    palavras_chaves = publicacao.get_palavras_chaves()
                    if palavras_chaves:
                        publicacao.save()
                        publicacao.palavras_chaves = palavras_chaves
                        publicacao.save()
                        count += 1
                        # print '[OK]'
                        # print publicacao.titulo
                        # print publicacao.texto
                        # print '\n\n\n\n'
        except Exception:
            import traceback
            if verbosity:
                traceback.print_exc()
    return count
