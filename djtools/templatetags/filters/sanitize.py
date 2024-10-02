from django.utils.safestring import mark_safe
from lxml import html
import re
from lxml.html import clean
from django import template

register = template.Library()


@register.filter
def sanitize(obj, skip=None):
    """
        Instances cleans the document of each of the possible offending
        elements.  The cleaning is controlled by attributes; you can
        override attributes in a subclass, or set them in the constructor.

        ``scripts``:
            Removes any ``<script>`` tags.

        ``javascript``:
            Removes any Javascript, like an ``onclick`` attribute. Also removes stylesheets
            as they could contain Javascript.

        ``comments``:
            Removes any comments.

        ``style``:
            Removes any style tags.

        ``inline_style``
            Removes any style attributes.  Defaults to the value of the ``style`` option.

        ``links``:
            Removes any ``<link>`` tags

        ``meta``:
            Removes any ``<meta>`` tags

        ``page_structure``:
            Structural parts of a page: ``<head>``, ``<html>``, ``<title>``.

        ``processing_instructions``:
            Removes any processing instructions.

        ``embedded``:
            Removes any embedded objects (flash, iframes)

        ``frames``:
            Removes any frame-related tags

        ``forms``:
            Removes any form tags

        ``annoying_tags``:
            Tags that aren't *wrong*, but are annoying.  ``<blink>`` and ``<marquee>``

        ``remove_tags``:
            A list of tags to remove.  Only the tags will be removed,
            their content will get pulled up into the parent tag.

        ``kill_tags``:
            A list of tags to kill.  Killing also removes the tag's content,
            i.e. the whole subtree, not just the tag itself.

        ``allow_tags``:
            A list of tags to include (default include all).

        ``remove_unknown_tags``:
            Remove any tags that aren't standard parts of HTML.

        ``safe_attrs_only``:
            If true, only include 'safe' attributes (specifically the list
            from the feedparser HTML sanitisation web site).

        ``safe_attrs``:
            A set of attribute names to override the default list of attributes
            considered 'safe' (when safe_attrs_only=True).

        ``add_nofollow``:
            If true, then any <a> tags will have ``rel="nofollow"`` added to them.

        ``host_whitelist``:
            A list or set of hosts that you can use for embedded content
            (for content like ``<object>``, ``<link rel="stylesheet">``, etc).
            You can also implement/override the method
            ``allow_embedded_url(el, url)`` or ``allow_element(el)`` to
            implement more complex rules for what can be embedded.
            Anything that passes this test will be shown, regardless of
            the value of (for instance) ``embedded``.

            Note that this parameter might not work as intended if you do not
            make the links absolute before doing the cleaning.

            Note that you may also need to set ``whitelist_tags``.

        ``whitelist_tags``:
            A set of tags that can be included with ``host_whitelist``.
            The default is ``iframe`` and ``embed``; you may wish to
            include other tags like ``script``, or you may want to
            implement ``allow_embedded_url`` for more control.  Set to None to
            include all tags.

        This modifies the document *in place*.
    """
    if skip == 'processo_eletronico':
        try:
            cleaner = clean.Cleaner(safe_attrs=html.defs.safe_attrs | set(['style']))
            conteudo = cleaner.clean_html(obj)
            # wkhtmltopdf quebra se não remover urls https
            # conteudo = re.sub(r'https:\/{2}[\d\w-]+(\.[\d\w-]+)*(?:(?:\/[^\s/]*))*', '', conteudo) # remove demais string demais
            conteudo = re.sub(r'(url\(\"*\'*https:\/\/)(\s)*(www\.)?(\s)*((\w|\s|\-)+\.)*([\w\-\s]+\/)*([\w\-\.]+)((\?)?[\w\s]*=\s*[\w\%&]*)*', '', conteudo)
            return mark_safe(conteudo)
        except Exception:
            return mark_safe(obj)
    else:
        cleaner = clean.Cleaner()
    try:
        return mark_safe(cleaner.clean_html(obj))
    except Exception:
        return mark_safe(obj)
