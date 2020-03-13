# https://github.com/Anamemnon/CrazyPython/blob/master/tours.py

from urllib.request import urlopen
from bs4 import BeautifulSoup
import re
"""
Поиск дешевых туров на сайте https://www.turcentr.by/pob.php
"""


def get_all_prices():
    return bsobj.findAll(text=re.compile("""
                                           ^(\d\s)?         # Если цена 4-значная, ищем цифру за которой следует пробел
                                            \d{3}           # Оставшаяся целая часть числа - 3 цифры, до знака запятой
                                            ,               # Разделитель между целой и дробной частью
                                            \d{2}           # Дробная часть числа, как правило, 2 ноля -> 00
                                            \sр.$           # После цены стоит пробел, русская буква р и точка
                                           """,
                                         re.VERBOSE)
                         )


def get_countries():
    return bsobj.findAll('p', {'class': 'r_title'})


def clear_price(price):
    """
    Example: 1 584,00 р. -> 1584    
    """
    cut_zeros = slice(-2)
    return price.replace(' ', '').replace(',', '').rstrip('р.')[cut_zeros]


def get_min_prices(prices):
    tour_min_price = slice(2, None, 3)
    return [clear_price(price) for price in prices[tour_min_price]]


def print_best_tours(countries, prices, desired_price=900):
    country_width = 10
    price_width = 4
    for country, min_price in sorted(zip(countries, prices), key=lambda x: x[-1]):
        if int(min_price) <= desired_price:
            print(
                f'{country.get_text():{country_width}} {min_price:{price_width}} р.')


if __name__ == "__main__":
    html = urlopen('https://www.turcentr.by/pob.php')
    bsobj = BeautifulSoup(html)
    prices = get_all_prices()
    prices = get_min_prices(prices)
    countries = get_countries()
#    desired_price = input('Введите желаемую цену тура: ')
    print_best_tours(countries, prices)
