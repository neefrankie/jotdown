import unittest

from jotdown.attribute import (
    Attributes,
    ClassAttribute,
    IdAttribute,
    PairAttribute,
    CommentAttribute,
    AttributeParser,
)

class TestAttributes(unittest.TestCase):
    def test_attributes(self):
        attrs = Attributes()
        elements = [
            ClassAttribute("foo"),
            ClassAttribute("bar"),
            IdAttribute("baz"),
            PairAttribute("src", "https://placehold.co/600x400")
        ]
        for elem in elements:
            attrs.push(elem)

        for i, elem in enumerate(attrs):
            self.assertEqual(elem, elements[i])

        keys = [
            'src',
            'class',
            'id'
        ]
        for key in keys:
            self.assertTrue(attrs.contains_key(key))

        key_values = [
            ('class', 'foo bar'),
            ('id', 'baz'),
            ('src', 'https://placehold.co/600x400')
        ]
        for (key, value) in key_values:
            self.assertEqual(attrs.get_value(key), value)
        
        pairs = attrs.unique_pairs()
        for (key, value) in key_values:
            self.assertEqual(pairs[key], value)

        self.assertEqual(attrs.raw_text(), '{.foo .bar #baz src="https://placehold.co/600x400"}')

    def test_read_identifier(self):
        cases = [
            ('id', 'id'),
            ('foo bar', 'foo'),
            ('data-name', 'data-name')
        ]
        for (src, expected) in cases:
            parser = AttributeParser(src)
            actual = parser._read_identifier()
            self.assertEqual(actual, expected)

    def test_read_quoted_string(self):
        cases = [
            ('"my value"', 'my value'),
            ('"foo\\"bar"', 'foo\\"bar'),
            ('"foo\\\\" bar', 'foo\\\\')
        ]
        for (src, expected) in cases:
            p = AttributeParser(src)
            actual = p._read_quoted_string()
            self.assertEqual(actual, expected)

    def test_read_comment(self):
        cases = [
            ("% later we'll add a class %", " later we'll add a class "),
            ("% This is a comment, spanning\nmultiple lines %", " This is a comment, spanning\nmultiple lines "),
            ("% This comment ends at righ brace }", " This comment ends at righ brace ")
        ]
        for (src, expected) in cases:
            p = AttributeParser(src)
            actual = p._read_comment()
            self.assertEqual(actual, expected)

    def test_skip_whitespace(self):
        cases = [
            ('  foo', 2),
            (' \n foo', 3),
            ('\t \nfoo', 3),
        ]
        for (src, expected) in cases:
            p = AttributeParser(src)
            p._skip_whitespace()
            self.assertEqual(p.pos, expected)

    def test_parse_class(self):
        cases = [
            ('.class1', {'class': ['class1']}),
            ('.class2 .class1', {'class': ['class2']})
        ]
        for (text, expected) in cases:
            p = AttributeParser(text)
            p._parse_class()

            for key, expected_values in expected.items():
                actual_values = p.attrs.get_values(key)
                self.assertEqual(
                    actual_values, 
                    expected_values,
                    f"{text}: key='{key}' expected {expected_values}, got {actual_values}"
                )

    def test_parse_id(self):
        cases = [
            ('#foo', {'id': ['foo']}),
        ]
        for (text, expected) in cases:
            p = AttributeParser(text)
            p._parse_id()

            for key, expected_values in expected.items():
                actual_values = p.attrs.get_values(key)
                self.assertEqual(
                    actual_values, 
                    expected_values,
                    f"{text}: key='{key}' expected {expected_values}, got {actual_values}"
                )

    def test_parse_comment(self):
        cases = [
            ('% This is comment %', [' This is comment ']),
        ]
        for (text, expected) in cases:
            p = AttributeParser(text)
            p._parse_comment()

            actual = [
                elem.value() 
                for elem in p.attrs 
                if isinstance(elem, CommentAttribute)
            ]

            self.assertEqual(actual, expected)
                

        
        


if __name__ == '__main__':
    unittest.main()