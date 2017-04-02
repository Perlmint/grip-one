from argparse import ArgumentParser
from getpass import getpass
from sys import stdout

from .lib import Renderer

def create_argparser():
	parser = ArgumentParser(description="Make single html page from Markdown repo")
	parser.add_argument("repo_root", help="Repository root to render")
	parser.add_argument("--entry", default="README.md", help="custom entry md file")
	parser.add_argument("--offline", action="store_true", help="use offline mode")
	parser.add_argument("--out", default="-", help="where to out")
	parser.add_argument("--login", action="store_true", help="login github to extend API limit")
	return parser

def main(parser=None):
	if not parser:
		parser = create_argparser()
	args = parser.parse_args()

	render_option = {
		"render_offline": args.offline
	}

	# prepare login option
	if args.login:
		username = input("Github username: ")
		password = getpass("Github password: ")
		render_option["username"] = username
		render_option["password"] = password

	renderer = Renderer(args.repo_root, args.entry, render_option)
	full_article = renderer.render_all()

	if args.out == "-":
		out = stdout
	else:
		out = open(args.out, "w")

	out.write(full_article.prettify())

	if out is not stdout:
		out.close()
