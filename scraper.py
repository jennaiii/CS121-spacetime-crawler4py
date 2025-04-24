import re
from urllib.parse import urlparse, urljoin, urlunparse
from bs4 import BeautifulSoup
from collections import Counter
from collections import defaultdict

stopwords = [
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's",
    "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves"
]


#1.unique urls
unique_urls = set()

#2.longest page
longest_page = ""
longest_page_words = 0

#3.fifty common words
common_words = Counter()

#4.subdomains
subdomains = defaultdict(int)

already_visited = set()
already_seen = set()

min_words = 20
max_words = 10000

def scraper(url, resp):
    links = extract_next_links(url, resp)

    with open("url_log.txt", "a") as f: #write down all valid urls scrapped
        f.write(f'{url}\n')
        for link in links:
            if is_valid(link):
                f.write(f'\t\t{link}\n')

    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    try:
        new_links = set()
        global unique_urls, longest_page, longest_page_words, common_words, subdomains

        #if the page has an error or has no response, skip this page
        if resp.status != 200 or resp.raw_response is None:
            already_visited.add(url)
            return list(new_links)
            
        #parse through html
        soup = BeautifulSoup(resp.raw_response.content, "html.parser")

        #getting all words on page (words is raw words, filtered_words is without stopwords)
        text = soup.get_text()
        words = re.findall(r"\b[a-zA-Z']+\b", text.lower()) #might use tokenizer here ?

        words = [word for word in words if len(word) > 1] #ensure words are at least two characters
        filtered_words = [word for word in words if word.lower() not in stopwords] #filter out stopwords

        #if too little words - low info/value -> skip
        if len(filtered_words) < min_words or len(filtered_words) > max_words:
            already_visited.add(url)
            return list(new_links)

        #canonical url
        url = canonical_url(soup,url)

        if url in already_visited:
            unique_urls.add(url)
            return list(new_links)

        #normalize the url by unfragmenting it, removing trailing /s, and removing www. (easier to compare)
        parsed = urlparse(url)
        parsed = parsed._replace(fragment="") #unfragment the url by parsing it to replace the fragments and then unparsing it
        parsed = parsed._replace(path = urlparse(url).path.rstrip("/")) #trailing / removed
        if parsed.netloc.lower().startswith("www."): #remove www.
                parsed_domain = parsed.netloc[4:]
                parsed = parsed._replace(netloc = parsed_domain)

        #unparsing the url! (it goes back to being a url)
        url = urlunparse(parsed)

        #1. adding it to unique urls
        if url not in unique_urls:
            unique_urls.add(url)

        #2. counting length of words to keep track of longest page
        word_count = len(words)
        if word_count > longest_page_words:
            longest_page_words = word_count
            longest_page = url

        #3. counting the frequency of of words
        word_frequencies = Counter(filtered_words)
        common_words += word_frequencies

        #4. adding url's subdomain to global subdomains dict and then sorting it alphabetically and by decreasing
        subdomain_parts = parsed.netloc.split('.')
        subdomain = '.'.join(subdomain_parts[:-2])
        subdomains[subdomain] += 1
        sorted_subdomains = dict(sorted(subdomains.items(), key=lambda item:(-item[1],item[0])))


        #magic happens: finds all hyperlinks, joins the hyperlinks, normalizes it, and adds it to list of new_links
        for hyperlink in soup.find_all("a", href = True): #loops through all hyperlinks
            hyperlink_url = hyperlink.get("href") #get the hyperlink's url (is an extension or a completely new domain)
            full_url = urljoin(url,hyperlink_url) #joins the hyperlink's url to the current domain (or returns hyperlink_url if it is a completely new domain)
            
            parsed_hyperlink = urlparse(full_url)
            parsed_hyperlink = parsed_hyperlink._replace(fragment="") #unfragment the url by parsing it to replace the fragments and then unparsing it
            parsed_hyperlink = parsed_hyperlink._replace(path = urlparse(full_url).path.rstrip("/")) #trailing / removed
            if parsed_hyperlink.netloc.lower().startswith("www."): #remove www.
                domain = parsed_hyperlink.netloc[4:]
                parsed_hyperlink = parsed_hyperlink._replace(netloc = domain)

            full_url = urlunparse(parsed_hyperlink)
            if full_url != url: #ensure the url is not the same one as it is currently on so we do not circle back
                if full_url not in already_seen: #ensure the url is not already seen (if seen, do not add to queue)
                    already_seen.add(full_url)
                    new_links.add(full_url) #adds to list of links

        #logs everything for the report
        with open('report.txt', 'a') as f:
            f.write(f'Unique URLS: {len(unique_urls)}\n')
            f.write(f'Longest Page: {longest_page}\t{longest_page_words} words\n')
            f.write(f'Fifty Common Words: {common_words.most_common(50)}\n')
            f.write(f'Subdomains: {sorted_subdomains}\n\n')

        already_visited.add(url)
        return list(new_links)
    except Exception as e:
        print(f'Error extracting from {url}\nError: {e}')
        already_visited.add(url) 
        return list(new_links)

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.

    try:
        parsed = urlparse(url)

        if url in already_visited:
            return False
        
        if parsed.scheme not in set(["http", "https"]): #if scheme not http or https
            return False
        
        allowed_domains = [
            "ics.uci.edu", 
            "cs.uci.edu", 
            "informatics.uci.edu",
            "stat.uci.edu", 
            "today.uci.edu"
        ]

        domain = parsed.netloc.lower()
        if not any (domain == d or domain.endswith(f'.{d}') for d in allowed_domains): #if domain not in any of the allowed_domains for the assignment
            return False

        if domain == "today.uci.edu" and not parsed.path.startswith("/department/information_computer_sciences"):
            return False
        
        #paths that are traps/low value
        unallowed_paths = [
            "admin", #administrator info
            "/auth/", #no value - account login
            # "/videos/", #leads to videos
            # "/images/", #leads to images
            # "/attachment/", #leads to files
            # "/raw-attachment/", #leads to files
            # "/image", #leads to image
            # "/img_", #leads to an image
            # "/video", #leads to a video
            # "/photo" #leads to a photo
            "/-/" #gitlab logs (commit, tree, raw, blame, merge_requests) - low value
        ]
        
        if any(p in parsed.path.lower() for p in unallowed_paths):
            return False
        
        #beginning of queries that are traps/low value
        unallowed_queries = [
            "ical=1",
            "filter"
        ] + ["share", "utm_source", "utm_medium", "utm_campaign", "ref", "fbclid", "gclid"]
        # added social sharing keywords as traps; from Claude 3.7 Sonnet -JD

        if any(parsed.query.lower() == q or parsed.query.lower().startswith(q) for q in unallowed_queries):
            return False

        #regex matching for queries
        if (
            re.search(r"[\w-]+(?==)", parsed.query.lower())
            ):
            return False

        #regex matching for paths
        return not (
            re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz"
            + r"|java|py|sql|c|h|dtd|apk|odc|img|mpg|grm|frk|txt|bam)$", parsed.path.lower()) #checking the path
            or re.search(r"/\d{4}-\d{2}-\d{2}", parsed.path.lower())    #avoid calendars - too many dates; do not provide much useful info
            or re.search(r"/\d{2}-\d{2}-\d{2}", parsed.path.lower())
            or re.search(r"/\d{4}-\d{2}", parsed.path.lower())
            or re.search(r"/\d{4}-\d{4}", parsed.path.lower())
            or re.search(r"/\d{2}-\d{2}-\d{4}", parsed.path.lower())
            or re.search(r"/\d{2}-\d{2}-\d{2}", parsed.path.lower())
            or re.search(r"/\d{4}/\d{2}", parsed.path.lower())
            or re.search(r"/\d{4}/\d{2}/\d{2}", parsed.path.lower())
            or re.search(r"/\d{4}", parsed.path.lower())
            or re.search(r"/page/\d+", parsed.path.lower())
            #or re.search(r"^/doku\.php/[^:\s]+:[^/\s]*", parsed.path.lower())
        )

    except TypeError:
        print ("TypeError for ", parsed)
        raise

def canonical_url(soup,url):
    # find the canonical url of an url (official url)
    canonical_tag = soup.find("link", rel="canonical")
    if canonical_tag and canonical_tag.get("href"):
        return canonical_tag["href"]
    return url

