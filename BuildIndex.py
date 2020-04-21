import requests, json, time, os, sys
import alpha_vantage
from datetime import date, datetime

def query_alpha_vantage(av_function, av_symbol, API_KEY):
	"""
	"""
	while True:
		url = "https://www.alphavantage.co/query"
		data = {
			"function": av_function,
			"symbol": av_symbol,
			"apikey": API_KEY
		}
		r = requests.get(url, params=data)
		if r.status_code == 200:
			if 'Global Quote' in json.loads(r.content).keys():
				print('{}\t{}: {}'.format(av_symbol, r.status_code, r.reason))
				return r
			else:
				content = json.loads(r.content)
				if 'Error Message' in content.keys():
					print('{}\t{}: {}\tError on request: {}'.format(av_symbol, r.status_code, r.reason, content['Error Message']))
					return None
				else:
					print("{}\t{}: Hit rate limit. Sleeping for 60 seconds".format(av_symbol, r.status_code, r.reason))
					time.sleep(60)
					continue
		else:
			print('Error parsing {}\t{}: {}'.format(av_symbol, r.status_code, r.reason))
			return None


def parse_av_response(r):
	"""
	"""
	if r is None:
		return None
	try:
		trading_data = json.loads(r.content)['Global Quote']
		
		output = {
			"price": float(trading_data['05. price']),
			"previous_close": float(trading_data['08. previous close']),
			"high": float(trading_data['03. high']),
			"trading_day": trading_data['07. latest trading day'],
			"low": float(trading_data['04. low']),
			"volume": float(trading_data['06. volume']),
			"open": float(trading_data['02. open']),
			"refresh_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		}
		output["change_from_open"] = output["price"] - output["open"]
		output["change_from_open_percent"] = output["change_from_open"] / output["open"]
		return output
	except Exception as e:
		return None


def query_yahoo_finance(symbol):
	url = 'https://finance.yahoo.com/quote/{}/key-statistics?p={}'.format(symbol, symbol)
	r = requests.get(url)
	content = str(r.content)
	
	# Chop up the response to find the part we're interested in
	i = content.find('Shares Outstanding')
	content = content[i:]
	i = content.find('</td>') + 5
	content = content[i:]
	i = content.find('</td>') - 10
	content = content[i:content.find('</td')]
	i = content.find('>')

	shares_outstanding = content[i + 1:]

	shares, denomination = shares_outstanding[:len(shares_outstanding) - 1], shares_outstanding[-1]
	if denomination == 'M':
		shares_outstanding = float(shares) * 1000000
	elif denomination == 'B':
		shares_outstanding = float(shares) * 1000000000
	else:
		shares_outstanding = -1

	return shares_outstanding


def populate_market_cap(symbol, contents):
	try:
		contents["shares_outstanding"] = query_yahoo_finance(symbol)
		contents["market_cap"] = contents["price"] * contents["shares_outstanding"]
	except Exception as e:
		contents["shares_outstanding"] = 0
		contents["market_cap"] = 0


def generate_html(tickers_json, css_file):
	""" This function will populate the HTML file for display
	"""
	down_facing_triangle = "&#x25bc"
	up_facing_triangle = "&#x25b2"
	side_facing_triangle = "&#x25BA"

	output = """
		<!DOCTYPE html>
			<html>
				<head>
				<style>

				</style>
					<link rel="stylesheet" type="text/css" href="{}">
				</head>
				<body>
					<div class="ticker-wrap">
					<div class="ticker">""".format(css_file)

	# Add the individual stocks
	for symbol in tickers_json:
		symbol_data = tickers_json[symbol]
		price, change_from_open_percent = symbol_data["price"], symbol_data["change_from_open_percent"]

		if change_from_open_percent < 0:
			# Negative change
			direction = down_facing_triangle
			change_color = "red"
		elif change_from_open_percent > 0:
			# Positive change
			direction = up_facing_triangle
			change_color = "green"
		else:
			# No change
			direction = side_facing_triangle
			change_color = "#1d4891"

		this_ticker = """
			<font color="#1d4891" style="font-family:arial"><b>{}</b></font>&nbsp;&nbsp;\n\t\t\
			<font color="#1d4891" style="font-family:arial-narrow"> ${:.2f}&nbsp;&nbsp;\n\t\t\
			<font color={}>{:.3%}&nbsp;\n\t\t\
			<font color={}>{}\n\t\t
			""".format(symbol, price, change_color, change_from_open_percent, change_color, direction)
		output += "<div class=\"ticker__item\">{}</div>".format(this_ticker)

	output += """	</div>
					</div>
				</body>
			</html>
		"""

	return output


def main():
	# File naming variables
	filename_prefix = "data" if len(sys.argv) == 1 else sys.argv[1]
	storage_file = "{}.json".format(filename_prefix)
	css_file = "{}.css".format(filename_prefix)
	html_file = "{}.html".format(filename_prefix)
	input_file = "{}.csv".format(filename_prefix)

	# Read in the stock symbols from the provided csv
	f = open(input_file, "r")
	contents = f.read().split(",")
	f.close()

	# Create the dictionary to contain the stock information
	try:
		f = open(storage_file, "r")
		current_data = json.loads(f.read())
		f.close
	except Exception as e:
		current_data = {}

	# Query all stocks for relevant data
	f = open(storage_file, "w+")
	API_KEY = os.environ['AV_API_KEY']
	for i in range(len(contents)):
		symbol = contents[i]
		data = parse_av_response(query_alpha_vantage("GLOBAL_QUOTE", symbol, API_KEY))
		if data is None:
			continue
		else:
			current_data[symbol] = data
			populate_market_cap(symbol, current_data[symbol])
	f.write(json.dumps(current_data, indent=2))
	f.close()

	# Generate the HTML file
	f = open(html_file, 'w+')
	f.write(generate_html(current_data, css_file))
	f.close()


if __name__ == "__main__":
	main()