from io import BytesIO
import struct
import datetime, time
from collections import OrderedDict
from weakref import WeakKeyDictionary as weakdict

class Undefined(object):
    __slots__ = ()

    def __new__(cls):
        return undefined

    def __eq__(self, other):
        return self is other

    def __neq__(self, other):
        return self is not other

undefined = object().__new__(Undefined)

class Loader(object):

    def add_alias(self, alias, constructor):
        raise NotImplementedError()

    def load(self, stream, proto=0, context=None):
        # please keep it reentrant
        if context is None:
            context = ReadContext()
        if proto == 0:
            return self._read_item0(stream, context)
        elif proto == 3:
            return self._read_item3(stream, context)
        else:
            raise ValueError(proto)

    def loads(self, value, proto=0):
        return self.load(BytesIO(value), proto)

    def load_all(self, stream, proto=0):
        context = Context()
        try:
            while True:
                yield self.load(stream, proto, context)
        except EOFError:
            return

    def loads_all(self, value, proto=0):
        return self.load_all(BytesIO(value), proto)

    def _read_item3(self, stream, context):
        marker = stream.read(1)[0]
        if marker ==    0x00:
            return undefined
        elif marker ==  0x01:
            return None
        elif marker ==  0x02:
            return False
        elif marker ==  0x03:
            return True
        elif marker ==  0x04:
            return self._read_vli(stream)
        elif marker ==  0x05:
            return struct.unpack('!d', stream.read(8))[0]
        elif marker ==  0x06:
            return self._read_string3(stream, context)
        elif marker ==  0x07:
            raise NotImplementedError("XML Document")
        elif marker ==  0x08:
            num = self._read_vli(stream)
            if num & 1:
                res = datetime.datetime.utcfromtimestamp(
                    struct.unpack('!d', stream.read(8))[0]/1000)
                context.add_object(res)
            else:
                res = context.get_object(num >> 1)
            return res
        elif marker ==  0x09:
            num = self._read_vli(stream)
            if num & 1:
                res = None
                while True:
                    val = self._read_string3(stream, context)
                    if val == '':
                        if res is None:
                            res = [None]*(num >> 1)
                            context.add_object(res)
                        break
                    elif res is None:
                        res = OrderedDict()
                        context.add_object(res)
                    res[val] = self._read_item3(stream, context)
                for i in range(num >> 1):
                    res[i] = self._read_item3(stream, context)
            else:
                res = context.get_object(num >> 1)
            return res
        elif marker ==  0x0A:
            num = self._read_vli(stream)
            if num & 1:
                if num & 2:
                    if num & 4: # traits-ext
                        trait = Trait()
                        raise NotImplementedError('Traits ext')
                    else: # traits
                        dyn = bool(num & 8)
                        memb = num >> 4
                        trait = Trait(dyn,
                            self._read_string3(stream, context),
                            (self._read_string3(stream, context)
                                for i in range(memb)))
                else: # traits-ref
                    trait = context.get_trait(num >> 2)
                context.add_object(trait)
            else:
                context.get_object(num)
            if trait.members:
                raise NotImplementedError("Trait members")
            if not trait.dynamic:
                raise NotImplementedError("Dynamic trait")
            res = {}
            while True:
                key = self._read_string3(stream, context)
                if key == "":
                    break
                value = self._read_item3(stream, context)
                res[key] = value
            return res
        elif marker ==  0x0B:
            # xml
            raise NotImplementedError()
        elif marker ==  0x0C:
            num = self._read_vli(stream)
            if num & 1:
                res = stream.read(num >> 1)
                context.add_object(res)
            else:
                res = context.get_object(num >> 1)
            return res
        else:
            raise NotImplementedError("Marker 0x{:02x}".format(marker))

    def _read_vli(self, stream):
        val = 0
        while True:
            byte = stream.read(1)[0]
            val = (val << 7) | (byte & 0x7f)
            if not (byte & 0x80):
                break
        return val

    def _read_string3(self, stream, context):
        num = self._read_vli(stream)
        if num & 1:
            num >>= 1
            if num:
                res = stream.read(num).decode('utf-8')
                context.add_string(res)
                return res
            else:
                return ''
        else:
            num >>= 1
            return context.get_string(num)

    def _read_string0(self, stream):
        len = struct.unpack('!H', stream.read(2))[0]
        return stream.read(len).decode('utf-8')

    def _read_item0(self, stream, context):
        marker = stream.read(1)
        if marker:
            marker = marker[0]
        else:
            raise EOFError()
        if marker ==   0x00:
            return struct.unpack('!d', stream.read(8))[0]
        elif marker == 0x01:
            return bool(stream.read(1)[0])
        elif marker == 0x02:
            return self._read_string0(stream)
        elif marker == 0x03:
            res = {}
            context.add_complex(res)
            while True:
                key = self._read_string0(stream)
                if key == '':
                    break
                res[key] = self._read_item0(stream, context)
            end = stream.read(1)[0]
            assert end == 0x09
            return res
        elif marker == 0x05: # null
            return None
        elif marker == 0x06: # undefined
            return undefined
        elif marker == 0x07: # ref
            idx = struct.unpack('!H', stream.read(2))[0]
            return context.get_complex(idx)
        elif marker == 0x08: # assoc arr
            cnt = struct.unpack('!L', stream.read(4))[0]
            res = {}
            context.add_complex(res)
            for i in range(cnt):
                key = self._read_string0(stream)
                res[key] = self._read_item0(stream, context)
            context.add_complex(res)
            return res
        elif marker == 0x0A: # strict array
            cnt = struct.unpack('!L', stream.read(4))[0]
            res = []
            context.add_complex(res)
            for i in range(cnt):
                res.append(self._read_item0(stream, context))
            return res
        elif marker == 0x0B: # date
            val = struct.unpack('!d', stream.read(8))[0]
            res = datetime.datetime.utcfromtimestamp(val/1000)
            tz = stream.read(2)
            assert tz == b'\x00\x00'
            return res
        elif marker == 0x0C: # longstring
            len = struct.unpack('!L', stream.read(4))[0]
            return stream.read(len).decode('utf-8')
        elif marker == 0x11: # AVM+
            return self._read_item3(stream, context)
        else:
            raise NotImplementedError("Marker {:02x}".format(marker))


