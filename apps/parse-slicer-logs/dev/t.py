import apache_log_parser
import sys


parser = apache_log_parser.make_parser("%a %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-Agent}i\"")

print(parser(sys.argv[1]))
