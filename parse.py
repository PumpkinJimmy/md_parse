from urllib.parse import quote
import re


class Block:
    """
    The interface of the AST block
    """

    def __init__(self, tp, apply_filter=True, **kwargs):
        self.type = tp
        self.apply_filter = apply_filter
        self.kwargs = kwargs

    def __repr__(self):
        return f"<{self.type}: {self.kwargs}>"

    def __getattr__(self, name):
        if name in self.kwargs:
            return self.kwargs[name]
        super().__getattribute__(name)


class Context:
    """
    The interface of the parsing context
    """
    def __init__(self, parser):
        self.parser = parser
        self.elements = []
        self.init()

    def init(self):
        pass

    @staticmethod
    def match(line):
        return True

    def handle(self, line):
        pass

    def accept(self, block):
        self.elements.append(block)

    def create(self):
        return Block("null")

    def on_exit(self):
        pass

class IndentContext(Context):
    def __init__(self, parser, indent=0):
        super().__init__(parser)
        self.indent = indent
    def applyIndent(self, line):
        if line[:self.indent] != ' ' * self.indent:
            raise Exception("Invalid indent")
        return line[self.indent:]


class HeadlineContext(Context):
    def init(self):
        self.hcnt = 0

    @staticmethod
    def match(line):
        return line.startswith('#') and not len(line) > 70

    def handle(self, line):
        while line.startswith('#'):
            self.hcnt += 1
            line = line[1:]
        self.text = line.strip()
        self.parser.nextLine()
        self.parser.contextExit()

    def create(self):
        return Block("headline", text=self.text, hcnt=self.hcnt)


class HLineContext(Context):
    @staticmethod
    def match(line):
        return re.match(r"^-{3,}$", line) or \
            re.match(r"^={3,}$", line)

    def handle(self, line):
        self.parser.nextLine()
        self.parser.contextExit()

    def create(self):
        return Block("hline")


class CodeContext(IndentContext):
    def init(self):
        self.inside = False
        self.lang = ''

    @staticmethod
    def match(line):
        return line.strip().startswith("```")

    def handle(self, line):
        line = self.applyIndent(line).rstrip()
        if line.strip().startswith('```'):
            line = line.strip()
            if self.inside:
                self.inside = False
                self.parser.contextExit()
            else:
                self.inside = True
                self.lang = line[3:]
        else:
            self.elements.append(line)
        self.parser.nextLine()

    def create(self):
        return Block("code", apply_filter=False, text='\n'.join(self.elements),
                     lang=self.lang)


class UListContext(IndentContext):
    @staticmethod
    def match(line):
        return line.startswith('- ')

    def __init__(self, parser, indent=0):
        super().__init__(parser,indent)
        self.li_eles = []

    def handle(self, line):
        if self.indent and not line[:self.indent].isspace():
            self.parser.contextExit()
            return
        line = line[self.indent:]
        if line.startswith('- '):
            if self.li_eles:
                self.elements.append(Block('listitem', elements=self.li_eles))
                self.li_eles = []
            line = line.lstrip('- ').rstrip(' ')
            self.li_eles.append(Block('paragraph', text=line))
            self.parser.nextLine()
        elif line[:2].isspace():
            line = line.lstrip('  ').rstrip(' ')
            for context in self.parser.contexts:
                if context.match(line):
                    self.parser.contextEnter(
                        context(self.parser, self.indent+2))
                    return
            self.li_eles.append(Block('paragraph', text=line))  # if not match
            self.parser.nextLine()
        else:
            self.parser.contextExit()

    def create(self):
        return Block("ulist", elements=self.elements)

    def accept(self, block):
        self.li_eles.append(block)

    def on_exit(self):
        if self.li_eles:
            self.elements.append(Block('listitem', elements=self.li_eles))


