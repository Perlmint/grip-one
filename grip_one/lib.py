""" grip-one implementation """
import mimetypes
from hashlib import sha256
from tempfile import gettempdir
from os import stat, mkdir, makedirs
from os.path import join, exists, dirname
from urllib.parse import unquote, urlparse
from queue import Queue
from pickle import dump, load

from bs4 import BeautifulSoup
from grip import render_page

from .util import embed_image

mimetypes.init()

def is_absolute(url):
	""" check url is absolute """
	return bool(urlparse(url).netloc)

def page_to_bookmark(page_name):
	""" modify page name to bookmark name """
	return "page-{0}".format(page_name)

def equal_dict(dict1, dict2):
	""" dictionary equality checker """
	key1, key2 = dict1.keys(), dict2.keys()

	if key1 != key2:
		return False

	for key in key1:
		if dict1[key] != dict2[key]:
			return False

	return True

class Renderer:
	""" single page html renderer """
	def __init__(self, root, entry, option):
		self.root = root
		self.entry = entry
		self.cache_root = join(gettempdir(), sha256(root.encode("utf-8")).hexdigest())
		if not exists(self.cache_root):
			mkdir(self.cache_root)
		self.grip_option = option["grip"]
		del option["grip"]
		self.option = option
		self.login = option["login"]
		del self.option["login"]

		self.invalid_cache = False
		cache_option_path = join(self.cache_root, ".grip-one-option")
		if exists(cache_option_path):
			with open(cache_option_path, "rb") as prev_option_file:
				loaded_option = load(prev_option_file)
			if not equal_dict(self.option, loaded_option):
				self.invalid_cache = True
		with open(cache_option_path, "wb") as new_option_file:
			dump(self.option, new_option_file)

		self.pages = set(self.entry)
		self.render_queue = Queue()
		self.render_queue.put(self.entry)

		self.full_article = BeautifulSoup("""<html>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width: 1280, initial-scale=1" />
    <style> body { width: 980px; margin-left: auto; margin-right: auto; } </style>
    <title></title>
  </head>
  <body>
  </body>
</html>""", "lxml")

	def append_css(self, head):
		""" append custom css """
		for css in self.option["css"]:
			csslink = self.full_article.new_tag("link")
			csslink["href"] = css
			csslink["rel"] = "stylesheet"
			head.append(csslink)

	def modify_single_page(self, page, body, links):
		""" modify single page to merged into one page """
		body.h1.a["id"] = page_to_bookmark(page)
		if page == self.entry:
			self.full_article.title.append(
				"".join([s for s in body.h1.strings]).strip()
			)
		for link in links:
			href = unquote(link.get("href"))
			# ignore heading
			if href.startswith("#"):
				continue

			# ignore non-md files
		# ex) images
			if not href.endswith(".md"):
				continue

			# ignore absolute url
			if is_absolute(href):
				continue

			# modify anchor to bookmark
			link["href"] = "#{0}".format(page_to_bookmark(href))

			# already processed
			if href in self.pages:
				continue

			# not existing file...
			if not exists(join(self.root, href)):
				raise Exception("{0} is not exists! broken link exists in {1}".format(link, page))

			self.pages.add(href)
			self.render_queue.put(href)

	def render_all(self):
		""" render all markdown files """
		head = self.full_article.head
		self.append_css(head)
		assets = set()

		while not self.render_queue.empty():
			page = self.render_queue.get()
			try:
				body, links, imgs = self.render(page)
				for img in imgs:
					assets.add(img)
			except Exception as error:
				raise Exception("Error occured while processing {0} - {1}".format(page, error))
			self.modify_single_page(page, body, links)
			self.full_article.body.append(body)

		return self.full_article, assets

	def render(self, page):
		""" render single page """
		path = join(self.root, page)
		path_dir = dirname(path)
		cache_path = join(self.cache_root, page)

		def should_build():
			""" check this page should build? """
			if not self.invalid_cache and exists(cache_path):
				src_mtime = stat(path).st_mtime
				cache_mtime = stat(cache_path).st_mtime
				return cache_mtime < src_mtime
			return True

		def build_or_cache():
			""" get html which built or cached """
			if should_build():
				if not self.grip_option["username"] and self.login:
					login_info = self.login()
					self.grip_option.update(login_info)
				rendered_page = render_page(path, **self.grip_option)
				soup = BeautifulSoup(rendered_page, "lxml")

				if soup.article is None:
					raise Exception(soup.h1.get_text())

				if self.option["embed_img"]:
					for img in soup.find_all("img"):
						img_src = unquote(img["src"])
						__img = embed_image(path_dir, img_src)
						img["src"] = __img["src"]
						img["alt"] = __img["alt"]

				if not exists(dirname(cache_path)):
					makedirs(dirname(cache_path))
				with open(cache_path, "w") as cache_file:
					cache_file.write(str(soup))
			else:
				with open(cache_path, "r") as prev_cache_file:
					soup = BeautifulSoup(prev_cache_file, "lxml")
			return soup
		soup = build_or_cache()

		imgs = []
		if not self.option["embed_img"]:
			for img in soup.find_all("img"):
				if img["src"].startswith("data:"):
					continue
				imgs.append(join(path_dir, unquote(img["src"])))

		page_body = soup.article
		all_links = page_body.find_all("a")
		return page_body, [link for link in all_links], imgs
