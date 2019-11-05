import re


class Block:

    def __init__(self, tp, apply_filter=True, **kwargs):
        self.type = tp
        self.apply_filter = apply_filter
        self.kwargs = kwargs

    def __repr__(self):
        return f"<{self.type}: {self.kwargs}>"

    def __getattr__(self, name):
        if name in self.kwargs:
            return self.kwargs[name]
        super().__getattr__(name)


class Context:
    # filters = [HeadlineFilter, EmphasisFilter, ItalicFilter,
    #           ImageFilter, HrefFilter]
    def __init__(self, parser):
        self.parser = parser
        self.elements = []
        self.init()
        # self.filters = Context.filters[:]

    def init(self):
        pass

    @staticmethod
    def match(line):
        return True

    def handle(self, line):
        pass

    def create():
        return Block("null")


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


class CodeContext(Context):
    def init(self):
        self.inside = False
        self.lang = ''

    @staticmethod
    def match(line):
        return line.strip().startswith("```")

    def handle(self, line):
        line = line.strip()
        if line.startswith('```'):
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


class UListContext(Context):
    @staticmethod
    def match(line):
        return line.startswith('-')

    def handle(self, line):
        if not line.startswith('-'):
            self.parser.contextExit()
        else:
            self.elements.append(line.strip('- '))
            self.parser.nextLine()

    def create(self):
        return Block("ulist", elements=self.elements)


class OListContext(Context):
    def init(self):
        self.cnt = 1

    @staticmethod
    def match(line):
        return line.startswith('1.')

    def handle(self, line):
        expect = str(self.cnt) + '.'
        if not line.startswith(expect):
            self.contextExit()
        else:
            self.elements.append(line.lstrip(expect + ' '))
            self.cnt += 1
            self.parser.nextLine()

    def create(self):
        return Block("olist", elements=self.elements)


class QuoteContext(Context):
    @staticmethod
    def match(line):
        return line.startswith('>')

    def handle(self, line):
        if not line.startswith('>'):
            self.parser.contextExit()
        else:
            self.elements.append('>')
            self.parser.nextLine()

    def create(self):
        return Block("quote", text='\n'.join(self.elements))


class TableContext(Context):
    @staticmethod
    def match(line): return False


class MathContext(Context):
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

    def __init__(self, ccontext=None, contexts=None, filters=None):
        if contexts is None:
            contexts = Parser.contexts[:]
        self.contexts = contexts
        self.ccontext = ccontext
        self.lineno = 0
        self.blocks = []

    def parse(self, src):
        self.lineno = 0
        self.lines = src.rstrip().split('\n')
        while self.lineno < len(self.lines):
            line = self.lines[self.lineno]
            if self.ccontext is None:
                self.handle(line.rstrip())
            else:
                self.ccontext.handle(line.rstrip())
        if self.ccontext:
            self.contextExit()
        return self.blocks

    def nextLine(self):
        self.lineno += 1

    def handle(self, line):
        for context in self.contexts:
            if context.match(line):
                self.ccontext = context(self)
                return
        self.blocks.append(Block("paragraph", text=line))
        self.nextLine()

    def contextExit(self):
        if not self.ccontext:
            return
        self.blocks.append(self.ccontext.create())
        self.ccontext = None


class HtmlRenderer:
    def __init__(self):
        self.filters = [
            (r'\<((http://)?(.+?)/)\>', r'<a href="\1">\1</a>'),
            (r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>'),
            (r'\*\*(.+?)\*\*', r'<span class="em">\1</span>'),
            (r'\*(.+?)\*', r'<span class="ita">\1</span>'),
            (r'!\[alt (.+?)]\((.+?)\)', r'<img alt="\1" src="\2" />')
             ]
        self.filters = list(map(lambda pair:
                                (re.compile(pair[0]), pair[1]), self.filters))
    def render(self, blocks):
        res = []
        for block in blocks:
            rfunc = getattr(
                self,
                "render_" +
                block.type,
                self.rdefault)
            data = rfunc(block)
            res.append(data)
        return ''.join(res)

    def rdefault(self, block):
        return ''

    def render_headline(self, block):
        return f"<h{block.hcnt}>{self.filter(block.text)}</h{block.hcnt}>"

    def render_hline(self, block):
        return "<hr />"

    def render_code(self, block):
        return f'<pre><code class="hljs {block.lang}">{block.text}</code></pre>'

    def render_paragraph(self, block):
        return f"<p>{self.filter(block.text)}</p>"

    def render_olist(self, block):
        texts = []
        for ele in block.elements:
            texts.append("<li>" + ele + "</li>")
        return "<ol>" + self.filter(''.join(texts)) + "</ol>"


    def render_ulist(self, block):
        texts = []
        for ele in block.elements:
            texts.append("<li>" + ele + "</li>")
        return "<ul>" + self.filter(''.join(texts)) + "</ul>"

    def filter(self, data):
        for pat, repl in self.filters:
            data = pat.sub(repl, data)
        return data


if __name__ == '__main__':
    parser = Parser()
    with open("README2.md", "r") as f:
        src = f.read()
    res = parser.parse(src)
#    blocks = parser.parse(
#        "aaa\nbbb\nccc\n```\nddd\neee\nfff\n```\nggg\nhhh:\n- p1\n- p2\n- p3\
# \n1. n1\n2. n2\n3. n3"
#    )
#    print(blocks)
    renderer = HtmlRenderer()
#    print(res)
    res2 = renderer.render(res)
#    print(res2)
    with open("tmp.html", 'w') as f:
        f.write(res2)
