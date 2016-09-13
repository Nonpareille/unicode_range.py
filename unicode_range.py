import sys
import re
import argparse
import csv
import pickle
import exrex
import urllib.request as urlreq

def utf_byte(char):
    if char < 0 or char > 255:
        raise Exception("Character integer is out of range: {}".format(char))
    return "\\x{:02X}".format(char)

def reg_range(mn, mx):
    if mn > mx:
        raise Exception("Range minimum is greater than maximum!")
    if mn == mx:
        return utf_byte(mn)
    return "[" + utf_byte(mn) + "-" + utf_byte(mx) + "]"

def reg_concat(l):
    ret = ""
    for idx, char in enumerate(l):
        if char < 0 or char > 255:
            raise Exception("List character is out of range: index {}, char {}, list {}".format(idx, char, l))
        ret += utf_byte(char)
    return ret

def add_successor_part(starts, s, mins, mn, maxs, mx):
    if s != mx:
        return starts + [s + 1]
    return add_successors(starts, mins, maxs) + [mn]

def add_successors(starts, mins, maxs):
    return add_successor_part(starts[:-1], starts[-1], mins[:-1], mins[-1], maxs[:-1], maxs[-1])

def add_predecessor_part(ends, e, mins, mn, maxs, mx):
    if e != mn:
        return ends + [e - 1]
    return add_predecessors(ends, mins, maxs) + [mx]

def add_predecessors(ends, mins, maxs):
    return add_predecessor_part(ends[:-1], ends[-1], mins[:-1], mins[-1], maxs[:-1], maxs[-1])

def convert_uni_part(l, starts, s, ends, e, mins, mn, maxs, mx):
    if not len(starts) == len(ends) == len(mins) == len(maxs) == l-1:
        print("l= " + str(l), "starts= " + str(starts), "s= " + str(s), "ends= " + str(ends), "e= " + str(e), "mins= " + str(mins), "mn= " + str(mn), "maxs= " + str(maxs), "mx= " + str(mx), sep='\n')
        raise Exception("lengths of arguments are not the same, this is bad")
    if l <= 1:
        print("l= " + str(l), "starts= " + str(starts), "s= " + str(s), "ends= " + str(ends), "e= " + str(e), "mins= " + str(mins), "mn= " + str(mn), "maxs= " + str(maxs), "mx= " + str(mx), sep='\n')
        raise Exception("length of unicode ranges is {}, that is bad".format(l))
    if starts == ends:
        return convert_uni_range(l-1, starts, ends, mins, maxs) + reg_range(s, e)
    elif s != mn:
        return "(" + reg_concat(starts) + reg_range(s, mx) + "|" + convert_uni_part(l, add_successors(starts, mins, maxs), mn, ends, e, mins, mn, maxs, mx) + ")"
    elif e != mx:
        return "(" + reg_concat(ends) + reg_range(mn, e) + "|" + convert_uni_part(l, starts, s, add_predecessors(ends, mins, maxs), mx, mins, mn, maxs, mx) + ")"
    return convert_uni_range(l-1, starts, ends, mins, maxs) + reg_range(mn, mx)

def convert_uni_range(l, starts, ends, mins, maxs):
    if not len(starts) == len(ends) == len(mins) == len(maxs) == l:
        print("l= " + str(l), "starts= " + str(starts), "ends= " + str(ends), "mins= " + str(mins), "maxs= " + str(maxs), sep='\n')
        raise Exception("lengths of arguments are not the same, this is bad")
    if l == 0:
        print("l= " + str(l), "starts= " + str(starts), "ends= " + str(ends), "mins= " + str(mins), "maxs= " + str(maxs), sep='\n')
        raise Exception("length of unicode ranges is 0, that is bad")
    if l == 1:
        return reg_range(starts[0], ends[0])
    if starts[0] == ends[0]:
        return utf_byte(starts[0]) + convert_uni_range(l-1, starts[1:], ends[1:], mins[1:], maxs[1:])
    return convert_uni_part(l, starts[:-1], starts[-1], ends[:-1], ends[-1], mins[:-1], mins[-1], maxs[:-1], maxs[-1])

unicode_range_data = {
    (0x00000000,0x0000007F): {"extra_bytes": 0, "hi_begin": 0x00, "hi_end": 0x7F, "exp_regex": "[\\x00-\\x7F]" }, 
    (0x00000080,0x000007FF): {"extra_bytes": 1, "hi_begin": 0xC0, "hi_end": 0xDF, "exp_regex": "[\\xC2-\\xDF][\\x80-\\xBF]" }, 
    (0x00000800,0x0000FFFF): {"extra_bytes": 2, "hi_begin": 0xE0, "hi_end": 0xEF, "exp_regex": "(\\xE0[\\xA0-\\xBF]|[\\xE1-\\xEF][\\x80-\\xBF])[\\x80-\\xBF]" }, 
    (0x00010000,0x001FFFFF): {"extra_bytes": 3, "hi_begin": 0xF0, "hi_end": 0xF7, "exp_regex": "(\\xF0[\\x90-\\xBF]|[\\xF1-\\xF7][\\x80-\\xBF])[\\x80-\\xBF][\\x80-\\xBF]" }, 
    (0x00200000,0x03FFFFFF): {"extra_bytes": 4, "hi_begin": 0xF8, "hi_end": 0xFB, "exp_regex": "(\\xF8[\\x88-\\xBF]|[\\xF9-\\xFB][\\x80-\\xBF])[\\x80-\\xBF][\\x80-\\xBF][\\x80-\\xBF]" }, 
    (0x04000000,0x7FFFFFFF): {"extra_bytes": 5, "hi_begin": 0xFC, "hi_end": 0xFD, "exp_regex": "(\\xFC[\\x84-\\xBF]|\\xFD[\\x80-\\xBF])[\\x80-\\xBF][\\x80-\\xBF][\\x80-\\xBF][\\x80-\\xBF]" } 
}

