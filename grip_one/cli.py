from argparse import ArgumentParser
from getpass import getpass
from sys import stdout

from .lib import Renderer
from pdfkit import from_string

def create_argparser():
	parser = ArgumentParser(description="Make single html page from Markdown repo")
	parser.add_argument("repo_root", help="Repository root to render")
	parser.add_argument("--entry", default="README.md", help="custom entry md file")
	parser.add_argument("--offline", action="store_true", help="use offline mode")
	parser.add_argument("--out", default="-", help="where to out - available etension is html or pdf")
	parser.add_argument("--login", action="store_true", help="login github to extend API limit")
	parser.add_argument("--embed", action="store_true", help="embed images into html in base64 form")
	parser.add_argument("--pdf", choices=["disable", "pdfkit"], default="disable", help="Select backend to use for making pdf")
	return parser

def main(parser=None):
	if not parser:
		parser = create_argparser()
	args = parser.parse_args()

	render_option = {
		"grip": {
			"render_offline": args.offline
		},
		"embed_img": args.embed,
		"pdf": args.pdf,
	}

	# prepare login option
	if args.login:
		username = input("Github username: ")
		password = getpass("Github password: ")
		render_option["username"] = username
		render_option["password"] = password

	renderer = Renderer(args.repo_root, args.entry, render_option)
	full_article = renderer.render_all()

	full_article_str = full_article.prettify()

	if args.pdf == "disable":
		out_content = full_article_str.encode("utf-8")
	elif args.pdf == "pdfkit":
		out_content = from_string(full_article_str, False)
	else:
		raise Exception("invalid pdf mode")

	if args.out == "-":
		out = stdout
	else:
		out = open(args.out, "wb")

	out.write(out_content)

	if out is not stdout:
		out.close()
