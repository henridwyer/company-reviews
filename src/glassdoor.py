import re
from datetime import datetime
import requests
from lxml import html
import traceback
import sys

# Glassdoor doesn't accept get requests without a header.
header = {"User-Agent":"Mozilla/5.0 Gecko/20100101 Firefox/33.0"}
base_url = 'http://www.glassdoor.com'

def search_company(company):
    search_url = base_url + '/Reviews/' + company.replace(' ','-') + '-reviews-SRCH_KE0,' + str(len(company)) +'.htm'
    return html.fromstring(requests.get(search_url, headers=header).text)

# go to the first company choice.
def company_url(tree):
    url = False

    # Case 1 - none found
    if tree.xpath('string(.)').find("Try more general keywords ('engineer' rather than 'systems engineer')") > -1:
        print "No companies found"

    # Case 2 - Several companies found
    elif re.search(r"Showing \d+.* of \d+ Companies", tree.xpath('string(//div[@id="ReviewSearchResults"]//header)')):
#         string = tree.xpath('string(//div[@id="ReviewSearchResults"]//header)')
        print "Several results"
        url = parse_xpath(tree.xpath('//div[@id="SearchResult_1"]//div[@class="companyLinks"]/a[text()="Reviews"]/@href'))

    # Otherwise already redirected to the right company page
    else:
        url = True

    return url

# Returns the first page that has reviews for the company with the given name
def company_reviews(company):
    tree = search_company(company)
    url = company_url(tree)
    if not url:
        return False
    elif url == True: # only 1 company, need to find review link
        url = parse_xpath(tree.xpath('//a/span[contains(text(),"Reviews")]/../@href'))
    print 'Company review URL:',company,url

    if type(url) == unicode:
        tree = html.fromstring(requests.get(base_url + url, headers=header).text)
    print "Page Title:", tree.xpath('string(//title)')
    return tree


def get_reviews(tree):
#     tree = html.fromstring(review_page_source)
    return tree.xpath('//div[@id="EmployerReviews"]//li[contains(@class, "empReview")]')

def review_rating_stars(review):
    li_elements = review.xpath('.//div[contains(@class,"subRatings")]//li')
    stars = []
    for li in li_elements:
        category = parse_xpath(li.xpath('.//div/text()'))
        rating = parse_xpath(li.xpath('.//span/@title'), float)
        stars.append({'category': category, 'rating': rating})
    return stars

def review_date(review):
    date_str = parse_xpath(review.xpath('.//time/@datetime'))
    try:
      return datetime.strptime(date_str, '%Y-%M-%d')
    except: #can't format string
      return date_str

def employment(review):
    return parse_xpath(review.xpath('.//div[contains(@class,"reviewBodyCell")]/p/text()'))

def review_blocks(review):
    blocks = review.xpath('.//div[contains(@class,"prosConsAdvice")]//div[contains(@class,"cell")]/p')
    return parse_xpath([' '.join(block.xpath('text()')) for block in blocks], unicode, False)

def review_outlook(review):
    return parse_xpath(review.xpath('.//div[contains(@class,"outlookEmpReview")]//div[contains(@class,"cell")]//i/following-sibling::span/text()'), unicode, False)

def employment_status_role(review):
    return parse_xpath(review.xpath('.//span[contains(@class,"authorInfo")]/span[contains(@class,"authorJobTitle")]//text()'), unicode, False)

def location(review):
    return parse_xpath(review.xpath('.//span[contains(@class,"authorInfo")]/span[contains(@class,"authorLocation")]//text()'))

def parse_review(review):
    status_role = employment_status_role(review)
    return {
        'rating stars': review_rating_stars(review), 'date': review_date(review),
        'employment': employment(review), 'blocks': review_blocks(review),
        'outlook': review_outlook(review), 'employment_status':status_role[0],
        'role': status_role[1], 'location':location(review),
    }

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

def get_all_reviews(tree, company, reviews_db, max_pages = 100):
  for i in range(max_pages):
        reviews_divs = get_reviews(tree)

        for review in reviews_divs:
            p_r = parse_review(review)
            p_r["company"] = company
            reviews_db.insert(p_r)

        next_page = tree.xpath('//div[contains(@class, "pagingControls")]//li[contains(@class,"next")]/a/@href')

        if len(next_page) == 0:
            print "No more pages", i
            break
        else: next_page = base_url + parse_xpath(next_page)
        tree = html.fromstring(requests.get(next_page, headers = header).text)

def get_all_company_reviews(companies_list, reviews_db , max_pages = 100):
    visited_companies = []
    failed_companies = []

    for company in companies_list:
        if company in visited_companies: continue
        try:
            tree = company_reviews(company)

            # sometimes stripping the last words from the company name helps
            nb_words = len(company.split(' '))
            if not tree and nb_words >= 2:
              print "1 split " + company
              tree = company_reviews(company.rsplit(' ', 1)[0])
              if not tree and nb_words >= 3:
                print "2 splits " + company
                tree = company_reviews(company.rsplit(' ', 2)[0])
            if '/' in company and not tree:
              # sometimes you can split the name that has a slash
              company_slash = company.replace('/',' ')
              print "Slash replaced " + company_slash
              tree = company_reviews(company_slash)
            if not tree:
              # sometimes adding a space before capital letters helps
              spaces_company = re.sub(r"(\w)([A-Z])", r"\1 \2", company)
              print "spaces " + spaces_company
              tree = company_reviews(spaces_company)

            if tree:
                get_all_reviews(tree, company, reviews_db, max_pages)
                visited_companies.append(company)
            else:
                print "No Tree", company
                failed_companies.append(company)
        except:
            print "Something failed", company
            failed_companies.append(company)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
            continue

    return visited_companies, failed_companies
