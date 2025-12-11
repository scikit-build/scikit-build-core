from importlib.resources import files

def get_static_data():
    return files().joinpath("static_data").read_text().rstrip()