def int_to_utf8(s, c, l):
    if l == 1:
        return [s + c]
    q, r = divmod(c, 0x40)
    return int_to_utf8(s, q, l - 1) + [0x80 + r]

def unicode_to_reg_range(start, end):
    def filter_func(key):
        return  (key[0] >= start and key[1] <= end) or (key[0] <= start <= key[1]) or (key[0] <= end <= key[1])
    expression = ""
    for range_key in filter(filter_func, list(unicode_range_data.keys())):
        s = max(start, range_key[0])
        e = min(end, range_key[1])
        data = unicode_range_data[range_key]
        num_bytes = data["extra_bytes"] + 1
        starts  = int_to_utf8(data["hi_begin"], s, num_bytes)
        ends    = int_to_utf8(data["hi_begin"], e, num_bytes)
        mins    = [data["hi_begin"]] + [0x80] * data["extra_bytes"]
        maxs    = [data["hi_end"]] + [0xBF] * data["extra_bytes"]
        if not len(starts) == len(ends) == len(mins) == len(maxs) == num_bytes:
            raise Exception("lengths don't match, something is weird!")
        expression += convert_uni_range(num_bytes, starts, ends, mins, maxs) + "|"
    return expression[:-1]

letter_classes      = ["Lu", "Ll", "Lt", "Lm", "Lo"]
mark_classes        = ["Mn", "Mc", "Me"]
number_classes      = ["Nd", "Nl", "No"]
symbol_classes      = ["Sm", "Sc", "Sk", "So"]
punctuation_classes = ["Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"]
whitespace_classes  = ["Zs", "Zl", "Zp"]
control_classes     = ["Cc", "Cf", "Cs", "Co"]
general_classes     = {"L": letter_classes, "M": mark_classes, "N": number_classes, "S": symbol_classes, "P": punctuation_classes, "Z": whitespace_classes, "C": control_classes}
all_classes         = letter_classes + mark_classes + number_classes + symbol_classes + punctuation_classes + whitespace_classes + control_classes
class_choices       = ["Any"] + [key for key in general_classes.keys()] + all_classes + ["Cn"]
class_long_names    = {
"Lu": "Uppercase_Letter", "Ll": "Lowercase_Letter", "Lt": "Titlecase_Letter", "Lm": "Modifier_Letter", "Lo": "Other_Letter",
"Mn": "Non_Spacing_Mark", "Mc": "Space_Combining_Mark", "Me": "Enclosing_Mark",
"Nd": "Decimal_Digit_Number", "Nl": "Letter_Number", "No": "Other_Number",
"Sm": "Math_Symbol", "Sc": "Currency_Symbol", "Sk": "Modifier_Symbol", "So": "Other_Symbol",
"Pc": "Connector_Punctuation", "Pd": "Dash_Punctuation", "Ps": "Open_Punctuation", "Pe": "Close_Punctuation", "Pi": "Initial_Punctuation", "Pf": "Final_Punctuation", "Po": "Other_Punctuation",
"Zs": "Space_Separator", "Zl": "Line_Separator", "Zp": "Paragraph_Separator",
"Cc": "Control", "Cf": "Format", "Cs": "Surrogate", "Co": "Private_Use", "Cn": "Not_Assigned"
}

class_ranges = dict()
combined_ranges = list()
classes = set()

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

@static_vars(last_codepoint=0)
@static_vars(strict=False)
def append_row(cl, codepoint):
    global class_ranges
    global combined_ranges
    global classes

    if codepoint < append_row.last_codepoint:
        raise Exception("Codepoints are not monotonically increasing! Bad Codepoint: {:0X}".format(codepoint))
    
    if cl not in classes:
        append_row.last_codepoint = codepoint
        return

    if codepoint > append_row.last_codepoint + 1 and 'Cn' in classes:
        if len(combined_ranges) == 0 or (combined_ranges[-1][1]) != append_row.last_codepoint:
            combined_ranges.append([append_row.last_codepoint + 1, codepoint - 1])
        else:
            combined_ranges[-1][1] = codepoint - 1

        if len(class_ranges['Cn']) == 0 or (class_ranges['Cn'][-1][1]) != append_row.last_codepoint:
            class_ranges['Cn'].append([append_row.last_codepoint + 1, codepoint - 1])
        else:
            class_ranges['Cn'][-1][1] = codepoint - 1
    if append_row.strict:
        append_row.last_codepoint = codepoint - 1

    if len(combined_ranges) == 0 or (combined_ranges[-1][1]) != append_row.last_codepoint:
        combined_ranges.append([codepoint, codepoint])
    else:
        combined_ranges[-1][1] = codepoint

    if len(class_ranges[cl]) == 0 or (class_ranges[cl][-1][1]) != append_row.last_codepoint:
        class_ranges[cl].append([codepoint, codepoint])
    else:
        class_ranges[cl][-1][1] = codepoint

    append_row.last_codepoint = codepoint

