import os
from typing import Iterable

from fpdf import FPDF

from smrti_quant_alerts.data_type import StockSymbol


class PDFApi:
    PWD = os.path.dirname(__file__)

    def __init__(self, file_name: str = None) -> None:
        if file_name is None:
            file_name = "output.pdf"
        self._file_name = file_name
        self._tmp_file_name = f"{file_name}.txt"

    @property
    def file_name(self) -> str:
        return self._file_name

    def start_new_pdf(self, file_name: str) -> None:
        """
        Start a new pdf

        :param file_name: file name
        """
        self.delete_pdf()
        self._file_name = file_name
        self._tmp_file_name = f"{file_name}.txt"

    def append_text(self, text: str) -> None:
        """
        Append text to pdf

        :param text: text
        """
        with open(self._tmp_file_name, "a", encoding="utf-8") as f:
            f.write(f"\n\n\n\n{text}\n\n\n\n\n\n")

    def append_stock_info(self, stock: StockSymbol, info: Iterable[str]) -> None:
        """
        Append stock info to pdf

        :param stock: stock symbol
        :param info: stock info
        """
        with open(self._tmp_file_name, "a", encoding="utf-8") as f:
            f.write(f"{stock.ticker}  {stock.security_name}\n")
            for i in info:
                f.write(f"{i}\n")
            f.write("\n\n\n\n")

    def save_pdf(self) -> None:
        """
        Save pdf
        """
        pdf = FPDF(format="letter")
        pdf.add_page()
        pdf.add_font(fname=os.path.join(self.PWD, 'DejaVuSansCondensed.ttf'))
        pdf.set_font("DejaVuSansCondensed", size=12)
        # pdf.add_font(fname='unifont.ttf')
        # pdf.set_font("unifont", size=12)
        if not os.path.exists(self._tmp_file_name):
            pdf.multi_cell(0, 5, txt="")
        else:
            prev_line = ""
            with open(self._tmp_file_name, "r", encoding="utf-8") as f:
                for line in f:
                    if line == "\n" and prev_line != "\n":
                        prev_line = line
                        continue
                    pdf.multi_cell(0, 5, text=line)
                    prev_line = line
        pdf.output(self._file_name)
        if os.path.exists(self._tmp_file_name):
            os.remove(self._tmp_file_name)

    def delete_pdf(self) -> None:
        """
        Delete pdf
        """
        if os.path.exists(self._file_name):
            os.remove(self._file_name)
