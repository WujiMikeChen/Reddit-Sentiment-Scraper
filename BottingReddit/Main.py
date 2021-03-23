from datetime import datetime, date
from RedditScrape import Data
import yahooFinanceScrape as yScrape
import time

"""
This program runs everything
"""
# the list of subreddits which will be scraped
list_of_subreddits = ["wallstreetbets", "investing", "stocks",
                      "wallstreetbetsOGs"]
# the number of posts in hot which will be scraped on each subreddit
num_hot = 20
# the number of posts in new which will be scraped on each subreddit
num_new = 50
# the number of comments sorted by best which will be scraped on each post
num_comments = 20
# the amount of seconds which the program will wait before scraping again
cycle = 1800
while True:
    def master(subnames, hot_lim, new_lim, com_lim) -> None:
        """
        The function which initializes the other functions
        :param subnames: the list of subreddits which will be scraped
        :param hot_lim: int
        :param new_lim: int
        :param com_lim: int
        :return: None
        """
        Goes_Up = Data(subnames, hot_lim, new_lim, com_lim)
        Goes_Up.master_sort()
        Goes_Up.data_create()
        yScrape.create_stock_csv()


    if __name__ == '__main__':
        # checks runtime
        start_time = time.time()
        master(list_of_subreddits, num_hot, num_new, num_comments)
        print("--- %s seconds ---" % (time.time() - start_time))
        # how often the program will scrape in seconds
        time.sleep(cycle)