class Trait(object):
    __slots__ = ('dynamic', 'classname', 'members')

    def __init__(self, dynamic, classname, members=()):
        self.dynamic = dynamic
        self.members = tuple(members)
        self.classname = classname

anonymous_trait = Trait(True, "")

class Dumper(object):

    def dump(self, data, stream=None, proto=None, context=None):
        # please keep it reentrant
        if context is None:
            context = WriteContext()
        if proto == 0:
            return self._write_item0(data, stream, context)
        elif proto == 3:
            return self._write_item3(data, stream, context)
        else:
            raise ValueError(proto)

    def _write_item0(self, data, stream, context):
        if isinstance(data, bool):
            stream.write(b'\x01\x01' if data else b'\x01\x00')
        elif isinstance(data, (float, int)):
            stream.write(b'\x00' + struct.pack('!d', data))
        elif isinstance(data, str):
            if len(data) < 65536:
                stream.write(b'\x02')
                self._write_string0(data, stream, context)
            else:
                data = data.encode('utf-8')
                stream.write(b'\x0c' + struct.pack('!L', len(data)))
                stream.write(data)
        elif isinstance(data, dict):
            ref = context.get_complex(data)
            if ref is not None:
                stream.write(b'\x07' + struct.pack('!H', ref))
            else:
                context.add_complex(data)
                stream.write(b'\x03')
                for k, v in data.items():
                    self._write_string0(k, stream, context)
                    self._write_item0(v, stream, context)
                self._write_string0("", stream, context)
                stream.write(b'\x09')
        elif data is None: # null
            stream.write(b'\x05')
        elif data is undefined: # undefined
            stream.write(b'\x06')
        elif isinstance(data, (list, tuple)): # strict array
            ref = context.get_complex(data)
            if ref is not None:
                stream.write(b'\x07' + struct.pack('!H', ref))
            else:
                context.add_complex(data)
                stream.write(b'\x0A' + struct.pack('!L', len(data)))
                for i in data:
                    self._write_item0(i, stream, context)
        elif isinstance(data, datetime.datetime):
            stream.write(b'\x0b' + struct.pack('!d',
                time.mktime(data.utctimetuple())*1000) + b'\x00\x00')
        else:
            raise NotImplementedError("Type {!r}".format(type(data)))

    def _write_string0(self, data, stream, context):
        data = data.encode('utf-8')
        stream.write(struct.pack('!H', len(data)))
        stream.write(data)


    def _write_item3(self, data, stream, context):
        if data is undefined:
            stream.write(b'\x00')
        elif data is None:
            stream.write(b'\x01')
        elif data is False:
            stream.write(b'\x02')
        elif data is True:
            stream.write(b'\x03')
        elif isinstance(data, int) and data >= 0 and data < (1 << 31):
            stream.write(b'\x04')
            self._write_vli(data, stream)
        elif isinstance(data, (int, float)):
            stream.write(b'\x05' + struct.pack('!d', data))
        elif isinstance(data, str):
            stream.write(b'\x06')
            self._write_string3(data, stream, context)
        elif isinstance(data, datetime.datetime):
            stream.write(b'\x08')
            ref = context.get_object(data)
            if ref is not None:
                self._write_vli((ref << 1), stream)
            else:
                self._write_vli(1, stream)
                stream.write(struct.pack('!d',
                    time.mktime(data.utctimetuple())*1000))
                context.add_object(data)
        elif isinstance(data, dict):
            stream.write(b'\x0A')
            ref = context.get_object(data)
            if ref is not None:
                self._write_vli((ref << 1), stream)
            else:
                ref = context.get_trait(anonymous_trait)
                if ref is not None:
                    self._write_vli((ref << 2), stream)
                else:
                    context.add_trait(anonymous_trait)
                    self._write_vli(11, stream)
                    self._write_string3(anonymous_trait.classname, stream, context)
                for k, v in data.items():
                    self._write_string3(k, stream, context)
                    self._write_item3(v, stream, context)
                self._write_string3("", stream, context)
        elif isinstance(data, list):
            stream.write(b'\x09')
            ref = context.get_object(data)
            if ref is not None:
                self._write_vli((ref << 1), stream)
            else:
                context.add_object(data)
                self._write_vli((len(data) << 1)|1, stream)
                self._write_string3("", stream, context)
                for i in data:
                    self._write_item3(i, stream, context)
        else:
            raise NotImplementedError("Type {!r}".format(type(data)))

    def _write_vli(self, data, stream):
        ba = bytearray()
        if not data:
            stream.write(b'\x00')
            return
        while data:
            ba.append((data & 0x7f) | 0x80)
            data >>= 7
        ba.reverse()
        ba[-1] &= 0x7f
        stream.write(ba)

    def _write_string3(self, data, stream, context):
        ref = context.get_string(data)
        if data and ref is not None:
            self._write_vli(ref << 1, stream)
        else:
            if data:
                context.add_string(data)
            data = data.encode('utf-8')
            self._write_vli((len(data) << 1)|1, stream)
            stream.write(data)

