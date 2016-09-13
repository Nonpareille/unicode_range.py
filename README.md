# unicode_range.py
Constructs a UTF-8 regular expression range from general character classes in the Unicode Character Database file found at [http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt]

# uses
This script is useful if you are stuck with a regex implementation that does not support shorthand notation for unicode general character classes (like \p{L}), or if you know of a range of code points that you need a regular expression for, but don't want to deal with figuring out the conversion to UTF8 and don't have code point based notation available. Examples of such situations are XML Schema, XPath, Perl pre 5.6, PCRE, Ruby pre 1.9, and Lex/Flex.

# planned features
 - support special ranges not manually specified in Unicode Character Database file (e.g. CJK Ideographs, Hangul Syllables, Surrogates and Private Use)
 - add support for specific code point ranges
 - add support for Language scripts and blocks
