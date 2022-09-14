import argparse
import bisect
import os
import re
import sys
import warnings
from typing import *

import unicodedata


# ========================================== CLASSES WITH METHODS ==========================================


class Occurrence(TypedDict):
    block_index_start: int
    block_index_end: int
    abs_start_of_start_block: int
    abs_start_of_end_block: int
    abs_end_of_start_block: int
    abs_end_of_end_block: int
    matched_position_in_start_block: int
    matched_position_in_end_block: int


class BaseMethods:
    @classmethod
    def determine_occurrence(cls, file_content: str, abs_start: int, abs_end: int):
        block_index_start = file_content.count('\n', 0, abs_start)
        block_index_end = file_content.count('\n', 0, abs_end)

        abs_start_of_start_block = file_content.rfind('\n', 0, abs_start)
        abs_start_of_end_block = file_content.rfind('\n', 0, abs_end)
        abs_end_of_start_block = file_content.find('\n', abs_start, len(file_content))
        abs_end_of_end_block = file_content.find('\n', abs_end, len(file_content))

        if abs_start_of_start_block == -1:
            abs_start_of_start_block = 0
        else:
            abs_start_of_start_block += 1

        if abs_start_of_end_block == -1:
            abs_start_of_end_block = 0
        else:
            abs_start_of_end_block += 1

        if abs_end_of_start_block == -1:
            abs_end_of_start_block = len(file_content)

        if abs_end_of_end_block == -1:
            abs_end_of_end_block = len(file_content)

        matched_position_in_start_block = abs_start - abs_start_of_start_block
        matched_position_in_end_block = abs_end - abs_start_of_end_block

        return Occurrence(block_index_start=block_index_start, block_index_end=block_index_end,
                          abs_start_of_start_block=abs_start_of_start_block,
                          abs_start_of_end_block=abs_start_of_end_block,
                          abs_end_of_start_block=abs_end_of_start_block,
                          abs_end_of_end_block=abs_end_of_end_block,
                          matched_position_in_start_block=matched_position_in_start_block,
                          matched_position_in_end_block=matched_position_in_end_block)

    @classmethod
    def replace_with_spaces(cls, file_content: str, regex: re.Pattern):
        for match in regex.finditer(file_content):
            start, end = match.span(0)
            mid_string = ''
            for line in match.group(0).splitlines(True):
                end = start + len(line)
                b = (line[-1] == '\n')
                mid_string += ' ' * (end - start - b) + '\n' * b
                start = end + 1
            start, end = match.span(0)
            file_content = file_content[:start] + mid_string + file_content[end:]
        return file_content


