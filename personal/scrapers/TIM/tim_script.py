import requests
from bs4 import BeautifulSoup
import os
import json
import sys
import logging
import re

PATH = os.path.dirname(os.path.realpath(__file__))
log_file = os.path.join(PATH, 'log.log')
logger = logging.getLogger(__name__)
logging.basicConfig(filename=log_file, encoding='utf-8', level=logging.DEBUG)


def read_json_args():
    input = sys.stdin.read()
    return json.loads(input)


def debug_print(t):
    sys.stderr.write(t + "\n")


class Scraper:
    def __init__(self, url):
        self.url = url

    def get_page(self):
        url = self.url
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        return soup

    @staticmethod
    def clean_title(title):
        return title

    @staticmethod
    def get_name(profile):
        name = profile.find('h3', class_='text-center').text.strip()
        return name

    @staticmethod
    def get_image(profile):
        img = None
        if profile.find_all(class_='field-type-image'):
            img = profile.find_all(class_='field-type-image')[0].find_all('a')[0]['href']
        return img

    @staticmethod
    def get_twitter(soup):
        try:
            return soup.find(class_='sociallinks-href')['href']
        except:
            pass

    @staticmethod
    def get_details(soup):
        details_dict = {}
        description = ''
        details = soup.find(id='content-description').find_all('li')
        try:
            description = soup.find_all(class_='field-name-body')[0].text
        except:
            pass

        for detail in details:
            details_dict[detail.contents[2].strip()] = detail.contents[1].text
        field_names = {'Eye color': 'eyecolor',
                       'Hair color': 'haircolor',
                       'Ethnicity': 'ethnicity',
                       'Height': 'height',
                       'Weight': 'weight',
                       }
        ret = {}
        details_field = []
        for k, v in details_dict.items():
            if k in field_names:
                ret[field_names[k]] = str(v)
            else:
                details_field.append(f'{k}: {v}')
                ret[k.lower()] = str(v)
        if description:
            details_field.append(description)
        if details_field:
            ret['details'] = '\n'.join(details_field)

        return ret

    @staticmethod
    def fix_weight(weight_lbs):
        weight_kg = float(weight_lbs) * 0.45359237
        return str(int(weight_kg))

    @staticmethod
    def fix_height(height_string):
        def feet_inches_to_cm(feet, inches):
            total_inches = int(feet) * 12 + int(inches)
            total_cm = total_inches * 2.54
            return total_cm
        m = re.match(r'(?P<feet>\d). (?P<inches>\d{1,2})', height_string)
        if m is not None:
            feet = m.groupdict().get('feet')
            inches = m.groupdict().get('inches')
            height_cm = feet_inches_to_cm(feet=feet, inches=inches)
            height_cm = str(int(height_cm))
            return height_cm


    def scrape(self):
        soup = self.get_page()
        profile = soup.find("div", class_="model-profile")
        name = self.get_name(profile)
        image = self.get_image(profile)
        details = self.get_details(soup)
        ret = {'name': name, 'image': image, 'gender': 'male'}
        twitter = self.get_twitter(soup)
        if twitter is not None:
            ret['twitter'] = twitter
        ret.update(details)
        if 'height' in ret:
            ret['height'] = self.fix_height(ret['height'])
        if 'weight' in ret:
            ret['weight'] = self.fix_weight(ret['weight'])

        return ret


"""
Name
Gender
URL
Twitter
Instagram
Birthdate
DeathDate
Ethnicity

Country
HairColor
EyeColor
Height
Weight
Measurements
FakeTits
CareerLength
Tattoos
Piercings
Aliases
Tags (see Tag fields)
Image
Details
"""

try:
    # read the input
    i = read_json_args()
    logger.debug(f'Input is: {i}')
    url = i['url']
    s = Scraper(url)
    ret = s.scrape()
    logger.debug(f'Returning: {ret}')
    print(json.dumps(ret))
except Exception as e:
    debug_print(str(e))

if __name__ == '__main__':
    url = 'https://men.treasureislandmedia.com/men/17368'