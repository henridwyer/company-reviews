# Utility functions


# Fixing the company names. You need to manually create the fixing dictionary
def fix_company_name(name, dic, remove_unicode = False):
  if remove_unicode:
    name = name.encode('ascii','ignore')
  if name in dic:
    return dic[name]
  else:
    return name

def fix_all_company_names(reviews_db, dic, remove_unicode = False):
  reviews = reviews_db.find({},{'company':1})
  for review in reviews:
    review_id = review['_id']
    company_name = review['company']
    reviews_db.update({'_id' : review_id},
                      {'$set': {'company':fix_company_name(company_name, dic, remove_unicode)}})

def get_company_names(reviews_db):
  companies = []
  reviews = reviews_db.find({},{'company':1})
  for review in reviews:
    companies.append(review['company'])
  return companies


