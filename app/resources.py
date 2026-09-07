from importlib.resources import files
from pathlib import Path


FIXTURES = (files("ava_jargon.fixtures") if __package__ == "ava_jargon"
            else Path(__file__).resolve().parents[1] / "fixtures")
