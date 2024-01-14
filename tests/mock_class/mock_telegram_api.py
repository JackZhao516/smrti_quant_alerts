from typing import List, Any


class MockTelegramBot:
    def __init__(self, tg_type: str = "CG_ALERT", daemon: bool = True) -> None:
        """
        TelegramBot class for sending message to telegram group via bot

        send_message(msg, blue_text=False) is the main method for sending message
        stop() should be called explicitly to stop TelegramBot


        ::param alert_type: "CG_ALERT", "CG_SUM", "TEST", "VOLUME", "PRICE", etc.
        ::param daemon: True if letting the TelegramBot handle the 20 msg/min limit,
                        False if you want to handle the limit yourself

        """
        pass

    def send_message(self, message: str, blue_text: bool = False) -> None:
        """
        send message to telegram group

        :param message: message to send
        :param blue_text: True if you want to send message in blue text

        """
        pass

    def send_file(self, file_path: str, output_file_name: str) -> Any:
        """
        send file to telegram group

        :param file_path: path of the file to send
        :param output_file_name: output name of the sent file
        """
        pass

    def send_data_as_csv_file(self, output_file_name: str, headers: List[str], data: List[List[Any]]) -> Any:
        """
        send data as csv file to telegram group

        :param output_file_name: output name of the sent file
        :param headers: headers of the csv file
        :param data: data of the csv file
        """
        pass