class ReadContext(object):
    def __init__(self):
        self.strings = []
        self.objects = []
        self.traits = []
        self.complex = []

    def add_string(self, val):
        self.strings.append(val)

    def get_string(self, key):
        return self.strings[key]

    def add_object(self, val):
        self.objects.append(val)

    def get_object(self, key):
        return self.objects[key]

    def add_trait(self, val):
        self.traits.append(val)

    def get_trait(self, key):
        return self.traits[key]

    def add_complex(self, val):
        self.complex.append(val)

    def get_complex(self, key):
        return self.complex[key]

class WriteContext(object):
    def __init__(self):
        self.strings = {}
        self.nstrings = 0
        self.objects = {}
        self.nobjects = 0
        self.traits = {}
        self.ntraits = 0
        self.complex = {}
        self.ncomplex = 0

    def add_string(self, val):
        self.strings[val] = self.nstrings
        self.nstrings += 1

    def get_string(self, key):
        return self.strings.get(key, None)

    def add_object(self, val):
        self.objects[id(val)] = self.nobjects
        self.nobjects += 1

    def get_object(self, key):
        return self.objects.get(id(key), None)

    def add_trait(self, val):
        self.traits[val] = self.ntraits
        self.ntraits += 1

    def get_trait(self, key):
        return self.traits.get(key, None)

    def add_complex(self, val):
        self.complex[id(val)] = self.ncomplex
        self.ncomplex += 1

    def get_complex(self, key):
        return self.complex.get(id(key), None)
