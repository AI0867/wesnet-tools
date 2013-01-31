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
            parts.append('{0}="{1}"'.format(str(key), str(self.keys[key])))
        for tag in self.tags:
            parts.append(str(tag))
        parts.append('[/{0}]'.format(self.name))
        return '\n'.join(parts)
class RootTag(Tag):
    def __init__(self):
        Tag.__init__(self, "ROOT")
    def __str__(self):
        parts = []
        for key in sorted(self.keys.keys()):
            parts.append('{0}="{1}"'.format(str(key), str(self.keys[key])))
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
            print "Only parsed {0} out of {1} characters".format(self.pos, len(self.wmlstring))
        return root

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
        c = self.next_char()
        if c == '"':
            endchar = '"'
        else:
            buf += c
            endchar = '\n'
        buf += self.next_until(endchar)
        return buf
    def parse_internal(self, tag):
        while True:
            try:
                c = self.next_char()
            except IndexError:
                break
            if c.isspace():
                continue
            if c == '[':
                tagname = self.next_tag()
                if tagname[0] == '/':
                    if tagname[1:] != tag.name:
                        print "ERROR: incorrect closing tag [{0}] for [{1}]".format(tagname, tag.name)
                    break
                else:
                    newtag = Tag(tagname)
                    tag.tags.append(newtag)
                    self.parse_internal(newtag)
            else:
                name = c + self.next_key()
                value = self.next_value()
                tag.keys[name] = value