class CppBaseMethods(BaseMethods):
    single_line_comment_regex = re.compile(r'//.*')
    preprocessor_directive_regex = re.compile(r"(#[^\n]*(?:\\\n[^\n]*)*?[^\\](?=\n))", re.DOTALL)
    multi_line_comment_regex = re.compile(r'/\*.*?\*/', re.DOTALL)
    char_literal_regex = re.compile(r'\'.*?(?<!\\)\'', re.DOTALL)
    string_literal_regex = re.compile(r'\".*?(?<!\\)\"', re.DOTALL)
    flow_control_regex = re.compile(r"\b(?:if|else(?:\s+if)?|while|for|do|catch|switch)\b|"
                                    r"\b\S*?\s*?\([^{};]*(?={)|\b(?:class|struct|union|enum|namespace)\b(?=[^;}]*?\{)")
    regex_for_single_line_skip = re.compile('|'.join([single_line_comment_regex.pattern]))
    regex_for_multi_line_skip = re.compile('|'.join([preprocessor_directive_regex.pattern,
                                                     multi_line_comment_regex.pattern,
                                                     char_literal_regex.pattern,
                                                     string_literal_regex.pattern]), re.DOTALL)

    @classmethod
    def generate_regex_for_single_line_skip(cls, single_line_comments: bool = False):
        one_line_regex_list = []
        if single_line_comments:
            one_line_regex_list.append(cls.single_line_comment_regex.pattern)
        return re.compile('|'.join(one_line_regex_list))

    @classmethod
    def generate_regex_for_multi_line_skip(cls, multi_line_comments: bool = False,
                                           preprocessor_directives: bool = False,
                                           char_literals: bool = False,
                                           string_literals: bool = False):
        multi_line_regex_list = []
        if multi_line_comments:
            multi_line_regex_list.append(cls.multi_line_comment_regex.pattern)
        if preprocessor_directives:
            multi_line_regex_list.append(cls.preprocessor_directive_regex.pattern)
        if string_literals:
            multi_line_regex_list.append(cls.string_literal_regex.pattern)
        if char_literals:
            multi_line_regex_list.append(cls.char_literal_regex.pattern)
        return re.compile('|'.join(multi_line_regex_list), flags=re.DOTALL)

    @classmethod
    def simple_mode_search(cls, regex: re.Pattern, file_content: str,
                           regex_for_single_line_skip: re.Pattern = None,
                           regex_for_multi_line_skip: re.Pattern = None) -> List[Tuple[str, str]]:
        original_file_content = file_content
        if isinstance(regex_for_single_line_skip, re.Pattern):
            file_content = CppBaseMethods.replace_with_spaces(file_content,
                                                              regex_for_single_line_skip)
        if isinstance(regex_for_multi_line_skip, re.Pattern):
            file_content = CppBaseMethods.replace_with_spaces(file_content,
                                                              regex_for_multi_line_skip)

        result = []
        for match in regex.finditer(file_content):
            abs_start, abs_end = match.span(0)
            occ = cls.determine_occurrence(file_content, abs_start, abs_end)
            format_string = f"{1 + occ['block_index_start']}:{1 + occ['matched_position_in_start_block']}-"
            format_string += f"{1 + occ['block_index_end']}:{1 + occ['matched_position_in_end_block']}"
            start = occ['abs_start_of_start_block']
            end = occ['abs_end_of_end_block']
            result.append((original_file_content[start:end], format_string))
        return result

    @classmethod
    def nesting_mode_search(cls, regex: re.Pattern, file_content: str,
                            regex_for_single_line_skip: re.Pattern = None,
                            regex_for_multi_line_skip: re.Pattern = None) -> List[List[Tuple[str, str]]]:
        original_file_content = file_content

        clean_file_content = CppBaseMethods.replace_with_spaces(file_content,
                                                                cls.regex_for_single_line_skip)
        clean_file_content = CppBaseMethods.replace_with_spaces(clean_file_content,
                                                                cls.regex_for_multi_line_skip)

        if isinstance(regex_for_single_line_skip, re.Pattern):
            file_content = CppBaseMethods.replace_with_spaces(file_content,
                                                              regex_for_single_line_skip)
        if isinstance(regex_for_multi_line_skip, re.Pattern):
            file_content = CppBaseMethods.replace_with_spaces(file_content,
                                                              regex_for_multi_line_skip)

        nesteds_start = []
        nesteds_end = []
        for match in cls.flow_control_regex.finditer(clean_file_content):
            start, end = match.span(0)
            round_brackets = 0
            square_brackets = 0
            curly_braces = 0
            error = False
            for pos, ch in enumerate(clean_file_content[start:], start):
                if ch == '{':
                    curly_braces += 1
                elif ch == '}':
                    curly_braces -= 1
                    if curly_braces == round_brackets == square_brackets == 0:
                        end = pos + 1
                        break
                    elif curly_braces < 0:
                        error = True
                        break
                elif ch == '(':
                    round_brackets += 1
                elif ch == ')':
                    round_brackets -= 1
                    if round_brackets < 0:
                        error = True
                        break
                elif ch == '[':
                    square_brackets += 1
                elif ch == ']':
                    square_brackets -= 1
                    if square_brackets < 0:
                        error = True
                        break
                elif ch == ';' and curly_braces == round_brackets == square_brackets == 0:
                    end = pos + 1
                    break
            else:
                end = len(clean_file_content)
            if not error:
                nesteds_start.append(start)
                nesteds_end.append(end)

        traces = []
        for match in regex.finditer(file_content):
            abs_start, abs_end = match.span(0)
            trace = []

            occ = cls.determine_occurrence(file_content, abs_start, abs_end)
            block_index_start = occ['block_index_start']
            block_index_end = occ['block_index_end']
            matched_position_in_start_block = occ['matched_position_in_start_block']
            matched_position_in_end_block = occ['matched_position_in_end_block']
            if (block_index_start == block_index_end and
                    matched_position_in_start_block == matched_position_in_end_block):
                format_string = f"{1 + block_index_start}:{1 + matched_position_in_start_block}"
            elif block_index_start == block_index_end:
                format_string = f"{1 + block_index_start}:{1 + matched_position_in_start_block}-"
                format_string += f"{1 + matched_position_in_end_block}"
            else:
                format_string = f"{1 + block_index_start}:{1 + matched_position_in_start_block}-"
                format_string += f"{1 + block_index_end}:{1 + matched_position_in_end_block}"
            start = occ['abs_start_of_start_block']
            end = occ['abs_end_of_end_block']
            trace.append((original_file_content[start:end], format_string))
            occ_block_index_start = block_index_start

            i = bisect.bisect_right(nesteds_start, abs_start) - 1
            last_block_index_start = occ_block_index_start
            while i >= 0:
                if nesteds_start[i] <= abs_start <= nesteds_end[i]:
                    start = nesteds_start[i]
                    end = nesteds_end[i]
                    occ = cls.determine_occurrence(file_content, start, end)
                    block_index_start = occ['block_index_start']
                    block_index_end = occ['block_index_end']
                    if block_index_start == last_block_index_start:
                        i -= 1
                        continue
                    if block_index_start != block_index_end:
                        format_string = f"{1 + block_index_start}-{1 + block_index_end}"
                    else:
                        format_string = f"{1 + block_index_start}"
                    start = occ['abs_start_of_start_block']
                    end = occ['abs_end_of_start_block']
                    trace.append((original_file_content[start:end], format_string))
                    last_block_index_start = block_index_start
                i -= 1
            trace = trace[::-1]

            traces.append(trace)
        return traces


