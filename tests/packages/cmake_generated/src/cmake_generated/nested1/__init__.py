from importlib.resources import read_text


def get_static_data():
    return read_text("cmake_generated.nested1", "static_data").rstrip()
