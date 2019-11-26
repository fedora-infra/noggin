class Representation(object):
    def __init__(self, raw):
        self.raw = raw

    def _attr(self, attr):
        if attr in self.raw and len(self.raw[attr]) > 0:
            return self.raw[attr][0]
        return None

    def _attrlist(self, attr):
        if attr in self.raw:
            return self.raw[attr]
        return []
