#!/usr/bin/python

class Tag(object):
    def __init__(self, name):
        self.name = name
        self.keys = {}
        self.tags = []
    def __str__(self):
        parts = []
        parts.append('[{0}]'.format(self.name))
        for key in sorted(self.keys.keys()):
            parts.append('{0}="{1}"'.format(str(key), str(self.keys[key]).replace('"', '""')))
        for tag in self.tags:
            parts.append(str(tag))
        parts.append('[/{0}]'.format(self.name))
        return '\n'.join(parts)
    def __repr__(self):
        return "[{0}]".format(self.name)
class RootTag(Tag):
    def __init__(self):
        Tag.__init__(self, "ROOT")
    def __str__(self):
        parts = []
        for key in sorted(self.keys.keys()):
            parts.append('{0}="{1}"'.format(str(key), str(self.keys[key]).replace('"', '""')))
        for tag in self.tags:
            parts.append(str(tag))
        return '\n'.join(parts)

class SimpleWML(object):
    def parse(self, wmlstring):
        root = RootTag()
        self.wmlstring = wmlstring
        self.pos = 0
        self.parse_internal(root)
        if self.pos < len(self.wmlstring):
            raise Exception("Only parsed {0} out of {1} characters".format(self.pos, len(self.wmlstring)))
        return root

    def has_next(self):
        return self.pos < len(self.wmlstring)
    def peek_char(self):
        return self.wmlstring[self.pos]
    def next_char(self):
        c = self.wmlstring[self.pos]
        self.pos += 1
        return c
    def next_until(self, endchar):
        newpos = self.wmlstring.find(endchar, self.pos)
        val = self.wmlstring[self.pos:newpos]
        self.pos = newpos + 1
        return val
    def next_tag(self):
        return self.next_until(']')
    def next_key(self):
        return self.next_until('=')
    def next_value(self):
        buf = ""
        append_another = True
        while append_another:
            append_another = False
            c = self.next_char()
            if c == '_':
                # We might skip something other than spaces, but that is what the server's simplewml does too
                while c != '"':
                    c = self.next_char()
            if c == '"':
                endchar = '"'
            else:
                buf += c
                endchar = '\n'
            buf += self.next_until(endchar)
            if endchar == '\n':
                return buf
            if self.has_next() and self.peek_char() == '"':
                buf += '"'
                append_another = True
            elif self.has_next():
                c = self.next_char()
                while True:
                    if c == '\n':
                        break
                    elif c == ' ':
                        c = self.next_char()
                    elif c == '+':
                        c = self.next_char()
                        if c != '\n':
                            raise Exception("No newline after concatenation operator\nString so far:\n{0}\nEntire tag:\n{1}".format(buf, self.wmlstring))
                        #if should be enough, but some idiot might switch the textdomain twice
                        while self.peek_char() == '#':
                            line = self.next_until('\n')
                            if not line.startswith("#textdomain "):
                                raise Exception("Unknown comment-line: {0}".format(line))
                        while self.peek_char().isspace():
                            self.next_char()
                        append_another = True
                        break
                    else:
                        raise Exception("No newline after end of attribute\nString so far:\n{0}\nEntire tag:\n{1}".format(buf, self.wmlstring))
        return buf
    def parse_internal(self, tag):
        while True:
            try:
                c = self.next_char()
            except IndexError:
                # We don't actually bother to check if tags are still open
                break
            if c.isspace():
                continue
            if c == '[':
                tagname = self.next_tag()
                if tagname[0] == '/':
                    if tagname[1:] != tag.name:
                        raise Exception("ERROR: incorrect closing tag [{0}] for [{1}]\nEntire tag:\n{2}".format(tagname, tag.name, self.wmlstring))
                    break
                else:
                    newtag = Tag(tagname)
                    tag.tags.append(newtag)
                    self.parse_internal(newtag)
            elif c == '#':
                line = self.next_until('\n')
                if not line.startswith("textdomain "):
                    raise Exception("Unknown comment-line: #{0}".format(line))
                # We completely ignore textdomains, just like wesnothd
            else:
                name = c + self.next_key()
                value = self.next_value()
                tag.keys[name] = value

