class Any(object):
    def __init__(self, predicate=None):
        self.predicate = predicate
    def __eq__(self, other):
        return not self.predicate or self.predicate(other)