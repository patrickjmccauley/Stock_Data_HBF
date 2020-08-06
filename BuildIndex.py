import requests, json, time, os, sys, ftplib
from datetime import date, datetime, timezone, timedelta
import datetime as dt
import traceback

DEBUG_MODE = False
EXISTING_TICKERS = {
    "HBRI": "HBRI - Hepatitis B Research Index",
    "ALT": "ALT - Altimmune, Inc.",
    "ARWR": "ARWR - Arrowhead Pharmaceuticals, Inc.",
    "ABUS": "ABUS - Arbutus Biopharma Corporation",
    "ASMB": "ASMB - Assembly Biosciences, Inc.",
    "BBI": "BBI - Brickell Biotech, Inc.",
    "DRNA": "DRNA - Dicerna Pharmaceuticals, Inc.",
    "DVAX": "DVAX - Dynavax Technologies Corporation",
    "ENTA": "ENTA - Enanta Pharmaceuticals, Inc.",
    "HEPA": "HEPA - Hepion Pharmaceuticals, Inc.",
    "NTLA": "NTLA - Intellia Therapeutics, Inc.",
    "SBPH": "SBPH - Spring Bank Pharmaceuticals, Inc.",
    "VIR": "VIR - Vir Biotechnology, Inc.",
}

def build_index_data(symbol):
    """ This will parse through the request passed back from the Global Quote api endpoint.
    It will return a dictionary object, also leveraging Yahoo Finance web scraping
    """
    log("About to start scraping for {}".format(symbol))
    try:
        if DEBUG_MODE: log("About to scrape yahoo for change")
        change_amt, change_pct = scrape_yahoo_change(symbol)
        log("[{}] Retrieved change amount: {}\tchange percent: {}".format(symbol, change_amt, change_pct))

        if DEBUG_MODE: log("About to scrape yahoo for price")
        price = scrape_yahoo_price(symbol)
        log("[{}] Retrieved price: {}".format(symbol, price))

        if DEBUG_MODE: log("About to scrape yahoo for mkt_cap")
        market_cap = scrape_yahoo_mkt_cap(symbol)
        log("[{}] Retrieved mkt cap: {}".format(symbol, market_cap))

        if DEBUG_MODE: log("About to scrape yahoo for name")
        name = scrape_yahoo_name(symbol)
        log("[{}] Retrieved name: {}".format(symbol, name))
        output = {
            "price": price,
            "refresh_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "market_cap": market_cap,
            "name": name,
            "change_from_open": change_amt,
            "change_from_open_percent": change_pct
        }
        return output
    except Exception as e:
        print(e)
        log("Error trying to scrape data for: {}".format(symbol), e)
        return None


def search_and_discard(str_to_find, str_to_search, keep_all_before=False, additional_spaces=0):
    """ Finds a substring, then returns the remainder of the string after or before that substring,
    plus any additional spaces. If you want to trim spaces, make additional_spaces negative
    """
    i = str_to_search.find(str_to_find)
    if keep_all_before:
        return str_to_search[:i + additional_spaces]
    return str_to_search[i + additional_spaces:]


def scrape_yahoo_change(symbol):
    """ This function will scrape the Yahoo finance page and return a tuple of
    (change amount, change percentage)
    """
    url = "https://finance.yahoo.com/quote/{}?p={}".format(symbol, symbol)
    r = requests.get(url)
    content = str(r.content)

    content = search_and_discard('quote-header-info', content)
    content = search_and_discard('data-reactid="51"', content, additional_spaces=len('data-reactid="51"') + 1)
    content = search_and_discard('<', content, keep_all_before=True)

    split_str = content.split(' ')
    split_str[1] = split_str[1].replace('(', '')
    split_str[1] = split_str[1].replace(')', '')
    return float(split_str[0]), float(split_str[1][:-1]) / 100


def scrape_yahoo_price(symbol):
    """ This function will scrape the yahoo finance page for the price
    """
    url = "https://finance.yahoo.com/quote/{}?p={}".format(symbol, symbol)
    r = requests.get(url)
    content = str(r.content)

    content = search_and_discard('quote-header-info', content)
    content = search_and_discard('data-reactid="50"', content, additional_spaces=len('data-reactid="50"')+1)
    content = search_and_discard('<', content, keep_all_before=True)
    return float(content)


