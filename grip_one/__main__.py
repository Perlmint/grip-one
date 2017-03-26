import os
import sys

if __name__ == '__main__':
	sys.path.insert(1, os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
	from grip_one.cli import main
	main()