# ========================================== MAIN ==========================================

def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='app', description="C++ code searcher",
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-m", "--mode", type=str, default='simple', required=False,
                        help="app mode:\n"
                             "`simple` - search for occurrences (default)\n"
                             "`nesting` - search for occurrences with nesting")
    parser.add_argument("-p", "--paths", type=str, default=[], required=True, nargs='+',
                        help="paths to dirs/files [example: `/path/to/dir /path/to/file`]")
    x_group_2 = parser.add_mutually_exclusive_group(required=True)
    x_group_2.add_argument("-t", "--text", type=str, default='',
                           help="plain text for search [example: `ab`]")
    x_group_2.add_argument("-r", "--regex", type=str, default='',
                           help="python-regex for search [example: `\"a.*?b\"`]")
    parser.add_argument('-f', '--flags', type=str, default='', required=False,
                        help="flags:\nA (ASCII-only matching),\nI (ignore case),\nL (locale dependent),\n"
                             "M (multi-line),\nS (dot matches all),\nU (Unicode matching)\n"
                             "[example: `AILMSU` or `ailmsu`]")
    parser.add_argument('-ic', '--ignore-comments', action='store_true', required=False,
                        help='Ignore comments')
    parser.add_argument('-id', '--ignore-directives', action='store_true', required=False,
                        help='Ignore preprocessing directives')
    parser.add_argument('-icsl', '--ignore-char-str-literals', action='store_true', required=False,
                        help='Ignore char and string literals')
    parser.add_argument('-mt', '--measure-time', action='store_true', required=False,
                        help='Measure program runtime')
    parser.add_argument('-v', '--verbose', action='store_true', required=False, help='Verbose mode')
    parser.add_argument('--debug-args', action='store_true', required=False, help='Debug mode '
                                                                                  '(only shows converted arguments)')
    return parser


class ParserArguments(TypedDict):
    mode: Literal['simple', 'nesting']
    paths: List[str]
    regex_string: str
    flags: int
    ignore_comments: bool
    ignore_directives: bool
    ignore_char_str_literals: bool
    measure_time: bool
    verbose: bool
    debug_args: bool


def parse_arguments(parser: argparse.ArgumentParser, *, verbose_stderr: bool) -> Union[int, ParserArguments]:
    try:
        args = parser.parse_args()
    except:
        return 1

    mode = args.mode if args.mode in {'simple', 'nesting'} else 'simple'
    debug_args = bool(args.debug_args)
    verbose = bool(args.verbose)
    ignore_comments = bool(args.ignore_comments)
    ignore_directives = bool(args.ignore_directives)
    ignore_char_str_literals = bool(args.ignore_char_str_literals)
    measure_time = bool(args.measure_time)

    files = []
    for path in args.paths:
        path = os.path.normpath(path)
        if os.path.isdir(path):
            for dirpath, dirnames, filenames in os.walk(top=path, topdown=True):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        with open(file_path, 'r') as fp:
                            fp.seek(0, 2)
                            symbols = fp.tell()
                        if symbols > 0:
                            files.append(file_path)
                        elif verbose_stderr:
                            print(f'File {file_path} is empty, skipped', file=sys.stderr)
                    except:
                        if verbose_stderr:
                            print(f'File {file_path} cannot be open for reading, skipped', file=sys.stderr)
        elif os.path.isfile(path):
            files.append(path)
        elif verbose_stderr:
            print(f'Object {path} is not dir or file, skipped', file=sys.stderr)

    flags = args.flags.upper()
    flags = int((bool('A' in flags) * re.A) | (bool('I' in flags) * re.I) | (bool('L' in flags) * re.L) |
                (bool('M' in flags) * re.M) | (bool('S' in flags) * re.S) | (bool('U' in flags) * re.U))

    regex_string = re.escape(args.text) if args.text else args.regex
    return ParserArguments(mode=mode, paths=files, regex_string=regex_string,
                           flags=flags, ignore_comments=ignore_comments,
                           ignore_directives=ignore_directives, ignore_char_str_literals=ignore_char_str_literals,
                           measure_time=measure_time, verbose=verbose, debug_args=debug_args)


