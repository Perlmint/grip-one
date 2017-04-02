from hashlib import sha256
from tempfile import gettempdir
from os import stat, mkdir, makedirs
from os.path import join, exists, dirname
from urllib.parse import unquote, urlparse
from queue import Queue

from bs4 import BeautifulSoup
from grip import render_page

def is_absolute(url):
	return bool(urlparse(url).netloc)

def page_to_bookmark(page_name):
	return "page-{0}".format(page_name)

class Renderer:
	def __init__(self, root, entry, option):
		self.root = root
		self.entry = entry
		self.option = option
		self.cache_root = join(gettempdir(), sha256(root.encode("utf-8")).hexdigest())

	def render_all(self):
		if not exists(self.cache_root):
			mkdir(self.cache_root)

		pages = set(self.entry)
		render_queue = Queue()
		render_queue.put(self.entry)

		full_article = BeautifulSoup("""<html>
  <head>
    <meta charset="UTF-8" />
    <title></title>
  </head>
  <body>
  </body>
</html>""", "lxml")

		while not render_queue.empty():
			page = render_queue.get()
			try:
				body, links = self.render(page)
			except Exception as e:
				raise Exception("Error occured while processing {0} - {1}".format(page, e))
			body.h1.a["id"] = page_to_bookmark(page)
			if page == self.entry:
				full_article.title.append(
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
				if href in pages:
					continue

				# not existing file...
				if not exists(join(self.root, href)):
					raise Exception("{0} is not exists! broken link exists in {1}".format(link, page))

				pages.add(href)
				render_queue.put(href)
			full_article.body.append(body)

		return full_article

	def render(self, page):
		path = join(self.root, page)
		cache_path = join(self.cache_root, page)
		build = True

		if exists(cache_path):
			src_mtime = stat(path).st_mtime
			cache_mtime = stat(cache_path).st_mtime
			build = cache_mtime < src_mtime

		if build:
			rendered_page = render_page(path, **self.option)
			soup = BeautifulSoup(rendered_page, "lxml")
			makedirs(dirname(cache_path))

			if soup.article is None:
				raise Exception(soup.h1.get_text())
			with open(cache_path, "w") as f:
				f.write(rendered_page)
		else:
			with open(cache_path, "r") as f:
				soup = BeautifulSoup(f, "lxml")

		page_body = soup.article
		all_links = page_body.find_all("a")
		return page_body, [link for link in all_links]
