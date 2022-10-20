from scikit_build_core.builder.cmake_module_dirs import get_cmake_modules


def test_provide_all_cmake_modules():
    module_dirs = get_cmake_modules()
    assert module_dirs


def test_provide_cmake_modules_select():
    (find_python,) = get_cmake_modules(lambda x: x == "find-python")
    assert find_python.is_dir()
    assert find_python.name == "find_python"
    assert find_python.joinpath("FindPython.cmake").is_file()
    assert find_python.joinpath("FindPython").is_dir()
    assert find_python.joinpath("FindPython/Support.cmake").is_file()


def test_provide_cmake_modules_select_nothing():
    module_dirs = get_cmake_modules(lambda _: False)
    assert len(module_dirs) == 0
