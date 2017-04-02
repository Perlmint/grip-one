from os.path import join, exists
from urllib.parse import unquote, urlparse
from queue import Queue

from bs4 import BeautifulSoup
from grip import render_page

def is_absolute(url):
	return bool(urlparse(url).netloc)

def render_all(root, entry, option):
	pages = set(entry)
	render_queue = Queue()
	render_queue.put(entry)

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
			body, links = render(root, page, option)
		except Exception as e:
			raise Exception("Error occured while processing {0} - {1}".format(page, e))
		full_article.body.append(body)
		for link in links:
			# already processed
			if link in pages:
				continue

			# ignore heading
			if link.startswith("#"):
				continue

			# ignore non-md files
		# ex) images
			if not link.endswith(".md"):
				continue

			# ignore absolute url
			if is_absolute(link):
				continue

			# not existing file...
			if not exists(join(root, link)):
				raise Exception("{0} is not exists! broken link exists in {1}".format(link, page))

			pages.add(link)
			render_queue.put(link)

	return full_article

def render(root, page, option):
	rendered_page = render_page(join(root, page), **option)
	soup = BeautifulSoup(rendered_page, "lxml")
	page_body = soup.article
	all_links = page_body.find_all("a")
	return page_body, [unquote(link.get("href")) for link in all_links]