def build_unicode_character_database(data):
    if not data or type(data) is not type(str()):
        raise Exception("Bad input for unicode character database, there is no data")
    dialect = csv.Sniffer().sniff(data, ';')
    reader = csv.reader([line for line in data.split('\n') if len(line) != 0], dialect, strict=True, skipinitialspace=True)

    for row in reader:
        if not row or len(row) != 15:
            raise Exception("Bad input in unicode character database, expected rows of length 15")
        append_row(row[2], int(row[0], 16))

def test():
    for key, data in iter(unicode_range_data.items()):
        s = unicode_to_reg_range(key[0], key[1])
        if s != data["exp_regex"]:
            print("ERROR: {} was not the expected value: \n       {} ".format(s, data["exp_regex"]))

def main():
    global class_ranges
    global combined_ranges
    global classes

    parser = argparse.ArgumentParser(description='concatenate codepoints from unicode character database into regex ranges')
    parser.add_argument('-g', '--classes', action='append', choices=class_choices, help='the unicode general class to be enumerated')
    parser.add_argument('-n', '--invert', action='store_true', help='inverts the selected classes specified by g')
    parser.add_argument('-t', '--unit_test', action='store_true', help='runs the unicode range to regex test suite')
    parser.add_argument('-v', '--verbose', action='store_true', help='runs in verbose mode, displays pattern\'s for individual classes and ranges as well as the final pattern')
    parser.add_argument('-s', '--strict', action='store_true', help='forces strict ranges, all individual code points must be represented in the data file or they will be not be in the pattern. WARNING: this makes the pattern extremely long')
    parser.add_argument('-i', '--input', default='http://www.unicode.org/Public/UCD/latest/ucd/UnicodeData.txt', help='the input csv file (either local or a url) to build the unicode character database from')
    
    args = parser.parse_args()
    if args.unit_test:
        exit(test())

    if args.classes is None or len(args.classes) == 0 or "Any" in args.classes:
        final_pattern = "Any"
        classes.update(all_classes)
        args.classes = all_classes.copy()
        if args.strict:
            classes.update(['Cn'])
    else:
        final_pattern = "p"
        classes.update([cl for cl in args.classes if cl not in general_classes])
        for cl in args.classes:
            final_pattern += "_" + cl
            if cl in general_classes:
                classes.update(general_classes[cl])
        if args.invert:
            final_pattern = "P" + final_pattern[1:]
            classes.symmetric_difference_update(all_classes)
            if args.strict:
                classes.symmetric_difference_update(['Cn'])

    if args.strict or 'Cn' in args.classes:
        setattr(append_row, 'strict', True)

    for cl in classes:
        class_ranges[cl] = list()

    print (sorted(classes, key=lambda i: (all_classes + ['Cn']).index(i)))

    if args.input[:4] == "http":
        with urlreq.urlopen(args.input) as data_file:
            build_unicode_character_database(str(data_file.read(), encoding='utf-8'))
    else:
        with open(args.input, 'r', encoding='utf-8') as data_file:
            build_unicode_character_database(data_file.read())

    for cl, ranges in sorted(iter(class_ranges.items()), key=lambda i: (all_classes + ['Cn']).index(i[0]) ):
        class_pattern = class_long_names[cl].ljust(24) + "("
        if args.verbose:
            print(cl + ":")
        for r in sorted(ranges, key=lambda r: r[0]):
            reg_range = unicode_to_reg_range(r[0], r[1])
            if args.verbose:
                print("    [\\x{0:04X}-\\x{1:04X}] == ({2})".format(r[0], r[1], reg_range))
            class_pattern += reg_range + "|"
        class_pattern = class_pattern[:-1] + ")"
        print(class_pattern)

    for cl in sorted(iter(class_ranges.keys()), key=lambda i: (all_classes + ['Cn']).index(i)):
        print(("p_" + cl).ljust(24) + "{" + class_long_names[cl] + "}")

    final_pattern = final_pattern.ljust(24) + "("
    for r in sorted(combined_ranges, key=lambda r: r[0]):
        reg_range = unicode_to_reg_range(r[0], r[1])
        if args.verbose:
            print("Combined:")
            print("    [\\x{0:04X}-\\x{1:04X}] == ({2})".format(r[0], r[1], reg_range))
        final_pattern += reg_range + "|"
    final_pattern = final_pattern[:-1] + ")"
    print(final_pattern)

if __name__ == "__main__":
    main()
