from sklearn.base import BaseEstimator, TransformerMixin
from shared.progress import ProgressEstimator
import io, tokenize
import numpy as np
import re

class PythonPreprocessor(BaseEstimator, TransformerMixin):

    def fit(self, X, y=None):
        return self

    def transform(self, X, y=None):
        return np.array([self.remove_comments_and_docstring(x) for x in X])

    @staticmethod
    def __remove_via_regex(source: str) -> str:
        pattern = r"(\".*?(?<!\\)\"|\'.*?(?<!\\)\')|(/\*.*?\*/|//[^\r\n]*$)"
        # first group captures quoted strings (double or single)
        # second group captures comments (//single-line or /* multi-line */)
        regex = re.compile(pattern, re.MULTILINE|re.DOTALL)
        def _replacer(match):
            # if the 2nd group (capturing comments) is not None,
            # it means we have captured a non-quoted (real) comment string.
            if match.group(2) is not None:
                return "" # so we will return empty to remove the comment
            else: # otherwise, we will return the 1st group
                return match.group(1) # captured quoted-string

        # Remove comments
        source = regex.sub(_replacer, source)
        # Remove triple-quoted strings (docstrings)
        source = re.sub(r'(class|def)(.+)\s+(("""[\s\S]*?""")|(\'\'\'[\s\S]*?\'\'\'))', r'\1\2', source)
        return source

    @staticmethod
    def __remove_via_parsing(source: str) -> str:
        io_obj = io.StringIO(source)
        out = ""
        prev_toktype = tokenize.INDENT
        last_lineno = -1
        last_col = 0
        for tok in tokenize.generate_tokens(io_obj.readline):
            token_type = tok[0]
            token_string = tok[1]
            start_line, start_col = tok[2]
            end_line, end_col = tok[3]
            # ltext = tok[4]
            if start_line > last_lineno:
                last_col = 0
            if start_col > last_col:
                out += (" " * (start_col - last_col))
            if token_type == tokenize.COMMENT:
                pass
            elif token_type == tokenize.STRING:
                if prev_toktype != tokenize.INDENT:
                    if prev_toktype != tokenize.NEWLINE:
                        if start_col > 0:
                            out += token_string
            else:
                out += token_string
            prev_toktype = token_type
            last_col = end_col
            last_lineno = end_line
        out = '\n'.join(l for l in out.splitlines() if l.strip())
        return out

    @staticmethod
    def remove_comments_and_docstring(source: str) -> str:
        try:
            return PythonPreprocessor.__remove_via_parsing(source)
        except:
            return PythonPreprocessor.__remove_via_regex(source)

    @staticmethod
    def run_tests():
        for i, test in enumerate(tests):
            print(f"# Test {i}")
            print(test)
            stripped = PythonPreprocessor.remove_comments_and_docstring(test)
            print(stripped)
            re_stripped = PythonPreprocessor.__remove_via_regex(test)
            if stripped.strip() != re_stripped.strip():
                print("Regex and parsing don't match!")
                print("Regex:")
                print(re_stripped)
            print("\n\n")


tests = [
'''
def example_function():
    string_with_comment = "This is a string with a # comment character inside."
    print(string_with_comment)
''',
'''
def example_function():
    string_with_comment = "This is a string with a # comment character inside."  # This is a comment
    print(string_with_comment)
''',
'''
def example_function():
    string_with_docstring = "This is a string with a triple-quoted docstring inside. ''\' Docstring \'''"
    print(string_with_docstring)
''',
'''
def example_function():
    complex_string = \'''
        This is a triple-quoted string with escaped quotes: \\"quote\\".
        And here's a comment inside: # Comment
    \'''
    print(complex_string)
''',
'''
def example_function():
    multiline_string = ''\'
        This is a multiline string.
        Line 2 with a comment: # Comment
        Line 3.
    \'''
    print(multiline_string)
''',
'''
def example_function():
    single_quoted_docstring = \'\'\'Single-quoted docstring\'\'\'
    double_quoted_docstring = \"\"\"Double-quoted docstring\"\"\"
    mixed_quoted_docstring = \'\'\'Mixed-quoted docstring with "quotes"\'\'\'
    print(single_quoted_docstring, double_quoted_docstring, mixed_quoted_docstring)
''',
'''
def valid(s, alphabet):
    """ (str, str) -> bool

    Return True iff s is composed only of characters in alphabet.

    >>> valid('adc', 'abcd')
    True
    >>> valid('ABC', 'abcd')
    False
    >>> valid('abc', 'abz')
    False
    """
    for x in s:
        if x.lower() not in alphabet.lower():
            return False
    return True
'''
]