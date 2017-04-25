"""
main for running grip-one
"""
from os.path import dirname, abspath
import sys

if __name__ == '__main__':
	LIB_DIR = dirname(dirname(abspath(__file__)))
	sys.path.insert(1, LIB_DIR)
	from grip_one.cli import main
	main()
