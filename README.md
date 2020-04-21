# Simple script to populate a scrolling stock ticker of pre-defined companies relevant to Hepatitis B research

### To run

The script can run constantly in the background using `python3 BuildIndex.py &` (command may vary on system). It will generate an HTML file but can be modified to return a div element to be embedded.

### Optional arguments

You can optionally pass in an argument, which can be useful for testing. The argument will change the output files such that they all start with that argument. Note that a new CSS file will need to be provided adhering to this naming convention.

** Example: Passing in a small subset of stock symbols so that you can avoid the rate limit on the API**
`python3 BuildIndex.py data_small`

This would require a `data_small.css` file
