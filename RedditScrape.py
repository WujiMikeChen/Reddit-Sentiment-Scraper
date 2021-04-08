import json
import operator
import os
import praw
import pandas as pd
import time
from datetime import datetime, date
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from operator import itemgetter
import csv

"""
This program will go through the subreddits listed and count the number of times
a stock is mentioned. 

Planned: 
-user interface (can select inputs) and saves them 
-line graph of interest in stock vs stock price (2)
-implement better sentiment scoring system
-can determine the % increase in interest in a stock based on past saved scrapes
-identify botting to figure out what narrative they're pushing (different program)

problems: stock recognition algorithm is bad, stocks not listed on nasdaq 
which are gaining traction because when they eventually go public they 
are projected to spike (ex: ALPP). People may say "GameStop stock" 
instead of "GME". No image recognition
"""


def setup(file):
    with open(file) as log:
        logi = log.readlines()
    for i in range(len(logi)):
        logi[i] = logi[i].strip()
    return logi


def get_stocks(filelist):
    with open('symbol_1500.json') as f:
        daa = json.load(f)
    list_w = daa
    for filename in filelist:
        df = pd.read_csv(filename, usecols=["Symbol"])
        list_w.extend(df.Symbol.tolist())
    return list_w


pos_cont = setup("positive-words.txt")
neg_cont = setup("negative-words.txt")
contents = setup("removewords.txt")
list_w1 = get_stocks(["nasdaq_screener_1612847323695.csv", "NYSE_20210319.csv"])
login = setup(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "Credentials",
                 "login.txt"))

# Don't give this out to people, keep it private
reddit = praw.Reddit(
    client_id=login[0],
    client_secret=login[1],
    user_agent=login[2]
)


class Stock:
    """
    name: the name of the stock
    mentions: the number of times the stock is mentioned
    positive: the amount of posts which have a positive sentiment
    negative: the number of posts which have a negative sentiment
    """

    def __init__(self, name):
        self.name = name
        self.mentions = 0
        self.positive = 0
        self.negative = 0


