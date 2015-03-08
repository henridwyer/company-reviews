# Company Reviews by Employees

Scrape Indeed for all recent jobs listings matching given keywords, and then scrape Indeed and Glassdoor the reviews of the companies offering jobs.

Plot the ratings, and use topic modeling on the reviews to understand how employees see their company. Visualize the topics.

Written in python by Henri Dwyer.

## Getting Started

Two ipython notebooks show how to use the library for scraping and plotting the ratings. Run them locally or see them hosted:

- [Scraping.ipynb](http://henri.io/posts/scraping.html)
- [Ratings.ipynb](http://henri.io/posts/ratings.html)

## Topic Modeling

For topic modeling, you can use a Hierarchical Dirichlet Process. I modified the library written by Chong Wang and David Blei in C++:
- [Modified HDP](https://github.com/henridwyer/hdp)

This ipython notebook shows how to prepare the data for use with the HDP library, and how to explore the topics form the results.

- [Topic Modeling.ipynb](http://henri.io/posts/topic-modeling.html)

## Further reading

An example: [Data science jobs in New York](http://henri.io/posts/choosing-a-job-data-science-new-york.html)
