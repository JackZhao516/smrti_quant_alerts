import os
import tempfile
import unittest

from smrti_quant_alerts.pdf_api import PDFApi
from smrti_quant_alerts.data_type import StockSymbol


class TestPDFApi(unittest.TestCase):
    def setUp(self) -> None:
        self._original_cwd = os.getcwd()
        self._temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self._temp_dir.name)
        self.pdf_api = PDFApi("test.pdf")

    def tearDown(self) -> None:
        os.chdir(self._original_cwd)
        self._temp_dir.cleanup()

    def test_file_name(self) -> None:
        self.assertEqual(self.pdf_api.file_name, "test.pdf")

    def test_default_file_name(self) -> None:
        self.assertEqual(PDFApi().file_name, "output.pdf")

    def test_start_new_pdf(self) -> None:
        self.pdf_api.start_new_pdf("next.pdf")

        self.assertEqual(self.pdf_api.file_name, "next.pdf")
        self.assertEqual(self.pdf_api._tmp_file_name, "next.pdf.txt")
        self.assertEqual(self.pdf_api._old_file_names, ["test.pdf"])

    def test_append_text(self) -> None:
        self.pdf_api.append_text("test")
        with open(self.pdf_api._tmp_file_name, encoding="utf-8") as f:
            self.assertEqual(f.read(), "\n\n\n\ntest\n\n\n\n\n\n")

    def test_append_stock_info(self) -> None:
        self.pdf_api.append_stock_info(StockSymbol("TEST", "Test"), ["test1", "test2"])
        with open(self.pdf_api._tmp_file_name, encoding="utf-8") as f:
            self.assertEqual(f.read(), "TEST  Test\ntest1\ntest2\n\n\n\n\n")

    def test_save_pdf(self) -> None:
        self.pdf_api.append_text("test")
        self.pdf_api.save_pdf()
        self.assertTrue(os.path.exists(self.pdf_api._file_name))

    def test_save_pdf_empty_file(self) -> None:
        self.pdf_api.append_text("")
        self.pdf_api.save_pdf()
        self.assertTrue(os.path.exists(self.pdf_api._file_name))

    def test_save_pdf_no_file(self) -> None:
        self.pdf_api.save_pdf()
        self.assertTrue(os.path.exists(self.pdf_api._file_name))

    def test_delete_pdf(self) -> None:
        self.pdf_api.append_text("test")
        self.pdf_api.save_pdf()
        self.assertTrue(os.path.exists(self.pdf_api._file_name))
        self.pdf_api.delete_pdf()
        self.assertFalse(os.path.exists(self.pdf_api._file_name))
        self.assertFalse(os.path.exists(self.pdf_api._tmp_file_name))
