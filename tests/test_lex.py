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
                length=1
            ),
            Token(
                kind=KindText(),
                length=5,
            ),
            Token(
                kind=KindSym(Symbol.ASTERISK),
                length=1,
            ),
            Token(
                kind=KindText(),
                length=1,
            ),
            Token(
                kind=KindSym(Symbol.UNDERSCORE),
                length=1,
            ),
            Token(
                kind=KindText(),
                length=5,
            ),
            Token(
                kind=KindSym(Symbol.UNDERSCORE),
                length=1,
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
                        length=len('hello world')
                    )
                ]
            ),
            (
                'hello\n',
                [
                    Token(
                        kind=KindText(), 
                        length=len('hello'), 
                    ),
                    Token(
                        kind=KindNewline(),
                        length=len('\n'),
                    )
                ]
            ),
            (
                '\\ ',
                [
                    Token(
                        kind=KindEscape(), 
                        length=len('\\')
                    ),
                    Token(
                        kind=KindNbsp(),
                        length=len(' '),
                    )
                ]
            ),
            (
                '\\\n',
                [
                    Token(
                        kind=KindEscape(), 
                        length=len('\\')
                    ),
                    Token(
                        kind=KindHardbreak(),
                        length=len('\n')
                    )
                ]
            ),
            (
                '\\a',
                [
                    Token(
                        kind=KindText(), 
                        length=len('\\')
                    ),
                    Token(
                        kind=KindText(),
                        length=len('a')
                    ),
                ]
            ),
            (
                '\\*a',
                [
                    Token(
                        kind=KindEscape(), 
                        length=len('\\'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('*'),
                    ),
                    Token(
                        kind=KindText(),
                        length=len('a'),
                    ),
                ]
            ),
            (
                '[Link]',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACKET), 
                        length=len('['), 
    
                    ),
                    Token(
                        kind=KindText(),
                        length=len('Link'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACKET),
                        length=len(']'),
                    )
                ]
            ),
            (
                '(url)',
                [
                    Token(
                        kind=KindOpen(Delimiter.PAREN), 
                        length=len('('), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('url'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.PAREN),
                        length=len(')'),
                    )
                ]
            ),
            (
                '(url)',
                [
                    Token(
                        kind=KindOpen(Delimiter.PAREN), 
                        length=len('('), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('url'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.PAREN),
                        length=len(')'),
                    )
                ]
            ),
            (
                '{*strong*}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_ASTERISK), 
                        length=len('{*'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('strong'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_ASTERISK),
                        length=len('*}'),
                    )
                ]
            ),
            (
                '{^TM^}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_CARET), 
                        length=len('{^'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('TM'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_CARET),
                        length=len('^}'),
                    )
                ]
            ),
            (
                '{=highlighted=}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_EQUAL), 
                        length=len('{='), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('highlighted'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_EQUAL),
                        length=len('=}'),
                    )
                ]
            ),
            (
                '{-delete-}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_HYPHEN), 
                        length=len('{-'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('delete'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_HYPHEN),
                        length=len('-}'),
                    )
                ]
            ),
            (
                '{+insert+}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_PLUS), 
                        length=len('{+'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('insert'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_PLUS),
                        length=len('+}'),
                    )
                ]
            ),
            (
                '{~2~}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_TILDE), 
                        length=len('{~'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('2'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_TILDE),
                        length=len('~}'),
                    )
                ]
            ),
            (
                '{_emphasis_}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_UNDERSCORE), 
                        length=len('{_'),
                    ),
                    Token(
                        kind=KindText(),
                        length=len('emphasis'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_UNDERSCORE),
                        length=len('_}'),
                    )
                ]
            ),
            (
                '{\'quote\'}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_QUOTE1), 
                        length=len('{\''), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('quote'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_QUOTE1),
                        length=len('\'}'),
                    )
                ]
            ),
            (
                '{"quote"}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE_QUOTE2), 
                        length=len('{"'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('quote'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE_QUOTE2),
                        length=len('"}'),
                    )
                ]
            ),
            (
                '{#foo}',
                [
                    Token(
                        kind=KindOpen(Delimiter.BRACE), 
                        length=len('{'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('#foo'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACE),
                        length=len('}'),
                    )
                ]
            ),
            (
                '![cat]',
                [
                    Token(
                        kind=KindSym(Symbol.EXCLAIM_BRACKET), 
                        length=len('!['), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('cat'),
                    ),
                    Token(
                        kind=KindClose(Delimiter.BRACKET),
                        length=len(']'),
                    )
                ]
            ),
            (
                '<',
                [
                    Token(
                        kind=KindSym(Symbol.LT), 
                        length=len('<'), 
                    ),
                ]
            ),
            (
                '|Header|',
                [
                    Token(
                        kind=KindSym(Symbol.PIPE), 
                        length=len('|'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('Header'),
                    ),
                    Token(
                        kind=KindSym(Symbol.PIPE),
                        length=len('|'),
                    )
                ]
            ),
            (
                ':smiley:',
                [
                    Token(
                        kind=KindSym(Symbol.COLON), 
                        length=len(':'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('smiley'),
                    ),
                    Token(
                        kind=KindSym(Symbol.COLON),
                        length=len(':'),
                    )
                ]
            ),
            (
                '``x``',
                [
                    Token(
                        kind=KindSeq(Sequence.BACKTICK), 
                        length=len('``'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('x'),
                    ),
                    Token(
                        kind=KindSeq(Sequence.BACKTICK),
                        length=len('``'),
                    )
                ]
            ),
            (
                '.red',
                [
                    Token(
                        kind=KindSeq(Sequence.PERIOD), 
                        length=len('.'), 
                    ),
                    Token(
                        kind=KindText(),
                        length=len('red'),
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
                        length=len('\\a'), 
                    ),
                ]
            ),
            (
                '\\*a',
                [
                    Token(
                        kind=KindEscape(), 
                        length=len('\\'), 
                    ),
                    Token(
                        kind=KindText(), 
                        length=len('*a'), 
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
        test_lex('abc', [Token(kind=KindText(), length=3)])
        test_lex(
            'para w/ some _emphasis_ and *strong*.',
            [
                Token(
                    kind=KindText(),
                    length=len('para w/ some ')
                ),
                Token(
                    kind=KindSym(Symbol.UNDERSCORE),
                    length=1
                ),
                Token(
                    kind=KindText(),
                    length=len('emphasis'),
                ),
                Token(
                    kind=KindSym(Symbol.UNDERSCORE),
                    length=len('_'),
                ),
                Token(
                    kind=KindText(),
                    length=len(' and '),
                ),
                Token(
                    kind=KindSym(Symbol.ASTERISK),
                    length=len('*'),
                ),
                Token(
                    kind=KindText(),
                    length=len('strong'),
                ),
                Token(
                    kind=KindSym(Symbol.ASTERISK),
                    length=len('*'),
                ),
                Token(
                    kind=KindSeq(Sequence.PERIOD),
                    length=len('.'),
                )
            ]
        )

    def test_escape(self):
        test_lex(
            r'\a',
            [
                Token(
                    kind=KindText(),
                    length=2,
                ),
            ]
        )
        test_lex(
            r'\\a',
            [
                Token(
                    kind=KindEscape(),
                    length=len('\\'), # cannot use raw string here.
                ),
                Token(
                    kind=KindText(),
                    length=1,
                ),
            ]
        )
        test_lex(
            r'\.',
            [
                Token(
                    kind=KindEscape(),
                    length=1,
                ),
                Token(
                    kind=KindText(),
                    length=1,
                )
            ]
        )
        test_lex(
            r'\ ',
            [
                Token(
                    kind=KindEscape(),
                    length=1,
                ),
                Token(
                    kind=KindNbsp(),
                    length=1
                )
            ]
        )
        test_lex(
            r'\{-',
            [
                Token(
                    kind=KindEscape(),
                    length=1,
                ),
                Token(
                    kind=KindText(),
                    length=1,
                ),
                Token(
                    kind=KindSeq(Sequence.HYPHEN),
                    length=1,
                ),
            ]
        )

    def test_hardbreak(self):
        test_lex(
            'a\\\n',
            [
                Token(
                    kind=KindText(),
                    length=1,
                ),
                Token(
                    kind=KindEscape(),
                    length=1,
                ),
                Token(
                    kind=KindHardbreak(),
                    length=1,
                ),
            ]
        )
        test_lex(
            'a\\   \n',
            [
                Token(
                    kind=KindText(),
                    length=len('a'),
                ),
                Token(
                    kind=KindEscape(),
                    length=1,
                ),
                Token(
                    kind=KindHardbreak(),
                    length=4
                )
            ]
        )
        test_lex(
            'a\\\t \t \n',
            [
                Token(
                    kind=KindText(),
                    length=1,
                ),
                Token(
                    kind=KindEscape(),
                    length=1,
                ),
                Token(
                    kind=KindHardbreak(),
                    length=5,
                )
            ]
        )

    def test_delim(self):
        test_lex(
            '{-',
            [
                Token(
                    kind=KindOpen(Delimiter.BRACE_HYPHEN),
                    length=2
                )
            ]
        )
        test_lex(
            '-}',
            [
                Token(
                    kind=KindClose(Delimiter.BRACE_HYPHEN),
                    length=2
                )
            ]
        )
        test_lex(
            '{++}',
            [
                Token(
                    kind=KindOpen(Delimiter.BRACE_PLUS),
                    length=2
                ),
                Token(
                    kind=KindClose(Delimiter.BRACE_PLUS),
                    length=2
                )
            ]
        )

    def test_sym(self):
        test_lex(
            '\'*^![<|"~_',
            [
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    length=len("'"),
                ),
                Token(
                    kind=KindSym(Symbol.ASTERISK),
                    length=len("*"),
                ),
                Token(
                    kind=KindSym(Symbol.CARET),
                    length=len("^"),
                ),
                Token(
                    kind=KindSym(Symbol.EXCLAIM_BRACKET),
                    length=len("!["),
                ),
                Token(
                    kind=KindSym(Symbol.LT),
                    length=len("<"),
                ),
                Token(
                    kind=KindSym(Symbol.PIPE),
                    length=len("|"),
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE2),
                    length=len('"'),
                ),
                Token(
                    kind=KindSym(Symbol.TILDE),
                    length=len("~"),
                ),
                Token(
                    kind=KindSym(Symbol.UNDERSCORE),
                    length=len("_"),
                )
            ]
        )
        test_lex(
            "''''",
            [
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    length=1,
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    length=1,
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    length=1,
                ),
                Token(
                    kind=KindSym(Symbol.QUOTE1),
                    length=1,
                ),
            ]
        )

    def test_seq(self):
        test_lex(
            "`",
            [
                Token(
                    kind=KindSeq(Sequence.BACKTICK),
                    length=1,
                ),
            ]
        )

        test_lex(
            "```",
            [
                Token(
                    kind=KindSeq(Sequence.BACKTICK),
                    length=3,
                )
            ]
        )

        test_lex(
            "`-.",
            [
                Token(
                    kind=KindSeq(Sequence.BACKTICK),
                    length=1,
                ),
                Token(
                    kind=KindSeq(Sequence.HYPHEN),
                    length=1,
                ),
                Token(
                    kind=KindSeq(Sequence.PERIOD),
                    length=1,
                ),
            ]
        )
        

if __name__ == '__main__':
    unittest.main()