class Data:
    """
    portfolio: A list of the Stocks
    subreddit_list: A list of the subreddits that will be scraped
    hot_limit: The number of posts in hot which will be scraped
    new_limit: The number of posts in new which will be scraped
    comment_limit: The number of comments in each post which will be scraped
    WARNING: Setting comment_limit to anything other than 0 results in very slow
    runtimes, only use for a deep scrape or if your computer is fast.
    """

    def __init__(self, subreddit_list, hot_limit, new_limit, comment_limit):
        self.portfolio = []
        self.subreddit_list = subreddit_list
        self.hot_limit = hot_limit
        self.new_limit = new_limit
        self.comment_limit = comment_limit

    def master_sort(self):
        """
        Passes in all the subreddits to the sorts
        :return: None
        """
        for subs in self.subreddit_list:
            self.new_sort(subs)
            self.hot_sort(subs)

    def data_create(self):
        """
        generates a csv file and a bar graph of the data in the class
        :return: None
        """
        self.create_datafile()
        self.generate_graph()

    def hot_sort(self, sub):
        """
        Finds the mentions of stocks in a subreddit up to the
        limit passed in hot
        :param: The name of the subreddit (string)
        :return: None
        """
        count = 0
        for submission in reddit.subreddit(sub).hot():
            if not submission.stickied and count <= self.hot_limit:
                self.find_stock(self.return_post(submission))
                count += 1
            if count >= self.hot_limit:
                break

    def new_sort(self, sub):
        """
        Finds the mentions of stocks in a subreddit up
        to the limit passed in new
        :return: None
        """
        count = 0
        for submission in reddit.subreddit(sub).new():
            if not submission.stickied and count <= self.new_limit:
                self.find_stock(self.return_post(submission))
                count += 1
            if count >= self.new_limit:
                break

    def return_post(self, submission):
        """
        Returns all the words inside the post
        :param submission: the post
        :return: string, the post contents
        """
        if self.comment_limit == 0:
            return submission.title.split() + submission.selftext.split()
        top_level_comments = ""
        submission.comments.replace_more(limit=0)
        for top_level_comment in submission.comments[:self.comment_limit]:
            top_level_comments += top_level_comment.body
        return submission.title.split() + submission.selftext.split() \
               + top_level_comments.split()

    def find_stock(self, wordlist):
        """
        Finds the mentions of a stock in a list of words and the sentiment value
        :param wordlist: list[string]
        :return: None
        """
        new_mentions = set()
        sentiment = 0
        for word in wordlist:
            n_word = remove_special(word)
            new_mentions.add(self.add_stock(n_word, new_mentions))
            sentiment += check_sentiments(word.lower())
        self.add_values(new_mentions, sentiment)

    def add_values(self, new_mentions, sentiment):
        """
        Increments the mentions value of the stocks mentioned and records
        sentiment
        :param new_mentions: List[String]
        :param sentiment: Int
        :return: None
        """
        for stonk in self.portfolio:
            if stonk.name in new_mentions:
                stonk.mentions += 1
                if sentiment > 0:
                    stonk.positive += 1
                elif sentiment < 0:
                    stonk.negative += 1

    def add_stock(self, n_word, new_mentions):
        """
        Checks to see if the word passes through all the conditions to be
        considered a stock as well as if it's a new
        :param n_word: string
        :param new_mentions: List[string]
        :return: string or None
        """
        if (2 <= len(n_word) <= 6) and n_word.isupper() and word_in_file(
                n_word) and n_word not in new_mentions:
            if n_word not in (nam.name for nam in self.portfolio):
                self.portfolio.append(Stock(n_word))
            return n_word
        return None

    def order_descending(self):
        """
        takes the list mentions and returns an ordered list
        :param: Data.portfolio
        :return: list
        """
        self.portfolio.sort(key=operator.attrgetter('mentions'),
                            reverse=True)
        return self.portfolio

    def generate_graph(self):
        """
        graphs the 10 most mentioned stocks
        :return: plot
        """
        stock_name = []
        mention = []
        pos = []
        neg = []
        new_store = self.order_descending()
        for stok in new_store[0:10]:
            stock_name.append(stok.name)
            mention.append(stok.mentions)
            pos.append(stok.positive)
            neg.append(stok.negative)

        x = np.arange(len(stock_name))  # the label locations
        width = 0.3  # the width of the bars

        fig, ax = plt.subplots()
        rects1 = ax.bar(x - width, mention, width, label='Mentions')
        rects2 = ax.bar(x, pos, width, label='Positive')
        rects3 = ax.bar(x + width, neg, width, label="Negative")

        ax.set_title(f'Stock Names and their sentiments time: {datetime.now()}')
        ax.set_xticks(x)
        ax.set_xticklabels(stock_name)
        ax.legend()

        def autolabel(rects):
            """Attach a text label above each bar in
            *rects*, displaying its height."""
            for rect in rects:
                height = rect.get_height()
                ax.annotate('{}'.format(height),
                            xy=(
                                rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom')

        autolabel(rects1)
        autolabel(rects2)
        autolabel(rects3)
        fig.tight_layout()
        fold = create_data_folder("ScrapedPlots", "Plots")
        plt.savefig(self.generate_name(fold, "Plot.png"))
        plt.close()

    def create_datafile(self):
        """
        Creates a .csv with all the data inside the class
        :return: None
        """
        filepath = self.generate_name(
            create_data_folder("ScrapedData", "Scraped"), "Data.csv")
        data = self.order_descending()
        with open(filepath, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Stock Name", "Mentions", "Positive", "Negative"])
            for stk in data:
                writer.writerow([stk.name, stk.mentions, stk.positive,
                                 stk.negative])

    def generate_name(self, subdir, name):
        """
        Creates a string which gives the correct path to the directory where
        the file is to be saved
        :param subdir: String, The directory where it will be saved
        :param name: String, The name of the file
        :return: String, the path+the name
        """
        count = 1
        present = datetime.now()
        pres = present.strftime("%H-%M-%S")
        here = os.path.dirname(os.path.realpath(__file__))
        filename = f"{date.today()}-time-{pres}-hot-{self.hot_limit}-new-" \
                   f"{self.new_limit}-comments-{self.comment_limit}-{name}"
        filepath = os.path.join(here, subdir, filename)
        while os.path.exists(filepath):
            if count == 1:
                filepath = filepath[:filepath.index(".")] + f"({count})" + \
                           filepath[filepath.index("."):len(filepath)]
            else:
                filepath = filepath.replace(f"({count - 1})", f"({count})")
            count += 1
        return filepath


def word_in_file(word):
    """
    Checks to see if the word is an actual stock name and isn't in a list of
    excluded words
    :param word:
    :return: True or False
    """
    return word.upper() in list_w1 and word.lower() not in contents


def check_sentiments(word):
    """
    looks at the word and determines if it's positive, negative or neither
    :param word: string
    :return: True,False, or None
    """
    if word in pos_cont:
        return 1
    elif word in neg_cont:
        return -1
    else:
        return 0


def remove_special(word):
    """
    removes all characters which are not alphabetical
    :param word: string
    :return: new_word: string
    """
    new_word = ""
    for char in word:
        if char.isalpha():
            new_word += char
    return new_word


def create_data_folder(folder, name) -> str:
    """
    checks to see if the folder exists, if it does not it creates it
    :param folder: str
    :param name: str
    :return: str
    """
    here = os.path.dirname(os.path.realpath(__file__))
    foldername = f"{date.today()}-{name}"
    filepath = os.path.join(here, folder, foldername)
    if not os.path.exists(filepath):
        os.makedirs(filepath)
    return folder + "\\" + foldername
