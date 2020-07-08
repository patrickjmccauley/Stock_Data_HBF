import requests, json, time, os, sys, ftplib
import alpha_vantage
from datetime import date, datetime, timezone, timedelta
import datetime as dt


DEBUG_MODE = False

def query_alpha_vantage(av_symbol, API_KEY):
	""" This will query the Alpha Vantage api for the Global Quote feed of a specific
    stock symbol. This will return an HTTP request response

    Official documentation here: https://www.alphavantage.co/documentation/
	"""
	log("Querying for {}".format(av_symbol))
	while True:
		url = "https://www.alphavantage.co/query"
		data = {
			"function": "GLOBAL_QUOTE",
			"symbol": av_symbol,
			"apikey": API_KEY
		}
		r = requests.get(url, params=data)
		log("Response: {}: {}".format(r.status_code, r.reason))
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
					log("Waiting 60 seconds due to rate limit")
					time.sleep(60)
					continue
		else:
			log('Error parsing {}\t{}: {}'.format(av_symbol, r.status_code, r.reason))
			return None


def parse_av_response(r):
	""" This will parse through the request passed back from the Global Quote api endpoint.
	It will return a dictionary object
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
		log("Error trying to parse alpha vantage response: {}".format(r), e)
		return None


def query_yahoo_finance(symbol):
	""" This function will scrape the yahoo finance page for the shares outstanding, which
	will be used to calculate market cap
	"""
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
	""" Simple helper to calculate the market cap and shares outstanding
	"""
	try:
		contents["shares_outstanding"] = query_yahoo_finance(symbol)
		contents["market_cap"] = contents["price"] * contents["shares_outstanding"]
	except Exception as e:
		log("Error trying to populate market cap for {}".format(symbol), e)
		contents["shares_outstanding"] = 0
		contents["market_cap"] = 0


def generate_html(tickers_json, css_file):
	""" This function will populate the HTML file for display
	"""
	log("Generating HTML")
	down_facing_triangle = "&#x25bc"
	up_facing_triangle = "&#x25b2"
	side_facing_triangle = "&#x25BA"

	output = """
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
			change_color = "gray"

		this_ticker = """
			<span class="tickerSymbol">{}</span>&nbsp;&nbsp;\n\t\t\
			<span class="tickerValue"> ${:.2f}</span>&nbsp;&nbsp;\n\t\t\
			<span class="tickerPercent {}">{:.3%}</span>&nbsp;\n\t\t\
			<span class="tickerDirection {}">{}</span>\n\t\t
			""".format(symbol, price, change_color, change_from_open_percent, change_color, direction)
		output += "<div class=\"ticker__item\">{}</div>".format(this_ticker)

	output += """	</div>
				</div>
		"""
	log("HTML created")
	return output


def validate_time(now):

	year, month, day = now.year, now.month, now.day
	delta = dt.timedelta(days=0)

	# Saturday, skip to Monday
	if now.weekday() == 6:
		delta = dt.timedelta(days=2)
	# Sunday, skip to Monday
	elif now.weekday() == 7:
		delta = dt.timedelta(days=1)
	elif now.hour > 16:
		# Friday afternoon, skip to Monday
		if now.weekday() == 5:
			delta = dt.timedelta(days=3)
		# All other weekday afternoons
		else:
			delta = dt.timedelta(days=1)
	
	future = now + delta
	year, month, day = future.year, future.month, future.day
	then = datetime(year=year, month=month, day=day, hour=9, minute=30)
	time_diff = then - now
	return max(time_diff.days * (24 * 60 * 60) + time_diff.seconds, 0)


def log(msg, err=None):
	""" Log locally to a file with message and optional error inclusion 
	"""
 	
	now = datetime.now
	tz = timezone(-timedelta(hours=4))
	time = now(tz=tz).strftime("%Y-%m-%d %H:%M:%S %Z")

	to_write = '{} > {}\n'.format(time, msg)
	if DEBUG_MODE:
		print(to_write)
	f = open('./log.txt', 'a+')
	f.write(to_write)
	f.close()

def upload():
	session = ftplib.FTP(os.environ['FTP_HOST'], os.environ['FTP_USER'], os.environ['FTP_PASS'])
	file = open('data.html','rb')
	session.storbinary('STOR public_html/dwd-ticker/data.html', file)
	file.close()
	session.quit()

def main():
	# File naming variables
	filename_prefix = "data" if len(sys.argv) == 1 else sys.argv[1]
	log("Beginning run using '{}' prefix".format(filename_prefix))
	storage_file = "{}.json".format(filename_prefix)
	css_file = "{}.css".format(filename_prefix)
	html_file = "{}.html".format(filename_prefix)
	input_file = "{}.csv".format(filename_prefix)

	# Infinite loop for calculations. This will rest when rate limit is hit,
	# or if it's not a valid trading time (markets are closed for weekend,
	# afternoon, etc.)
	while True:

		# Sleep until next trading day
		# sec_until_next_trading_day = validate_time(datetime.now())
		# print("Sleeping for {} second(s)".format(sec_until_next_trading_day))
		# time.sleep(sec_until_next_trading_day)

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
			log("Error trying to read in the current data.", e)
			current_data = {}

		# Query all stocks for relevant data
		f = open(storage_file, "w+")
		API_KEY = os.environ['AV_API_KEY']
		for i in range(len(contents)):
			symbol = contents[i]
			data = parse_av_response(query_alpha_vantage(symbol, API_KEY))
			if data is None:
				continue
			else:
				current_data[symbol] = data
				populate_market_cap(symbol, current_data[symbol])
		if len(current_data) != 0:
			f.write(json.dumps(current_data, indent=2))
		f.close()

		# Generate the HTML file
		f = open(html_file, 'w+')
		f.write(generate_html(current_data, css_file))
		f.close()

		upload()

		# Sleep for 15 minutes, then repeat
		time.sleep(15 * 60)

if __name__ == "__main__":
	main()
