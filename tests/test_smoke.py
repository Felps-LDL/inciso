from importlib.metadata import version

import inciso


def test_pacote_instalado() -> None:
    assert inciso.__name__ == "inciso"
    assert version("inciso") == "9.9.9"
