import datetime
import requests
from lxml import html
import re

base_url = "http://www.indeed.com"

def build_url(url, *filters):
    return url + ''.join(["&" + param + "=" + val for param,val in filters])

def build_search_url(keywords, location):
    query = "/jobs?"
    keyword_filter = "q", keywords
    location_filter = "l", location
    date_filter = 'fromage', 'last' # only get the latest postings
    return build_url(base_url + query, keyword_filter, location_filter, date_filter)

def parse_xpath(xpath, type=unicode, unique=True):
    if len(xpath)== 0:
        #print "No elements found by xpath."
        return ''
    if unique and len(xpath) > 1:
        print "xpath expected 1 element, but found:", str(xpath)

    if unique:
        return type(xpath[0])
    else:
        return [type(x) for x in xpath]

def parse_date(job_date):
    hours = re.match(r"(\d+) hours", job_date)
    days = re.match(r"(\d+) days", job_date)
    if hours:
        hours = int(hours.group(1))
    else:
        hours = 0
    if days:
        days = int(days.group(1))
    else:
        days = 0

    job_date_obj = datetime.datetime.today() - datetime.timedelta(days=days, hours=hours)
    return job_date_obj

def parse_job(job):
    job_title = parse_xpath(job.xpath('.//h2[contains(@class,"jobtitle")]/a/@title'))
    job_url = parse_xpath(job.xpath('.//h2[contains(@class,"jobtitle")]/a/@href'))
    job_date = parse_date(parse_xpath(job.xpath('.//span[contains(@class,"date")]/text()')))
    company = parse_xpath(job.xpath('.//span[contains(@class,"company")]//text()'))
    location = parse_xpath(job.xpath('.//span[contains(@class,"location")]//text()'))
    review_url = parse_xpath(job.xpath('.//a[contains(@title,"review") and contains(text(), "reviews")]/@href'))

    return {'job_url':job_url, 'job_title':job_title, 'company':company,
            'location':location, 'review_url':review_url, 'job_date':job_date}

def get_jobs(keywords, location, jobs_db, max_pages=1):

    tree = html.fromstring(requests.get(build_search_url(keywords, location)).text)

    jobs = []
    for i in range(max_pages):
        jobs_divs = tree.xpath('//div[contains(@itemtype,"JobPosting")]')
        for job in jobs_divs:
            p_j = parse_job(job)
            jobs_db.insert(p_j)
            jobs.append(parse_job(job))

        next_page = tree.xpath('//div[contains(@class,"pagination")]//span[contains(text(),"Next")]/../../@href')
        if len(next_page) == 0:
            print "Last page: ", i + 1
            break
        else: next_page = base_url + next_page[0]

        tree = html.fromstring(requests.get(next_page).text)

    return jobs


def get_stars(span_style):
    width_val = re.match(r"width:(\d+\.\d+)", span_style)
    if not width_val:
        print "No width style found"
        return 0
    return int(round(float(width_val.group(1))/17.2))

def review_rating(review):
    overall_rating = parse_xpath(review.xpath('.//span[contains(@class,"rating")]//@title'))
    rating_categories = parse_xpath(review.xpath('.//table[contains(@class,"ratings_expanded")]//text()'), unicode, False)
    expanded_ratings_styles = parse_xpath(review.xpath('.//table[contains(@class,"ratings_expanded")]//span[contains(@class,"rating")]/@style'), unicode,False)
    stars = {key:val for (key,val) in zip(rating_categories, [get_stars(s) for s in expanded_ratings_styles])}
    return overall_rating, stars

def parse_review(review):
    company_name = parse_xpath(review.xpath('//span[@id="company_name"]//text()'))
    overall_rating, stars = review_rating(review)
    job_title = parse_xpath(review.xpath('.//span[contains(@class,"reviewer_job_title")]/span[contains(@class,"reviewer")]/text()'))
    employment_status = parse_xpath(review.xpath('.//span[contains(@class,"reviewer_job_title")]/text()'))
    location = parse_xpath(review.xpath('.//span[contains(@class,"location")]/text()'))
    date = parse_xpath(review.xpath('.//span[contains(@class,"dt")]/text()'))
    date = datetime.datetime.strptime(date, '%B %d, %Y')
    review_title = parse_xpath(review.xpath('.//div[contains(@class,"review_title")]/text()'))
    review_text = unicode(review.xpath('string(.//div[contains(@class,"content")]/div[contains(@class,"description")])'))
    review_pros = unicode(review.xpath('string(.//div[contains(@class,"content")]/div[@class="review_pros"])'))
    review_cons = unicode(review.xpath('string(.//div[contains(@class,"content")]/div[@class="review_cons"])'))

    return {'company':company_name,'rating': overall_rating, 'stars': stars, 'job_title':job_title,
            'employment_status':employment_status, 'location':location,
            'date':date, 'review_title':review_title, 'review_text':review_text,
            'review_pros':review_pros, 'review_cons':review_cons}

def get_all_reviews(review_url, reviews_db, max_pages=100):
    tree = html.fromstring(requests.get(base_url + review_url).text)
    for i in range(max_pages):
        reviews_divs = tree.xpath('//div[contains(@id,"company_review") and contains(@class,"company_review_container")]')

        for review in reviews_divs:
            p_r = parse_review(review)
            reviews_db.insert(p_r)

        next_page = tree.xpath('//div[contains(@id,"pagination")]//span[contains(text(),"Next")]/../@href')
        if len(next_page) == 0:
            print "No more pages", i
            break
        else: next_page = base_url + next_page[0]
        tree = html.fromstring(requests.get(next_page).text)

def get_all_company_reviews(jobs_list, reviews_db, max_pages=100):
  visited_urls = []
  for job in jobs_list:
    url = job["review_url"]
    if not url or url in visited_urls: continue
    get_all_reviews(url, reviews_db, max_pages)
    visited_urls.append(url)
