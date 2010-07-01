from io import BytesIO

from .core import Dumper, Loader, undefined

def dump(data, stream, proto=3, Dumper=Dumper):
    Dumper().dump(data, stream, proto=proto)

def load(input, proto=3, Loader=Loader):
    return Loader().load(input, proto=proto)

def dumps(data, proto=3, Dumper=Dumper):
    buf = BytesIO()
    dump(data, buf, proto=proto, Dumper=Dumper)
    return buf.getvalue()

def loads(data, proto=3, Loader=Loader):
    buf = BytesIO(data)
    return load(buf, proto=proto, Loader=Loader)
