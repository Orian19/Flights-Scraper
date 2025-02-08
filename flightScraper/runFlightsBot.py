from config.email_config import *

from config.logger_config import configure_logger
import logging

from flights.flights import Flights

from datetime import datetime
import uuid
import os


def init_logger(logger_name=__name__):
    """
    intimating logger using logging_config module
    :param logger_name:
    :return: log object
    """
    now = datetime.now()
    current_time = now.strftime('%d-%m-%Y_%H-%M-%S')

    base_dir = os.path.dirname(os.getcwd())
    if 'flightScraper' in base_dir.split('/')[-1]:
        os.chdir(base_dir)
    if not os.path.exists(f'.\\log_files'):
        os.makedirs(f'.\\log_files')

    log = configure_logger(logger_name=logger_name, logging_level=logging.DEBUG, print_logging=True,
                           log_output_path=f'.\\log_files\\bot-log_file-{current_time}.log')

    log.info("Logger initiated ... ")

    return log


def get_inputs(log=None):
    """
    getting inputs for flights search
    :param log:
    :return: inputs
    """
    log.info("getting user input")

    from_loc = input("From (format=city): ")
    to_loc = input("To (format=city): ")
    carry_on = int(input("Carry-on bag (0/1): "))
    checked_bag = int(input("Checked bag: "))
    date_format = input("Exact dates? (y/n): ")

    if date_format == 'y':
        depart_date = int(input("Departure date (format=yyyymmdd): "))
        return_date = int(input("Return date (format=yyyymmdd): "))
        return from_loc, to_loc, carry_on, checked_bag, depart_date, return_date, date_format
    else:
        duration = input("Duration (format=d,d(ex. 5,10)): ")
        year = int(input("Year (format=yyyy): "))
        month = int(input("Month (format=m(ex. 9 for sept.)): "))
        return from_loc, to_loc, carry_on, checked_bag, duration, year, month, date_format


def main():
    # logging setup
    logger = init_logger()

    # creates a random uuid(universally unique identifier)
    print(f"{uuid.uuid4()}\n")

    inputs = [None, None, None, None, None, None, None, None]
    is_default = input("Use default configuration ? (y/n): ") == 'y'
    print("\n")
    if not is_default:
        inputs = get_inputs(logger)

    # running flights bot
    try:
        results_receiver = input("\nEmail (to receive results): ")

        logger.info("creating a bot instance")
        print("\nloading driver...")

        with Flights(sender=email_sender, receiver=results_receiver, s_password=email_pass, subject="Flights Bot",
                     body="Today's Results: ", teardown=True, loc_from=inputs[0], loc_to=inputs[1]) as flightsBot:
            if inputs[-1] == 'y':
                flightsBot.load_explore_page(is_exact=True, depart_date=inputs[4], return_date=inputs[5])
            else:
                flightsBot.load_explore_page(duration=inputs[4], year=inputs[5], month=inputs[6])
            flightsBot.get_general_flights_info(user_mode=not is_default)
            flightsBot.generate_generic_table()
            flightsBot.get_top_flights(user_mode=not is_default, carry=inputs[2], checked=inputs[3])
            flightsBot.generate_top_deal_table()
            logger.info("Bot process finished.")
            print("Exiting ...")
    except Exception as e:
        logger.error("unsuccessful run")
        if "in PATH" in str(e):
            logger.exception("issue with selenium driver")
            print(
                "Trying to run FlightsBot from cmd \n"
                "Need to add Selenium Driver to PATH n\n"
                "run: set PATH=%PATH%;C:your-path\\ \n"
            )
        else:
            logger.exception("other error")
            print(f"\n Error: {e}")


if __name__ == "__main__":
    main()
