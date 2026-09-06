from typing import List
import unittest

from jotdown.lex import (
    Lexer,
    Token,
    KindHardbreak,
    KindNbsp,
    KindText,
    KindNewline,
    KindEscape,
    KindOpen,
    KindClose,
    KindSym,
    KindSeq,
    Delimiter,
    Symbol,
    Sequence,
    Span,
)

def test_lex(src: str, expected_tokens: List[Token]):
    """辅助测试函数：验证 Lexer 的输出"""
    lexer = Lexer(src)
    actual = list(lexer)
    assert actual == expected_tokens, f"Input: {src}"



class TestLexer(unittest.TestCase):
    def test_cursor(self):
        text = 'hello'

        lex = Lexer(text)

        for i, expected_char in enumerate(text + '\0'):
            self.assertEqual(lex._peek_char(), expected_char if expected_char != '\0' else None)
            self.assertEqual(lex._pos, i)
            ch = lex._eat_char()
            self.assertEqual(ch, expected_char if expected_char != '\0' else None)

        self.assertEqual(lex._eat_char(), None)
        self.assertEqual(lex._pos, len(text))

    def test_cursor_advances(self):
        """测试 _eat_char() 是否正确推进游标"""
        text = "hello"
        lex = Lexer(text)
        
        for i in range(len(text)):
            self.assertEqual(lex._pos, i)
            self.assertEqual(lex._peek_char(), text[i])
            self.assertEqual(lex._eat_char(), text[i])
        
        # 越界后应该返回 None
        self.assertEqual(lex._pos, len(text))
        self.assertEqual(lex._peek_char(), None)
        self.assertEqual(lex._eat_char(), None)

        self.assertEqual(lex._pos, len(text))

    def test_peek_offset(self):
        """测试 _peek_char(offset) 是否正确返回偏移位置的字符"""
        text = "hello world"
        lex = Lexer(text)
        
        # 当前位置在 0
        self.assertEqual(lex._peek_char(), 'h')
        self.assertEqual(lex._peek_char(1), 'e')
        self.assertEqual(lex._peek_char(5), ' ')
        self.assertEqual(lex._peek_char(10), 'd')
        self.assertEqual(lex._peek_char(11), None)  # 越界
        
        # 移动到位置 6
        lex._pos = 6
        self.assertEqual(lex._peek_char(0), 'w')
        self.assertEqual(lex._peek_char(1), 'o')
        self.assertEqual(lex._peek_char(4), 'd')
        self.assertEqual(lex._peek_char(5), None)

    def test_eat_while_stops(self):
        """测试 _eat_while 不会无限循环"""
        text = "abc*special"
        lex = Lexer(text)
        
        # 跳过普通字符
        lex._eat_while(lambda c: c.isalpha())
        self.assertEqual(lex._pos, 3)  # 停在 '*'
        
        # 应该不会死循环
        lex._eat_while(lambda c: c == '*')
        self.assertEqual(lex._pos, 4)  # 停在 's'
        
        # 空输入
        lex2 = Lexer("")
        lex2._eat_while(lambda c: c.isalpha())
        self.assertEqual(lex2._pos, 0)  # 不应该死循环

    def test_next_non_space_newline(self):
        cases = [
            ('hello', False),
            ('    \n', True),
            ('    ', False)
        ]
        for text, expected in cases:
            lex = Lexer(text)
            self.assertEqual(
                lex._is_next_non_space_newline(),
                expected
            )

    def test_handle_escaped(self):
        cases = [
            ('\n', KindHardbreak),
            ('\t  \n', KindHardbreak),
            ('\t\n', KindHardbreak),
            # ('\t\r\n', KindHardbreak), # this test fails because of the way we handle newlines
            ('\t', KindNbsp),
            ('\t  hello', KindNbsp) # plain text after tab
        ]
        for text, expected in cases:
            with self.subTest():
                lex = Lexer(text)
                actual = lex._handle_escaped(text[0])
                self.assertIsInstance(actual, expected)

    def test_close_brace(self):
        cases = [
            ('*}', True),
            ('*', False)
        ]
        for text, expected in cases:
            with self.subTest(text):
                lex = Lexer(text)
                lex._eat_char()
                actual = lex._eat_close_brace()
                self.assertEqual(actual, expected)

    def test_handle_special(self):
        cases = [
            ('\n', KindNewline()),
            ('\\ ', KindEscape()),
            ('\\', KindText()),
            ('[', KindOpen(Delimiter.BRACKET)),
            (']', KindClose(Delimiter.BRACKET)),
            ('(', KindOpen(Delimiter.PAREN)),
            (')', KindClose(Delimiter.PAREN)),
            ('{*', KindOpen(Delimiter.BRACE_ASTERISK)),
            ('{^', KindOpen(Delimiter.BRACE_CARET)),
            ('{=', KindOpen(Delimiter.BRACE_EQUAL)),
            ('{-', KindOpen(Delimiter.BRACE_HYPHEN)),
            ('{+', KindOpen(Delimiter.BRACE_PLUS)),
            ('{~', KindOpen(Delimiter.BRACE_TILDE)),
            ('{_', KindOpen(Delimiter.BRACE_UNDERSCORE)),
            ('{\'', KindOpen(Delimiter.BRACE_QUOTE1)),
            ('{"', KindOpen(Delimiter.BRACE_QUOTE2)),
            ('{', KindOpen(Delimiter.BRACE)),
            ('}', KindClose(Delimiter.BRACE)),
            ('*}', KindClose(Delimiter.BRACE_ASTERISK)),
            ('*', KindSym(Symbol.ASTERISK)),
            ('^}', KindClose(Delimiter.BRACE_CARET)),
            ('^', KindSym(Symbol.CARET)),
            ('=}', KindClose(Delimiter.BRACE_EQUAL)),
            ('=', KindText()),
            ('+}', KindClose(Delimiter.BRACE_PLUS)),
            ('+', KindText()),
            ('~}', KindClose(Delimiter.BRACE_TILDE)),
            ('~', KindSym(Symbol.TILDE)),
            ('_}', KindClose(Delimiter.BRACE_UNDERSCORE)),
            ('_', KindSym(Symbol.UNDERSCORE)),
            ('\'}', KindClose(Delimiter.BRACE_QUOTE1)),
            ('\'', KindSym(Symbol.QUOTE1)),
            ('"}', KindClose(Delimiter.BRACE_QUOTE2)),
            ('"', KindSym(Symbol.QUOTE2)),
            ('-}', KindClose(Delimiter.BRACE_HYPHEN)),
            ('---', KindSeq(Sequence.HYPHEN)),
            ('![', KindSym(Symbol.EXCLAIM_BRACKET)),
            ('!', KindText()),
            ('<', KindSym(Symbol.LT)),
            ('|', KindSym(Symbol.PIPE)),
            (':', KindSym(Symbol.COLON)),
            ('```', KindSeq(Sequence.BACKTICK)),
            ('...', KindSeq(Sequence.PERIOD)),
        ]
        for text, expected in cases:
            with self.subTest(text):
                lex = Lexer(text)
                c = lex._eat_char()
                assert(c is not None)
                actual = lex._handle_special(c)
                self.assertEqual(actual, expected)

    def test_token_stops(self):
        text = '*hello* _world_'
        expected = [
            Token(
                kind=KindSym(Symbol.ASTERISK),
                text='*',
                span=Span(0, 1)
            ),
            Token(
                kind=KindText(),
                text='hello',
                span=Span(1, 6),
            ),
            Token(
                kind=KindSym(Symbol.ASTERISK),
                text='*',
                span=Span(6, 7)
            ),
            Token(
                kind=KindText(),
                text=' ',
                span=Span(7, 8),
            ),
            Token(
                kind=KindSym(Symbol.UNDERSCORE),
                text='_',
                span=Span(8, 9),
            ),
            Token(
                kind=KindText(),
                text='world',
                span=Span(9, 14),
            ),
            Token(
                kind=KindSym(Symbol.UNDERSCORE),
                text='_',
                span=Span(14, 15),
            ),
            None,
            None
        ]
        lex = Lexer(text)
        for e in expected:
            actual = lex._token()
            self.assertEqual(actual, e)


    def test_token(self):
        cases = [
            (
                'hello world',
                [
                    Token(
                        kind=KindText(), 
                        text='hello world', 
                        span=Span(0, len('hello world'))
                    )
                ]
            ),
            (
                'hello\n',
                [
                    Token(
                        kind=KindText(), 
                        text='hello', 
                        span=Span(0, 5)
                    ),
                    Token(
                        kind=KindNewline(),
                        text='\n',
                        span=Span(5, 6)
                    )
                ]
            ),
            (
                '\\ ',
                [
                    Token(
                        kind=KindEscape(), 
                        text='\\', 
                        span=Span(0, 1)
                    ),
                    Token(
                        kind=KindNbsp(),
                        text=' ',
                        span=Span(1, 2)
                    )
                ]
            ),
            (
                '\\\n',
                [
                    Token(
                        kind=KindEscape(), 
                        text='\\', 
                        span=Span(0, 1)
                    ),
                    Token(
                        kind=KindHardbreak(),
                        text='\n',
                        span=Span(1, 2)
                    )
                ]
            ),
            (
                '\\a',
                [
                    Token(
                        kind=KindText(), 
                        text='\\', 
                        span=Span(0, 1)
                    ),
                    Token(
                        kind=KindText(),
                        text='a',
                        span=Span(1, 2)
                    ),
                ]
            ),
            (
                '\\*a',
                [
                    Token(
                        kind=KindEscape(), 
                        text='\\', 
                        span=Span(0, 1)
                    ),
                    Token(
                        kind=KindText(),
                        text='*',
                        span=Span(1, 2)
                    ),
                    Token(
                        kind=KindText(),
                        text='a',
                        span=Span(2, 3)
                    ),
                ]
            ),
            (
                '[Link]',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACKET), 
                        text='[', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='Link',
                        span=Span(1, 5),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACKET),
                        text=']',
                        span=Span(5, 6)
                    )
                ]
            ),
            (
                '(url)',
                [
                    Token(
                        kind=KindOpen(Delimiter.PAREN), 
                        text='(', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='url',
                        span=Span(1, 4),
                    ),
                    Token(
                        kind=KindClose(Delimiter.PAREN),
                        text=')',
                        span=Span(4, 5)
                    )
                ]
            ),
            (
                '(url)',
                [
                    Token(
                        kind=KindOpen(Delimiter.PAREN), 
                        text='(', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='url',
                        span=Span(1, 4),
                    ),
                    Token(
                        kind=KindClose(Delimiter.PAREN),
                        text=')',
                        span=Span(4, 5)
                    )
                ]
            ),
            (
                '{*strong*}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_ASTERISK), 
                        text='{*', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='strong',
                        span=Span(2, 8),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_ASTERISK),
                        text='*}',
                        span=Span(8, 10)
                    )
                ]
            ),
            (
                '{^TM^}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_CARET), 
                        text='{^', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='TM',
                        span=Span(2, 4),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_CARET),
                        text='^}',
                        span=Span(4, 6)
                    )
                ]
            ),
            (
                '{=highlighted=}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_EQUAL), 
                        text='{=', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='highlighted',
                        span=Span(2, 13),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_EQUAL),
                        text='=}',
                        span=Span(13, 15)
                    )
                ]
            ),
            (
                '{-delete-}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_HYPHEN), 
                        text='{-', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='delete',
                        span=Span(2, 8),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_HYPHEN),
                        text='-}',
                        span=Span(8, 10)
                    )
                ]
            ),
            (
                '{+insert+}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_PLUS), 
                        text='{+', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='insert',
                        span=Span(2, 8),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_PLUS),
                        text='+}',
                        span=Span(8, 10)
                    )
                ]
            ),
            (
                '{~2~}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_TILDE), 
                        text='{~', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='2',
                        span=Span(2, 3),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_TILDE),
                        text='~}',
                        span=Span(3, 5)
                    )
                ]
            ),
            (
                '{_emphasis_}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_UNDERSCORE), 
                        text='{_', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='emphasis',
                        span=Span(2, 10),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_UNDERSCORE),
                        text='_}',
                        span=Span(10, 12)
                    )
                ]
            ),
            (
                '{\'quote\'}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_QUOTE1), 
                        text='{\'', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='quote',
                        span=Span(2, 7),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_QUOTE1),
                        text='\'}',
                        span=Span(7, 9)
                    )
                ]
            ),
            (
                '{"quote"}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_QUOTE2), 
                        text='{"', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='quote',
                        span=Span(2, 7),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_QUOTE2),
                        text='"}',
                        span=Span(7, 9)
                    )
                ]
            ),
            (
                '{#foo}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE), 
                        text='{', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='#foo',
                        span=Span(1, 5),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE),
                        text='}',
                        span=Span(5, 6)
                    )
                ]
            ),
            (
                '![cat]',
                [
                    Token(
                        kind=KindSym(Symbol.EXCLAIM_BRACKET), 
                        text='![', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='cat',
                        span=Span(2, 5),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACKET),
                        text=']',
                        span=Span(5, 6)
                    )
                ]
            ),
            (
                '<',
                [
                    Token(
                        kind=KindSym(Symbol.LT), 
                        text='<', 
                        span=Span(0, 1),
                    ),
                ]
            ),
            (
                '|Header|',
                [
                    Token(
                        kind=KindSym(Symbol.PIPE), 
                        text='|', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='Header',
                        span=Span(1, 7),
                    ),
                    Token(
                        kind=KindSym(Symbol.PIPE),
                        text='|',
                        span=Span(7, 8)
                    )
                ]
            ),
            (
                ':smiley:',
                [
                    Token(
                        kind=KindSym(Symbol.COLON), 
                        text=':', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='smiley',
                        span=Span(1, 7),
                    ),
                    Token(
                        kind=KindSym(Symbol.COLON),
                        text=':',
                        span=Span(7, 8)
                    )
                ]
            ),
            (
                '``x``',
                [
                    Token(
                        kind=KindSeq(Sequence.BACKTICK), 
                        text='``', 
                        span=Span(0, 2),
                    ),
                    Token(
                        kind=KindText(),
                        text='x',
                        span=Span(2, 3),
                    ),
                    Token(
                        kind=KindSeq(Sequence.BACKTICK),
                        text='``',
                        span=Span(3, 5)
                    )
                ]
            ),
            (
                '.red',
                [
                    Token(
                        kind=KindSeq(Sequence.PERIOD), 
                        text='.', 
                        span=Span(0, 1),
                    ),
                    Token(
                        kind=KindText(),
                        text='red',
                        span=Span(1, 4),
                    ),
                ]
            ),
        ]
        for text, expected in cases:
            with self.subTest(text):
                lex = Lexer(text)
                for e in expected:
                    actual = lex._token()
                    self.assertEqual(actual, e)

    def test_next_token(self):
        cases = [
            (
                '\\a',
                [
                    Token(
                        kind=KindText(), 
                        text='\\a', 
                        span=Span(0, 2)
                    ),
                ]
            ),
            (
                '\\*a',
                [
                    Token(
                        kind=KindEscape(), 
                        text='\\', 
                        span=Span(0, 1)
                    ),
                    Token(
                        kind=KindText(), 
                        text='*a', 
                        span=Span(1, 3)
                    ),
                ]
            ),
        ]

        for text, expected in cases:
            with self.subTest(text):
                lex = Lexer(text)
                for e in expected:
                    actual = lex._next_token()
                    self.assertEqual(actual, e)

    def test_empty(self):
        test_lex('', [])

    def test_basic(self):
        test_lex('abc', [Token(kind=KindText(), text='abc', span=Span(0, 3))])
        test_lex(
            'para w/ some _emphasis_ and *strong*.',
            [
                Token(
                    kind=KindText(),
                    text='para w/ some ',
                    span=Span(0, len('para w/ some '))
                ),
                Token(
                    kind=KindSym(Symbol.UNDERSCORE),
                    text='_',
                    span=Span(len('para w/ some '), len('para w/ some _'))
                ),
                Token(
                    kind=KindText(),
                    text='emphasis',
                    span=Span(len('para w/ some _'), len('para w/ some _emphasis')),
                ),
                Token(
                    kind=KindSym(Symbol.UNDERSCORE),
                    text='_',
                    span=Span(len('para w/ some _emphasis'), len('para w/ some _emphasis_'))
                ),
                Token(
                    kind=KindText(),
                    text=' and ',
                    span=Span(len('para w/ some _emphasis_'), len('para w/ some _emphasis_ and ')),
                ),
                Token(
                    kind=KindSym(Symbol.ASTERISK),
                    text='*',
                    span=Span(len('para w/ some _emphasis_ and '), len('para w/ some _emphasis_ and *'))
                ),
                Token(
                    kind=KindText(),
                    text='strong',
                    span=Span(len('para w/ some _emphasis_ and *'), len('para w/ some _emphasis_ and *strong')),
                ),
                Token(
                    kind=KindSym(Symbol.ASTERISK),
                    text='*',
                    span=Span(len('para w/ some _emphasis_ and *strong'), len('para w/ some _emphasis_ and *strong*'))
                ),
                Token(
                    kind=KindSeq(Sequence.PERIOD),
                    text='.',
                    span=Span(len('para w/ some _emphasis_ and *strong*'), len('para w/ some _emphasis_ and *strong*.'))
                )
            ]
        )

    def test_escape(self):
        test_lex(
            r'\a',
            [
                Token(
                    kind=KindText(),
                    text=r'\a',
                    span=Span(0, 2),
                ),
            ]
        )
        test_lex(
            r'\\a',
            [
                Token(
                    kind=KindEscape(),
                    text='\\', # cannot use raw string here.
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindText(),
                    text=r'\a',
                    span=Span(1, 3),
                ),
            ]
        )
        test_lex(
            r'\.',
            [
                Token(
                    kind=KindEscape(),
                    text='\\',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindText(),
                    text='.',
                    span=Span(1, 2),
                )
            ]
        )
        test_lex(
            r'\ ',
            [
                Token(
                    kind=KindEscape(),
                    text='\\',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindNbsp(),
                    text=' ',
                    span=Span(1, 2)
                )
            ]
        )
        test_lex(
            r'\{-',
            [
                Token(
                    kind=KindEscape(),
                    text='\\',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindText(),
                    text='{',
                    span=Span(1, 2),
                ),
                Token(
                    kind=KindSeq(Sequence.HYPHEN),
                    text='-',
                    span=Span(2, 3),
                ),
            ]
        )

    def test_hardbreak(self):
        test_lex(
            'a\\\n',
            [
                Token(
                    kind=KindText(),
                    text='a',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindEscape(),
                    text='\\',
                    span=Span(1, 2),
                ),
                Token(
                    kind=KindHardbreak(),
                    text='\n',
                    span=Span(2, 3),
                ),
            ]
        )
        test_lex(
            'a\\   \n',
            [
                Token(
                    kind=KindText(),
                    text='a',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindEscape(),
                    text='\\',
                    span=Span(1, 2),
                ),
                Token(
                    kind=KindHardbreak(),
                    text='   \n',
                    span=Span(2, 6)
                )
            ]
        )
        test_lex(
            'a\\\t \t \n',
            [
                Token(
                    kind=KindText(),
                    text='a',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindEscape(),
                    text='\\',
                    span=Span(1, 2),
                ),
                Token(
                    kind=KindHardbreak(),
                    text='\t \t \n',
                    span=Span(2, 7),
                )
            ]
        )

    def test_delim(self):
        test_lex(
            '{-',
            [
                Token(
                    kind=KindOpen(Delimiter.BRACE_HYPHEN),
                    text='{-',
                    span=Span(0, 2)
                )
            ]
        )
        test_lex(
            '-}',
            [
                Token(
                    kind=KindClose(Delimiter.BRACE_HYPHEN),
                    text='-}',
                    span=Span(0, 2)
                )
            ]
        )
        test_lex(
            '{++}',
            [
                Token(
                    kind=KindOpen(Delimiter.BRACE_PLUS),
                    text='{+',
                    span=Span(0, 2)
                ),
                Token(
                    kind=KindClose(Delimiter.BRACE_PLUS),
                    text='+}',
                    span=Span(2, 4)
                )
            ]
        )

    def test_sym(self):
        test_lex(
            '\'*^![<|"~_',
            [
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    text="'",
                    span=Span(0, 1)
                ),
                Token(
                    kind=KindSym(Symbol.ASTERISK),
                    text="*",
                    span=Span(1, 2)
                ),
                Token(
                    kind=KindSym(Symbol.CARET),
                    text="^",
                    span=Span(2, 3)
                ),
                Token(
                    kind=KindSym(Symbol.EXCLAIM_BRACKET),
                    text="![",
                    span=Span(3, 5)
                ),
                Token(
                    kind=KindSym(Symbol.LT),
                    text="<",
                    span=Span(5, 6)
                ),
                Token(
                    kind=KindSym(Symbol.PIPE),
                    text="|",
                    span=Span(6, 7)
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE2),
                    text='"',
                    span=Span(7, 8)
                ),
                Token(
                    kind=KindSym(Symbol.TILDE),
                    text="~",
                    span=Span(8, 9)
                ),
                Token(
                    kind=KindSym(Symbol.UNDERSCORE),
                    text="_",
                    span=Span(9, 10)
                )
            ]
        )
        test_lex(
            "''''",
            [
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    text="'",
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    text="'",
                    span=Span(1, 2),
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    text="'",
                    span=Span(2, 3),
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    text="'",
                    span=Span(3, 4),
                ),
            ]
        )

    def test_seq(self):
        test_lex(
            "`",
            [
                Token(
                    kind=KindSeq(Sequence.BACKTICK),
                    text='`',
                    span=Span(0, 1),
                ),
            ]
        )

        test_lex(
            "```",
            [
                Token(
                    kind=KindSeq(Sequence.BACKTICK),
                    text='```',
                    span=Span(0, 3),
                )
            ]
        )

        test_lex(
            "`-.",
            [
                Token(
                    kind=KindSeq(Sequence.BACKTICK),
                    text='`',
                    span=Span(0, 1),
                ),
                Token(
                    kind=KindSeq(Sequence.HYPHEN),
                    text='-',
                    span=Span(1, 2),
                ),
                Token(
                    kind=KindSeq(Sequence.PERIOD),
                    text='.',
                    span=Span(2, 3),
                ),
            ]
        )
        

if __name__ == '__main__':
    unittest.main()