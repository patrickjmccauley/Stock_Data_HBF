# HBRI Stock Ticker
A simple script to generate a scrolling stock ticker displaying the price fluctuations of companies engaged in Hepatitis-B Virus-related research. The companies are aggregated to generate a market-value-weighted index, the Hepatitis B Research Index (HBRI).

## Installation
The script can be run locally or on a Heroku server. To run locally, comment out the `upload()` call near the bottom of `main()`. This function is required for Heroku deployment, but meaningless in a local environment.

## Usage
```shell script
python3 BuildIndex.py         # Runs the script with default data.csv as input

python3 BuildIndex.py arg1    # Runs the script with optional argument containing 
                              # file prefix. All generated files will adhere to this 
                              # naming convention (arg1.csv, arg1.html, arg1.css).
```
After building the ticker, it will need to be injected into the page in which it is being embedded. That is not addressed here, this simply generates the HTML for use elsewhere.

## Example Output in Use
![embedded_ticker](https://github.com/pmccau/Stock_Data_HBF/blob/master/assets/embedded_ticker.png)

## License
[MIT](https://choosealicense.com/licenses/mit/)