def scrape_yahoo_mkt_cap(symbol):
    """ This function will scrape the yahoo finance page for the market cap of the company
    """
    url = "https://finance.yahoo.com/quote/{}?p={}".format(symbol, symbol)
    r = requests.get(url)
    content = str(r.content)

    multipliers = {
        'T': 1000000000000,
        'B': 1000000000,
        'M': 1000000,
        'K': 1000,
    }

    to_find = '<div id="Main" role="content"'

    content = search_and_discard(to_find, content)
    content = search_and_discard('data-reactid="139"', content, additional_spaces=len('data-reactid="139"')+1)
    content = search_and_discard('<', content, keep_all_before=True)
    mkt_cap = float(content.strip()[:-1])
    mkt_cap_multiplier = content.strip()[-1]
    return mkt_cap * multipliers[mkt_cap_multiplier]



def scrape_yahoo_name(symbol):
    """ This function will scrape the yahoo finance page for the name of the company
    """
    name = symbol
    if name not in EXISTING_TICKERS.keys():
        url = 'https://finance.yahoo.com/quote/{}/key-statistics?p={}'.format(symbol, symbol)
        r = requests.get(url)
        content = str(r.content)

        content = search_and_discard('quote-header-info', content)
        content = search_and_discard('<h1', content)
        content = search_and_discard('>', content, additional_spaces=1)
        content = search_and_discard('<', content, keep_all_before=True).strip()
        name = content
    else:
        name = EXISTING_TICKERS[symbol]
    return name



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
        name = symbol_data['name']
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
            """.format(name, price, change_color, change_from_open_percent, change_color, direction)
        output += "<div class=\"ticker__item\">{}</div>".format(this_ticker)

    output += """	</div>
                </div>
        """
    log("HTML created")
    return output

def update_index_data(current_data, idx_symbol):
    """ This function is used to build a condensed 'index' value of all the market fluctuations across companies.
    The divisor is arbitrary (see price)
    """
    log("UPDATING THE INDEX DATA... SYMBOL={}".format(idx_symbol))
    current_mkt_cap = 0
    open_mkt_cap = 0
    for symbol in current_data:
        if symbol != idx_symbol:
            cur_mkt_cap = current_data[symbol]['market_cap']
            change_pct = current_data[symbol]['change_from_open_percent']
            op_mkt_cap = cur_mkt_cap - (change_pct * cur_mkt_cap)

            open_mkt_cap += op_mkt_cap
            current_mkt_cap += cur_mkt_cap

    current_data[idx_symbol] = {
        "price": current_mkt_cap / 30000000,
        "open": open_mkt_cap,
        "change_from_open": current_mkt_cap - open_mkt_cap,
        "change_from_open_percent": (current_mkt_cap - open_mkt_cap) / open_mkt_cap,
        "market_cap": current_mkt_cap,
        "name": "{} - Hepatitis B Research Index".format(idx_symbol)
    }

    log("HBRI BELOW")
    log(json.dumps(current_data[idx_symbol], indent=2))


def validate_time(now):
    """ Checks to make sure this is a valid trading time. If not, we'll sleep until
    trading resumes
    """
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
    if err is not None:
        to_write += '{}\n'.format(err)
        to_write += '{}\n'.format(traceback.print_exc())
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
    index_symbol = 'HBRI'

    # Infinite loop for calculations. This will rest when rate limit is hit,
    # or if it's not a valid trading time (markets are closed for weekend,
    # afternoon, etc.)
    while True:

        # Sleep until next trading day
        sec_until_next_trading_day = validate_time(datetime.now())
        print("Sleeping for {} second(s)".format(sec_until_next_trading_day))
        time.sleep(sec_until_next_trading_day)

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
        for i in range(len(contents)):
            symbol = contents[i]
            symbol = symbol.strip()
            symbol = symbol.replace('\n', '')
            if symbol == index_symbol:
                current_data[symbol] = {}
                continue
            data = build_index_data(symbol)
            if data is None:
                continue
            else:
                current_data[symbol] = data

        # Update the overall index value
        update_index_data(current_data, index_symbol)

        # Save this data
        if len(current_data) != 0:
            f.write(json.dumps(current_data, indent=2))
        f.close()

        # Generate the HTML file
        f = open(html_file, 'w+')
        f.write(generate_html(current_data, css_file))
        f.close()

        upload()

        # Sleep for 20 minutes, then repeat
        time.sleep(20 * 60)

if __name__ == "__main__":
    main()
