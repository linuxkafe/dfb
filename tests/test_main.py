"""Sample test for AES project."""

from src.main import main


def test_main_output(capsys):
    """Test that main() prints expected output."""
    main()
    captured = capsys.readouterr()
    assert "Hello from AES project!" in captured.out


def test_version():
    """Test version is defined."""
    from src import __version__
    assert __version__ == "0.1.0"