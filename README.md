# Cpp-Searcher

Application to search for strings containing a substring or matching a regular expression with C++ hints.

Search is always carried out in all files.  
However, it is for C++ files additional hints are displayed (in which namespace/class/function/loop...).

## Example

Search for "item.second->unload()" in the [rttr](https://github.com/rttrorg/rttr) library:

```
python app.py --mode nesting --paths rttr\src\ --text "item.second->unload()" --flags m -id -ic -icsl -mt
```

As a result, we get the location of the substring we are looking for.

```
rttr\src\rttr\library.cpp:34-199
    namespace rttr
rttr\src\rttr\library.cpp:37-107
    namespace detail
rttr\src\rttr\library.cpp:46-106
    class library_manager
rttr\src\rttr\library.cpp:90-101
    void clean_all_libs()
rttr\src\rttr\library.cpp:92-100
    for (auto& item : m_library_map)
rttr\src\rttr\library.cpp:95-99
    if (item.second.use_count() == 1)
rttr\src\rttr\library.cpp:98:21-42
    item.second->unload();

Files: 328
Time: 1.453 seconds
```


## Usage

```
usage: app [-h] [-m MODE] -p PATHS [PATHS ...] (-t TEXT | -r REGEX) [-f FLAGS]
           [-ic] [-id] [-icsl] [-mt] [-v] [--debug-args]

C++ code searcher

options:
  -h, --help            show this help message and exit
  -m MODE, --mode MODE  app mode:
                        `simple` - search for occurrences (default)
                        `nesting` - search for occurrences with nesting
  -p PATHS [PATHS ...], --paths PATHS [PATHS ...]
                        paths to dirs/files [example: `/path/to/dir /path/to/file`]
  -t TEXT, --text TEXT  plain text for search [example: `ab`]
  -r REGEX, --regex REGEX
                        python-regex for search [example: `"a.*?b"`]
  -f FLAGS, --flags FLAGS
                        flags:
                        A (ASCII-only matching),
                        I (ignore case),
                        L (locale dependent),
                        M (multi-line),
                        S (dot matches all),
                        U (Unicode matching)
                        [example: `AILMSU` or `ailmsu`]
  -ic, --ignore-comments
                        Ignore comments
  -id, --ignore-directives
                        Ignore preprocessing directives
  -icsl, --ignore-char-str-literals
                        Ignore char and string literals
  -mt, --measure-time   Measure program runtime
  -v, --verbose         Verbose mode
  --debug-args          Debug mode (only shows converted arguments)
```






