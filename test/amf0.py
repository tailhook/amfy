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
    Tests the output from the AMF0 L{Encoder<pyamf.amf0.Encoder>} class.
    """

    def _run(self, data):
        for val in data:
            self.assertEquals(amfy.load(val[1], proto=0), val[2] if len(val) > 2 else val[0])
            self.assertEquals(amfy.dump(val[0], proto=0), val[1])

    def test_number(self):
        data = [
            (0,    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
            (0.2,  b'\x00\x3f\xc9\x99\x99\x99\x99\x99\x9a'),
            (1,    b'\x00\x3f\xf0\x00\x00\x00\x00\x00\x00'),
            (42,   b'\x00\x40\x45\x00\x00\x00\x00\x00\x00'),
            (-123, b'\x00\xc0\x5e\xc0\x00\x00\x00\x00\x00'),
            (1.23456789, b'\x00\x3f\xf3\xc0\xca\x42\x83\xde\x1b')]

        # XXX nick: Should we be testing python longs here?

        self._run(data)

    def test_boolean(self):
        data = [
            (True, b'\x01\x01'),
            (False, b'\x01\x00')]

        self._run(data)

    def test_string(self):
        data = [
            ('', b'\x02\x00\x00'),
            ('hello', b'\x02\x00\x05hello'),
            # unicode taken from http://www.columbia.edu/kermit/utf8.html
            ('ᚠᛇᚻ', b'\x02\x00\t\xe1\x9a\xa0\xe1\x9b\x87\xe1\x9a\xbb')]

        self._run(data)

    def test_null(self):
        self._run([(None, b'\x05')])

    def test_undefined(self):
        self._run([(amfy.undefined, b'\x06')])

    def test_list(self):
        data = [
            ([], b'\x0a\x00\x00\x00\x00'),
            ([1, 2, 3], b'\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00\x00\x00\x00\x00'
                b'\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x40\x08\x00\x00'
                b'\x00\x00\x00\x00'),
            ((1, 2, 3), b'\x0a\x00\x00\x00\x03\x00\x3f\xf0\x00\x00\x00\x00\x00'
                b'\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x40\x08\x00\x00'
                b'\x00\x00\x00\x00', [1.0, 2.0, 3.0])]

        self._run(data)

    def test_longstring(self):
        self._run([('a' * 65537, b'\x0c\x00\x01\x00\x01' + b'a' * 65537)])

    def test_dict(self):
        self._run([
            ({'a': 'a'}, b'\x03\x00\x01a\x02\x00\x01a\x00\x00\t')])

    def test_date(self):
        self._run([
            (datetime.datetime(2005, 3, 18, 1, 58, 31),
                b'\x0bBp+6!\x15\x80\x00\x00\x00'),
            (datetime.date(2003, 12, 1),
                b'\x0bBo%\xe2\xb2\x80\x00\x00\x00\x00'),
            (datetime.datetime(2009, 3, 8, 23, 30, 47, 770122),
                b'\x0bBq\xfe\x86\xca5\xa1\xf4\x00\x00')])

        try:
            self._run([(datetime.time(22, 3), '')])
        except pyamf.EncodeError as e:
            self.assertEquals(str(e), 'A datetime.time instance was found but '
                'AMF0 has no way to encode time objects. Please use '
                'datetime.datetime instead (got:datetime.time(22, 3))')
        else:
            self.fail('pyamf.EncodeError not raised when encoding datetime.time')

    def test_object(self):
        self._run([
            ({'a': 'b'}, b'\x03\x00\x01a\x02\x00\x01b\x00\x00\x09')])

    def test_complex_list(self):
        self._run([
            ([[1.0]], b'\x0A\x00\x00\x00\x01\x0A\x00\x00\x00\x01\x00\x3F\xF0\x00'
                b'\x00\x00\x00\x00\x00')])

        self._run([
            ([['test','test','test','test']], b'\x0A\x00\x00\x00\x01\x0A\x00\x00'
                b'\x00\x04\x02\x00\x04\x74\x65\x73\x74\x02\x00\x04\x74\x65\x73'
                b'\x74\x02\x00\x04\x74\x65\x73\x74\x02\x00\x04\x74\x65\x73\x74')
        ])

        x = {'a': 'spam', 'b': 'eggs'}
        self._run([
            ([[x, x]], b'\n\x00\x00\x00\x01\n\x00\x00\x00\x02\x03\x00\x01a\x02'
                b'\x00\x04spam\x00\x01b\x02\x00\x04eggs\x00\x00\t\x07\x00\x02')])

if __name__ == '__main__':
    unittest.main()
