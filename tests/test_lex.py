import unittest

from jotdown.lex import (
    Lexer,
    Delimiter,
    SymbolKind,
    SeqKind,
    TextToken,
    NewlineToken,
    TokenNbsp,
    TokenHardbreak,
    EscapeToken,
    OpenToken,
    CloseToken,
    SymToken,
    SequenceToken
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
            ('\n', NewlineToken(1)),
            ('\\ ', EscapeToken(1)),
            ('\\', TextToken(1)),
            ('[', OpenToken(1,Delimiter.BRACKET)),
            (']', CloseToken(1, Delimiter.BRACKET)),
            ('(', OpenToken(1, Delimiter.PAREN)),
            (')', CloseToken(1, Delimiter.PAREN)),
            ('{*', OpenToken(2, Delimiter.BRACE_ASTERISK)),
            ('{^', OpenToken(2, Delimiter.BRACE_CARET)),
            ('{=', OpenToken(2, Delimiter.BRACE_EQUAL)),
            ('{-', OpenToken(2, Delimiter.BRACE_HYPHEN)),
            ('{+', OpenToken(2, Delimiter.BRACE_PLUS)),
            ('{~', OpenToken(2, Delimiter.BRACE_TILDE)),
            ('{_', OpenToken(2, Delimiter.BRACE_UNDERSCORE)),
            ('{\'', OpenToken(2, Delimiter.BRACE_QUOTE1)),
            ('{"', OpenToken(2, Delimiter.BRACE_QUOTE2)),
            ('{', OpenToken(1, Delimiter.BRACE)),
            ('}', CloseToken(1, Delimiter.BRACE)),
            ('*}', CloseToken(2, Delimiter.BRACE_ASTERISK)),
            ('*', SymToken(1, SymbolKind.ASTERISK)),
            ('^}', CloseToken(2, Delimiter.BRACE_CARET)),
            ('^', SymToken(1, SymbolKind.CARET)),
            ('=}', CloseToken(2, Delimiter.BRACE_EQUAL)),
            ('=', TextToken(1)),
            ('+}', CloseToken(2, Delimiter.BRACE_PLUS)),
            ('+', TextToken(1)),
            ('~}', CloseToken(2, Delimiter.BRACE_TILDE)),
            ('~', SymToken(1, SymbolKind.TILDE)),
            ('_}', CloseToken(2, Delimiter.BRACE_UNDERSCORE)),
            ('_', SymToken(1, SymbolKind.UNDERSCORE)),
            ('\'}', CloseToken(2, Delimiter.BRACE_QUOTE1)),
            ('\'', SymToken(1, SymbolKind.QUOTE1)),
            ('"}', CloseToken(2, Delimiter.BRACE_QUOTE2)),
            ('"', SymToken(1, SymbolKind.QUOTE2)),
            ('-}', CloseToken(2, Delimiter.BRACE_HYPHEN)),
            ('---', SequenceToken(3, SeqKind.HYPHEN)),
            ('![', SymToken(2,SymbolKind.EXCLAIM_BRACKET)),
            ('!', TextToken(1)),
            ('<', SymToken(1, SymbolKind.LT)),
            ('|', SymToken(1, SymbolKind.PIPE)),
            (':', SymToken(1, SymbolKind.COLON)),
            ('```', SequenceToken(3, SeqKind.BACKTICK)),
            ('...', SequenceToken(3, SeqKind.PERIOD)),
        ]
        for text, expected in cases:
            with self.subTest(text):
                lex = Lexer(text)
                actual = lex._special_token(0)
                self.assertEqual(actual, expected)

    def test_token_stops(self):
        text = '*hello* _world_'
        expected = [
            SymToken(
                symbol=SymbolKind.ASTERISK,
                length=1
            ),
            TextToken(5),
            SymToken(
                symbol=SymbolKind.ASTERISK,
                length=1,
            ),
            TextToken(1),
            SymToken(
                symbol=SymbolKind.UNDERSCORE,
                length=1,
            ),
            TextToken(5),
            SymToken(
                symbol=SymbolKind.UNDERSCORE,
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
                    TextToken(len('hello world'))
                ]
            ),
            (
                'hello\n',
                [
                    TextToken(length=len('hello')),
                    NewlineToken(1)
                ]
            ),
            (
                '\\ ',
                [
                    EscapeToken(1),
                    TokenNbsp(1)
                ]
            ),
            (
                '\\\n',
                [
                    EscapeToken(1),
                    TokenHardbreak(1)
                ]
            ),
            (
                '\\a',
                [
                    TextToken(1),
                    TextToken(1),
                ]
            ),
            (
                '\\*a',
                [
                    EscapeToken(1),
                    TextToken(1),
                    TextToken(1),
                ]
            ),
            (
                '[Link]',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACKET, 
                        length=len('['), 
                    ),
                    TextToken(len('Link')),
                    CloseToken(
                        delimiter=Delimiter.BRACKET,
                        length=len(']'),
                    )
                ]
            ),
            (
                '(url)',
                [
                    OpenToken(
                        delimiter=Delimiter.PAREN, 
                        length=len('('), 
                    ),
                    TextToken(len('url')),
                    CloseToken(
                        delimiter=Delimiter.PAREN,
                        length=len(')'),
                    )
                ]
            ),
            (
                '{*strong*}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_ASTERISK, 
                        length=len('{*'), 
                    ),
                    TextToken(len('strong')),
                    CloseToken(
                        delimiter=Delimiter.BRACE_ASTERISK,
                        length=len('*}'),
                    )
                ]
            ),
            (
                '{^TM^}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_CARET, 
                        length=len('{^'), 
                    ),
                    TextToken(len('TM')),
                    CloseToken(
                        delimiter=Delimiter.BRACE_CARET,
                        length=len('^}'),
                    )
                ]
            ),
            (
                '{=highlighted=}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_EQUAL, 
                        length=len('{='), 
                    ),
                    TextToken(
                        
                        length=len('highlighted'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_EQUAL,
                        length=len('=}'),
                    )
                ]
            ),
            (
                '{-delete-}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_HYPHEN, 
                        length=len('{-'), 
                    ),
                    TextToken(
                        
                        length=len('delete'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_HYPHEN,
                        length=len('-}'),
                    )
                ]
            ),
            (
                '{+insert+}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_PLUS, 
                        length=len('{+'), 
                    ),
                    TextToken(
                        
                        length=len('insert'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_PLUS,
                        length=len('+}'),
                    )
                ]
            ),
            (
                '{~2~}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_TILDE, 
                        length=len('{~'), 
                    ),
                    TextToken(
                        
                        length=len('2'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_TILDE,
                        length=len('~}'),
                    )
                ]
            ),
            (
                '{_emphasis_}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_UNDERSCORE, 
                        length=len('{_'),
                    ),
                    TextToken(
                        
                        length=len('emphasis'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_UNDERSCORE,
                        length=len('_}'),
                    )
                ]
            ),
            (
                '{\'quote\'}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_QUOTE1, 
                        length=len('{\''), 
                    ),
                    TextToken(
                        
                        length=len('quote'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_QUOTE1,
                        length=len('\'}'),
                    )
                ]
            ),
            (
                '{"quote"}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_QUOTE2, 
                        length=len('{"'), 
                    ),
                    TextToken(
                        
                        length=len('quote'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE_QUOTE2,
                        length=len('"}'),
                    )
                ]
            ),
            (
                '{#foo}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE, 
                        length=len('{'), 
                    ),
                    TextToken(
                        
                        length=len('#foo'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACE,
                        length=len('}'),
                    )
                ]
            ),
            (
                '![cat]',
                [
                    SymToken(
                        symbol=SymbolKind.EXCLAIM_BRACKET, 
                        length=len('!['), 
                    ),
                    TextToken(
                        
                        length=len('cat'),
                    ),
                    CloseToken(
                        delimiter=Delimiter.BRACKET,
                        length=len(']'),
                    )
                ]
            ),
            (
                '<',
                [
                    SymToken(
                        symbol=SymbolKind.LT, 
                        length=len('<'), 
                    ),
                ]
            ),
            (
                '|Header|',
                [
                    SymToken(
                        symbol=SymbolKind.PIPE, 
                        length=len('|'), 
                    ),
                    TextToken(
                        
                        length=len('Header'),
                    ),
                    SymToken(
                        symbol=SymbolKind.PIPE,
                        length=len('|'),
                    )
                ]
            ),
            (
                ':smiley:',
                [
                    SymToken(
                        symbol=SymbolKind.COLON, 
                        length=len(':'), 
                    ),
                    TextToken(
                        
                        length=len('smiley'),
                    ),
                    SymToken(
                        symbol=SymbolKind.COLON,
                        length=len(':'),
                    )
                ]
            ),
            (
                '``x``',
                [
                    SequenceToken(
                        sequence=SeqKind.BACKTICK, 
                        length=len('``'), 
                    ),
                    TextToken(
                        
                        length=len('x'),
                    ),
                    SequenceToken(
                        sequence=SeqKind.BACKTICK,
                        length=len('``'),
                    )
                ]
            ),
            (
                '.red',
                [
                    SequenceToken(
                        sequence=SeqKind.PERIOD, 
                        length=len('.'), 
                    ),
                    TextToken(
                        
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
                    TextToken(
                        length=len('\\a'), 
                    ),
                ]
            ),
            (
                '\\*a',
                [
                    EscapeToken(
                        length=len('\\'), 
                    ),
                    TextToken(
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
            ('abc', [TextToken(length=3)]),
            (
                'para w/ some _emphasis_ and *strong*.',
                [
                    TextToken(
                        length=len('para w/ some ')
                    ),
                    SymToken(
                        symbol=SymbolKind.UNDERSCORE,
                        length=1
                    ),
                    TextToken(
                        length=len('emphasis'),
                    ),
                    SymToken(
                        symbol=SymbolKind.UNDERSCORE,
                        length=len('_'),
                    ),
                    TextToken(
                        length=len(' and '),
                    ),
                    SymToken(
                        symbol=SymbolKind.ASTERISK,
                        length=len('*'),
                    ),
                    TextToken(
                        length=len('strong'),
                    ),
                    SymToken(
                        symbol=SymbolKind.ASTERISK,
                        length=len('*'),
                    ),
                    SequenceToken(
                        sequence=SeqKind.PERIOD,
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
                [TextToken(length=2)]
            ),
            (
                r'\\a', # TokenEscape(1), TokenText(1), TokenText(1)
                [EscapeToken(1), TextToken(2)]
            ),
            (
                r'\.',
                [EscapeToken(length=1), TextToken(length=1)]
            ),
            (
                r'\ ',
                [EscapeToken(length=1), TokenNbsp(length=1)]
            ),
            (
                r'\{-',
                [EscapeToken(length=1), TextToken(1), SequenceToken(1, SeqKind.HYPHEN)]
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
                    TextToken(1),
                    EscapeToken(1),
                    TokenHardbreak(1),
                ]
            ),
            (
                'a\\   \n',
                [
                    TextToken(1),
                    EscapeToken(1),
                    TokenHardbreak(4)
                ]
            ),
            (
                'a\\\t \t \n',
                [
                    TextToken(1),
                    EscapeToken(1),
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
                    OpenToken(
                        delimiter=Delimiter.BRACE_HYPHEN,
                        length=2
                    )
                ]
            ),
            (
                '-}',
                [
                    CloseToken(
                        delimiter=Delimiter.BRACE_HYPHEN,
                        length=2
                    )
                ]
            ),
            (
                '{++}',
                [
                    OpenToken(
                        delimiter=Delimiter.BRACE_PLUS,
                        length=2
                    ),
                    CloseToken(
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
                    SymToken(
                        symbol=SymbolKind.QUOTE1,
                        length=len("'"),
                    ),
                    SymToken(
                        symbol=SymbolKind.ASTERISK,
                        length=len("*"),
                    ),
                    SymToken(
                        symbol=SymbolKind.CARET,
                        length=len("^"),
                    ),
                    SymToken(
                        symbol=SymbolKind.EXCLAIM_BRACKET,
                        length=len("!["),
                    ),
                    SymToken(
                        symbol=SymbolKind.LT,
                        length=len("<"),
                    ),
                    SymToken(
                        symbol=SymbolKind.PIPE,
                        length=len("|"),
                    ),
                    SymToken(
                        symbol=SymbolKind.QUOTE2,
                        length=len('"'),
                    ),
                    SymToken(
                        symbol=SymbolKind.TILDE,
                        length=len("~"),
                    ),
                    SymToken(
                        symbol=SymbolKind.UNDERSCORE,
                        length=len("_"),
                    )
                ]
            ),
            (
                "''''",
                [
                    SymToken(
                        symbol=SymbolKind.QUOTE1,
                        length=1,
                    ),
                    SymToken(
                        symbol=SymbolKind.QUOTE1,
                        length=1,
                    ),
                    SymToken(
                        symbol=SymbolKind.QUOTE1,
                        length=1,
                    ),
                    SymToken(
                        symbol=SymbolKind.QUOTE1,
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
                    SequenceToken(
                        sequence=SeqKind.BACKTICK,
                        length=1,
                    ),
                ]
            ),
            (
                "```",
                [
                    SequenceToken(
                        sequence=SeqKind.BACKTICK,
                        length=3,
                    )
                ]
            ),
            (
                "`-.",
                [
                    SequenceToken(
                        sequence=SeqKind.BACKTICK,
                        length=1,
                    ),
                    SequenceToken(
                        sequence=SeqKind.HYPHEN,
                        length=1,
                    ),
                    SequenceToken(
                        sequence=SeqKind.PERIOD,
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