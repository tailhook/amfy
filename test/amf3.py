# -*- coding: utf-8 -*-
#
# Copyright (c) 2007-2009 The PyAMF Project.
# See LICENSE.txt for details.

"""
Tests for AMF0 Implementation.

@since: 0.1.0
"""

import unittest
import datetime
import types
from io import BytesIO

import amfy

class Roundtrip(unittest.TestCase):
    """
    Tests the output from the AMF3 L{Encoder<pyamf.amf3.Encoder>} class.
    """
    def _run(self, data):
        for val in data:
            self.assertEquals(amfy.loads(val[1], proto=3),
                val[2] if len(val) > 2 else val[0])
            self.assertEquals(amfy.dumps(val[0], proto=3), val[1])

    def test_list_references(self):
        y = [0, 1, 2, 3]
        self._run([
            (y, b'\x09\x09\x01\x04\x00\x04\x01\x04\x02\x04\x03'),
            ([y,y,y], b'\x09\07\x01\x09\x09\x01\x04\x00\x04\x01\x04\x02\x04\x03\x09\x02\x09\x02'),
            ])

    def test_dict(self):
        from collections import OrderedDict
        self._run([
            ({'spam': 'eggs'}, b'\n\x0b\x01\tspam\x06\teggs\x01')])

        src = OrderedDict()
        src['a'] = 'e'
        src['b'] = 'f'
        src['c'] = 'g'
        src['d'] = 'h'
        self._run([
            (src,  b'\n\x0b\x01'
                b'\x03a\x06\x03e'
                b'\x03b\x06\x03f'
                b'\x03c\x06\x03g'
                b'\x03d\x06\x03h'
                b'\x01')
        ])

    def test_object(self):
        self._run([
            ({'a': 'spam', 'b': 5},
                b'\n\x0b\x01\x03a\x06\tspam\x03b\x04\x05\x01')])

    def test_date(self):
        import datetime

        x = datetime.datetime(2005, 3, 18, 1, 58, 31)
        self._run([(x, b'\x08\x01Bp+6!\x15\x80\x00')])


    def test_number(self):
        vals = [
            (0,        b'\x04\x00'),
            (0.2,      b'\x05\x3f\xc9\x99\x99\x99\x99\x99\x9a'),
            (1,        b'\x04\x01'),
            (127,      b'\x04\x7f'),
            (128,      b'\x04\x81\x00'),
            (0x3fff,   b'\x04\xff\x7f'),
            (0x4000,   b'\x04\x81\x80\x00'),
            (0x1FFFFF, b'\x04\xff\xff\x7f'),
            #~ (0x200000, b'\x04\x80\xc0\x80\x00'),
            #~ (0x3FFFFF, b'\x04\x80\xff\xff\xff'),
            #~ (0x400000, b'\x04\x81\x80\x80\x00'),
            #~ (-1,       b'\x04\xff\xff\xff\xff'),
            #~ (42,       b'\x04\x2a'),
            #~ (-123,     b'\x04\xff\xff\xff\x85'),
            #~ (1.23456789, b'\x05\x3f\xf3\xc0\xca\x42\x83\xde\x1b')
        ]
        self._run(vals)


if __name__ == '__main__':
    unittest.main()
