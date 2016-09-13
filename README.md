# unicode_range.py
Constructs a UTF-8 regular expression range from general character classes in the Unicode Character Database file found at [http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt]

# Uses
This script is useful if you are stuck with a regex implementation that does not support shorthand notation for unicode general character classes, or if you know of a range of code points that you need a regular expression for, but don't want to deal with figuring out the conversion to UTF8.

# Future features
 - add support for specific code point ranges
 - add support for Language categories
