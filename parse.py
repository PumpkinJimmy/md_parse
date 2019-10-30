import re


class Block:
    def __init__(self, elements):
        self.elements = elements

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.elements}>"


class Paragraph(Block):
    pass


class CodeBlock(Block):
    pass


class UListItem(Block):
    pass


class UList(Block):
    pass


class OListItem(Block):
    pass


class OList(Block):
    pass


class State:
    def __init__(self, parser):
        self.parser = parser
        self.elements = []

    @staticmethod
    def match(line):
        return True

    def handle(self, line):
        mstate = self.parser.find_match_state(line)
        if mstate:
            self.parser.contextEnter(mstate(self.parser))
        else:
            self.elements.append(Paragraph([line]))
            self.parser.nextLine()

    def addElement(self, element):
        self.elements.append(element)

    def create(self):
        return self.elements


class CodeState(State):

    def __init__(self, parser):
        super().__init__(parser)
        self.enter = False

    @staticmethod
    def match(line):
        return line.strip() == '```'

    def handle(self, line):
        if line.strip() == '```':
            self.parser.nextLine()
            if not self.enter:
                self.enter = True
            else:
                self.parser.contextExit(self)
        else:
            super().handle(line)

    def create(self):
        return CodeBlock(self.elements)


class UListState(State):

    @staticmethod
    def match(line):
        return line.strip().endswith(':') or line.strip().endswith('：')

    def handle(self, line):
        if line.strip().endswith(':') or line.strip().endswith('：'):
            self.elements.append(Paragraph([line]))
            self.parser.nextLine()
            return
        if not line.startswith('-'):
            self.parser.contextExit(self)
        else:
            self.elements.append(UListItem([line.lstrip('- ')]))
            self.parser.nextLine()

    def create(self):
        if len(self.elements) == 1:
            return self.elements[0]
        return UList(self.elements)


class OListState(State):

    def __init__(self, parser):
        super().__init__(parser)
        self.cnt = 1

    @staticmethod
    def match(line):
        return line.strip().startswith('1.')

    def handle(self, line):
        expect = str(self.cnt) + '.'
        if not line.startswith(expect):
            self.parser.contextExit(self)
        else:
            self.cnt += 1
            self.elements.append(OListItem([line.lstrip(expect + ' ')]))
            self.parser.nextLine()

    def create(self):
        return OList(self.elements)


class Parser:
    def __init__(self):
        self.states = [CodeState, UListState, OListState]
        self.current_state = State(self)
        self.current_lineno = 0
        self.context = [self.current_state]
        self.lines = []
        self.blocks = []

    def parse(self, src):
        self.lines = src.strip().split('\n')
        if not self.lines:
            return []
        while self.current_lineno < len(self.lines):
            self.current_state.handle(self.lines[self.current_lineno])
        while len(self.context) > 1:
            self.contextExit(self.context[-1])
        return self.current_state.create()

    def nextLine(self):
        self.current_lineno += 1

    def find_match_state(self, line):
        for state in self.states:
            if state.match(line):
                return state

    def contextEnter(self, state):
        self.context.append(state)
        self.current_state = state

    def contextExit(self, state):
        if state in self.context:
            while self.context[-1] != state:
                estate = self.context.pop()
                self.context[-1].addElement(estate.create())
            self.context.pop()
            self.context[-1].addElement(state.create())
            self.current_state = self.context[-1]


class Renderer:
    def __init__(self):
        pass

    def render(self, blocks):
        texts = []
        for block in blocks:
            texts.append(self.render_(block))
        res = ''.join(texts)
        for i in range(1, 6):
            pat = re.compile("<p>" + '#' * i + ' *?([^# ]*?)</p>')
            res = pat.sub(r'<h' + str(i) + r'>\1</h' + str(i) + '>', res)
        res = re.sub("<p>[-=]{3,}</p>", "<hr />", res)
        res = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", res)
        res = re.sub(
            r"\*(.+?)\*",
            r'<span style="font-style:italic">\1</span>',
            res)
        return res

    def render_(self, block):
        rfunc = getattr(
            self,
            "render" +
            block.__class__.__name__,
            self.rdefault)
        return rfunc(block)

    def rdefault(self, block):
        return block.elements[0]

    def renderCodeBlock(self, block):
        texts = []
        for ele in block.elements:
            if isinstance(ele, Paragraph):
                texts.append(ele.elements[0])
            else:
                texts.append(self.render_(ele))
        return "<pre>" + '\n'.join(texts) + "</pre>"

    def renderParagraph(self, block):
        return "<p>" + block.elements[0] + '</p>'

    def renderOList(self, block):
        texts = []
        for ele in block.elements:
            texts.append("<li>" + ele.elements[0] + "</li>")
        return "<ol>" + ''.join(texts) + "</ol>"

    def renderUList(self, block):
        texts = []
        for ele in block.elements[1:]:
            texts.append("<li>" + ele.elements[0] + "</li>")
        return "<p>" + block.elements[0].elements[0] + \
            "</p>" + "<ul>" + ''.join(texts) + "</ul>"


if __name__ == '__main__':
    parser = Parser()
    with open("README.md", "r") as f:
        src = f.read()
    res = parser.parse(src)
#    blocks = parser.parse(
#        "aaa\nbbb\nccc\n```\nddd\neee\nfff\n```\nggg\nhhh:\n- p1\n- p2\n- p3\
# \n1. n1\n2. n2\n3. n3"
#    )
#    print(blocks)
    renderer = Renderer()
    print(res)
    print(renderer.render(res))
