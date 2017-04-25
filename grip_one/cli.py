"""
CLI implementation
"""
from argparse import ArgumentParser
from getpass import getpass
from shutil import copy2
from sys import stdout
from os import linesep, getcwd
from os.path import relpath, join, splitext, dirname, exists

from pdfkit import from_string
import requests

from .lib import Renderer
from .util import embed_image

MAIN_DEFAULT_CSS = "https://sindresorhus.com/github-markdown-css/github-markdown.css"

def create_argparser():
	"""
	create argparser for grip-one cli
	"""
	parser = ArgumentParser(description="Make single html page from Markdown repo")
	parser.add_argument(
		"repo_root",
		help="Repository root to render")
	parser.add_argument(
		"--entry",
		default="README.md",
		help="custom entry md file")
	parser.add_argument(
		"--offline",
		action="store_true",
		help="use offline mode")
	parser.add_argument(
		"--out",
		default="-",
		help="where to out - available etension is html or pdf")
	parser.add_argument(
		"--login",
		action="store_true",
		help="login github to extend API limit")
	parser.add_argument(
		"--embed",
		action="store_true",
		help="embed images into html in base64 form")
	parser.add_argument(
		"--pdf",
		choices=["disable", "pdfkit"],
		default="disable",
		help="Select backend to use for making pdf")
	parser.add_argument(
		"--maincss",
		default="default",
		help="main css for result - default makes result that look like github markdown view")
	parser.add_argument(
		"--css",
		default=[],
		nargs="*",
		help="additional css")
	parser.add_argument(
		"--cover",
		default=None,
		help="cover image")
	return parser

def validate_args(args):
	"""
	validate parsed args
	"""
	ext = splitext(args.out)[1]
	if args.out == "-" and not args.embed:
		raise Exception("non embedded image option is not allowed with stdout option")

	if args.pdf == "disable" and ext != ".html":
		if ext == "":
			args.out += ".html"
		else:
			raise Exception("html out mode is enabled! out filename should have .html extension")

	if args.pdf != "disable" and ext != ".pdf":
		if ext == "":
			args.out += ".pdf"
		else:
			raise Exception("pdf out mode is enabled! out filename should have .pdf extension")

	if args.login and args.offline:
		raise Exception("login and offline option can be use at the same time")

	if args.maincss == "default":
		args.maincss = MAIN_DEFAULT_CSS
	elif "://" not in args.maincss and not exists(args.maincss):
		raise Exception(
			"main css is invalid, it looks like local file, but it is not exists")

	for css in args.css:
		if "://" not in css and not exists(css):
			raise Exception(
				"css({0}) is invalid, it looks like local file, but it is not exists".\
				format(css))

def create_render_option(args, css):
	""" create render_option for renderer """
	render_option = {
		"grip": {
			"render_offline": args.offline,
			"username": None,
			"password": None
		},
		"embed_img": args.embed,
		"pdf": args.pdf,
		"css": css
	}
	login_info = {
		"username": None,
		"password": None
	}

	def login():
		""" login callback """
		# prepare login option
		if not login_info["username"]:
			username = input("Github username: ")
			password = getpass("Github password: ")
			login_info["username"] = username
			login_info["password"] = password
		return login_info

	if args.login:
		render_option["login"] = login

	return render_option

def main(parser=None):
	"""
	cli main function
	"""
	if not parser:
		parser = create_argparser()
	args = parser.parse_args()
	validate_args(args)
	css = [args.maincss] + args.css

	render_option = create_render_option(args, css)
	full_article_str, assets, cache_root = render(args.repo_root, args.entry, render_option)
	copy_assets(args, assets)

	if args.pdf == "disable":
		out_content = full_article_str.encode("utf-8")
	elif args.pdf == "pdfkit":
		pdf_option, pdf_kwargs = create_pdfkit_option(args, cache_root, css)

		out_content = from_string(
			full_article_str,
			False,
			options=pdf_option,
			**pdf_kwargs)

	if args.out == "-":
		out = stdout
	else:
		out = open(args.out, "wb")

	out.write(out_content)

	if out is not stdout:
		out.close()

def render(root, entry, option):
	""" render html """
	renderer = Renderer(root, entry, option)
	full_article, assets = renderer.render_all()

	return full_article.prettify(), assets, renderer.cache_root

def copy_assets(args, assets):
	""" copy assets to outdir """
	if not args.embed:
		outdir = dirname(args.out)
		for asset in assets:
			out_asset = join(outdir, relpath(asset, args.repo_root))
			copy2(asset, out_asset)

def create_pdfkit_option(args, cache_root, css):
	""" create pdfkit option and needed files - css, cover """
	pdf_kwargs = {
	}
	pdf_option = {
		# "page-size": "A4",
		"disable-javascript": "",
		# fxxk... must set width & height in px...
		"page-width": "595px",
		"page-height": "842px",
		"margin-top": "52px",
		"margin-left": "52px",
		"margin-bottom": "52px",
		"margin-right": "52px"
	}
	if css:
		merged_css = join(cache_root, "css.css")
		with open(merged_css, "w") as css_file:
			for _css in css:
				if _css.startswith("http"):
					css_file.write(requests.get(_css).text)
				else:
					with open(_css, "r") as other_css:
						css_file.write(other_css.read())
				css_file.write(linesep)
		pdf_kwargs["css"] = merged_css
	if args.cover:
		if splitext(args.cover)[1] not in (".html", ".htm"):
			generated_cover = join(cache_root, "__cover.html")
			with open(generated_cover, "w") as cover_file:
				img = embed_image(getcwd(), args.cover)
				cover_file.write("""<html>
<head><title>cover</title></head>
<body style="margin:0;padding:0;">
<img src="{src}" alt="{alt}" width="595"/>
</body>
</html>""".format(**img))
		pdf_kwargs["cover"] = generated_cover
		pdf_kwargs["cover_first"] = True

	return pdf_option, pdf_kwargs
