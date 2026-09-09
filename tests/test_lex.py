import unittest

from jotdown.lex import (
    Lexer,
    Delimiter,
    Symbol,
    Sequence,
    TokenText,
    TokenNewline,
    TokenNbsp,
    TokenHardbreak,
    TokenEscape,
    TokenOpen,
    TokenClose,
    TokenSym,
    TokenSeq
)

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

    def test_escaped_token(self):
        cases = [
            ('\n', TokenHardbreak),
            ('\t  \n', TokenHardbreak),
            ('\t\n', TokenHardbreak),
            # ('\t\r\n', TokenHardbreak), # this test fails because of the way we handle newlines
            ('\t', TokenNbsp),
            ('\t  hello', TokenNbsp) # plain text after tab
        ]
        for text, expected in cases:
            with self.subTest():
                lex = Lexer(text)
                actual = lex._escaped_token(0)
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

    def test_special_token(self):
        cases = [
            ('\n', TokenNewline(1)),
            ('\\ ', TokenEscape(1)),
            ('\\', TokenText(1)),
            ('[', TokenOpen(1,Delimiter.BRACKET)),
            (']', TokenClose(1, Delimiter.BRACKET)),
            ('(', TokenOpen(1, Delimiter.PAREN)),
            (')', TokenClose(1, Delimiter.PAREN)),
            ('{*', TokenOpen(2, Delimiter.BRACE_ASTERISK)),
            ('{^', TokenOpen(2, Delimiter.BRACE_CARET)),
            ('{=', TokenOpen(2, Delimiter.BRACE_EQUAL)),
            ('{-', TokenOpen(2, Delimiter.BRACE_HYPHEN)),
            ('{+', TokenOpen(2, Delimiter.BRACE_PLUS)),
            ('{~', TokenOpen(2, Delimiter.BRACE_TILDE)),
            ('{_', TokenOpen(2, Delimiter.BRACE_UNDERSCORE)),
            ('{\'', TokenOpen(2, Delimiter.BRACE_QUOTE1)),
            ('{"', TokenOpen(2, Delimiter.BRACE_QUOTE2)),
            ('{', TokenOpen(1, Delimiter.BRACE)),
            ('}', TokenClose(1, Delimiter.BRACE)),
            ('*}', TokenClose(2, Delimiter.BRACE_ASTERISK)),
            ('*', TokenSym(1, Symbol.ASTERISK)),
            ('^}', TokenClose(2, Delimiter.BRACE_CARET)),
            ('^', TokenSym(1, Symbol.CARET)),
            ('=}', TokenClose(2, Delimiter.BRACE_EQUAL)),
            ('=', TokenText(1)),
            ('+}', TokenClose(2, Delimiter.BRACE_PLUS)),
            ('+', TokenText(1)),
            ('~}', TokenClose(2, Delimiter.BRACE_TILDE)),
            ('~', TokenSym(1, Symbol.TILDE)),
            ('_}', TokenClose(2, Delimiter.BRACE_UNDERSCORE)),
            ('_', TokenSym(1, Symbol.UNDERSCORE)),
            ('\'}', TokenClose(2, Delimiter.BRACE_QUOTE1)),
            ('\'', TokenSym(1, Symbol.QUOTE1)),
            ('"}', TokenClose(2, Delimiter.BRACE_QUOTE2)),
            ('"', TokenSym(1, Symbol.QUOTE2)),
            ('-}', TokenClose(2, Delimiter.BRACE_HYPHEN)),
            ('---', TokenSeq(3, Sequence.HYPHEN)),
            ('![', TokenSym(2,Symbol.EXCLAIM_BRACKET)),
            ('!', TokenText(1)),
            ('<', TokenSym(1, Symbol.LT)),
            ('|', TokenSym(1, Symbol.PIPE)),
            (':', TokenSym(1, Symbol.COLON)),
            ('```', TokenSeq(3, Sequence.BACKTICK)),
            ('...', TokenSeq(3, Sequence.PERIOD)),
        ]
        for text, expected in cases:
            with self.subTest(text):
                lex = Lexer(text)
                actual = lex._special_token(0)
                self.assertEqual(actual, expected)

    def test_token_stops(self):
        text = '*hello* _world_'
        expected = [
            TokenSym(
                symbol=Symbol.ASTERISK,
                length=1
            ),
            TokenText(5),
            TokenSym(
                symbol=Symbol.ASTERISK,
                length=1,
            ),
            TokenText(1),
            TokenSym(
                symbol=Symbol.UNDERSCORE,
                length=1,
            ),
            TokenText(5),
            TokenSym(
                symbol=Symbol.UNDERSCORE,
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
                    TokenText(len('hello world'))
                ]
            ),
            (
                'hello\n',
                [
                    TokenText(length=len('hello')),
                    TokenNewline(1)
                ]
            ),
            (
                '\\ ',
                [
                    TokenEscape(1),
                    TokenNbsp(1)
                ]
            ),
            (
                '\\\n',
                [
                    TokenEscape(1),
                    TokenHardbreak(1)
                ]
            ),
            (
                '\\a',
                [
                    TokenText(1),
                    TokenText(1),
                ]
            ),
            (
                '\\*a',
                [
                    TokenEscape(1),
                    TokenText(1),
                    TokenText(1),
                ]
            ),
            (
                '[Link]',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACKET, 
                        length=len('['), 
                    ),
                    TokenText(len('Link')),
                    TokenClose(
                        delimiter=Delimiter.BRACKET,
                        length=len(']'),
                    )
                ]
            ),
            (
                '(url)',
                [
                    TokenOpen(
                        delimiter=Delimiter.PAREN, 
                        length=len('('), 
                    ),
                    TokenText(len('url')),
                    TokenClose(
                        delimiter=Delimiter.PAREN,
                        length=len(')'),
                    )
                ]
            ),
            (
                '{*strong*}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_ASTERISK, 
                        length=len('{*'), 
                    ),
                    TokenText(len('strong')),
                    TokenClose(
                        delimiter=Delimiter.BRACE_ASTERISK,
                        length=len('*}'),
                    )
                ]
            ),
            (
                '{^TM^}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_CARET, 
                        length=len('{^'), 
                    ),
                    TokenText(len('TM')),
                    TokenClose(
                        delimiter=Delimiter.BRACE_CARET,
                        length=len('^}'),
                    )
                ]
            ),
            (
                '{=highlighted=}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_EQUAL, 
                        length=len('{='), 
                    ),
                    TokenText(
                        
                        length=len('highlighted'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_EQUAL,
                        length=len('=}'),
                    )
                ]
            ),
            (
                '{-delete-}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_HYPHEN, 
                        length=len('{-'), 
                    ),
                    TokenText(
                        
                        length=len('delete'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_HYPHEN,
                        length=len('-}'),
                    )
                ]
            ),
            (
                '{+insert+}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_PLUS, 
                        length=len('{+'), 
                    ),
                    TokenText(
                        
                        length=len('insert'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_PLUS,
                        length=len('+}'),
                    )
                ]
            ),
            (
                '{~2~}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_TILDE, 
                        length=len('{~'), 
                    ),
                    TokenText(
                        
                        length=len('2'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_TILDE,
                        length=len('~}'),
                    )
                ]
            ),
            (
                '{_emphasis_}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_UNDERSCORE, 
                        length=len('{_'),
                    ),
                    TokenText(
                        
                        length=len('emphasis'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_UNDERSCORE,
                        length=len('_}'),
                    )
                ]
            ),
            (
                '{\'quote\'}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_QUOTE1, 
                        length=len('{\''), 
                    ),
                    TokenText(
                        
                        length=len('quote'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_QUOTE1,
                        length=len('\'}'),
                    )
                ]
            ),
            (
                '{"quote"}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_QUOTE2, 
                        length=len('{"'), 
                    ),
                    TokenText(
                        
                        length=len('quote'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_QUOTE2,
                        length=len('"}'),
                    )
                ]
            ),
            (
                '{#foo}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE, 
                        length=len('{'), 
                    ),
                    TokenText(
                        
                        length=len('#foo'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE,
                        length=len('}'),
                    )
                ]
            ),
            (
                '![cat]',
                [
                    TokenSym(
                        symbol=Symbol.EXCLAIM_BRACKET, 
                        length=len('!['), 
                    ),
                    TokenText(
                        
                        length=len('cat'),
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACKET,
                        length=len(']'),
                    )
                ]
            ),
            (
                '<',
                [
                    TokenSym(
                        symbol=Symbol.LT, 
                        length=len('<'), 
                    ),
                ]
            ),
            (
                '|Header|',
                [
                    TokenSym(
                        symbol=Symbol.PIPE, 
                        length=len('|'), 
                    ),
                    TokenText(
                        
                        length=len('Header'),
                    ),
                    TokenSym(
                        symbol=Symbol.PIPE,
                        length=len('|'),
                    )
                ]
            ),
            (
                ':smiley:',
                [
                    TokenSym(
                        symbol=Symbol.COLON, 
                        length=len(':'), 
                    ),
                    TokenText(
                        
                        length=len('smiley'),
                    ),
                    TokenSym(
                        symbol=Symbol.COLON,
                        length=len(':'),
                    )
                ]
            ),
            (
                '``x``',
                [
                    TokenSeq(
                        sequence=Sequence.BACKTICK, 
                        length=len('``'), 
                    ),
                    TokenText(
                        
                        length=len('x'),
                    ),
                    TokenSeq(
                        sequence=Sequence.BACKTICK,
                        length=len('``'),
                    )
                ]
            ),
            (
                '.red',
                [
                    TokenSeq(
                        sequence=Sequence.PERIOD, 
                        length=len('.'), 
                    ),
                    TokenText(
                        
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
                    TokenText(
                        length=len('\\a'), 
                    ),
                ]
            ),
            (
                '\\*a',
                [
                    TokenEscape(
                        length=len('\\'), 
                    ),
                    TokenText(
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
        cases = [
            ('', [])
        ]
        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_basic(self):
        cases = [
            ('abc', [TokenText(length=3)]),
            (
                'para w/ some _emphasis_ and *strong*.',
                [
                    TokenText(
                        length=len('para w/ some ')
                    ),
                    TokenSym(
                        symbol=Symbol.UNDERSCORE,
                        length=1
                    ),
                    TokenText(
                        length=len('emphasis'),
                    ),
                    TokenSym(
                        symbol=Symbol.UNDERSCORE,
                        length=len('_'),
                    ),
                    TokenText(
                        length=len(' and '),
                    ),
                    TokenSym(
                        symbol=Symbol.ASTERISK,
                        length=len('*'),
                    ),
                    TokenText(
                        length=len('strong'),
                    ),
                    TokenSym(
                        symbol=Symbol.ASTERISK,
                        length=len('*'),
                    ),
                    TokenSeq(
                        sequence=Sequence.PERIOD,
                        length=len('.'),
                    )
                ]
            )
        ]

        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_escape(self):
        cases = [
            (
                r'\a',
                [TokenText(length=2)]
            ),
            (
                r'\\a', # TokenEscape(1), TokenText(1), TokenText(1)
                [TokenEscape(1), TokenText(2)]
            ),
            (
                r'\.',
                [TokenEscape(length=1), TokenText(length=1)]
            ),
            (
                r'\ ',
                [TokenEscape(length=1), TokenNbsp(length=1)]
            ),
            (
                r'\{-',
                [TokenEscape(length=1), TokenText(1), TokenSeq(1, Sequence.HYPHEN)]
            )
        ]

        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_hardbreak(self):
        cases = [
            (
                'a\\\n',
                [
                    TokenText(1),
                    TokenEscape(1),
                    TokenHardbreak(1),
                ]
            ),
            (
                'a\\   \n',
                [
                    TokenText(1),
                    TokenEscape(1),
                    TokenHardbreak(4)
                ]
            ),
            (
                'a\\\t \t \n',
                [
                    TokenText(1),
                    TokenEscape(1),
                    TokenHardbreak(5)
                ]
            )
        ]
        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_delimiter(self):
        cases = [
            (
                '{-',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_HYPHEN,
                        length=2
                    )
                ]
            ),
            (
                '-}',
                [
                    TokenClose(
                        delimiter=Delimiter.BRACE_HYPHEN,
                        length=2
                    )
                ]
            ),
            (
                '{++}',
                [
                    TokenOpen(
                        delimiter=Delimiter.BRACE_PLUS,
                        length=2
                    ),
                    TokenClose(
                        delimiter=Delimiter.BRACE_PLUS,
                        length=2
                    )
                ]
            ),
        ]

        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_sym(self):
        cases = [
            (
                '\'*^![<|"~_',
                [
                    TokenSym(
                        symbol=Symbol.QUOTE1,
                        length=len("'"),
                    ),
                    TokenSym(
                        symbol=Symbol.ASTERISK,
                        length=len("*"),
                    ),
                    TokenSym(
                        symbol=Symbol.CARET,
                        length=len("^"),
                    ),
                    TokenSym(
                        symbol=Symbol.EXCLAIM_BRACKET,
                        length=len("!["),
                    ),
                    TokenSym(
                        symbol=Symbol.LT,
                        length=len("<"),
                    ),
                    TokenSym(
                        symbol=Symbol.PIPE,
                        length=len("|"),
                    ),
                    TokenSym(
                        symbol=Symbol.QUOTE2,
                        length=len('"'),
                    ),
                    TokenSym(
                        symbol=Symbol.TILDE,
                        length=len("~"),
                    ),
                    TokenSym(
                        symbol=Symbol.UNDERSCORE,
                        length=len("_"),
                    )
                ]
            ),
            (
                "''''",
                [
                    TokenSym(
                        symbol=Symbol.QUOTE1,
                        length=1,
                    ),
                    TokenSym(
                        symbol=Symbol.QUOTE1,
                        length=1,
                    ),
                    TokenSym(
                        symbol=Symbol.QUOTE1,
                        length=1,
                    ),
                    TokenSym(
                        symbol=Symbol.QUOTE1,
                        length=1,
                    ),
                ]
            )
        ]

        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_seq(self):
        cases = [
            (
                "`",
                [
                    TokenSeq(
                        sequence=Sequence.BACKTICK,
                        length=1,
                    ),
                ]
            ),
            (
                "```",
                [
                    TokenSeq(
                        sequence=Sequence.BACKTICK,
                        length=3,
                    )
                ]
            ),
            (
                "`-.",
                [
                    TokenSeq(
                        sequence=Sequence.BACKTICK,
                        length=1,
                    ),
                    TokenSeq(
                        sequence=Sequence.HYPHEN,
                        length=1,
                    ),
                    TokenSeq(
                        sequence=Sequence.PERIOD,
                        length=1,
                    ),
                ]
            )
        ]
        for (text, expected) in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)
        

if __name__ == '__main__':
    unittest.main()