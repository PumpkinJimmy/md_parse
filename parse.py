class Block:
    def __init__(self, blines):
        self.blines = blines


class Rule:
    def __init__(self):
        pass

    def match(self):
        return True

    def createBlock(self, blines):
        return Block(blines)


class Parser:
    def __init__(self):
        self.rules = [Rule()]

    def parse(self, src):
        lines = src.strip().split('\n')
        blocks = []
        block = []
        for line in lines:
            rematch = False
            if self.current_rule is not None:
                if self.current_rule.match(line):
                    block.append(line)
                else:
                    blocks.append(self.current_rule.createBlock(block))
                    self.current_rule = None
                    block = []
                    rematch = True
            else:
                rematch = True
            if rematch:
                for rule in self.rules:
                    if rule.match(line):
                        if rule.is_multi:
                            self.current_rule = rule
                        else:
                            blocks.append(rule.createBlock([line]))


class Renderer:
    def __init__(self):
        pass

    def render(self, tobjs):
        pass