class OListContext(IndentContext):
    def __init__(self, parser, indent=0):
        super().__init__(parser, indent)
        self.indent = indent
        self.cnt = 1
        self.li_eles = []

    @staticmethod
    def match(line):
        return line.startswith('1. ')

    def handle(self, line):
        if self.indent and not line[:self.indent].isspace():
            self.parser.contextExit()
            return
        expect = str(self.cnt) + '. '
        line = line[self.indent:]
        if line.startswith(expect):
            if self.li_eles:
                self.elements.append(Block('listitem', elements=self.li_eles))
                self.li_eles = []
            line = line.lstrip(expect).rstrip()
            self.li_eles.append(Block('paragraph', text=line))
            self.cnt += 1
            self.parser.nextLine()
        elif line[:len(expect)].isspace():
            line = line[len(expect):]
            for context in self.parser.contexts:
                if context.match(line):
                    self.parser.contextEnter(
                                             context(
                                                 self.parser, self.indent +
                                                 len(expect)))
                    return
            self.li_eles.append(Block('paragraph', text=line))  # if not match
            self.parser.nextLine()
        else:
            self.parser.contextExit()

    def create(self):
        return Block("olist", elements=self.elements)

    def accept(self, block):
        self.li_eles.append(block)

    def on_exit(self):
        if self.li_eles:
            self.elements.append(Block('listitem', elements=self.li_eles))


class QuoteContext(IndentContext):
    @staticmethod
    def match(line):
        return line.startswith('>')

    def handle(self, line):
        line = self.applyIndent(line).rstrip()
        if not line.startswith('>'):
            self.parser.contextExit()
        else:
            self.elements.append(line.lstrip('>'))
            self.parser.nextLine()

    def create(self):
        return Block("quote", elements=self.elements)


class TableContext(Context):
    @staticmethod
    def match(line): return False


class MathContext(Context):
    @staticmethod
    def match(line): return False

class InlineMathContext(Context):
    @staticmethod
    def match(line): return False


class Parser:
    contexts = [
        HeadlineContext,
        HLineContext,
        CodeContext,
        UListContext,
        OListContext,
        QuoteContext,
        TableContext,
        MathContext]
    # filters = [HeadlineFilter, EmphasisFilter, ItalicFilter, Image, Href]

    def __init__(self, ccontexts=None, contexts=None, filters=None):
        if contexts is None:
            contexts = Parser.contexts[:]
        self.contexts = contexts
        if ccontexts is None:
            ccontexts = []
        self.ccontexts = ccontexts
        self.lineno = 0
        self.blocks = []

    def parse(self, src):
        self.lineno = 0
        self.lines = src.rstrip().split('\n')
        while self.lineno < len(self.lines):
            line = self.lines[self.lineno]
            if not self.ccontexts:
                self.handle(line.rstrip())
            else:
                self.ccontexts[-1].handle(line.rstrip())
        while self.ccontexts:
            self.contextExit()
        return self.blocks

    def nextLine(self):
        self.lineno += 1

    def contextMatch(self, line):
        for context in self.contexts:
            if context.match(line):
                self.contextEnter(context(self))
                return True

    def handle(self, line):
        if not self.contextMatch(line):
            self.blocks.append(Block("paragraph", text=line))
            self.nextLine()

    def contextEnter(self, context):
        self.ccontexts.append(context)

    def contextExit(self):
        if not self.ccontexts:
            return
        econtext = self.ccontexts.pop(-1)
        econtext.on_exit()
        if self.ccontexts:
            self.ccontexts[-1].accept(econtext.create())
        else:
            self.blocks.append(econtext.create())


