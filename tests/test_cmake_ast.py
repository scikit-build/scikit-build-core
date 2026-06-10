import textwrap
from pathlib import Path

import pytest

from scikit_build_core.ast.ast import ParseError, parse
from scikit_build_core.ast.tokenizer import tokenize
from scikit_build_core.settings.auto_cmake_version import find_min_cmake_version

DIR = Path(__file__).parent.absolute()

FILENAMES = [
    *DIR.joinpath("packages").rglob("**/CMakeLists.txt"),
    *DIR.parent.joinpath("docs/examples").rglob("**/CMakeLists.txt"),
]
IDS = [str(p.relative_to(DIR.parent).parent) for p in FILENAMES]


@pytest.mark.parametrize("filename", FILENAMES, ids=IDS)
def test_cmake_file_parse(filename: Path):
    for x in parse(tokenize(filename.read_text(encoding="utf-8"))):
        assert str(x).startswith(f"{x.name}({x.value})")


def test_cmake_ast_parse():
    txt = textwrap.dedent("""\

        # [[[ Not a block comment
        cmake_minimum_required(VERSION 3.25...3.30)
        # ]]] Not a block comment

        #[[ A block comment
        invalid syntax
        ]]

        if(True)
            block()
                my_function()
            endblock()
        endif()

        """)

    ast = list(parse(tokenize(txt)))

    assert ast[0].name == "cmake_minimum_required"
    assert ast[1].name == "if"
    assert ast[1].contents[0].name == "block"  # type: ignore[attr-defined]
    assert ast[1].contents[0].contents[0].name == "my_function"  # type: ignore[attr-defined]


def test_cmake_ast_parse_long():
    txt = textwrap.dedent(
        """\
        # CMakeLists.txt - Example for Tokenization

        cmake_minimum_required(VERSION 3.10)

        # Set the project name
        project(TokenizationExample VERSION 1.0)

        # Include directories
        include_directories(
            ${PROJECT_SOURCE_DIR}/include
            ${PROJECT_SOURCE_DIR}/external
            [[
            Multiline
            string
            ]]
        )

        # Add executable
        add_executable(TokenizationExample
            src/main.cpp
            src/utils.cpp
        )

        # Set C++ standard
          set(CMAKE_CXX_STANDARD 11)
          set(CMAKE_CXX_STANDARD_REQUIRED True)

        # Link libraries
        target_link_libraries(TokenizationExample
            PUBLIC
            SomeLibrary
            AnotherLibrary
        )

        #[[ Block comment example

        This is a block comment.
        It spans multiple lines.
        It is used to provide more detailed explanations
        or to temporarily disable code.
        ]]

        # Multiline string example
        set(MULTILINE_STRING "This is a multiline string \
        that spans multiple lines. \
        It is often used for setting large chunks of text \
        or configurations.")

        # Multiline function call example
        add_library(MyLibrary
            ${PROJECT_SOURCE_DIR}/src/lib.cpp
            ${PROJECT_SOURCE_DIR}/src/helper.cpp
            ${PROJECT_SOURCE_DIR}/src/another_helper.cpp
        )

        #[==[ Another block comment example

        The following block of code adds a custom target
        and a custom command to run some script.
        It is useful for adding pre-build or post-build steps.

        ]=] and ]] and ]===] can't confuse it.

        function(not real)

        ]==]


        if(DEFINED VALUE)
            add_custom_target(RunScript ALL
                COMMAND ${CMAKE_COMMAND} -E echo "Running custom script"
                COMMAND ${CMAKE_COMMAND} -E touch ${PROJECT_BINARY_DIR}/dummy_file
            ) # trailing comment

            # Set properties for the custom target
            set_target_properties(RunScript PROPERTIES
                COMMENT "This target runs a custom script."
            )
        endif()

        # End of CMakeLists.txt
        """
    )
    for _ in parse(tokenize(txt)):
        pass


@pytest.mark.parametrize(
    "comment",
    [
        "# why not\n",
        "#[[ bracket comment ]]\n",
    ],
)
def test_find_min_cmake_version_with_inner_comment(comment: str) -> None:
    txt = f"cmake_minimum_required(VERSION 3.15 {comment})\n"
    assert find_min_cmake_version(txt) == "3.15"


def test_find_min_cmake_version_with_leading_inner_comment() -> None:
    # A bracket comment swallows leading whitespace; ensure the version token
    # stays separated from the surrounding arguments.
    txt = "cmake_minimum_required(\n  #[[ note ]]\n  VERSION 3.20)\n"
    assert find_min_cmake_version(txt) == "3.20"


def test_unterminated_block_raises_parse_error() -> None:
    # A file ending mid-block must raise a catchable ParseError, not a bare
    # IndexError.
    with pytest.raises(ParseError):
        list(parse(tokenize("if(x)\n")))


def test_missing_open_paren_raises_parse_error() -> None:
    with pytest.raises(ParseError):
        list(parse(tokenize("cmake_minimum_required VERSION 3.15\n")))
