from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives.parts import Sectnum
from docutils.writers import html4css1
import sphinx.domains.std


class MyHTMLWriter(html4css1.Writer):
    """
This docutils writer will use the MyHTMLTranslator class below.
    """

    def __init__(self):
        html4css1.Writer.__init__(self)
        self.translator_class = MyHTMLTranslator


class MyHTMLTranslator(html4css1.HTMLTranslator):
    """
This is a translator class for the docutils system.
It will produce a minimal set of html output.
(No extry divs, classes oder ids.)
    """

    def visit_section(self, node):
        import sys

        sys.exit(1)

        self.section_level += 1
        self.body.append(self.starttag(node, 'div', CLASS='section'))

    def depart_section(self, node):
        self.section_level -= 1
        self.body.append('</div>\n')


############################################################################################
############################################################################################
############################################################################################
############################################################################################


class highlight(nodes.Inline, nodes.TextElement):
    pass


def visit_highlight(self, node):
    self.body.append(self.starttag(node, 'span', '', CLASS="highlight"))


def depart_highlight(self, node):
    self.body.append('</span>')


############################################################################################
############################################################################################
############################################################################################
############################################################################################


############################################################################################
############################################################################################
############################################################################################
############################################################################################


class example_node(nodes.Element):
    pass


class Examp(Directive):
    # .. container::
    #    :class: myclass
    #
    #    Content material here....
    # That should do exactly what you're trying to do with your custom directive. (<div class="myclass">Content material here...</div>)
    has_content = True

    def run(self):
        text = '\n'.join(self.content)
        node = example_node(rawsource=text)
        self.state.nested_parse(self.content, self.content_offset, node)
        return [node]


def visit_example(self, node):
    self.body.append(self.starttag(node, 'div', CLASS='example'))


def depart_example(self, node):
    self.body.append('</div>\n')


############################################################################################
############################################################################################
############################################################################################


"""
Changes section references to be the section number
instead of the title of the section.
"""


class CustomStandardDomain(sphinx.domains.std.StandardDomain):
    def __init__(self, env):
        env.settings['footnote_references'] = 'superscript'
        sphinx.domains.std.StandardDomain.__init__(self, env)

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        res = super(CustomStandardDomain, self).resolve_xref(env, fromdocname, builder, typ, target, node, contnode)

        if res is None:
            return res

        if typ == 'ref' and not node['refexplicit']:
            docname, labelid, sectname = self.data['labels'].get(target, ('', '', ''))
            res['refdocname'] = docname

        return res


def doctree_resolved(app, doctree, docname):

    secnums = app.builder.env.toc_secnumbers

    #     print '**********************************', docname
    #
    #     print '\n\n\n'
    #     if docname == 'uc/adm/ae/doc_visao':
    #         for node in doctree.traverse(nodes.title):
    #             print node
    # #         sys.exit(1)
    #

    for node in doctree.traverse(nodes.reference):
        if 'refdocname' in node:
            refdocname = node['refdocname']
            if refdocname in secnums:
                secnum = secnums[refdocname]
                emphnode = node.children[0]
                textnode = emphnode.children[0]

                toclist = app.builder.env.tocs[refdocname]
                anchorname = None
                for refnode in toclist.traverse(nodes.reference):
                    if refnode.astext() == textnode.astext():
                        anchorname = refnode['anchorname']
                if anchorname is None:
                    continue
                linktext = '.'.join(map(str, secnum[anchorname]))
                node.replace(emphnode, nodes.Text(linktext))


def visit_section(self, node):
    import sys

    sys.exit(1)

    self.section_level += 1
    self.body.append(self.starttag(node, 'div', CLASS='sections'))


def depart_section(self, node):
    self.section_level -= 1
    self.body.append('</div>\n')


def setup(app):

    app.override_domain(CustomStandardDomain)
    app.connect('doctree-resolved', doctree_resolved)

    app.add_directive('example', Examp)
    app.add_node(example_node, html=(visit_example, depart_example))

    # parts(transforms) class SectNum(Transform):

    app.add_node(Sectnum, html=(visit_section, depart_section))

    app.add_node(highlight, html=(visit_highlight, depart_highlight))
    app.add_generic_role('highlight', highlight)
