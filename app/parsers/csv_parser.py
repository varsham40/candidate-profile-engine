import pandas as pd

from parsers.base_parser import BaseParser
from models.parser import ParserOutput
from utils.logger import logger
from utils.exceptions import ParserError


class CSVParser(BaseParser):

    def parse(self, file_path: str) -> ParserOutput:
        try:
            logger.info(f"Parsing CSV file: {file_path}")

            df = pd.read_csv(file_path).fillna('')

            records = df.to_dict(orient="records")

            return ParserOutput(
                source="recruiter_csv",
                source_type="structured",
                content=records
            )

        except Exception as e:
            logger.error(f"CSV parsing failed: {str(e)}")
            raise ParserError(str(e))
