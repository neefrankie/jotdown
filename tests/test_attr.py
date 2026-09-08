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

class TestAttrbuteParser(unittest.TestCase):
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
            ('.class1', 'class1'),
            ('.class2 .class1', 'class2')
        ]
        for (text, expected) in cases:
            p = AttributeParser(text)
            actual = p._parse_class()

            self.assertEqual(actual.value(), expected)

    def test_parse_id(self):
        cases = [
            ('#foo', 'foo'),
        ]
        for (text, expected) in cases:
            p = AttributeParser(text)
            actual = p._parse_id()

            self.assertEqual(actual.value(), expected)

    def test_parse_comment(self):
        cases = [
            ('% This is comment %', ' This is comment '),
        ]
        for (text, expected) in cases:
            p = AttributeParser(text)
            actual = p._parse_comment()

            self.assertEqual(actual.value(), expected)

    def test_parse_pair(self):
        cases = [
            ('key="value"', 'value'),
            ('key="foo\\"bar"', 'foo\\"bar')
        ]
        for (text, expected) in cases:
            with self.subTest(text):
                p = AttributeParser(text)
                actual = p._parse_pair()
                self.assertEqual(actual.value(), expected)

    def test_parse_one_block(self):
        cases = [
            ('{.class1 .class2 #id}', ['class1', 'class2', 'id']),
            ('{key=value}', ['value']),
            ('{key="value"}', ['value']),
            ('{key="foo\\"bar"}', ['foo\\"bar']),
            ('{#id % comment %}', ['id', ' comment '])
        ]
        for (text, expected) in cases:
            with self.subTest(text):
                p = AttributeParser(text)
                actual = [
                    elem.value()
                    for elem in p._parse_one_block()
                ]
                self.assertEqual(actual, expected)

    def test_parse(self):
        cases = [
            ('{% multi-line %}{.class}', [' multi-line ', 'class']),
            ('{lang=fr}{.blue}', ['fr', 'blue']),
            ('{#water}\n{.important .large}', ['water', 'important', 'large']),
            ('{#foo .bar key=value % comment %}', ['foo', 'bar', 'value', ' comment '])
        ]
        for (text, expected) in cases:
            with self.subTest(text):
                p = AttributeParser(text)
                actual = [
                    elem.value()
                    for elem in p.parse()
                ]
                self.assertEqual(actual, expected)

    def test_finish(self):
        cases = [
            # 基本
            ('{.class1 .class2 #id}', {'class': ['class1', 'class2'], 'id': ['id']}),
            ('{key=value}', {'key': ['value']}),
            ('{key="value"}', {'key': ['value']}),
            ('{key="foo\\"bar"}', {'key': ['foo\\"bar']}),
            
            # 注释
            ('{#id % comment %}', {'id': ['id']}),
            ('{% multi-line %}{.class}', {'class': ['class']}),
            
            # 堆叠
            ('{lang=fr}{.blue}', {'lang': ['fr'], 'class': ['blue']}),
            
            # 多行
            ('{#water}\n{.important .large}', {'id': ['water'], 'class': ['important', 'large']}),
            
            # 混合
            ('{#foo .bar key=value % comment %}', {'id': ['foo'], 'class': ['bar'], 'key': ['value']}),
        ]
        for text, expected in cases:
            with self.subTest(text):
                p = AttributeParser(text)
                attrs = p.finish()

                for key, expected_values in expected.items():
                    actual_values = attrs.get_values(key)
                    self.assertEqual(
                        actual_values,
                        expected_values
                    )



if __name__ == '__main__':
    unittest.main()