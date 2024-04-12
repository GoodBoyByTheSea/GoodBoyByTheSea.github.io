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


class OtterScraper:
    def __init__(self):
        self.base_url = f"https://vod.deviantotter.com/?p="
        self.max_pages = 18
        # self.max_pages = 2
        self.scenes = {}
        self.path = os.path.dirname(os.path.realpath(__file__))
        self.scenes_file = 'scenes'
        self.load_scenes()

    def load_scenes(self):
        for n in range(1, self.max_pages + 1):
            self.load_scenes_page(n)

    def load_scenes_page(self, n):
        path = os.path.join(self.path, self.scenes_file)
        file = f'{path}{str(n)}.json'
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                self.scenes.update(json.load(f))
            return True
        return False

    def save_scenes(self):
        with open(os.path.join(self.path, self.scenes_file), 'w', encoding='utf-8') as f:
            json.dump(self.scenes, f, ensure_ascii=False, indent=4)

    def save_scenes_page(self, n, scenes):
        path = os.path.join(self.path, self.scenes_file)
        file = f'{path}{str(n)}.json'
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(scenes, f, ensure_ascii=False, indent=4)

    def get_otter_page(self, n=1):
        url = self.base_url + str(n)
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        return soup

    @staticmethod
    def clean_title(title):
        title = title.replace("trailer", "")
        title = title.replace("Trailer", "")
        title = title.strip()
        return title

    @staticmethod
    def get_description(video):
        l = 0
        description = ''
        for i in video.find_all('p'):
            if len(i.text) > l:
                description = i.text
                l = len(description)
        return description

    @staticmethod
    def get_image(video):
        img = None
        if video.find(class_='imageGallery'):
            if video.find(class_='imageGallery').find_all('a'):
                img = video.find(class_='imageGallery').find_all('a')[0]['href']
        return img

    def scrape_page(self, n=1, overwrite=False):
        if not overwrite:
            if self.load_scenes_page(n):
                return self.scenes

        soup = self.get_otter_page(n=n)
        videos = soup.find_all("div", class_="videoItem")
        ret = {}
        for video in videos:
            title = video.find("h2").text
            title = self.clean_title(title)
            description = OtterScraper.get_description(video)
            img = OtterScraper.get_image(video)
            ret[title.lower()] = {'title': title,
                                  'details': description,
                                  'image': img,
                                  'url': self.base_url + str(n)}
        self.scenes.update(ret)
        self.save_scenes_page(n=n, scenes=ret)
        return self.scenes

    def find_video(self, title):
        posts = {}
        title = self.clean_title(title)
        title = title.lower()
        if title in self.scenes:
            return self.scenes[title]
        return posts


def search_scene(name):
    s = OtterScraper()
    ret = s.find_video(title=name)
    return ret


# read the input
i = read_json_args()
logger.debug(f'Input is: {i}')
try:
    ret = {}
    title = i['title']
    pattern = '(?P<code>[\d]{3})? (?P<title>.*)'
    m = re.match(pattern, title)
    if m is not None:
        code = m.group('code')
        title = m.group('title')
        ret['code'] = code
        logger.debug(f'code updated to {code}')
        ret['title'] = m.group('title')
        logger.debug(f'title updated to {title}')

    result = search_scene(title)
    if result:
        logger.debug(f'Scene found: {result}')
    else:
        logger.debug(f'No scene found for {title}')
    ret.update(result)
    if not ret:
        ret['code'] = f'{title} not found'
    logger.debug(f'Returning: {ret}')
    print(json.dumps(ret))
except Exception as e:
    debug_print(str(e))
#
#
# if __name__ == '__main__':
#     path = r'C:\Personal\Porn\Stash\scrapers\community\DeviantOtter'
#     scenes_file = 'scenes.json'
#     s = OtterScraper()
#
#     title = 'Human Urinal and Cum Dumpster'
#     # title = 'A Proper Dicking Trailer'
