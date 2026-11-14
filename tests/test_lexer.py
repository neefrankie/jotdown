import unittest

from jotdown.lex.lexer import (
    Lexer,
)
from jotdown.lex.token import (
    Delimiter,
    SymbolKind,
    SeqKind,
    TextToken,
    NewlineToken,
    NbspToken,
    HardbreakToken,
    EscapeToken,
    OpenToken,
    CloseToken,
    SymToken,
    SequenceToken
)

class TestLexer(unittest.TestCase):
    def test_link(self):
        text = '[foo](bar)'

        expected = [
            OpenToken(1, Delimiter.BRACKET),
            TextToken(3),
            CloseToken(1, Delimiter.BRACKET),
            OpenToken(1, Delimiter.PAREN),
            TextToken(3),
            CloseToken(1, Delimiter.PAREN),
        ]

        lexer = Lexer(text)

        actual = list(lexer)

        self.assertEqual(actual, expected)

    def test_image(self):
        text = '![foo](bar)'

        expected = [
            SymToken(2, SymbolKind.EXCLAIM_BRACKET),
            TextToken(3),
            CloseToken(1, Delimiter.BRACKET),
            OpenToken(1, Delimiter.PAREN),
            TextToken(3),
            CloseToken(1, Delimiter.PAREN),
        ]

        lexer = Lexer(text)
        
        actual = list(lexer)

        self.assertEqual(actual, expected)

    def test_brace(self):
        cases = [
            (
                '{*foo*}',
                [
                    OpenToken(2, Delimiter.BRACE_ASTERISK),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_ASTERISK)
                ]
            ),
            (
                '{^foo^}',
                [
                    OpenToken(2, Delimiter.BRACE_CARET),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_CARET)
                ]
            ),
            (
                '{=foo=}',
                [
                    OpenToken(2, Delimiter.BRACE_EQUAL),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_EQUAL)
                ]
            ),
            (
                '{-foo-}',
                [
                    OpenToken(2, Delimiter.BRACE_HYPHEN),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_HYPHEN)
                ]
            ),
            (
                '{+foo+}',
                [
                    OpenToken(2, Delimiter.BRACE_PLUS),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_PLUS)
                ]
            ),
            (
                '{~foo~}',
                [
                    OpenToken(2, Delimiter.BRACE_TILDE),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_TILDE)
                ]
            ),
            (
                '{_foo_}',
                [
                    OpenToken(2, Delimiter.BRACE_UNDERSCORE),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_UNDERSCORE)
                ]
            ),
            (
                '{\'foo\'}',
                [
                    OpenToken(2, Delimiter.BRACE_QUOTE1),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_QUOTE1)
                ]
            ),
            (
                '{"foo"}',
                [
                    OpenToken(2, Delimiter.BRACE_QUOTE2),
                    TextToken(3),
                    CloseToken(2, Delimiter.BRACE_QUOTE2)
                ]
            ),
            (
                '{foo}',
                [
                    OpenToken(1, Delimiter.BRACE),
                    TextToken(3),
                    CloseToken(1, Delimiter.BRACE)
                ]
            )
        ]

        for text, expected in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_asterisk(self):
        text = '*foo*'

        expected = [
            SymToken(1, SymbolKind.ASTERISK),
            TextToken(3),
            SymToken(1, SymbolKind.ASTERISK)
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_hyphen(self):
        cases = [
            (
                '-foo--',
                [
                    SequenceToken(1, SeqKind.HYPHEN),
                    TextToken(3),
                    SequenceToken(2, SeqKind.HYPHEN)
                ]
            ),
            (
                '{-foo---}',
                [
                    OpenToken(2, Delimiter.BRACE_HYPHEN),
                    TextToken(3),
                    SequenceToken(2, SeqKind.HYPHEN),
                    CloseToken(2, Delimiter.BRACE_HYPHEN)
                ]
            )
        ]

        for text, expected in cases:
            with self.subTest(text):
                lexer = Lexer(text)
                actual = list(lexer)
                self.assertEqual(actual, expected)

    def test_autolink(self):
        text = '<foo>'

        expected = [
            SymToken(1, SymbolKind.LT),
            TextToken(4),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_emoji(self):
        text = ':foo:'

        expected = [
            SymToken(1, SymbolKind.COLON),
            TextToken(3),
            SymToken(1, SymbolKind.COLON),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_ellipsis(self):
        text = '...'

        expected = [
            SequenceToken(3, SeqKind.PERIOD),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_verb(self):
        text = '```foo```'

        expected = [
            SequenceToken(3, SeqKind.BACKTICK),
            TextToken(3),
            SequenceToken(3, SeqKind.BACKTICK),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_pipe(self):
        text = '|foo|'

        expected = [
            SymToken(1, SymbolKind.PIPE),
            TextToken(3),
            SymToken(1, SymbolKind.PIPE),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_newline(self):
        text = 'foo\n'

        expected = [
            TextToken(3),
            NewlineToken(1),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_hardbreak(self):
        text = 'foo\\    \n'
        expected = [
            TextToken(3),
            EscapeToken(1),
            HardbreakToken(5),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_nbsp(self):
        text = 'foo\\ '
        expected = [
            TextToken(3),
            EscapeToken(1),
            NbspToken(1),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)

    def test_escaped_char(self):
        text = 'foo\\*bar'

        expected = [
            TextToken(3),
            EscapeToken(1),
            TextToken(4),
        ]

        lexer = Lexer(text)
        actual = list(lexer)
        self.assertEqual(actual, expected)




if __name__ == '__main__':
    unittest.main()