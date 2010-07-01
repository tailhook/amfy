from io import BytesIO

from .core import Dumper, Loader, undefined

def dump(data, stream=None, proto=3, Dumper=Dumper):
    if stream is None:
        stream = BytesIO()
    Dumper().dump(data, stream, proto=proto)
    return stream.getvalue()

def load(input, proto=3, Loader=Loader):
    if not hasattr(input, 'read'):
        input = BytesIO(input)
    return Loader().load(input, proto=proto)
