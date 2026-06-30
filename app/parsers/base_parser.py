from abc import ABC, abstractmethod
from models.parser import ParserOutput


class BaseParser(ABC):

    @abstractmethod
    def parse(self, file_path: str) -> ParserOutput:
        pass
