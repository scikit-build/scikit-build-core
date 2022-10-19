from scikit_build_core.builder.cmake_module_dirs import provide_cmake_modules


def test_provide_all_cmake_modules():
    with provide_cmake_modules() as module_dirs:
        assert module_dirs


def test_provide_cmake_modules_select():
    with provide_cmake_modules(lambda x: x == "find-python") as module_dirs:
        (find_python,) = module_dirs
        assert find_python.is_dir()
        assert find_python.name == "find_python"
        assert find_python.joinpath("FindPython.cmake").is_file()
        assert find_python.joinpath("FindPython").is_dir()
        assert find_python.joinpath("FindPython/Support.cmake").is_file()


def test_provide_cmake_modules_select_nothing():
    with provide_cmake_modules(lambda _: False) as module_dirs:
        assert len(module_dirs) == 0
