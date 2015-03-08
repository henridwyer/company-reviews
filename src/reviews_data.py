from nltk.stem.porter import PorterStemmer
from nltk.tokenize import sent_tokenize, word_tokenize
import re
from pymongo import MongoClient


# Different ways to get the reviews and ratings information

def get_separate_reviews_indeed(indeed_reviews_db):
    reviews = []
    for p in indeed_reviews_db.find({}, {"company":1,"review_text":1, "review_pros":1, "review_cons":1, "review_title":1}):
        text = p["review_text"]
        pros = p["review_pros"]
        cons = p["review_cons"]
        title = p["review_title"]
        if text: reviews.append(text)
        if pros: reviews.append(pros)
        if cons: reviews.append(cons)
        #if title: reviews.append(title) # The titles are generally too short on their own
    return reviews

def get_combined_reviews_indeed(indeed_reviews_db):
    combined = []
    for p in indeed_reviews_db.find({}, {"company":1,"review_text":1, "review_pros":1, "review_cons":1, "review_title":1}):
        text = p["review_text"]
        pros = p["review_pros"]
        cons = p["review_cons"]
        title = p["review_title"]
        total = ' '.join([title, text, pros, cons])
        if total: combined.append(total)
    return combined

def get_combined_reviews_glassdoor(glassdoor_reviews_db):
    combined = []
    for p in glassdoor_reviews_db.find({}, {"blocks":1}):
        blocks = p["blocks"]
        if not blocks: continue
        total = ' '.join(blocks)
        combined.append(total)
    return combined

def get_separate_reviews_glassdoor(glassdoor_reviews_db):
    reviews = []
    for p in glassdoor_reviews_db.find({}, {"blocks":1}):
        blocks = p["blocks"]
        if not blocks: continue
        for block in blocks:
            if block: reviews.append(block)
    return reviews

def get_separate_reviews(indeed_reviews_db, glassdoor_reviews_db):
    separate_indeed = get_separate_reviews_indeed(indeed_reviews_db)
    separate_glassdoor = get_separate_reviews_glassdoor(glassdoor_reviews_db)
    separate = separate_indeed + separate_glassdoor
    return separate

def get_combined_reviews(indeed_reviews_db, glassdoor_reviews_db):
    combined_indeed = get_combined_reviews_indeed(indeed_reviews_db)
    combined_glassdoor = get_combined_reviews_glassdoor(glassdoor_reviews_db)
    combined = combined_indeed + combined_glassdoor
    return combined

def get_stemmed_combined_reviews(indeed_reviews_db, glassdoor_reviews_db):
    combined = get_combined_reviews(indeed_reviews_db, glassdoor_reviews_db)

    stemmer = PorterStemmer()
    stemmed_reviews = []
    for review in combined:
        stemmed_reviews.append(' '.join([stemmer.stem(word) for sent in sent_tokenize(review) for word in word_tokenize(sent.lower())]))

    return stemmed_reviews

def get_stemmed_separate(indeed_reviews_db, glassdoor_reviews_db):
    separate = get_separate_reviews(indeed_reviews_db, glassdoor_reviews_db)
    stemmer = PorterStemmer()
    stemmed_reviews = []
    for review in separate:
        stemmed_reviews.append(' '.join([stemmer.stem(word) for sent in sent_tokenize(review) for word in word_tokenize(sent.lower())]))
    return stemmed_reviews

def get_combined_lower(indeed_reviews_db, glassdoor_reviews_db):
    combined = get_combined_reviews(indeed_reviews_db,glassdoor_reviews_db)
    combined_lower = []
    for review in combined:
        combined_lower.append(review.lower())#' '.join([word for sent in sent_tokenize(review) for word in word_tokenize(sent.lower())]))
    return combined_lower


# Make the ratings keys standard
rating_indeed_map = {'Compensation/Benefits':'Compensation and Benefits', 'Job Culture': 'Culture and Values',
                     'Job Security/Advancement': 'Career Opportunities', 'Management':'Management',
                     'Job Work/Life Balance': 'Work and Life Balance'}
def indeed_ratings(indeed_reviews_db):
    ratings = []
    for review in indeed_reviews_db.find({}, {"company":1,"rating":1,"stars":1}):
        this_rating = {}
        company = review["company"]
        rating = review["rating"]
        stars = review["stars"]
        if company: this_rating["company"] = company
        else:
            print "No Company!"
            raise
        if stars:
            for key in stars:
                this_rating[rating_indeed_map[key]] = stars[key]
        if rating: this_rating["rating"] = rating

        ratings.append(this_rating)
    return ratings

rating_glassdoor_map = {'Comp & Benefits':'Compensation and Benefits', 'Culture & Values': 'Culture and Values',
                     'Career Opportunities': 'Career Opportunities', 'Senior Management':'Management',
                     'Work/Life Balance':'Work and Life Balance'}
def glassdoor_ratings(glassdoor_reviews_db):
    ratings = []
    for review in glassdoor_reviews_db.find({}, {"company":1,"rating stars":1}):
        this_rating = {}
        company = review["company"]
        stars = review["rating stars"]
        if company: this_rating["company"] = company
        else:
            print "No Company!?!"
            raise
        if stars:
            for star in stars:
                this_rating[rating_glassdoor_map[star['category']]] = star['rating']

        # Glassdoor doesn't have an overall rating but, substitute the average of the other categories
        if len(this_rating)>1: this_rating['rating'] = sum([v for v in this_rating.values() if type(v) == float])/ float(len(this_rating) -1)

        ratings.append(this_rating)
    return ratings

def all_ratings(indeed_reviews_db,glassdoor_reviews_db):
    return indeed_ratings(indeed_reviews_db) + glassdoor_ratings(glassdoor_reviews_db)


word_regex = re.compile(r"(\d*)(\w+)")
def strip_and_split(word):
    try:
        new_words = sum([w.split('/') for w in word.split('.') if w],[])
        regexes = [word_regex.match(word) for word in new_words]
        return [r.group(2) for r in regexes if r and len(r.groups()) == 2]
    except:
        print word
        raise

# doc_indexes are the indices of documents that are kept
def preprocess(reviews, stop, MIN_WORDS):
    docs = []
    doc_indexes = []
    for i,review in enumerate(reviews):
        rev_words = []
        words = [word for sent in sent_tokenize(review) for word in word_tokenize(sent.lower())]
        stripped_words = []
        for word in words:
            new_words = strip_and_split(word) # some words aren't separated correctly or have numbers
            stripped_words += [nw for nw in new_words if nw not in stop]
        if len(stripped_words) < MIN_WORDS: continue
        docs.append(stripped_words)
        doc_indexes.append(i)
    return docs, doc_indexes

def write_ldac(file_name, corpus):
  # lda-c format: [topic] [term_nb]:[count]
  with open(file_name,'w') as out:
      for doc in corpus:
          unique_words = []
          corpus_s = ""
          for word,count in doc:
              corpus_s += str(word) + ":" + str(count) + " "
              unique_words.append(word)
          corpus_s = str(len(unique_words)) + " " + corpus_s

          out.write(corpus_s.encode("utf-8") + '\n')
