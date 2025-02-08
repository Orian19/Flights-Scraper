from datetime import datetime
from calendar import monthrange
from datetime import date
import time

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium import webdriver

from bs4 import BeautifulSoup

import json
import os

from prettytable import PrettyTable
from tqdm import tqdm
import pyshorteners
from pyshorteners import shorteners

from config.logger_config import configure_logger
import logging

from email.message import EmailMessage
import smtplib
import ssl


class Flights(webdriver.Chrome):
    def __init__(self,  sender, receiver, s_password, subject, body, server='smtp.gmail.com', port=465,
                 driver_path=r"C:\DRIVERS\SeleniumDrivers", cfg_file='flights/cfg.json',
                 teardown=False, loc_from=None, loc_to=None):
        """
        init
        :param driver_path:
        :param cfg_file:
        :param teardown: leave driver open or quit
        :param loc_from:
        :param loc_to:
        """
        self.driver_path = driver_path
        self.teardown = teardown
        self.logger = self.init_logger()
        self.cfg_file = cfg_file
        self.cfg_data = self._load_config()

        # email attributes
        self.sender = sender
        self.receiver = receiver
        self.s_password = s_password
        self.subject = subject
        self.body = body
        self.server = server
        self.port = port

        # runs chrome in the background if enabled
        options = webdriver.ChromeOptions()
        if self.cfg_data['headless']:
            options.add_argument("--headless=new")

        # to ignore warnings when running from cmd
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        os.environ['PATH'] += self.driver_path
        super(Flights, self).__init__(options=options)

        # implicit waiting for elements to load
        self.implicitly_wait(15)

        # main site
        self.site = self.cfg_data['site']

        # locations-default
        if loc_from and loc_to:
            self.loc_from = loc_from
            self.loc_to = loc_to
        else:
            self.loc_from = self.cfg_data['explore']['location']['from']
            self.loc_to = self.cfg_data['explore']['location']['to']

        # errors
        self.f_error_count = 0

        # general info
        self.cities = []
        self.prices = []
        self.dates = []

        self.generic_data = [self.cities, self.dates, self.prices]

        # top info
        self.f_prices_ls = []
        self.f_isFinal_price = []
        self.f_cities_ls = []
        self.f_dates_ls = []
        self.companies_ls = []
        self.times_from_ls = []
        self.times_to_ls = []
        self.deals_link_ls = []

        self.top_data = [self.f_cities_ls, self.f_dates_ls, self.f_prices_ls, self.f_isFinal_price, self.companies_ls,
                         self.times_from_ls, self.times_to_ls, self.deals_link_ls]

    def _load_config(self):
        with open(self.cfg_file) as config_file:
            return json.load(config_file)

    def load_explore_page(self, is_exact=False, duration=None, year=None, month=None,
                          depart_date=None, return_date=None):
        """
        load main explore page to search for flights
        :param is_exact:
        :param duration:
        :param year:
        :param month:
        :param depart_date:
        :param return_date:
        :return:
        """
        stops = self.cfg_data['explore']['filters']['stops']

        if is_exact:
            f_loc_temp = self.cfg_data['explore']['location']['from']
            url = fr"{self.site}/explore/{f_loc_temp}-anywhere/{depart_date},{return_date}"
        else:
            if not duration and not month:
                duration = self.cfg_data['explore']['dates']['range']['duration']
                month = self.cfg_data['explore']['dates']['range']['month']
            if not year:
                year = date.today().year
            month_days = monthrange(year, month)
            month = f'0{month}' if len(str(month)) == 1 else month
            dates_to_explore = self._correct_dates_format(year, month, month_days)

            url = fr"{self.site}/explore/{self.loc_from}-anywhere/{dates_to_explore}\
                                                        \?stops={stops}&tripdurationrange={duration}"

        # navigate to URL
        self.get(url)

    @staticmethod
    def _correct_dates_format(year, month, month_days):
        """
        convert dates format to website format
        :param year:
        :param month:
        :param month_days:
        :return:
        """
        dates = [datetime.fromisoformat(f"{year}-{month}-01"),
                 datetime.fromisoformat(f"{year}-{month}-{month_days[1]}")]
        dates = [dates[0].strftime("%Y%m%d"), dates[1].strftime("%Y%m%d")]
        dates = f"{dates[0]},{dates[1]}"

        return dates

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.teardown:
            self.quit()

    def get_general_flights_info(self, user_mode=False):
        """
        getting the general info about the current cheapest destinations
        :param user_mode:
        :return:
        """
        if user_mode:
            self._modify_locations_to_explore()
            f_xpath = self.cfg_data['xPaths']['specific_flight_xpath']
            price_class = self.cfg_data['xPaths']['specific_price_class']
            city_class = self.cfg_data['xPaths']['specific_city_class']
            date_class = self.cfg_data['xPaths']['specific_date_class']

            flights = self.find_elements(By.XPATH, f_xpath)

        else:
            f_xpath = self.cfg_data['xPaths']['flight_xpath']
            price_class = self.cfg_data['xPaths']['price_class']
            city_class = self.cfg_data['xPaths']['city_class']
            date_class = self.cfg_data['xPaths']['date_class']

            flights = self.find_elements(By.XPATH, f_xpath)

        if not flights:
            self.logger.critical("Bot encountered and error/block, try again later ...")
            return

        # tqdm general
        # TODO: create tqdm objects for the different progress bars (for styling)

        # get general flights info
        print("\n")
        for web_element in tqdm(flights, desc='Gathering General Flights Info: ', colour='cyan', ncols=90):
            element_html = web_element.get_attribute('outerHTML')
            element_soup = BeautifulSoup(element_html, 'html.parser')

            price = element_soup.find("div", {"class": price_class})
            if user_mode:
                city = self.loc_to
            else:
                city = element_soup.find("div", {"class": city_class}).text
            dates = element_soup.find("div", {"class": date_class})

            self.prices.append(price.text.split()[1])
            self.cities.append(city)
            self.dates.append(dates.text)

        print("\n")

    def get_top_flights(self, user_mode=None, carry=None, checked=None):
        """
        getting top flights info for the explored destination/s
        :param user_mode:
        :param carry:
        :param checked:
        :return:
        """
        print("\n")
        for i, city in enumerate(tqdm(self.cities, desc='Finding Top Deals: ', colour='cyan', ncols=100)):
            # select location (in explore page)
            if user_mode:
                curr_cheap_dest_xpath = self.cfg_data['xPaths']['check_flights_xpath']
            else:
                curr_cheap_dest_xpath = self.cfg_data['xPaths']['curr_cheap_dest_xpath']

            self._select_destination_to_explore_by_index(i, curr_cheap_dest_xpath)

            # search flights for that location
            check_flights_xpath = self.cfg_data['xPaths']['check_flights_xpath']
            self._element_click_by_xpath(check_flights_xpath)

            self.implicitly_wait(10)

            # currently opened tabs (=handles)
            handles = self.window_handles
            explore_tab = handles[0]
            cur_flights_tab = handles[1]
            self.switch_to.window(cur_flights_tab)  # switch to 'flights' tab

            self.refresh()
            time.sleep(2)

            # add luggage
            self._add_luggage(carry_on_bag=carry, checked_bag=checked)

            # apply 0 stops
            self._apply_nonstop_flight()

            time.sleep(2)

            # paths
            flight_box_xpath = self.cfg_data['xPaths']['flight_box_xpath']
            flight_boxes = self.find_elements(By.XPATH, flight_box_xpath)
            f_price_class = self.cfg_data['xPaths']['f_price_class']
            f_times_class = self.cfg_data['xPaths']['f_times_class']

            # get flights info
            for element in flight_boxes:
                try:
                    element_html = element.get_attribute('outerHTML')
                except Exception as e:
                    self.logger.exception(f"issue with html element (soup): {e}")
                    self.f_error_count += 1
                    break

                element_soup = BeautifulSoup(element_html, 'html.parser')

                if not element_soup:
                    self.logger.error("Bot encountered and error/block, try again later ...")
                    return

                # check if no carry-on option available on site (maybe only available when booking)
                is_final_price = self._check_if_carry_available(element_soup)

                time_from = element_soup.findAll("div", {"class": f_times_class})[0]
                time_to = element_soup.findAll("div", {"class": f_times_class})[1]
                from_company = time_from.next_sibling
                to_company = time_to.next_sibling
                price = element_soup.findAll("div", {"class": f_price_class})[0]
                link = element_soup.findAll("a", href=True)[0].parent.contents[0].attrs['href']

                link = f"{self.site}{link}"
                link = self._shorten_link(link)

                # checking if the flight company is the same for both directions (if not we skip this flight)
                # this is inorder to get good flights
                if from_company.text != to_company.text:
                    continue
                else:
                    company = from_company

                self.f_prices_ls.append(price.text)
                self.f_isFinal_price.append(is_final_price)
                self.f_cities_ls.append(city)
                self.f_dates_ls.append(self.dates[i])  # from general results
                self.companies_ls.append(company.text)  # from general results
                self.times_from_ls.append(time_from.text)
                self.times_to_ls.append(time_to.text)
                self.deals_link_ls.append(link)

            # close current flights tab
            self.close()

            # go back a page to main explore page with all the results
            self.switch_to.window(explore_tab)
            self.back()

    print("\n")

    def _element_click_by_xpath(self, xpath):
        """
        wait for element to be present and click it
        :param xpath: of the element
        :return:
        """
        WebDriverWait(self, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
        self.find_element(By.XPATH, xpath).click()

    def _element_double_click_by_xpath(self, xpath):
        wait = WebDriverWait(self, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
        ActionChains(self).double_click(wait).perform()

    def _shorten_link(self, link):
        """
        shorten url for convince
        :param link: original url
        :return: shortened link
        """
        shortener_l = pyshorteners.Shortener()
        try:
            link = shortener_l.tinyurl.short(link)
        except Exception as e:
            self.logger.exception(f"\nunsuccessful link shortening: {e}")

        return link

    def _add_luggage(self, carry_on_bag=None, checked_bag=None):
        """
        apply luggage filters - carry-on and checked bags
        :param carry_on_bag:
        :param checked_bag:
        :return:
        """
        if not carry_on_bag and not checked_bag:
            carry_on_bag = self.cfg_data['flight']['luggage']['carry-on_bag']
            checked_bag = self.cfg_data['flight']['luggage']['checked_bag']

        luggage_carry_xpath = self.cfg_data['xPaths']['luggage_carry_xpath']
        luggage_checked_xpath = self.cfg_data['xPaths']['luggage_checked_xpath']

        try:
            # can use _ instead of i (if variable is not used)
            [self._element_click_by_xpath(luggage_carry_xpath) for _ in range(carry_on_bag)]
            [self._element_click_by_xpath(luggage_checked_xpath) for _ in range(checked_bag)]
        except TimeoutException as time_e:
            pass

    def _apply_nonstop_flight(self):
        """
        apply non-stop flight filter
        :return:
        """
        try:
            nonstop_xpath = self.cfg_data['xPaths']['nonstop_xpath']
            WebDriverWait(self, 10).until(EC.presence_of_element_located((By.XPATH, nonstop_xpath)))
            nonstop_element = self.find_element(By.XPATH, nonstop_xpath)
            if not nonstop_element.is_selected():
                nonstop_element.click()
        except Exception as e:
            pass

    def _select_destination_to_explore_by_index(self, index, xpath):
        curr_cheap_dest_xpath = f'{xpath}[{index + 1}]'
        self._element_click_by_xpath(curr_cheap_dest_xpath)

    def _check_if_carry_available(self, element_soup):
        """
        checking if a specific flight really offers a carry-on bag (for pricing considerations)
        :param element_soup:
        :return:
        """
        f_carry_bag_class = self.cfg_data['xPaths']['f_carry_bag_class']
        carry_bag = element_soup.findAll("div", {"class": f_carry_bag_class})[1].text
        if carry_bag == '?':  # TODO: has some issues (sometimes gives 0 when ?)
            return False
        return True

    def create_results_table(self, cols_names, cols_data, title, sort=None):
        """
        creating a results table using prettyTable
        :param cols_names:
        :param cols_data:
        :param title:
        :param sort:
        :return:
        """
        results_table = PrettyTable()
        for i, col in enumerate(cols_names):
            results_table.add_column(col, cols_data[i])

        print(f"\n{title} ({len(cols_data[0])}):\n\n")
        results = results_table.get_string(sortby=sort, sort_key=lambda row: int(row[0].split('$')[-1]))
        print(results)

        self.logger.debug(f"Errors (table={title}): {self.f_error_count}\n")

        return results

    def generate_generic_table(self):
        """
        creating base table with general info
        :return:
        """
        headers = ["City", "Dates", "Starting Price"]
        try:
            self.create_results_table(headers, self.generic_data, "Top Locations - General Results", "Starting Price")
        except Exception as e:
            self.logger.exception(f"issue with creating generic table: {e}")

    def generate_top_deal_table(self):
        """
        creating a table with all the best flights
        :return:
        """
        headers = ["City", "Dates", "Price", "Is Final Price ?", "Company",
                   f"Times: {self.loc_from}-{self.loc_to}", f"Times:{self.loc_to}-{self.loc_from}", "Link to Deal"]

        print("\n\n" + "*" * 100 + "\n")
        try:
            results = self.create_results_table(headers, self.top_data, "Top Flights", sort="Price")
            self.report_results_via_email(results)
        except Exception as e:
            self.logger.exception(f"issue with creating top table: {e}")
        print("\n")

    def _modify_locations_to_explore(self):
        """
        changing departure and return locations according to user input
        :return:
        """
        from_xpath = self.cfg_data['xPaths']['from_xpath']
        to_xpath = self.cfg_data['xPaths']['to_xpath']
        from_loc_drop_down_xpath = self.cfg_data['xPaths']['from_loc_drop_down_xpath']
        to_loc_drop_down_xpath = self.cfg_data['xPaths']['to_loc_drop_down_xpath']
        from_click_drop_xpath = self.cfg_data['xPaths']['from_click_drop_xpath']
        to_click_drop_xpath = self.cfg_data['xPaths']['to_click_drop_xpath']

        # change from location
        self._change_explore_location(from_click_drop_xpath, from_xpath, from_loc_drop_down_xpath, self.loc_from)

        # change to location
        self._change_explore_location(to_click_drop_xpath, to_xpath, to_loc_drop_down_xpath, self.loc_to)

        # submit(=explore options) - redundant
        # submit_xpath = self.cfg_data['xPaths']['submit_xpath']
        # self._element_click_by_xpath(submit_xpath)

    def _change_explore_location(self, click_xpath, loc_xpath, drop_xpath, loc):
        """
        helper method to change locations to explore. changes value in text box
        :param click_xpath:
        :param loc_xpath:
        :param drop_xpath:
        :param loc:
        :return:
        """
        self._element_click_by_xpath(click_xpath)
        element = self.find_element(By.XPATH, loc_xpath)
        while element.get_attribute("value"):
            if 'destination' in loc_xpath:
                element.send_keys(Keys.CONTROL, "a")
                element.send_keys(Keys.DELETE)
            else:
                element.clear()
            time.sleep(0.5)

        # changing location value
        element.send_keys(loc)
        drop_elem = self.find_element(By.XPATH, drop_xpath)

        if (loc != 'anywhere') and (loc != 'EUcg'):
            passed = False
            for _ in range(10):
                try:
                    drop_elem.click()
                    passed = True
                except:
                    pass

                if passed:
                    break

    @staticmethod
    def init_logger(logger_name=__name__):
        """
        initiating logger using helper module
        :param logger_name:
        :return: log instance
        """
        now = datetime.now()
        current_time = now.strftime('%d-%m-%Y_%H-%M-%S')

        logger = configure_logger(logger_name=logger_name, logging_level=logging.DEBUG, print_logging=True,
                                  log_output_path=f'.\\log_files\\flights-log_file-{current_time}.log')

        logger.info("Flights logger initiated ... ")

        return logger

    def report_results_via_email(self, results):
        """
        send table of results via email
        :return:
        """
        em = EmailMessage()
        em['From'] = self.sender
        em['To'] = self.receiver
        em['Subject'] = self.subject
        em.set_content(f"{self.body}\n\n{results}")

        context = ssl.create_default_context()

        self.logger.info("sending results via email")
        with smtplib.SMTP_SSL(self.server, self.port, context=context) as smtp:
            smtp.login(self.sender, self.s_password)
            smtp.sendmail(self.sender, self.receiver, em.as_string())