def main():
    import time
    unicode_normalization_method = "NFKD"

    warnings.filterwarnings("error")
    dict_args = parse_arguments(get_parser(), verbose_stderr=True)
    if isinstance(dict_args, int):
        sys.exit(dict_args)
    mode = dict_args['mode']
    mode = mode if mode in {'simple', 'nesting'} else 'simple'
    files = dict_args['paths']
    flags = dict_args['flags']
    ignore_comments = dict_args['ignore_comments']
    ignore_directives = dict_args['ignore_directives']
    ignore_char_str_literals = dict_args['ignore_char_str_literals']
    measure_time = dict_args['measure_time']
    regex_string = unicodedata.normalize(unicode_normalization_method, dict_args['regex_string'])
    try:
        if not regex_string:
            raise re.error('')
        regex = re.compile(regex_string, flags)
    except re.error:
        print(f'regex is invalid: {repr(dict_args["regex_string"])}', file=sys.stderr)
        sys.exit(2)
    verbose = dict_args['verbose']
    debug_args = dict_args['debug_args']
    if debug_args:
        print(f'mode: {mode}\n'
              f'files: ' + " ".join(f"\"{file}\"" for file in files) + '\n' +
              f'regex: {regex}\n'
              f'flags: {flags or "-"}\n'
              f'ignore_comments: {ignore_comments}\n'
              f'ignore_directives: {ignore_directives}\n'
              f'ignore_char_str_literals: {ignore_char_str_literals}\n'
              f'measure_time: {measure_time}\n'
              f'verbose: {verbose}\n'
              f'debug_args: {debug_args}',
              file=sys.stderr)
        sys.exit(0)

    normalize_string_regex = re.compile(r'\s+')

    # main process
    indent = ' ' * 4
    if measure_time:
        time_start = time.monotonic()
    regex_for_single_line_skip = CppBaseMethods.generate_regex_for_single_line_skip(
        single_line_comments=ignore_comments
    )
    regex_for_multi_line_skip = CppBaseMethods.generate_regex_for_multi_line_skip(
        multi_line_comments=ignore_comments,
        preprocessor_directives=ignore_directives,
        char_literals=ignore_char_str_literals,
        string_literals=ignore_char_str_literals)
    cpp_filename_regex = re.compile(r'^.*(?:\.cc|\.cpp|\.cxx|\.c|\.c\+\+|\.h|\.hpp|\.hh|\.hxx|\.h\+\+)$', re.MULTILINE)
    for file in files:
        try:
            with open(file, 'r') as fp:
                file_content = unicodedata.normalize(unicode_normalization_method, fp.read())
                if mode == 'nesting' and cpp_filename_regex.match(file):
                    result = []
                    for trace in CppBaseMethods.nesting_mode_search(regex, file_content,
                                                                    regex_for_single_line_skip,
                                                                    regex_for_multi_line_skip):
                        str_trace_list = []
                        for s, p in trace:
                            s = repr(normalize_string_regex.sub(' ', s.strip()))[1:-1]
                            str_trace_list.append(f"{file}:{p}\n{indent + s}")
                        if str_trace_list:
                            result.append('\n'.join(str_trace_list))
                    if result:
                        print('\n\n'.join(result), end='\n\n')
                else:  # 'simple'
                    result = []
                    for s, p in CppBaseMethods.simple_mode_search(regex, file_content,
                                                                  regex_for_single_line_skip,
                                                                  regex_for_multi_line_skip):
                        s = repr(normalize_string_regex.sub(' ', s.strip()))[1:-1]
                        result.append(f"{file}:{p}\n{indent + s}")
                    if result:
                        print('\n'.join(result), end='\n\n')
        except BaseException as e:
            if verbose:
                print(file, e, file=sys.stderr)
    if measure_time:
        time_stop = time.monotonic()
        print('Files:', len(files))
        print('Time:', round(time_stop - time_start, 3), 'seconds')


if __name__ == "__main__":
    main()