class HtmlRenderer:
    def __init__(self):
        self.filters = [
            (r'!\[alt (.+?)\]\((.+?)\)', r'<img alt="\1" src="\2" />'),
            (r'\[\]\((.+?)\)', r'<a href="\1">\1</a>'),
            (r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>'),
            (r'\*\*(.+?)\*\*', r'<span class="em">\1</span>'),
            (r'\*(.+?)\*', r'<span class="ita">\1</span>'),
            (r'`(.+?)`', r' <code>\1</code> '),
            (r'$(.+?)$', r'\1')
             ]
        self.filters = list(map(lambda pair:
                                (re.compile(pair[0]), pair[1]), self.filters))

    def _render(self, block):
        rfunc = getattr(
            self,
            "render_" +
            block.type,
            self.rdefault)
        data = rfunc(block)
        return data

    def render(self, blocks):
        res = []
        for block in blocks:
            res.append(self._render(block))
        return ''.join(res)

    def rdefault(self, block):
        return ''

    def render_text(self, block):
        return block.text
    def render_headline(self, block):
        if hasattr(block, 'anchor'):
            return f'<h{block.hcnt}><a name="{block.anchor}">{self.filter(block.text)}</a></h{block.hcnt}>'
        else:
            return f"<h{block.hcnt}>{self.filter(block.text)}</h{block.hcnt}>"

    def render_hline(self, block):
        return "<hr />"

    def render_code(self, block):
        return f'<pre><code class="hljs {block.lang}">{block.text}</code></pre>'

    def render_paragraph(self, block):
        return f"<p>{self.filter(block.text)}</p>"

    def render_quote(self, block):
        text = '</p><p>'.join(block.elements)
        return f"<blockquote><p>{self.filter(text)}</p></blockquote>"

    def render_olist(self, block):
        texts = []
        for ele in block.elements:
            if isinstance(ele, Block):
                texts.append(self._render(ele))
            else:
                texts.append(ele)
        return "<ol>" + ''.join(texts) + "</ol>"

    def render_ulist(self, block):
        texts = []
        for ele in block.elements:
            if isinstance(ele, Block):
                texts.append(self._render(ele))
            else:
                texts.append(ele)
        return "<ul>" + ''.join(texts) + "</ul>"

    def render_listitem(self, block):
        texts = []
        for ele in block.elements:
            if isinstance(ele, Block):
                texts.append(self._render(ele))
            else:
                texts.append(ele)
        return "<li>" + ''.join(texts) + "</li>"

    def filter(self, data):
        for pat, repl in self.filters:
            data = pat.sub(repl, data)
        return data

class ContentsParser:
    def __init__(self):
        pass
    def parse(self, ast):
        cnt = 1
        s = []
        roots = []
        peeks = roots
        last = None
        for e in ast:
            if e.type == 'headline':
                e.anchor = cnt
                e = Block(tp='headline', text=e.text, hcnt=e.hcnt)
                e.anchor = cnt
                e.children = []
                cnt += 1
                if last is None:
                    peeks.append(e)
                else:
                    if last.hcnt == e.hcnt:
                        peeks.append(e)
                    elif last.hcnt < e.hcnt:
                        s.append(last)
                        last.children.append(e)
                        peeks = last.children
                    else:
                        while s and s[-1].hcnt >= e.hcnt:
                            s.pop()
                        if not s:
                            peeks = roots
                        else:
                            peeks = s[-1].children
                        peeks.append(e)
                last = e
        return roots
class ContentsRenderer:
    def __init__(self):
        pass
    def render(self, roots):
        s = ['<ul>']
        for root in roots:
            s.extend([f'<li><a href="#{root.anchor}">', root.text, '</a>'])
            if root.children:
                s.append(self.render(root.children))
            s.append('</li>')
        s.append('</ul>')
        return ''.join(s)
if __name__ == '__main__':
    parser = Parser()
    with open("md_parse/tmp.md", "r") as f:
        src = f.read()
    res = parser.parse(src)
    cparser = ContentsParser()
    cs = cparser.parse(res)
    print(cs)
    print(ContentsRenderer().render(cs))
    renderer = HtmlRenderer()
    res2 = renderer.render(res)
    with open("tmp.html", 'w') as f:
        f.write(res2)
